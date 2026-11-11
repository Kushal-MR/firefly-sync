"""The run loop: steps the swarm, talks to the ESP32, measures, draws.

This is the outer layer. It owns the clock; the swarm never sees it.

Two ways to run:
* run_realtime - in step with the wall clock, for the window and for the
  real ESP32, which lives in real time
* run_headless - as fast as the CPU allows, no window, for experiments

Real LEDs join automatically: the first FIRE from a new id (esp32-L1,
esp32-L2, ...) adds that LED to the swarm as an external node, placed in a
small cluster near the middle-left of the floor.
"""
import csv
import math
import random
import time
from collections import deque

from fireflysync import metrics

FLASH_SECONDS = 0.12          # how long a flash stays lit on screen
SAMPLE_EVERY = 0.05           # seconds between sync-level samples
HISTORY_SECONDS = 30
SYNC_THRESHOLD = 0.95         # sync level that counts as "synchronized"
SYNC_HOLD = 2.0               # ...if it stays there this long
IN_SYNC_MS = 30               # a real LED this close to the swarm counts as in sync

LOSS_STEPS = [0.0, 0.1, 0.3, 0.5]
ROGUE_STEPS = [0, 1, 3, 5]
DRIFT_ON = 0.02
SPEED_ON = 0.8


class Session:
    def __init__(self, swarm, dt=0.002, link=None, oneway_delay=None, log_path=None):
        self.swarm = swarm
        self.dt = dt
        self.link = link
        self.oneway_override = oneway_delay            # seconds; None = measure it
        self.exts = {}                                 # LED name -> node index
        self.real_offsets = {}                         # LED name -> recent offsets (ms)
        self.last_fire = {}                            # node -> time of its last flash
        self.history = deque(maxlen=int(HISTORY_SECONDS / SAMPLE_EVERY))
        self.times, self.levels = [], []
        self.paused = False
        self.epoch_start = 0.0                         # start, or the last scenario change
        self.synced_after = None                       # seconds from epoch_start to sync
        self._above_since = None
        self._next_sample = 0.0
        self._next_hello = 0.0
        self._next_ping = 0.0
        self._link_rng = random.Random(f"{id(self)}-linkloss")
        self._targets = set()
        self._targets_key = None
        self._log_file = None
        self._log = None
        if log_path:
            self._log_file = open(log_path, "w", newline="")
            self._log = csv.writer(self._log_file)
            self._log.writerow(["time_s", "node", "kind", "sync_level", "esp32_offset_ms"])

    # ----- real LEDs ----------------------------------------------------------
    @property
    def oneway(self):
        """One-way Wi-Fi delay in seconds: the override, else what PING measured."""
        if self.oneway_override is not None:
            return self.oneway_override
        if self.link is not None and self.link.oneway_ms is not None:
            return self.link.oneway_ms / 1000.0
        return 0.0

    def _led_position(self, k):
        """Small sunflower spiral, left of centre (in the left room if walls go up)."""
        w, h = self.swarm.area
        r, a = 0.6 * math.sqrt(k), k * 2.39996
        return (w / 2 - 1.8 + r * math.cos(a), h / 2 + r * math.sin(a))

    def _ensure_led(self, name):
        if name not in self.exts:
            self.exts[name] = self.swarm.add_external(name, self._led_position(len(self.exts)))
            self.real_offsets[name] = deque(maxlen=10)
        return self.exts[name]

    def _link_targets(self):
        """Virtual drones in radio range of ANY real LED: their flashes go to the ESP32."""
        key = (self.swarm.layout_version, len(self.exts))
        if key != self._targets_key:
            self._targets = {j for e in self.exts.values() for j in self.swarm.neighbours_of(e)
                             if j < self.swarm.n_virtual}
            self._targets_key = key
        return self._targets

    # ----- one tick of the simulation ---------------------------------------
    def _handle_link(self):
        if self.link is None:
            return
        for msg in self.link.poll(self.swarm.time):
            if msg.node_id.startswith("v"):            # one of ours echoed back: ignore
                continue
            idx = self._ensure_led(msg.node_id)
            mean = metrics.circular_mean(self.swarm.healthy_phases)
            off = metrics.offset_ms(mean, self.swarm.period, self.oneway)
            self.real_offsets[msg.node_id].append(off)
            self.swarm.external_fired(idx)
            self._write(self.swarm.time, idx, msg.node_id, off)
        t = self.swarm.time
        if t >= self._next_hello:
            self.link.send_hello()
            self._next_hello = t + 2.0
        if t >= self._next_ping:
            self.link.send_ping()
            self._next_ping = t + 1.0

    def _step(self):
        for ev in self.swarm.step(self.dt):
            self.last_fire[ev.node] = ev.time
            if ev.external:
                continue
            self._write(ev.time, ev.node, "virtual", "")
            if self.link is not None and ev.node in self._link_targets():
                # artificial packet loss applies to the real link too
                if self.swarm.loss and self._link_rng.random() < self.swarm.loss:
                    continue
                self.link.send_fire(f"v{ev.node}")
        if self.swarm.time >= self._next_sample:
            lvl = metrics.order_parameter(self.swarm.healthy_phases)
            self.history.append((self.swarm.time, lvl))
            self.times.append(self.swarm.time)
            self.levels.append(lvl)
            self._next_sample = self.swarm.time + SAMPLE_EVERY
            self._track_sync(lvl)

    def _track_sync(self, lvl):
        t = self.swarm.time
        if lvl >= SYNC_THRESHOLD:
            if self._above_since is None:
                self._above_since = t
            if self.synced_after is None and t - self._above_since >= SYNC_HOLD:
                self.synced_after = self._above_since - self.epoch_start
        else:
            self._above_since = None

    def _restart_sync_clock(self):
        self.epoch_start = self.swarm.time
        self.synced_after = None
        self._above_since = None

    def _write(self, t, node, kind, offset):
        if self._log:
            lvl = self.levels[-1] if self.levels else ""
            self._log.writerow([f"{t:.4f}", node, kind,
                                f"{lvl:.4f}" if lvl != "" else "",
                                f"{offset:.1f}" if offset != "" else ""])

    # ----- scenarios (keys in the window) ------------------------------------
    def scramble(self):
        """Knock every virtual drone out of sync and restart the sync clock."""
        self.swarm.scramble()
        self._restart_sync_clock()

    def apply(self, action):
        """Change a scenario. Returns a short message for the screen, or None.
        Every change restarts the sync clock, so "synced in" shows recovery."""
        sw = self.swarm
        msg = None
        if action == "scramble":
            self.scramble()
            return "Scrambled - watch them re-sync"
        if action == "walls":
            sw.set_walls(not sw.walls_on)
            msg = ("Wall up: two rooms, two rhythms" if sw.walls_on else "Wall removed: one open floor")
        elif action == "door":
            if not sw.walls_on:
                return "Put the wall up first (W)"
            sw.set_door(not sw.door_open)
            msg = "Doorway open: the rooms can hear each other" if sw.door_open else "Doorway closed"
        elif action == "rogue":
            nxt = ROGUE_STEPS[(ROGUE_STEPS.index(len(sw.rogues)) + 1) % len(ROGUE_STEPS)] \
                if len(sw.rogues) in ROGUE_STEPS else 0
            sw.set_rogues(nxt)
            msg = f"{nxt} rogue drone{'s' if nxt != 1 else ''} firing at random" if nxt else "Rogue drones removed"
        elif action == "drift":
            sw.set_drift(0.0 if sw.drift else DRIFT_ON)
            msg = f"Clock drift ±{100 * DRIFT_ON:.0f}%: every clock runs a bit fast or slow" if sw.drift else "Clocks identical again"
        elif action == "move":
            sw.set_speed(0.0 if sw.speed else SPEED_ON)
            msg = f"Drones moving at {SPEED_ON} m/s" if sw.speed else "Drones stopped"
        elif action == "loss":
            nxt = LOSS_STEPS[(LOSS_STEPS.index(sw.loss) + 1) % len(LOSS_STEPS)] if sw.loss in LOSS_STEPS else 0.0
            sw.set_loss(nxt)
            msg = f"{100 * nxt:.0f}% of flashes lost" if nxt else "No packet loss"
        if msg:
            self._restart_sync_clock()
        return msg

    def scenarios(self):
        """(key, name, state text, active) for every scenario, for the panel."""
        sw = self.swarm
        return [
            ("W", "Walls", "two rooms" if sw.walls_on else "off", sw.walls_on),
            ("D", "Doorway", ("open" if sw.door_open else "closed") if sw.walls_on else "-",
             sw.walls_on and sw.door_open),
            ("X", "Rogue drones", str(len(sw.rogues)) if sw.rogues else "off", bool(sw.rogues)),
            ("C", "Clock drift", f"±{100 * sw.drift:.0f}%" if sw.drift else "off", bool(sw.drift)),
            ("M", "Moving drones", f"{sw.speed:g} m/s" if sw.speed else "off", bool(sw.speed)),
            ("P", "Packet loss", f"{100 * sw.loss:.0f}%" if sw.loss else "off", bool(sw.loss)),
        ]

    # ----- runners -----------------------------------------------------------
    def run_headless(self, seconds, report_every=5.0, stop_when_synced=False):
        next_report = report_every
        while self.swarm.time < seconds:
            self._handle_link()
            self._step()
            if stop_when_synced and self.synced_after is not None:
                break
            if self.swarm.time >= next_report:
                print(self.status_line())
                next_report += report_every
        return self.summary()

    def run_realtime(self, view=None, seconds=None):
        wall = time.perf_counter()
        backlog = 0.0
        try:
            while seconds is None or self.swarm.time < seconds:
                now = time.perf_counter()
                backlog = min(backlog + (now - wall), 0.25)   # never try to catch up >0.25 s
                wall = now
                if view is not None:
                    action = view.handle_events()
                    if action == "quit":
                        break
                    if action == "pause":
                        self.paused = not self.paused
                    elif action:
                        msg = self.apply(action)
                        if msg:
                            view.toast(msg)
                if self.paused:
                    backlog = 0.0
                    if self.link:
                        self.link.poll(self.swarm.time)        # drain, ignore
                else:
                    self._handle_link()
                    while backlog >= self.dt:
                        self._step()
                        backlog -= self.dt
                if view is not None:
                    view.draw(self)
                else:
                    time.sleep(0.001)
        finally:
            self.close()
        return self.summary()

    # ----- reporting ---------------------------------------------------------
    def sync_level(self):
        return self.levels[-1] if self.levels else metrics.order_parameter(self.swarm.healthy_phases)

    def rhythms(self):
        return metrics.rhythm_groups(self.swarm.healthy_phases)

    def led_offsets(self):
        """Latest smoothed offset (ms) per real LED that has been heard."""
        out = {}
        for name, d in self.real_offsets.items():
            if d:
                recent = list(d)[-3:]
                out[name] = sum(recent) / len(recent)
        return out

    def esp32_offset(self):
        offs = self.led_offsets()
        return sum(offs.values()) / len(offs) if offs else None

    def leds_in_sync(self):
        offs = self.led_offsets()
        return sum(1 for v in offs.values() if abs(v) < IN_SYNC_MS), len(offs)

    def flash_intensity(self, node, fade=0.35):
        """1.0 at the instant a node fires, fading to 0 over `fade` seconds."""
        t = self.last_fire.get(node)
        if t is None:
            return 0.0
        return max(0.0, 1.0 - (self.swarm.time - t) / fade)

    def is_flashing(self, node):
        t = self.last_fire.get(node)
        return t is not None and self.swarm.time - t < FLASH_SECONDS

    def status_line(self):
        s = f"t={self.swarm.time:6.1f}s  sync={100 * self.sync_level():5.1f}%  rhythms={self.rhythms()}"
        if self.link is not None:
            if not self.exts:
                s += "  esp32: " + ("found, waiting for flashes" if self.link.peer else "searching...")
            else:
                ok, n = self.leds_in_sync()
                s += f"  esp32: {ok}/{n} LEDs in sync, avg {self.esp32_offset():+.1f} ms"
                if self.link.oneway_ms is not None:
                    s += f", one-way {self.link.oneway_ms:.0f} ms"
        return s

    def summary(self):
        tts = metrics.time_to_sync(self.times, self.levels)
        off = self.esp32_offset()
        ok, n = self.leds_in_sync()
        return {
            "seconds": round(self.swarm.time, 2),
            "final_sync_level": round(self.sync_level(), 4),
            "time_to_sync_s": None if tts is None else round(tts, 2),
            "cycles_to_sync": None if tts is None else round(metrics.cycles(tts, self.swarm.period), 1),
            "rhythms": self.rhythms(),
            "esp32_leds_heard": n,
            "esp32_leds_in_sync": ok,
            "esp32_offset_ms": None if off is None else round(off, 1),
            "oneway_ms": None if self.link is None or self.link.oneway_ms is None else round(self.link.oneway_ms, 1),
        }

    def close(self):
        if self._log_file:
            self._log_file.close()
            self._log_file = None
        if self.link:
            self.link.close()

"""The run loop: steps the swarm, talks to the ESP32, measures, draws.

This is the outer layer. It owns the clock; the swarm never sees it.

Two ways to run:
* run_realtime - in step with the wall clock, for the window and for the
  real ESP32, which lives in real time
* run_headless - as fast as the CPU allows, no window, for experiments
"""
import csv
import time
from collections import deque

from fireflysync import metrics

FLASH_SECONDS = 0.12          # how long a flash stays lit on screen
SAMPLE_EVERY = 0.05           # seconds between sync-level samples
HISTORY_SECONDS = 30


class Session:
    def __init__(self, swarm, dt=0.002, link=None, external_index=None,
                 external_name="esp32-1", oneway_delay=0.0, log_path=None):
        self.swarm = swarm
        self.dt = dt
        self.link = link
        self.ext = external_index
        self.ext_name = external_name
        self.oneway = oneway_delay
        self.last_fire = {}                         # node -> time of its last flash
        self.history = deque(maxlen=int(HISTORY_SECONDS / SAMPLE_EVERY))
        self.times, self.levels = [], []
        self.real_offsets = deque(maxlen=20)        # ms, recent ESP32 flashes
        self.paused = False
        self._next_sample = 0.0
        self._next_hello = 0.0
        self._ext_neighbours = set(swarm.neighbours_of(external_index)) if external_index is not None else set()
        self._log_file = None
        self._log = None
        if log_path:
            self._log_file = open(log_path, "w", newline="")
            self._log = csv.writer(self._log_file)
            self._log.writerow(["time_s", "node", "kind", "sync_level", "esp32_offset_ms"])

    # ----- one tick of the simulation ---------------------------------------
    def _handle_link(self):
        if self.link is None:
            return
        for msg in self.link.poll(self.swarm.time):
            if msg.node_id != self.ext_name:
                continue
            mean = metrics.circular_mean(self.swarm.virtual_phases)
            off = metrics.offset_ms(mean, self.swarm.period, self.oneway)
            self.real_offsets.append(off)
            self.swarm.external_fired(self.ext)
            self._write(self.swarm.time, self.ext, "esp32", off)
        if self.swarm.time >= self._next_hello:
            self.link.send_hello()
            self._next_hello = self.swarm.time + 2.0

    def _step(self):
        for ev in self.swarm.step(self.dt):
            self.last_fire[ev.node] = ev.time
            if ev.external:
                continue
            self._write(ev.time, ev.node, "virtual", "")
            if self.link is not None and ev.node in self._ext_neighbours:
                self.link.send_fire(f"v{ev.node}")
        if self.swarm.time >= self._next_sample:
            lvl = metrics.order_parameter(self.swarm.virtual_phases)
            self.history.append((self.swarm.time, lvl))
            self.times.append(self.swarm.time)
            self.levels.append(lvl)
            self._next_sample = self.swarm.time + SAMPLE_EVERY

    def _write(self, t, node, kind, offset):
        if self._log:
            lvl = self.levels[-1] if self.levels else ""
            self._log.writerow([f"{t:.4f}", node, kind,
                                f"{lvl:.4f}" if lvl != "" else "",
                                f"{offset:.1f}" if offset != "" else ""])

    # ----- runners -----------------------------------------------------------
    def run_headless(self, seconds, report_every=5.0):
        next_report = report_every
        while self.swarm.time < seconds:
            self._handle_link()
            self._step()
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
                    if action == "scramble":
                        self.swarm.scramble()
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
        return self.levels[-1] if self.levels else metrics.order_parameter(self.swarm.virtual_phases)

    def esp32_offset(self):
        if not self.real_offsets:
            return None
        recent = list(self.real_offsets)[-5:]
        return sum(recent) / len(recent)

    def is_flashing(self, node):
        t = self.last_fire.get(node)
        return t is not None and self.swarm.time - t < FLASH_SECONDS

    def status_line(self):
        s = f"t={self.swarm.time:6.1f}s  sync={100 * self.sync_level():5.1f}%"
        off = self.esp32_offset()
        if self.ext is not None:
            s += "  esp32: " + ("not heard yet" if off is None else f"{off:+6.1f} ms off-beat")
        return s

    def summary(self):
        tts = metrics.time_to_sync(self.times, self.levels)
        return {
            "seconds": round(self.swarm.time, 2),
            "final_sync_level": round(self.sync_level(), 4),
            "time_to_sync_s": None if tts is None else round(tts, 2),
            "esp32_offset_ms": None if self.esp32_offset() is None else round(self.esp32_offset(), 1),
        }

    def close(self):
        if self._log_file:
            self._log_file.close()
            self._log_file = None
        if self.link:
            self.link.close()

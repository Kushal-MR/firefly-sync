"""Data messages on a shared radio channel: why the swarm needs sync at all.

Pure logic: no drawing, no sockets, no real clock. The session calls update()
after every swarm step and hands it the time.

The point of firefly sync is not the flashing. It gives every drone the same
idea of when a cycle starts. With that shared beat each cycle is split into
time slots, like a class timetable, and each drone sends its data message
only in its own slot (TDMA, time-division multiple access). Nobody talks over
anybody.

Two ways of choosing when to talk:

* "slots"  - drone i sends when ITS OWN firefly clock reaches slot i. If the
             clocks agree (synced) the slots line up and never overlap; if
             they don't, everybody's slots land at random times and collide.
* "random" - drone i sends once per cycle at a random moment (no timetable).
             This is the baseline: what a swarm does with no coordination.

A collision: drone R can't decode a message from J if, while J is talking,
R itself is talking or some other drone that R can hear is talking.
Every (message, receiver) pair is a "delivery"; the loss rate is the fraction
of deliveries ruined by a collision.

Simplifications, kept visible on purpose:
* one slot per drone, assigned by drone number (real systems negotiate them)
* a message takes AIRTIME of its slot; the rest of the slot is a guard gap
  that absorbs small timing errors (drift, delay)
* the firefly sync pulses themselves are treated as "a flash happened", which
  a receiver can detect even when several overlap. Keeping those pulses from
  overlapping is what Reachback's random send delay is for (future work).
"""
import math
import random
from collections import deque

AIRTIME = 0.6        # fraction of a slot a message takes; the rest is guard time
WINDOW = 5.0         # seconds of history kept for the rolling loss rate
DRAW_KEEP = 2.5      # seconds of transmissions kept for drawing
MODES = ("slots", "random")


class Transmission:
    __slots__ = ("node", "start", "end", "pos", "lost", "deliveries", "done")

    def __init__(self, node, start, end, pos):
        self.node = node
        self.start = start
        self.end = end
        self.pos = pos            # where it lands in the swarm's cycle, 0..1 (for drawing)
        self.lost = 0             # deliveries ruined
        self.deliveries = 0       # receivers in range
        self.done = False         # collisions decided (after it ends)


class Radio:
    def __init__(self, n, period, mode="slots", seed=None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.n = n
        self.period = period
        self.mode = mode
        self.slots = n                        # one slot per drone
        self.airtime = AIRTIME * period / n   # seconds a message is on air
        self._rng = random.Random(None if seed is None else f"{seed}-radio")
        self._prev = None                     # phases at the previous update
        self._next_random = [None] * n        # random mode: next send time per drone
        self.active = []                      # transmissions not yet decided
        self.recent = deque()                 # decided + active, for drawing
        self._window = deque()                # (end_time, deliveries, lost)
        self.sent = 0
        self.deliveries = 0
        self.lost = 0

    # ----- configuration -------------------------------------------------------
    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.mode = mode
        self._next_random = [None] * self.n
        self.reset_stats()

    def reset_stats(self):
        self._window.clear()
        self.sent = self.deliveries = self.lost = 0

    def slot_start(self, i):
        """Phase (0..1) at which drone i starts talking: inside its slot,
        centred, with half the guard gap before and after."""
        return (i % self.slots + (1 - AIRTIME) / 2) / self.slots

    # ----- one step ------------------------------------------------------------
    def update(self, t, phases, neighbours, swarm_phase):
        """phases: each virtual drone's clock (0..1). neighbours: who hears whom
        (indices >= n are ignored). swarm_phase: the swarm's average phase
        (a number, or a function returning it - only called when someone starts
        talking), used only to place transmissions on the drawn timeline."""
        if self.mode == "slots":
            starts = self._slot_starts(phases)
        else:
            starts = self._random_starts(t)
        self._prev = list(phases)
        if starts and callable(swarm_phase):
            swarm_phase = swarm_phase()
        for i in starts:
            self._begin(i, t, swarm_phase)
        self._finish(t, neighbours)

    def _slot_starts(self, phases):
        if self._prev is None:
            return []
        out = []
        for i, (a, b) in enumerate(zip(self._prev, phases)):
            s = self.slot_start(i)
            if b >= a:
                crossed = a < s <= b
            else:                                 # the clock wrapped (it fired)
                crossed = s > a or s <= b
            if crossed:
                out.append(i)
        return out

    def _random_starts(self, t):
        out = []
        for i in range(self.n):
            nxt = self._next_random[i]
            if nxt is None:                        # first cycle: random moment in it
                self._next_random[i] = t + self._rng.uniform(0, self.period)
            elif t >= nxt:
                out.append(i)
                # once per cycle on average, at a fresh random moment each time
                self._next_random[i] = nxt + self._rng.uniform(0.5, 1.5) * self.period
        return out

    def _begin(self, i, t, swarm_phase):
        tx = Transmission(i, t, t + self.airtime, swarm_phase % 1.0)
        self.active.append(tx)
        self.recent.append(tx)
        self.sent += 1

    def _finish(self, t, neighbours):
        """Decide every transmission that has ended, then drop old history."""
        still = []
        for tx in self.active:
            if t < tx.end:
                still.append(tx)
                continue
            self._decide(tx, neighbours)
        self.active = still
        while self.recent and self.recent[0].end < t - DRAW_KEEP:
            self.recent.popleft()
        while self._window and self._window[0][0] < t - WINDOW:
            self._window.popleft()

    def _decide(self, tx, neighbours):
        overlapping = [o for o in self.recent
                       if o is not tx and o.start < tx.end and o.end > tx.start]
        talkers = {o.node for o in overlapping}
        receivers = [r for r in neighbours[tx.node] if r < self.n]
        lost = 0
        for r in receivers:
            if r in talkers:                       # busy talking itself
                lost += 1
            elif any(k in talkers for k in neighbours[r] if k != tx.node):
                lost += 1                          # two voices at once: garbled
        tx.deliveries, tx.lost, tx.done = len(receivers), lost, True
        self.deliveries += len(receivers)
        self.lost += lost
        self._window.append((tx.end, len(receivers), lost))

    # ----- reporting -----------------------------------------------------------
    def loss_rate(self, since=None):
        """Fraction of deliveries lost to collisions in the rolling window (or
        only those that ended after `since`). None if nothing was sent."""
        rows = [w for w in self._window if since is None or w[0] >= since]
        total = sum(d for _, d, _ in rows)
        return None if total == 0 else sum(l for _, _, l in rows) / total

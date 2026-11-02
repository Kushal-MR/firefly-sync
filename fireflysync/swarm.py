"""A swarm of fireflies (drones) on a floor plan, with limited radio range.

Pure logic: no drawing, no sockets, no real clock. The caller hands it a time
step and tells it when an outside node fired.

Two kinds of node live in the swarm:

* virtual nodes - an Oscillator each, stepped by this class
* external nodes - a real device (the ESP32). The swarm cannot step or nudge
  it; it only learns when it fired (external_fired) and passes that flash on
  to the virtual nodes in range. Sending flashes the other way, to the device,
  is the caller's job: see neighbours_of().

Within one step, a fire can trigger more fires (a cascade). Each node fires at
most once per step, and a node that already fired this step is not nudged
again - the Mirollo-Strogatz "absorption" rule that keeps a synced group
together.
"""
import math
import random
from collections import deque
from dataclasses import dataclass

from fireflysync.oscillator import Oscillator


@dataclass(frozen=True)
class FireEvent:
    node: int
    time: float
    external: bool = False


class Swarm:
    def __init__(self, n, period=1.0, coupling=0.01, dissipation=3.0, refractory=0.05,
                 radio_range=None, area=(20.0, 12.0), seed=None):
        if n < 1:
            raise ValueError("need at least one drone")
        self.rng = random.Random(seed)
        self.period = period
        self.area = area
        self.radio_range = radio_range          # None means everyone hears everyone
        self.time = 0.0
        w, h = area
        self.positions = [(self.rng.uniform(0, w), self.rng.uniform(0, h)) for _ in range(n)]
        self.oscillators = [
            Oscillator(period, coupling, self.rng.random() * 0.999, dissipation, refractory)
            for _ in range(n)
        ]
        self.n_virtual = n
        self.external_names = {}                # index -> name
        self._external_last_fire = {}           # index -> time
        self._pending_external = []
        self._rebuild_neighbours()

    # ----- layout ------------------------------------------------------------
    def _rebuild_neighbours(self):
        pts, r = self.positions, self.radio_range
        self.neighbours = []
        for i, (xi, yi) in enumerate(pts):
            near = [j for j, (xj, yj) in enumerate(pts)
                    if j != i and (r is None or math.hypot(xi - xj, yi - yj) <= r)]
            self.neighbours.append(near)

    def add_external(self, name, position=None):
        """Add a real device as a node. Returns its index."""
        if position is None:
            position = (self.area[0] / 2, self.area[1] / 2)
        self.positions.append(tuple(position))
        idx = len(self.positions) - 1
        self.external_names[idx] = name
        self._rebuild_neighbours()
        return idx

    def neighbours_of(self, idx):
        return list(self.neighbours[idx])

    def is_connected(self):
        """True if a flash can travel from any node to every other node."""
        seen, todo = {0}, deque([0])
        while todo:
            for j in self.neighbours[todo.popleft()]:
                if j not in seen:
                    seen.add(j)
                    todo.append(j)
        return len(seen) == len(self.positions)

    # ----- time --------------------------------------------------------------
    def external_fired(self, idx):
        """The real device at idx flashed. Delivered on the next step."""
        if idx not in self.external_names:
            raise KeyError(f"{idx} is not an external node")
        self._pending_external.append(idx)

    def step(self, dt):
        """Advance every virtual node by dt. Returns every fire in this step."""
        self.time += dt
        t = self.time
        events, queue, fired = [], [], set()

        for i, osc in enumerate(self.oscillators):
            if osc.advance(dt):
                fired.add(i)
                queue.append(i)
                events.append(FireEvent(i, t))
        for idx in self._pending_external:
            self._external_last_fire[idx] = t
            queue.append(idx)
            events.append(FireEvent(idx, t, external=True))
        self._pending_external.clear()

        while queue:
            src = queue.pop()
            for j in self.neighbours[src]:
                if j >= self.n_virtual or j in fired:
                    continue
                if self.oscillators[j].on_neighbour_fired():
                    fired.add(j)
                    queue.append(j)
                    events.append(FireEvent(j, t))
        return events

    # ----- state -------------------------------------------------------------
    @property
    def virtual_phases(self):
        return [o.phase for o in self.oscillators]

    def phase_of(self, idx):
        if idx < self.n_virtual:
            return self.oscillators[idx].phase
        last = self._external_last_fire.get(idx)
        if last is None:
            return None
        return ((self.time - last) / self.period) % 1.0

    def scramble(self):
        """Throw every virtual node to a random phase."""
        for o in self.oscillators:
            o.scramble(self.rng.random() * 0.999)

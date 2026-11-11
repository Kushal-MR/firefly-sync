"""A swarm of fireflies (drones) on a floor plan, with limited radio range.

Pure logic: no drawing, no sockets, no real clock. The caller hands it a time
step and tells it when an outside node fired.

Two kinds of node live in the swarm:

* virtual nodes - an Oscillator each, stepped by this class
* external nodes - real devices (each LED on the ESP32). The swarm cannot step
  or nudge them; it only learns when they fired (external_fired) and passes
  that flash on to the virtual nodes in range. Sending flashes the other way,
  to the device, is the caller's job: see neighbours_of().

Within one step, a fire can trigger more fires (a cascade). Each node fires at
most once per step, and a node that already fired this step is not nudged
again - the Mirollo-Strogatz "absorption" rule that keeps a synced group
together.

Scenarios (all off by default, each switchable at run time):

* walls      - a wall splits the floor into two rooms; radio can't cross it
* door_open  - opens a door in that wall, so the rooms can hear each other
* loss       - each flash delivery is dropped with this probability
* drift      - each drone's clock runs a little fast or slow (std, e.g. 0.02)
* speed      - drones wander at this speed (m/s); neighbours change as they move
* rogues     - faulty drones (0, 1, 3, 5...) that fire at random and ignore everyone

Every scenario draws from its OWN random stream, so switching one on never
changes the layout or what the others do. With everything off, a given seed
behaves exactly as it always has.
"""
import math
import random
from collections import deque
from dataclasses import dataclass

from fireflysync import geometry
from fireflysync.oscillator import Oscillator

NEIGHBOUR_REFRESH = 0.1        # seconds between radio-range rebuilds while moving


@dataclass(frozen=True)
class FireEvent:
    node: int
    time: float
    external: bool = False


class Swarm:
    def __init__(self, n, period=1.0, coupling=0.01, dissipation=3.0, refractory=0.05,
                 radio_range=None, area=(20.0, 12.0), seed=None,
                 walls=False, door_open=False, loss=0.0, drift=0.0, speed=0.0, rogues=0):
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

        # one random stream per scenario (see module docstring)
        def stream(tag):
            return random.Random(None if seed is None else f"{seed}-{tag}")
        self._rng_loss = stream("loss")
        self._rng_rogue = stream("rogue")
        self._rng_move = stream("move")
        drift_rng = stream("drift")
        self._drift_z = [max(-3.0, min(3.0, drift_rng.gauss(0, 1))) for _ in range(n)]
        self._headings = [self._rng_move.uniform(0, 2 * math.pi) for _ in range(n)]

        self.walls_on = walls
        self.door_open = door_open
        self.loss = 0.0
        self.drift = 0.0
        self.speed = 0.0
        self.rogues = set()                     # indices of faulty drones
        self.layout_version = 0                 # bumps whenever neighbours change
        self._next_refresh = 0.0
        self.set_loss(loss)
        self.set_drift(drift)
        self.set_speed(speed)
        self._rebuild_neighbours()
        self.set_rogues(rogues)

    # ----- layout ------------------------------------------------------------
    @property
    def walls(self):
        return geometry.two_rooms(self.area, self.door_open) if self.walls_on else []

    def _rebuild_neighbours(self):
        pts, r, walls = self.positions, self.radio_range, self.walls
        self.neighbours = []
        for i, a in enumerate(pts):
            near = [j for j, b in enumerate(pts)
                    if j != i
                    and (r is None or math.hypot(a[0] - b[0], a[1] - b[1]) <= r)
                    and not (walls and geometry.blocked(a, b, walls))]
            self.neighbours.append(near)
        self.layout_version += 1

    def add_external(self, name, position=None):
        """Add a real device (or one LED of it) as a node. Returns its index."""
        if position is None:
            position = (self.area[0] / 2, self.area[1] / 2)
        self.positions.append(tuple(position))
        idx = len(self.positions) - 1
        self.external_names[idx] = name
        self._rebuild_neighbours()
        return idx

    def neighbours_of(self, idx):
        return list(self.neighbours[idx])

    def components(self):
        """Groups of nodes that can reach each other (e.g. the two rooms)."""
        seen, groups = set(), []
        for start in range(len(self.positions)):
            if start in seen:
                continue
            group, todo = [], deque([start])
            seen.add(start)
            while todo:
                k = todo.popleft()
                group.append(k)
                for j in self.neighbours[k]:
                    if j not in seen:
                        seen.add(j)
                        todo.append(j)
            groups.append(group)
        return groups

    def is_connected(self):
        """True if a flash can travel from any node to every other node."""
        return len(self.components()) == 1

    # ----- scenarios ---------------------------------------------------------
    def set_walls(self, on):
        self.walls_on = bool(on)
        self._rebuild_neighbours()

    def set_door(self, is_open):
        self.door_open = bool(is_open)
        self._rebuild_neighbours()

    def set_loss(self, p):
        if not 0.0 <= p < 1.0:
            raise ValueError("loss must be in [0, 1)")
        self.loss = p

    def set_drift(self, std):
        """Give drone i a clock that runs (1 + std * z_i) times normal speed."""
        if not 0.0 <= std < 0.2:
            raise ValueError("drift must be in [0, 0.2)")
        self.drift = std
        for o, z in zip(self.oscillators, self._drift_z):
            o.period = self.period / (1.0 + std * z)

    def set_speed(self, speed):
        if speed < 0:
            raise ValueError("speed must be >= 0")
        self.speed = speed

    def set_rogues(self, count):
        """Make the `count` best-connected drones faulty: they fire at random
        and ignore everyone. Best-connected, so the test is as hard as it gets."""
        count = max(0, min(int(count), self.n_virtual - 2))
        ranked = sorted(range(self.n_virtual), key=lambda i: (-len(self.neighbours[i]), i))
        self.rogues = set(ranked[:count])

    @property
    def healthy(self):
        """Virtual drones that follow the firefly rule (everyone but the rogues)."""
        return [i for i in range(self.n_virtual) if i not in self.rogues]

    # ----- time --------------------------------------------------------------
    def external_fired(self, idx):
        """The real device at idx flashed. Delivered on the next step."""
        if idx not in self.external_names:
            raise KeyError(f"{idx} is not an external node")
        self._pending_external.append(idx)

    def _move(self, dt):
        w, h = self.area
        walls = self.walls
        rng = self._rng_move
        for i in range(self.n_virtual):
            hdg = self._headings[i] + rng.gauss(0, 1.2) * math.sqrt(dt)
            x, y = self.positions[i]
            nx, ny = x + self.speed * dt * math.cos(hdg), y + self.speed * dt * math.sin(hdg)
            if not 0 <= nx <= w:
                hdg = math.pi - hdg
                nx = x
            if not 0 <= ny <= h:
                hdg = -hdg
                ny = y
            if walls and geometry.blocked((x, y), (nx, ny), walls):
                hdg = math.pi - hdg                     # bounce off the wall
                nx, ny = x, y
            self._headings[i] = hdg
            self.positions[i] = (nx, ny)
        if self.time >= self._next_refresh:
            self._rebuild_neighbours()
            self._next_refresh = self.time + NEIGHBOUR_REFRESH

    def step(self, dt):
        """Advance every virtual node by dt. Returns every fire in this step."""
        self.time += dt
        t = self.time
        if self.speed > 0:
            self._move(dt)
        events, queue, fired = [], [], set()

        for i, osc in enumerate(self.oscillators):
            if i in self.rogues:
                # faulty: fires at random, about once a period on average
                if self._rng_rogue.random() < dt / self.period:
                    osc.scramble(0.0)
                    fired.add(i)
                    queue.append(i)
                    events.append(FireEvent(i, t))
                else:
                    osc.scramble(min(0.999, osc.phase + dt / self.period))
                continue
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
                if j >= self.n_virtual or j in fired or j in self.rogues:
                    continue
                if self.loss and self._rng_loss.random() < self.loss:
                    continue                            # this flash was not heard
                if self.oscillators[j].on_neighbour_fired():
                    fired.add(j)
                    queue.append(j)
                    events.append(FireEvent(j, t))
        return events

    # ----- state -------------------------------------------------------------
    @property
    def virtual_phases(self):
        return [o.phase for o in self.oscillators]

    @property
    def healthy_phases(self):
        return [self.oscillators[i].phase for i in self.healthy]

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

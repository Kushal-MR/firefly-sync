"""A swarm of oscillators on a floor plan, with limited radio range.

PHASE 1. Build after oscillator.py.

Also pure — no drawing, no sockets, no real clock.

Planned interface
-----------------
class Swarm:
    def __init__(self, n, period, coupling, radio_range, area, seed=None): ...

    def step(self, dt) -> list[FireEvent]
        Advance every oscillator by dt, deliver each fire to the nodes in
        range, and return everything that fired this step.

    @property
    def phases(self) -> list[float]
        Current phase of every node, for metrics and drawing.

Design notes
------------
- Start with everyone hearing everyone. Get that working and synchronizing
  first. Only then add radio range.
- Radio range is what makes this a *floor plan* rather than a single room,
  and it is where interesting failures live: too small a range and the swarm
  splits into groups that never agree.
- Fires delivered within one step must not cascade forever. Decide whether a
  node that fires because of a nudge can itself trigger others in the same
  step, and cap the depth if so. Write the choice down.
- seed makes a run repeatable, which Phase 3 needs.

TODO(phase-1): implement.
"""

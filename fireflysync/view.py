"""Live pygame window: flashing dots and a phase-spread line.

PHASE 1. Build this LAST in the phase. It is the most fun and the easiest
place to lose a week.

Planned interface
-----------------
class View:
    def __init__(self, width, height): ...
    def draw(self, swarm, spread_history) -> None
    def handle_events(self) -> bool    # False when the user closes the window
    def close(self) -> None

Design notes
------------
- The view reads swarm state and draws it. It never changes the swarm and it
  never advances time. The loop in scripts/run_sim.py owns the stepping.
- A node that fired this step should stay lit for a few frames, otherwise
  flashes are invisible at 60 fps.
- Draw the drones as small drone-ish markers rather than plain dots; it costs
  nothing and sells the story in the demo.
- Show the live phase-spread line next to the swarm. Watching that curve fall
  is what makes the synchronization legible to an evaluator.

TODO(phase-1): implement.
"""

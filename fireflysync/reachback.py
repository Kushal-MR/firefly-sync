"""The Reachback Firefly Algorithm (Werner-Allen et al., 2005).

PHASE 3. This is the improvement the project is built around.

Two changes to the plain rule:

1. Random staggered send. Wait a small random time before broadcasting, and
   put that delay in the message so the receiver can subtract it. Stops
   everyone transmitting at the same instant once they are nearly synced.

2. Reachback. Do not react to a fire the moment it is heard. Collect every
   fire heard during one cycle, then apply all the adjustments together at
   the start of the next cycle.

Planned interface
-----------------
class ReachbackOscillator(Oscillator):
    def on_neighbour_fired(self, heard_at, tx_delay_ms) -> None
        Record it. Do not change the phase yet.

    def advance(self, dt) -> bool
        At a cycle boundary, apply everything collected, then continue.

Design notes
------------
- This is a thin layer over Oscillator, not a rewrite. If it turns into a
  rewrite, the Phase 1 boundary was drawn in the wrong place.
- Keeping both available at runtime is the whole point: every experiment runs
  the same scenario twice, once with each, and compares.
- The random send delay must be bounded well below one cycle, or a message
  arrives after the cycle it belongs to.

TODO(phase-3): implement.
"""

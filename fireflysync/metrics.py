"""Measuring how well the swarm is synchronized.

PHASE 1. Needed as soon as swarm.py runs, so you can see progress as a
number instead of squinting at dots.

Planned interface
-----------------
def phase_spread(phases) -> float
    How far apart the nodes are right now. 0.0 means perfectly together.

def time_to_sync(history, tolerance) -> float | None
    Scanning a run's history, the first moment the spread drops below
    tolerance and stays there. None if it never does.

Design notes
------------
- Phases live on a circle: 0.99 and 0.01 are close together, not far apart.
  A plain max-minus-min will report those as almost a full period apart and
  make a synced swarm look broken. Use a circular measure.
- "Stays there" in time_to_sync matters. A run that dips below tolerance for
  one step and bounces out has not synchronized.
- Record the tolerance you chose in docs/EXPERIMENTS.md; every number in the
  report depends on it.

TODO(phase-1): implement.
"""

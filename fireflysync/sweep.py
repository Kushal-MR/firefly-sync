"""Headless runs over a grid of settings.

PHASE 3. This is where the Phase 1 architecture rule pays off — or doesn't.

Planned interface
-----------------
def run_once(config) -> dict
    One simulation, no window, returns time-to-sync, final spread, whether
    it synced at all.

def sweep(grid, repeats, out_path) -> None
    Every combination in the grid, repeated, written to CSV in data/.

Design notes
------------
- No pygame import anywhere in this file's call path. If importing sweep.py
  opens a window, the layering is broken.
- Write results to CSV as they finish, not at the end. A sweep that dies at
  90% should not lose everything.
- Record the full config in every row, including the seed. Six weeks from now
  "which settings produced this figure?" must be answerable from the file.
- Start with a tiny grid and 2 repeats to check the pipeline end to end, then
  scale up. Do not launch a 5000-run sweep as your first test.

TODO(phase-3): implement.
"""

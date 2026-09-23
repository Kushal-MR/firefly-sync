"""Plot helpers shared by the report figures.

PHASE 3. Called by scripts/plot_results.py.

Keep the styling in one place — same fonts, same colours, same axis labels —
so the five figures read as one set in the report.

Design notes
------------
- Always plot the spread across repeats (error bars or a shaded band), not
  just the mean. A mean with no spread hides whether the effect is real.
- Label axes with units. "Time to sync (s)", not "time".
- Save at a resolution that survives being pasted into a slide.

TODO(phase-3): implement.
"""

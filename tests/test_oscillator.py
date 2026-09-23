"""Tests for fireflysync.oscillator.

PHASE 1. Write these alongside oscillator.py, not after.

Cases to cover
--------------
- phase rises at the right rate for a given dt
- it fires exactly when the phase reaches the threshold
- firing resets the phase to zero
- a nudge moves the phase forward by the coupling strength
- a nudge that reaches the threshold causes an immediate fire
- a nudge never overshoots past the threshold and wraps around
- two oscillators started at different phases end up firing together

The last one is the real test: it is the 1990 result, in miniature, and it
should pass before anyone touches the pygame window.

TODO(phase-1): implement.
"""

"""One firefly: a phase that rises, fires, and is nudged by neighbours.

PHASE 1. Build this first, with its test, before anything else.

This module is pure. It must not import pygame, socket, or time. It is
handed a time step and told when a neighbour fired; it never finds those
out for itself. That is what lets Phase 3 run it thousands of times faster
than real time.

Planned interface
-----------------
class Oscillator:
    def __init__(self, period, coupling, phase=0.0): ...

    def advance(self, dt) -> bool
        Move the phase forward by dt seconds.
        Returns True if the oscillator fired during this step.

    def on_neighbour_fired(self) -> bool
        Jump the phase forward by the coupling strength.
        Returns True if that jump pushed it over the threshold and it fired.

Design notes
------------
- Phase is kept in the range 0.0 to 1.0. Firing resets it to 0.0.
- The nudge is capped at the threshold; it never overshoots past 1.0 and
  wraps around, because that would let a node skip a whole cycle.
- Decide and write down what happens when several neighbours fire in the
  same step: are the nudges applied one after another, or only once? The
  Mirollo-Strogatz model applies each one. Pick that, and note it.

TODO(phase-1): implement and make tests/test_oscillator.py pass.
"""

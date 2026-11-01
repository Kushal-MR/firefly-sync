"""One firefly: a phase that rises, fires, and is nudged by neighbours.

This is the Mirollo-Strogatz pulse-coupled oscillator (1990).

This module is pure. It never imports pygame, socket or time. It is handed a
time step and told when a neighbour fired; it never finds those out itself.
That is what lets the experiments run it thousands of times faster than real
time, with no window open.

How the nudge works
-------------------
The phase (0 -> 1) rises at a steady rate. Underneath it sits a "charge"
x = f(phase), where f is a curve that bends over: it climbs fast early and
flattens near the top, like a capacitor charging.

When a neighbour fires, the CHARGE goes up by a fixed amount (the coupling).
Because the curve is flat near the top, a fixed step in charge becomes a
BIG step in phase for a firefly that is nearly ready to flash, and a small
step for one that has just flashed. Nearly-ready fireflies get dragged into
flashing together, and once two flash together they stay together. That
lopsided pull is why the group locks into one rhythm.

`dissipation` sets how strongly the curve bends. Near 0 it is a straight
line, and the nudge becomes a plain fixed jump in phase.
"""
import math


class Oscillator:
    def __init__(self, period=1.0, coupling=0.1, phase=0.0, dissipation=3.0):
        if period <= 0:
            raise ValueError("period must be positive")
        if not 0.0 < coupling < 1.0:
            raise ValueError("coupling must be between 0 and 1")
        if not 0.0 <= phase < 1.0:
            raise ValueError("phase must be in [0, 1)")
        if dissipation <= 0:
            raise ValueError("dissipation must be positive (use a small value like 1e-6 for linear)")
        self.period = period
        self.coupling = coupling
        self.dissipation = dissipation
        self._phase = float(phase)

    @property
    def phase(self):
        return self._phase

    # --- the curve between phase and charge -------------------------------
    def _charge(self, phase):
        b = self.dissipation
        return math.log1p(math.expm1(b) * phase) / b

    def _phase_of(self, charge):
        b = self.dissipation
        return math.expm1(b * charge) / math.expm1(b)

    # --- the two things that can happen to a firefly ----------------------
    def advance(self, dt):
        """Let dt seconds pass. Returns True if it fired during this step.

        The leftover past the threshold is kept, so firing time stays
        accurate even with a coarse time step.
        """
        if not 0.0 < dt < self.period:
            raise ValueError("dt must be positive and smaller than the period")
        self._phase += dt / self.period
        if self._phase >= 1.0:
            self._phase -= 1.0
            return True
        return False

    def on_neighbour_fired(self):
        """A neighbour flashed. Returns True if this pushed us to fire too.

        Each call is one flash. If three neighbours fire in the same step,
        call this three times: Mirollo-Strogatz applies every pulse.
        A nudge never wraps past the threshold - it fires and resets to 0,
        so a firefly can never skip a whole cycle.
        """
        charge = self._charge(self._phase) + self.coupling
        if charge >= 1.0:
            self._phase = 0.0
            return True
        self._phase = self._phase_of(charge)
        return False

    def __repr__(self):
        return f"Oscillator(phase={self._phase:.3f}, coupling={self.coupling}, period={self.period})"

"""Tests for fireflysync.oscillator."""
import random

import pytest

from fireflysync.oscillator import Oscillator


def test_phase_rises_at_the_right_rate():
    o = Oscillator(period=2.0)
    o.advance(0.5)
    assert o.phase == pytest.approx(0.25)


def test_fires_when_phase_reaches_threshold_and_keeps_leftover():
    o = Oscillator(period=1.0, phase=0.9)
    assert o.advance(0.05) is False
    assert o.advance(0.1) is True
    assert o.phase == pytest.approx(0.05)


def test_nudge_moves_phase_forward():
    o = Oscillator(phase=0.3)
    before = o.phase
    o.on_neighbour_fired()
    assert o.phase > before


def test_nudge_is_bigger_near_threshold():
    """The lopsided pull that makes synchronization happen."""
    early, late = Oscillator(phase=0.2), Oscillator(phase=0.7)
    e0, l0 = early.phase, late.phase
    early.on_neighbour_fired()
    late.on_neighbour_fired()
    assert (late.phase - l0) > (early.phase - e0)


def test_nudge_that_reaches_threshold_fires_and_resets():
    o = Oscillator(phase=0.99, coupling=0.1)
    assert o.on_neighbour_fired() is True
    assert o.phase == 0.0


def test_nudge_never_overshoots_or_wraps():
    for p in [i / 100 for i in range(100)]:
        o = Oscillator(phase=p, coupling=0.5)
        o.on_neighbour_fired()
        assert 0.0 <= o.phase < 1.0


def test_tiny_dissipation_behaves_like_a_plain_jump():
    o = Oscillator(phase=0.3, coupling=0.1, dissipation=1e-6)
    o.on_neighbour_fired()
    assert o.phase == pytest.approx(0.4, abs=1e-4)


@pytest.mark.parametrize("kwargs", [
    {"period": 0}, {"coupling": 0}, {"coupling": 1.0},
    {"phase": 1.0}, {"phase": -0.1}, {"dissipation": 0},
])
def test_rejects_bad_settings(kwargs):
    with pytest.raises(ValueError):
        Oscillator(**kwargs)


def test_rejects_bad_time_step():
    o = Oscillator(period=1.0)
    with pytest.raises(ValueError):
        o.advance(0)
    with pytest.raises(ValueError):
        o.advance(1.0)


def _fire_times_after(oscillators, seconds, dt=0.001):
    """Tiny all-to-all loop. Real stepping belongs in swarm.py; this exists
    only so the test can check the 1990 result in miniature."""
    t, fires = 0.0, []
    while t < seconds:
        t += dt
        fired = [i for i, o in enumerate(oscillators) if o.advance(dt)]
        queue, done = list(fired), set(fired)
        while queue:                       # a fire can trigger others
            queue.pop()
            for i, o in enumerate(oscillators):
                if i not in done and o.on_neighbour_fired():
                    done.add(i)
                    queue.append(i)
        if done:
            fires.append((t, sorted(done)))
    return fires


@pytest.mark.parametrize("seed", range(5))
def test_random_fireflies_end_up_flashing_together(seed):
    """The Mirollo-Strogatz result: from a random start, everyone syncs."""
    rng = random.Random(seed)
    group = [Oscillator(coupling=0.1, phase=rng.random() * 0.999) for _ in range(5)]
    fires = _fire_times_after(group, seconds=30)
    last_ten = fires[-10:]
    assert all(ids == [0, 1, 2, 3, 4] for _, ids in last_ten), last_ten

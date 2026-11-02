import pytest

from fireflysync import metrics


def test_identical_phases_are_fully_synced():
    assert metrics.order_parameter([0.3] * 10) == pytest.approx(1.0)
    assert metrics.phase_spread([0.3] * 10) == pytest.approx(0.0, abs=1e-12)


def test_opposite_phases_cancel_out():
    assert metrics.order_parameter([0.0, 0.5]) == pytest.approx(0.0, abs=1e-12)


def test_wraparound_counts_as_close():
    """0.99 and 0.01 are neighbours on the circle, not opposite ends."""
    assert metrics.order_parameter([0.99, 0.01]) > 0.99


def test_circular_mean_handles_the_wrap():
    m = metrics.circular_mean([0.98, 0.02])
    assert min(m, 1 - m) < 1e-9


def test_wrap_takes_the_short_way_round():
    assert metrics.wrap(0.9) == pytest.approx(-0.1)
    assert metrics.wrap(0.1) == pytest.approx(0.1)


def test_offset_sign_late_and_early():
    assert metrics.offset_ms(0.02, period=1.0) == pytest.approx(20.0)
    assert metrics.offset_ms(0.98, period=1.0) == pytest.approx(-20.0)


def test_offset_subtracts_network_delay():
    assert metrics.offset_ms(0.02, period=1.0, oneway_delay=0.01) == pytest.approx(10.0)


def test_time_to_sync_needs_to_hold():
    times = [i * 0.5 for i in range(20)]
    levels = [0.5, 0.97, 0.5] + [0.97] * 17          # brief spike, then real sync at t=1.5
    assert metrics.time_to_sync(times, levels, threshold=0.95, hold=3.0) == 1.5


def test_time_to_sync_none_if_never():
    assert metrics.time_to_sync([0, 1, 2], [0.1, 0.2, 0.3]) is None

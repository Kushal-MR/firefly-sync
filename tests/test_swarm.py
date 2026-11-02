import pytest

from fireflysync import metrics
from fireflysync.swarm import Swarm


def run(swarm, seconds, dt=0.002):
    while swarm.time < seconds:
        swarm.step(dt)


@pytest.mark.parametrize("seed", range(3))
def test_all_to_all_swarm_synchronizes(seed):
    s = Swarm(20, radio_range=None, seed=seed)
    assert metrics.order_parameter(s.virtual_phases) < 0.9
    run(s, 90)
    assert metrics.order_parameter(s.virtual_phases) > 0.99


def test_swarm_with_radio_range_synchronizes():
    s = Swarm(20, radio_range=9.0, seed=1)
    assert s.is_connected()
    run(s, 90)
    assert metrics.order_parameter(s.virtual_phases) > 0.99


def test_disconnected_layout_is_detected():
    s = Swarm(10, radio_range=0.01, seed=0)
    assert not s.is_connected()


def test_same_seed_same_run():
    a, b = Swarm(10, seed=7), Swarm(10, seed=7)
    run(a, 5)
    run(b, 5)
    assert a.virtual_phases == b.virtual_phases


def test_each_node_fires_at_most_once_per_step():
    s = Swarm(30, radio_range=None, seed=3)
    for _ in range(5000):
        nodes = [e.node for e in s.step(0.002)]
        assert len(nodes) == len(set(nodes))


def test_external_fire_only_reaches_nodes_in_range():
    s = Swarm(5, radio_range=3.0, area=(20, 12), seed=0)
    s.positions[:] = [(1, 1), (2, 1), (15, 10), (16, 10), (18, 10)]
    s._rebuild_neighbours()
    ext = s.add_external("esp32", position=(1.5, 1.5))
    assert set(s.neighbours_of(ext)) == {0, 1}
    for o in s.oscillators:
        o.scramble(0.5)
    s.external_fired(ext)
    s.step(1e-6)
    near, far = s.virtual_phases[:2], s.virtual_phases[2:]
    assert all(p > 0.51 for p in near)
    assert all(p == pytest.approx(0.5, abs=1e-4) for p in far)


def test_external_phase_is_estimated_from_its_last_flash():
    s = Swarm(3, seed=0)
    ext = s.add_external("esp32")
    assert s.phase_of(ext) is None
    s.external_fired(ext)
    s.step(0.1)
    s.step(0.2)
    assert s.phase_of(ext) == pytest.approx(0.2)


def test_scramble_breaks_sync():
    s = Swarm(20, seed=2)
    run(s, 90)
    s.scramble()
    assert metrics.order_parameter(s.virtual_phases) < 0.9

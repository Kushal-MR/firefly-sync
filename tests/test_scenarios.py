"""Each scenario from the demo, locked in as a test."""
import pytest

from fireflysync import metrics
from fireflysync.session import Session
from fireflysync.swarm import Swarm


def run(s, seconds, dt=0.002):
    end = s.time + seconds
    while s.time < end:
        s.step(dt)


def sync(s):
    return metrics.order_parameter(s.healthy_phases)


def test_everything_off_keeps_the_demo_layout_unchanged():
    s = Swarm(20, radio_range=9.0, seed=3)
    r = Session(s).run_headless(30, report_every=1e9)
    assert r["time_to_sync_s"] == pytest.approx(7.67, abs=0.05)


def test_closed_wall_splits_radio_into_two_rooms_and_door_merges_them():
    s = Swarm(20, radio_range=9.0, seed=3, walls=True)
    assert len(s.components()) == 2
    run(s, 40)
    assert metrics.rhythm_groups(s.healthy_phases) == 2
    s.set_door(True)
    assert len(s.components()) == 1
    run(s, 60)
    assert sync(s) > 0.95


@pytest.mark.parametrize("seed", range(6))
def test_open_door_connects_rooms_in_many_layouts(seed):
    s = Swarm(20, radio_range=9.0, seed=seed, walls=True, door_open=True)
    assert s.is_connected()


@pytest.mark.parametrize("loss", [0.1, 0.3, 0.5])
def test_swarm_still_syncs_with_lost_flashes(loss):
    s = Swarm(20, radio_range=9.0, seed=3, loss=loss)
    run(s, 60)
    assert sync(s) > 0.95


def test_loss_is_repeatable_with_a_seed():
    a, b = Swarm(15, seed=5, loss=0.3), Swarm(15, seed=5, loss=0.3)
    run(a, 10)
    run(b, 10)
    assert a.virtual_phases == b.virtual_phases


@pytest.mark.parametrize("drift", [0.01, 0.02, 0.05])
def test_swarm_holds_sync_despite_clock_drift(drift):
    s = Swarm(20, radio_range=9.0, seed=3, drift=drift)
    assert len({round(o.period, 6) for o in s.oscillators}) > 1     # clocks really differ
    run(s, 60)
    assert sync(s) > 0.95


def test_drift_off_restores_identical_clocks():
    s = Swarm(10, seed=1, drift=0.05)
    s.set_drift(0.0)
    assert {o.period for o in s.oscillators} == {1.0}


def test_moving_drones_change_neighbours_and_stay_synced():
    s = Swarm(20, radio_range=9.0, seed=3, speed=1.0)
    before = [list(n) for n in s.neighbours]
    run(s, 60)
    assert [list(n) for n in s.neighbours] != before
    assert sync(s) > 0.95


def test_moving_drones_never_pass_through_a_closed_wall():
    s = Swarm(20, radio_range=9.0, seed=3, walls=True, speed=2.0)
    left = {i for i, (x, _) in enumerate(s.positions) if x < 10}
    run(s, 30)
    assert left == {i for i, (x, _) in enumerate(s.positions[:20]) if x < 10}


@pytest.mark.parametrize("count", [1, 3])
def test_a_few_rogues_cannot_break_a_synced_swarm(count):
    s = Swarm(20, radio_range=9.0, seed=3)
    run(s, 20)
    s.set_rogues(count)
    assert len(s.rogues) == count and len(s.healthy) == 20 - count
    run(s, 40)
    assert sync(s) > 0.9


def test_rogues_ignore_everyone():
    s = Swarm(5, seed=0)
    s.set_rogues(1)
    (r,) = s.rogues
    s.oscillators[r].scramble(0.5)
    others = [i for i in range(5) if i != r]
    for i in others:
        s.oscillators[i].scramble(0.999)
    s.step(0.002)                          # everyone else fires
    assert s.oscillators[r].phase == pytest.approx(0.502, abs=1e-6)


# ----- thin walls --------------------------------------------------------------
def _cross_links(sw):
    mid = sw.area[0] / 2
    return [(i, j) for i in range(sw.n_virtual) for j in sw.neighbours[i]
            if j > i and (sw.positions[i][0] < mid) != (sw.positions[j][0] < mid)]


def test_thin_wall_lets_only_short_links_through():
    from fireflysync.swarm import Swarm
    sw = Swarm(20, radio_range=9.0, seed=3, walls=True, wall_type="thin")
    links = _cross_links(sw)
    assert links, "a thin wall should let some signal through"
    reach = sw.through_wall_reach
    assert reach == 4.5
    for i, j in links:
        (ax, ay), (bx, by) = sw.positions[i], sw.positions[j]
        assert ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 <= reach + 1e-9
    solid = Swarm(20, radio_range=9.0, seed=3, walls=True, wall_type="solid")
    assert _cross_links(solid) == []


def test_solid_wall_splits_but_thin_wall_merges_the_rooms():
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm
    sw = Swarm(20, radio_range=9.0, seed=3)
    s = Session(sw)
    sw.set_walls(True, "solid")
    s.scramble()
    while sw.time < 25:
        s._step()
    assert s.rhythms() >= 2
    sw.set_walls(True, "thin")
    while sw.time < 85:
        s._step()
    assert s.rhythms() == 1 and s.sync_level() > 0.95


def test_w_key_cycles_off_solid_thin_off():
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm
    s = Session(Swarm(20, radio_range=9.0, seed=3))
    seen = []
    for _ in range(3):
        s.apply("walls")
        seen.append((s.swarm.walls_on, s.swarm.wall_type if s.swarm.walls_on else None))
    assert seen == [(True, "solid"), (True, "thin"), (False, None)]


def test_bad_wall_type_is_refused():
    import pytest
    from fireflysync.swarm import Swarm
    with pytest.raises(ValueError):
        Swarm(5, wall_type="glass")

"""The radio model: when does the timetable stop collisions?"""
import pytest

from fireflysync import metrics
from fireflysync.radio import AIRTIME, Radio
from fireflysync.swarm import Swarm


def _run(mode, sync, seconds=40, n=20, seed=3):
    sw = Swarm(n, radio_range=9.0, seed=seed)
    sw.sync_on = sync
    r = Radio(n, sw.period, mode, seed=seed)
    while sw.time < seconds:
        sw.step(0.002)
        r.update(sw.time, sw.virtual_phases, sw.neighbours, metrics.circular_mean(sw.healthy_phases))
    return r


def test_identical_clocks_in_slots_never_collide():
    # everyone in range of everyone, clocks exactly equal: a perfect timetable
    n = 10
    r = Radio(n, 1.0, "slots")
    everyone = [[j for j in range(n) if j != i] for i in range(n)]
    t, ph = 0.0, 0.0
    for _ in range(3000):
        t += 0.001
        ph = (ph + 0.001) % 1.0
        r.update(t, [ph] * n, everyone, ph)
    assert r.sent >= 2 * n and r.lost == 0 and r.loss_rate() == 0.0


def test_two_drones_talking_at_once_garble_each_other():
    r = Radio(2, 1.0, "slots")
    both = [[1], [0]]
    # both clocks cross BOTH slot starts in the same step -> both talk together
    r.update(0.0, [0.0, 0.0], both, 0.0)
    r.update(0.001, [0.99, 0.99], both, 0.0)
    r.update(0.5, [0.99, 0.99], both, 0.0)
    assert r.sent == 2 and r.lost == 2


def test_far_apart_drones_do_not_collide():
    r = Radio(2, 1.0, "slots")
    alone = [[], []]                               # nobody hears anybody
    r.update(0.0, [0.0, 0.0], alone, 0.0)
    r.update(0.001, [0.99, 0.99], alone, 0.0)
    r.update(0.5, [0.99, 0.99], alone, 0.0)
    assert r.lost == 0 and r.loss_rate() is None   # no receivers, nothing to lose


def test_firefly_sync_removes_collisions_on_the_demo_layout():
    synced = _run("slots", True)
    unsynced = _run("slots", False)
    assert synced.loss_rate() == 0.0                       # last 5 s, after sync
    assert unsynced.loss_rate() > 0.2                      # same timetable, clocks disagree


def test_random_timing_collides_even_when_synced():
    assert _run("random", True).loss_rate() > 0.2


def test_slot_start_sits_inside_its_slot_with_guard_gaps():
    r = Radio(20, 1.0)
    for i in range(20):
        s = r.slot_start(i)
        assert i / 20 < s and s + AIRTIME / 20 < (i + 1) / 20


def test_bad_mode_is_refused():
    with pytest.raises(ValueError):
        Radio(5, 1.0, "aloha")

import csv

from fireflysync.session import Session
from fireflysync.swarm import Swarm


def test_headless_run_syncs_and_reports(capsys):
    s = Swarm(15, radio_range=None, seed=4)
    result = Session(s).run_headless(90, report_every=100)
    assert result["final_sync_level"] > 0.99
    assert result["time_to_sync_s"] is not None


def test_log_file_records_flashes(tmp_path):
    path = tmp_path / "run.csv"
    s = Swarm(5, seed=1)
    sess = Session(s, log_path=str(path))
    sess.run_headless(3, report_every=100)
    sess.close()
    rows = list(csv.reader(open(path)))
    assert rows[0][:3] == ["time_s", "node", "kind"]
    assert len(rows) > 10


def test_each_led_joins_the_swarm_on_its_first_flash():
    from fireflysync.link import FireMessage
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm

    class FakeLink:
        oneway_ms = 20.0
        def __init__(self):
            self.inbox, self.out = [], []
        def poll(self, now):
            got, self.inbox = self.inbox, []
            return got
        def send_fire(self, node_id, tx_delay_ms=0):
            self.out.append(node_id)
        def send_hello(self): pass
        def send_ping(self): pass
        def close(self): pass

    link = FakeLink()
    s = Session(Swarm(20, radio_range=9.0, seed=3), link=link)
    n0 = s.swarm.n_virtual
    for k in (1, 2, 3, 1):
        link.inbox.append(FireMessage(f"esp32-L{k}", 0, 0, 0.0))
        s._handle_link()
    assert sorted(s.exts) == ["esp32-L1", "esp32-L2", "esp32-L3"]
    assert s.swarm.n_virtual == n0                     # LEDs are not virtual drones
    assert abs(s.oneway - 0.020) < 1e-9                # measured delay used
    for _ in range(1500):
        s._step()
    assert link.out and all(x.startswith("v") for x in link.out)


# ----- run statistics ----------------------------------------------------------
def _go(s, seconds):
    end = s.swarm.time + seconds
    while s.swarm.time < end:
        s._step()


def test_each_convergence_is_logged_once_with_its_cause():
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm
    s = Session(Swarm(20, radio_range=9.0, seed=3))
    _go(s, 15)
    s.apply("scramble")
    _go(s, 25)
    assert [r.cause for r in s.runs] == ["start", "scramble"]
    assert s.runs[0].cycles == 7.7                      # the known demo layout
    assert all(r.settings == "open floor" for r in s.runs)


def test_switching_a_scenario_while_synced_logs_nothing():
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm
    s = Session(Swarm(20, radio_range=9.0, seed=3))
    _go(s, 15)
    n = len(s.runs)
    s.apply("loss")                                     # already synced: no fake "0 cycles"
    _go(s, 10)
    assert len(s.runs) == n


def test_stats_only_compare_runs_with_the_same_settings(tmp_path):
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm
    s = Session(Swarm(20, radio_range=9.0, seed=3))
    _go(s, 15)
    s.apply("loss")
    s.apply("scramble")
    _go(s, 40)
    open_floor = s.run_stats("open floor")
    lossy = s.run_stats()
    assert open_floor["n"] == 1 and lossy["n"] == 1
    assert lossy["settings"] == "packet loss 10%"
    path = s.save_runs(str(tmp_path / "runs.csv"))
    rows = open(path).read().splitlines()
    assert rows[0].startswith("run,cause,settings") and len(rows) == 3


def test_no_runs_means_no_file(tmp_path):
    from fireflysync.session import Session
    from fireflysync.swarm import Swarm
    assert Session(Swarm(5, seed=1)).save_runs(str(tmp_path / "x.csv")) is None

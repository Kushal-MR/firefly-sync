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

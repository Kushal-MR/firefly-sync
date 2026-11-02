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

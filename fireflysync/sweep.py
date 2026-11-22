"""Headless experiments: many runs over a list of settings, written to CSV.

No pygame anywhere in this call path - importing this file must never open
a window. Every row carries its full settings and seed, so any number in a
figure can be traced back to the exact run that produced it.

Each experiment changes ONE thing and keeps the rest at the demo defaults
(20 drones, 20 x 12 m, radio range 9 m, coupling 0.01). Repeats use seeds
100, 101, ... so every value of the setting is tried on the same layouts.

Two rules keep the comparison fair:
- Only layouts where every drone can (indirectly) hear every other one are
  used. A drone out of everyone's range can never sync, and that would be a
  measurement of the layout, not of the algorithm. If a seed gives a split
  layout, the next seed is tried; the seed actually used is in the CSV.
- In the size experiment the floor grows with the swarm (same drones per
  square metre as the demo: 20 on 20 x 12 m). Five drones on the full floor
  would mostly be out of range of each other.
"""
import csv
import os
from concurrent.futures import ProcessPoolExecutor

from fireflysync import metrics
from fireflysync.session import Session
from fireflysync.swarm import Swarm

BASE = dict(drones=20, radio_range=9.0, area=(20.0, 12.0), coupling=0.01,
            loss=0.0, drift=0.0, speed=0.0, rogues=0, walls=False, door_open=False,
            wall_type="solid", radio_mode="slots", sync_on=True)

# The "collisions" experiment: how each drone decides when to send its data.
TALK_CONDITIONS = {
    0: ("random timing", dict(radio_mode="random", sync_on=True)),
    1: ("timetable, clocks not synced", dict(radio_mode="slots", sync_on=False)),
    2: ("timetable + firefly sync", dict(radio_mode="slots", sync_on=True)),
}
COLLISION_SIZES = [5, 10, 20, 35, 50]
MEASURE_FROM = 30.0     # collisions are counted from here to the end of the run
                        # (a few small swarms take 20-30 s to sync; count the steady state)

# The "walls" experiment: value -> (label, settings). Numbered so they sort in order.
WALL_CONDITIONS = {
    0: ("no wall", dict(walls=False)),
    1: ("thin wall", dict(walls=True, wall_type="thin")),
    2: ("solid wall\n+ 6 m doorway", dict(walls=True, wall_type="solid", door_open=True)),
    3: ("solid wall", dict(walls=True, wall_type="solid")),
}

# name: (setting changed, values, what is measured, run length in seconds)
EXPERIMENTS = {
    "size":   ("drones", [5, 10, 20, 35, 50], "time", 90.0),
    "loss":   ("loss",   [0.0, 0.1, 0.2, 0.3, 0.4, 0.5], "time", 90.0),
    "drift":  ("drift",  [0.0, 0.01, 0.02, 0.05], "time", 90.0),
    "speed":  ("speed",  [0.0, 0.5, 1.0, 1.5], "time", 90.0),
    "rogues": ("rogues", [0, 1, 3, 5], "steady", 60.0),
    "walls":  ("wall",   list(WALL_CONDITIONS), "time", 90.0),
    "collisions": ("condition", list(TALK_CONDITIONS), "collisions", 40.0),
}

FIELDS = ["experiment", "setting", "value", "seed", "drones", "area", "radio_range", "coupling",
          "loss", "drift", "speed", "rogues", "connected", "synced", "time_to_sync_s",
          "cycles_to_sync", "mean_sync_last10s", "min_sync_last10s", "run_seconds",
          "radio_mode", "sync_on", "msgs_sent", "msgs_lost_pct"]

DT = 0.002


def area_for(drones, base=BASE):
    """Floor size with the same density as the demo floor."""
    k = (drones / base["drones"]) ** 0.5
    return (round(base["area"][0] * k, 2), round(base["area"][1] * k, 2))


def make_swarm(c, seed, max_tries=200):
    """The first layout from `seed` on that is connected WITHOUT walls, then
    the walls are put up. So every wall condition is tried on the same
    layouts, and a solid wall really does split a connected swarm.
    Returns (swarm, seed used)."""
    for s in range(seed, seed + max_tries * 1000, 1000):
        sw = Swarm(c["drones"], coupling=c["coupling"], radio_range=c["radio_range"],
                   area=c["area"], seed=s, loss=c["loss"], drift=c["drift"],
                   speed=c["speed"], rogues=c["rogues"])
        if sw.is_connected():
            break
    if c["walls"]:
        sw.door_open = c["door_open"]
        sw.set_walls(True, c["wall_type"])
    return sw, s


def run_once(config, seed, seconds, stop_when_synced=True, measure_from=0.0):
    """One simulation, no window. Returns a result row (dict).
    Messages lost to collisions are counted from `measure_from` seconds on."""
    c = {**BASE, **config}
    sw, seed = make_swarm(c, seed)
    sw.sync_on = c["sync_on"]
    s = Session(sw, dt=DT, radio_mode=c["radio_mode"], radio_seed=seed)
    base = None
    while sw.time < seconds:
        s._step()
        if base is None and sw.time >= measure_from:
            base = (s.radio.sent, s.radio.deliveries, s.radio.lost)
        if stop_when_synced and s.synced_after is not None:
            break
    base = base or (0, 0, 0)
    sent, deliv, lost = (s.radio.sent - base[0], s.radio.deliveries - base[1], s.radio.lost - base[2])
    tail = [lvl for t, lvl in zip(s.times, s.levels) if t >= sw.time - 10.0]
    tts = s.synced_after
    return {
        "seed": seed, "drones": c["drones"], "area": f"{c['area'][0]:g}x{c['area'][1]:g}",
        "radio_range": c["radio_range"],
        "coupling": c["coupling"], "loss": c["loss"], "drift": c["drift"],
        "speed": c["speed"], "rogues": c["rogues"], "connected": sw.is_connected(),
        "synced": tts is not None,
        "time_to_sync_s": None if tts is None else round(tts, 3),
        "cycles_to_sync": None if tts is None else round(metrics.cycles(tts, sw.period), 2),
        "mean_sync_last10s": round(sum(tail) / len(tail), 4) if tail else None,
        "min_sync_last10s": round(min(tail), 4) if tail else None,
        "run_seconds": round(sw.time, 2),
        "radio_mode": c["radio_mode"], "sync_on": c["sync_on"], "msgs_sent": sent,
        "msgs_lost_pct": None if deliv == 0 else round(100 * lost / deliv, 2),
    }


def _job(args):
    name, setting, value, seed, seconds, stop, extra = args
    config = {setting: value}
    if setting == "wall":
        config = dict(WALL_CONDITIONS[value][1])
    if setting == "condition":
        config = dict(TALK_CONDITIONS[value][1])
    config.update(extra)
    if "drones" in config and "area" not in config:
        config["area"] = area_for(config["drones"])
    row = run_once(config, seed, seconds, stop,
                   measure_from=MEASURE_FROM if setting == "condition" else 0.0)
    return {"experiment": name, "setting": setting, "value": value, **row}


def sweep(name, repeats, out_path, workers=None, progress=print):
    """Run one named experiment. Rows are written as they finish, so a sweep
    that dies part-way still leaves everything it finished on disk."""
    setting, values, measure, seconds = EXPERIMENTS[name]
    stop = measure == "time"
    sizes = COLLISION_SIZES if name == "collisions" else [None]
    jobs = [(name, setting, v, 100 + r, seconds, stop, {} if n is None else {"drones": n})
            for n in sizes for v in values for r in range(repeats)]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="") as f, ProcessPoolExecutor(workers) as pool:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for k, row in enumerate(pool.map(_job, jobs), 1):
            w.writerow(row)
            f.flush()
            if progress and (k % max(1, len(jobs) // 10) == 0 or k == len(jobs)):
                progress(f"  {name}: {k}/{len(jobs)} runs")
    return out_path


def load(path):
    """Read a sweep CSV back with numbers as numbers."""
    def num(x):
        if x in ("", "None"):
            return None
        if x in ("True", "False"):
            return x == "True"
        try:
            return int(x)
        except ValueError:
            return float(x)
    with open(path, newline="") as f:
        return [{k: (v if k in ("experiment", "setting", "area", "radio_mode") else num(v)) for k, v in row.items()}
                for row in csv.DictReader(f)]


def summarise(rows):
    """Per value: n, % synced, mean/std cycles-to-sync (synced runs only),
    mean of the steady-state sync level."""
    import statistics as st
    out = []
    for v in sorted({r["value"] for r in rows}):
        rs = [r for r in rows if r["value"] == v]
        cyc = [r["cycles_to_sync"] for r in rs if r["synced"] and r["cycles_to_sync"] is not None]
        steady = [r["mean_sync_last10s"] for r in rs if r["mean_sync_last10s"] is not None]
        lows = [r["min_sync_last10s"] for r in rs if r["min_sync_last10s"] is not None]
        out.append({
            "value": v, "n": len(rs),
            "pct_synced": 100.0 * sum(r["synced"] for r in rs) / len(rs),
            "pct_connected": 100.0 * sum(r["connected"] for r in rs) / len(rs),
            "cycles_mean": st.mean(cyc) if cyc else None,
            "cycles_std": st.stdev(cyc) if len(cyc) > 1 else 0.0,
            "cycles_median": st.median(cyc) if cyc else None,
            "steady_mean": st.mean(steady) if steady else None,
            "steady_std": st.stdev(steady) if len(steady) > 1 else 0.0,
            "steady_min": min(lows) if lows else None,
        })
    return out

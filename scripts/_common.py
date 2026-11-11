"""Command-line options shared by run_sim.py and run_live.py."""
import argparse
import datetime
import os
import sys

# Let `python scripts/run_sim.py` find the fireflysync package from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def swarm_args(desc):
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--drones", type=int, default=20, help="number of virtual drones")
    ap.add_argument("--period", type=float, default=1.0, help="seconds per flash cycle")
    ap.add_argument("--coupling", type=float, default=0.01, help="how hard ONE flash pulls a neighbour")
    ap.add_argument("--dissipation", type=float, default=3.0, help="how lopsided the pull is")
    ap.add_argument("--refractory", type=float, default=0.05, help="ignore window after firing (fraction of period)")
    ap.add_argument("--range", type=float, default=9.0, dest="radio_range",
                    help="radio range in metres (0 = everyone hears everyone)")
    ap.add_argument("--area", default="20x12", help="floor plan size in metres, WxH")
    ap.add_argument("--seed", type=int, default=3,
                    help="layout + start (3 = known-good demo layout, ~8 s to sync)")
    ap.add_argument("--dt", type=float, default=0.002, help="simulation step in seconds")
    ap.add_argument("--no-window", action="store_true", help="run without the pygame window")
    ap.add_argument("--seconds", type=float, default=None, help="stop after this long")
    ap.add_argument("--log", action="store_true", help="save every flash to data/*.csv")
    sc = ap.add_argument_group("scenarios (also switchable live with keys)")
    sc.add_argument("--walls", action="store_true", help="wall splits the floor into two rooms (W)")
    sc.add_argument("--door-open", action="store_true", help="open the doorway in the wall (D)")
    sc.add_argument("--rogues", type=int, default=0, help="number of faulty drones firing at random (X)")
    sc.add_argument("--drift", type=float, default=0.0, help="clock drift std, e.g. 0.02 = ±2%% (C)")
    sc.add_argument("--move", type=float, default=0.0, dest="speed", help="drone speed in m/s (M)")
    sc.add_argument("--loss", type=float, default=0.0, help="fraction of flashes lost, e.g. 0.3 (P)")
    return ap


def parse_area(s):
    w, h = s.lower().split("x")
    return float(w), float(h)


def make_swarm(args):
    from fireflysync.swarm import Swarm
    return Swarm(args.drones, period=args.period, coupling=args.coupling,
                 dissipation=args.dissipation, refractory=args.refractory,
                 radio_range=args.radio_range or None, area=parse_area(args.area), seed=args.seed,
                 walls=args.walls, door_open=args.door_open, loss=args.loss, drift=args.drift,
                 speed=args.speed, rogues=args.rogues)


def log_path(prefix):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(root, "data", f"{prefix}_{stamp}.csv")

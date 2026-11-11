"""Run the experiments and write the results to data/sweep_<name>.csv.

    python scripts/run_sweep.py                    every experiment, 50 repeats (about a minute)
    python scripts/run_sweep.py --experiment size  just one
    python scripts/run_sweep.py --repeats 2        quick check of the pipeline

Experiments (each changes ONE thing, see fireflysync/sweep.py):
    size     5, 10, 20, 35, 50 drones           -> cycles to sync
    loss     0 - 50 % of flashes lost            -> cycles to sync
    drift    clocks 0 - 5 % fast or slow         -> cycles to sync
    speed    drones moving 0 - 1.5 m/s           -> cycles to sync
    rogues   0, 1, 3, 5 faulty drones            -> steady sync level

Then:  python scripts/plot_results.py
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fireflysync.sweep import EXPERIMENTS, summarise, sweep, load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiment", choices=list(EXPERIMENTS) + ["all"], default="all")
    ap.add_argument("--repeats", type=int, default=50)
    ap.add_argument("--workers", type=int, default=None, help="parallel processes (default: all cores)")
    args = ap.parse_args()
    names = list(EXPERIMENTS) if args.experiment == "all" else [args.experiment]
    for name in names:
        t0 = time.time()
        path = os.path.join(ROOT, "data", f"sweep_{name}.csv")
        print(f"{name}: {len(EXPERIMENTS[name][1]) * args.repeats} runs ...")
        sweep(name, args.repeats, path, args.workers)
        print(f"  wrote {os.path.relpath(path, ROOT)} in {time.time() - t0:.0f} s")
        for s in summarise(load(path)):
            cyc = "never" if s["cycles_mean"] is None else f"{s['cycles_mean']:5.1f} ± {s['cycles_std']:4.1f} cycles"
            print(f"    {EXPERIMENTS[name][0]}={s['value']:<5}  synced {s['pct_synced']:5.1f}%  {cyc}"
                  f"  steady sync {s['steady_mean']:.3f}")


if __name__ == "__main__":
    main()

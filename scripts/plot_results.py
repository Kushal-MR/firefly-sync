"""Turn data/sweep_*.csv into the report figures in data/figures/.

    python scripts/run_sweep.py        first, makes the CSVs (about a minute)
    python scripts/plot_results.py     then this

Every figure comes from the CSVs - nothing typed in by hand - so any number
in the report can be regenerated with these two commands. Also writes
data/figures/summary.md, a table to paste into the report.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib.pyplot as plt  # noqa: E402

from analysis.plots import footnote, spread_plot, style  # noqa: E402
from fireflysync.sweep import (COLLISION_SIZES, EXPERIMENTS, TALK_CONDITIONS,  # noqa: E402
                               WALL_CONDITIONS, load, summarise)

DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "figures")

CYCLES = "Cycles to sync (flashes)"
SPECS = {   # experiment: (x label, title, x formatter)
    "size":  ("Swarm size (drones)", "Bigger swarms take only a little longer", str),
    "loss":  ("Flashes lost", "Sync survives heavy packet loss", lambda v: f"{100 * v:.0f}%"),
    "drift": ("Clock error (typical, each drone's own)", "Small clock errors barely matter",
              lambda v: f"±{100 * v:.0f}%"),
    "speed": ("Drone speed (m/s)", "Moving drones still sync", lambda v: f"{v:g}"),
    "walls": ("Wall between the two halves of the floor", "Walls only stop sync if they block every signal",
              lambda v: WALL_CONDITIONS[int(v)][0]),
}
NOTE = ("Each dot is one run (random layout, all drones connected). Line = mean, band = ±1 std.\n"
        "Synced = sync level ≥ 95% held for 2 s. Demo settings: 20 drones on 20×12 m, radio range 9 m, coupling 0.01.")


def load_exp(name):
    path = os.path.join(DATA, f"sweep_{name}.csv")
    if not os.path.exists(path):
        return None, None
    rows = load(path)
    if name == "walls":
        # Behind a solid wall the rooms never exchange a single flash. A few runs
        # still pass the 95 % test because the two separate rhythms happen to
        # start a few % of a cycle apart. That is luck, not sync: no time shown.
        for r in rows:
            if not r["connected"]:
                r["cycles_to_sync"] = None
        summ = summarise(rows)
        for s in summ:
            if not any(r["connected"] for r in rows if r["value"] == s["value"]):
                s["cycles_mean"] = None
        return rows, summ
    return rows, summarise(rows)


def wall_notes(rows, summ):
    """Label under the solid-wall column: why there is no point there."""
    out = {}
    for s in summ:
        if s["cycles_mean"] is None:
            out[s["value"]] = f"never connected\n({s['pct_synced']:.0f}% in step by chance)"
    return out


def fig_cycles(name, rows, summ):
    xl, title, fmt = SPECS[name]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    spread_plot(ax, rows, summ, "cycles_to_sync", "cycles_mean", "cycles_std", xl, CYCLES, title, fmt,
                notes=wall_notes(rows, summ) if name == "walls" else None, connect=name != "walls")
    note = NOTE + ("\nFloor grows with the swarm so density stays the same." if name == "size" else "")
    if name == "walls":
        note = note.replace("Line = mean, band = ±1 std.", "Dot = mean, whisker = ±1 std.")
        note += ("\nThin wall: radio passes through, but only up to 4.5 m (half the normal range)."
                 " Same 50 layouts for every column.")
    footnote(fig, note, y=-0.08 if name == "walls" else -0.02)
    return fig


# validated categorical slots 1-3 (dataviz reference palette: safe for colour-blind readers)
TALK_COLOURS = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a"}


def collision_summary(rows):
    import statistics as st
    out = {}
    for v in TALK_CONDITIONS:
        for n in COLLISION_SIZES:
            xs = [r["msgs_lost_pct"] for r in rows if r["value"] == v and r["drones"] == n
                  and r["msgs_lost_pct"] is not None]
            if xs:
                out[(v, n)] = (st.mean(xs), st.stdev(xs) if len(xs) > 1 else 0.0, len(xs))
    return out


def collisions_plot(ax, rows, label_lines=True):
    summ = collision_summary(rows)
    xs = list(range(len(COLLISION_SIZES)))
    for v, (label, _) in TALK_CONDITIONS.items():
        pts = [(i, *summ[(v, n)][:2]) for i, n in enumerate(COLLISION_SIZES) if (v, n) in summ]
        if not pts:
            continue
        x, m, sd = zip(*pts)
        col = TALK_COLOURS[v]
        ax.fill_between(x, [max(0, a - b) for a, b in zip(m, sd)], [min(100, a + b) for a, b in zip(m, sd)],
                        color=col, alpha=0.12, linewidth=0)
        ax.plot(x, m, color=col, linewidth=2.2, marker="o", markersize=7,
                markeredgecolor="white", markeredgewidth=1.5, label=label)
        if label_lines:                          # direct label at the right end
            nudge = {0: 9, 1: -9}.get(v, 0)         # the two "no sync" lines end together
            ax.annotate(label, (x[-1], m[-1]), textcoords="offset points", xytext=(10, nudge),
                        va="center", fontsize=9.5, color="#1f2430")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(n) for n in COLLISION_SIZES])
    ax.set_xlim(-0.3, len(xs) - 1 + (1.9 if label_lines else 0.3))
    ax.set_ylim(-2, 100)
    ax.set_xlabel("Swarm size (drones)")
    ax.set_ylabel("Messages lost to collisions (%)")
    ax.set_title("Firefly sync + a timetable removes collisions", loc="left")
    ax.legend(loc="upper right", fontsize=8.5, frameon=False) if not label_lines else None
    return summ


def fig_collisions(rows):
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    collisions_plot(ax, rows)
    footnote(fig, "Each drone sends one data message per cycle. Line = mean of 50 runs, band = ±1 std; "
                  "measured from 30 s to 40 s.\nTimetable = one time slot per drone, timed by the drone's "
                  "own firefly clock. Collision = a receiver hears two drones talking at once.\n"
                  "Bigger swarms = more, thinner slots (1/N of a cycle each), so messages are shorter: "
                  "that is why losses without sync fall with size.")
    return fig


def fig_rogues(rows, summ):
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    spread_plot(ax, rows, summ, "mean_sync_last10s", "steady_mean", "steady_std",
                "Rogue (faulty) drones firing at random", "Sync level of healthy drones",
                "One faulty drone is harmless; five can break it", str, ylim=(0, 1.05), note_synced=False,
                  cap=1.0, vfmt=lambda v: f"{100 * v:.0f}%")
    ax.axhline(0.95, color="#059669", linewidth=1, linestyle="--", zorder=0)
    ax.annotate("95% = synchronized", (0, 0.95), xycoords=("axes fraction", "data"),
                textcoords="offset points", xytext=(4, 4), fontsize=8.5, color="#059669")
    footnote(fig, "Each dot is one 60 s run; value = average sync of the healthy drones over the last 10 s.\n"
                  "Rogues are the best-connected drones (worst case). 20 drones, 20×12 m, radio range 9 m.")
    return fig


def overview(data):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.2))
    coll = load(os.path.join(DATA, "sweep_collisions.csv")) if os.path.exists(
        os.path.join(DATA, "sweep_collisions.csv")) else None
    if coll:
        collisions_plot(axes.flat[0], coll, label_lines=False)
    panels = [(1, "size"), (2, "loss"), (3, "drift"), (5, "walls")] if coll else \
             [(0, "size"), (1, "loss"), (2, "drift"), (3, "speed"), (5, "walls")]
    for ax, name in [(axes.flat[i], n) for i, n in panels]:
        rows, summ = data[name]
        if rows:
            xl, title, fmt = SPECS[name]
            spread_plot(ax, rows, summ, "cycles_to_sync", "cycles_mean", "cycles_std", xl, CYCLES, title, fmt,
                        notes=wall_notes(rows, summ) if name == "walls" else None, connect=name != "walls")
    rows, summ = data["rogues"]
    ax = axes.flat[4]
    if rows:
        spread_plot(ax, rows, summ, "mean_sync_last10s", "steady_mean", "steady_std",
                    "Rogue drones", "Sync level of healthy drones", "One faulty drone is harmless", str,
                    ylim=(0, 1.05), note_synced=False, cap=1.0, vfmt=lambda v: f"{100 * v:.0f}%")
    fig.suptitle("FireSync: robustness at a glance", x=0.01, ha="left", fontsize=16, weight="bold")
    fig.tight_layout()
    footnote(fig, NOTE)
    return fig


def summary_md(data):
    lines = ["# FireSync experiment results", "",
             "Generated by `scripts/plot_results.py` from `data/sweep_*.csv`.", ""]
    for name, (setting, _, measure, seconds) in EXPERIMENTS.items():
        rows, summ = data[name]
        if not rows:
            continue
        if name == "collisions":
            cs = collision_summary(rows)
            lines += ["## collisions  (% of messages lost, mean ± std, 50 runs per cell, 30-40 s)", "",
                      "| drones | " + " | ".join(l for l, _ in TALK_CONDITIONS.values()) + " |",
                      "|---|" + "---|" * len(TALK_CONDITIONS)]
            for n in COLLISION_SIZES:
                cells = [f"{cs[(v, n)][0]:.1f}% ± {cs[(v, n)][1]:.1f}" if (v, n) in cs else "-"
                         for v in TALK_CONDITIONS]
                lines.append(f"| {n} | " + " | ".join(cells) + " |")
            lines.append("")
            continue
        lines += [f"## {name}  (changing `{setting}`, {summ[0]['n']} runs per value)", ""]
        label = (lambda v: WALL_CONDITIONS[int(v)][0].replace("\n", " ")) if name == "walls" else str
        if measure == "time":
            lines += ["| value | synced | cycles to sync (mean ± std) | median |", "|---|---|---|---|"]
            for s in summ:
                c = "-" if s["cycles_mean"] is None else f"{s['cycles_mean']:.1f} ± {s['cycles_std']:.1f}"
                if s["cycles_mean"] is None and name == "walls":
                    c = "never - rooms can't hear each other (the % is runs in step by chance)"
                md = "-" if s["cycles_median"] is None else f"{s['cycles_median']:.1f}"
                lines.append(f"| {label(s['value'])} | {s['pct_synced']:.0f}% | {c} | {md} |")
        else:
            lines += ["| value | sync of healthy drones (mean ± std) | worst moment |", "|---|---|---|"]
            for s in summ:
                lines.append(f"| {s['value']} | {100 * s['steady_mean']:.1f}% ± {100 * s['steady_std']:.1f} "
                             f"| {100 * s['steady_min']:.0f}% |")
        lines.append("")
    return "\n".join(lines)


def main():
    style()
    os.makedirs(OUT, exist_ok=True)
    data = {n: load_exp(n) for n in EXPERIMENTS}
    if not any(r for r, _ in data.values()):
        sys.exit("No data/sweep_*.csv yet - run  python scripts/run_sweep.py  first.")
    made = []
    for name in SPECS:
        rows, summ = data[name]
        if rows:
            made.append((f"fig_{name}.png", fig_cycles(name, rows, summ)))
    if data["rogues"][0]:
        made.append(("fig_rogues.png", fig_rogues(*data["rogues"])))
    coll_path = os.path.join(DATA, "sweep_collisions.csv")
    if os.path.exists(coll_path):
        made.append(("fig_collisions.png", fig_collisions(load(coll_path))))
    made.append(("fig_overview.png", overview(data)))
    for fname, fig in made:
        fig.savefig(os.path.join(OUT, fname))
        plt.close(fig)
        print("wrote", os.path.join("data", "figures", fname))
    with open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md(data))
    print("wrote", os.path.join("data", "figures", "summary.md"))


if __name__ == "__main__":
    main()

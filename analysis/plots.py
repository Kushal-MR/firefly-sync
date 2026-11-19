"""Plot helpers shared by the report figures (called by scripts/plot_results.py).

One style for every figure: one colour for the data, grey for everything
else, the spread across repeats always shown (each run as a faint dot, the
mean as a line, mean ± 1 std as a band). Saved at 200 dpi so they survive
being pasted into slides.
"""
import random

import matplotlib

matplotlib.use("Agg")                       # never open a window
import matplotlib.pyplot as plt             # noqa: E402

INK = "#1f2430"
MUTED = "#6b7280"
GRID = "#e5e7eb"
DATA = "#2563eb"
BAND = "#93c5fd"
WARN = "#b45309"


def style():
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.labelcolor": INK, "axes.edgecolor": GRID, "axes.linewidth": 1,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight",
    })


def spread_plot(ax, rows, summary, y_key, mean_key, std_key, xlabel, ylabel, title,
                xfmt=str, ylim=None, note_synced=True, cap=None, vfmt=None, notes=None,
                connect=True):
    """connect=False for separate conditions (not a trend): no line, no band,
    the mean shown as a short bar with a ±1 std whisker."""
    """Individual runs as faint dots, mean line with markers, ±1 std band."""
    xs = [s["value"] for s in summary]
    pos = {v: i for i, v in enumerate(xs)}               # even spacing, real labels
    rnd = random.Random(0)
    dots = [(pos[r["value"]] + rnd.uniform(-0.12, 0.12), r[y_key]) for r in rows if r[y_key] is not None]
    if dots:
        ax.scatter(*zip(*dots), s=9, color=DATA, alpha=0.18, linewidths=0, zorder=2)
    pts = [(pos[s["value"]], s[mean_key], s[std_key]) for s in summary if s[mean_key] is not None]
    x, m, sd = zip(*pts)
    lo = [a - b for a, b in zip(m, sd)]
    hi = [a + b for a, b in zip(m, sd)]
    if cap is not None:                                    # a level can't exceed 100%
        hi = [min(cap, h) for h in hi]
    if connect:
        ax.fill_between(x, lo, hi, color=BAND, alpha=0.35, linewidth=0, zorder=1)
        ax.plot(x, m, color=DATA, linewidth=2, marker="o", markersize=7, zorder=3,
                markeredgecolor="white", markeredgewidth=1.5)
    else:
        ax.errorbar(x, m, yerr=sd, fmt="o", color=DATA, markersize=7, capsize=5, elinewidth=1.5,
                    markeredgecolor="white", markeredgewidth=1.5, zorder=3)
    for xi, mi in zip(x, m):
        label = vfmt(mi) if vfmt else (f"{mi:.1f}" if mi < 10 else f"{mi:.0f}")
        ax.annotate(label, (xi, mi), textcoords="offset points",
                    xytext=(0, 9) if connect else (10, 0), ha="center" if connect else "left",
                    va="baseline" if connect else "center", fontsize=9, color=INK, zorder=4)
    for v, text in (notes or {}).items():                  # custom label instead of "% synced"
        ax.annotate(text, (pos[v], 0), xycoords=("data", "axes fraction"), textcoords="offset points",
                    xytext=(0, 6), ha="center", va="bottom", fontsize=8.5, color=WARN)
    if note_synced:
        for s in summary:
            if s["pct_synced"] < 100 and s["value"] not in (notes or {}):
                ax.annotate(f"{s['pct_synced']:.0f}% synced", (pos[s["value"]], 0), xycoords=("data", "axes fraction"),
                            textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8.5, color=WARN)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels([xfmt(v) for v in xs])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    if ylim:
        ax.set_ylim(*ylim)
    else:
        ax.set_ylim(bottom=0)


def footnote(fig, text, y=-0.02):
    fig.text(0.01, y, text, fontsize=8.5, color=MUTED, ha="left", va="top")

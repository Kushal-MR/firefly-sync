# Experiments

What Phase 3 measures, and how.

## Results so far (Phase 3a, plain firefly rule)

Run with `python scripts/run_sweep.py` (50 runs per value, ~1 min), then
`python scripts/plot_results.py`. Figures: `docs/results/fig_*.png`.

How each run works: random layout (seed 100, 101, …; only layouts where
every drone is connected), all drones start at random phases, run until the
sync level of the healthy drones stays ≥ 95 % for 2 s (max 90 s). Rogue runs
last 60 s and report the average sync of the healthy drones over the last
10 s. Swarm-size runs grow the floor with the swarm so density stays the same.

What we learned:
- **Size:** 5 → 50 drones only goes 11 → 13 cycles. It does not blow up.
- **Loss:** each 10 % of lost flashes costs ~2 cycles; even at 50 % loss
  98 % of runs still sync.
- **Drift:** ±1–2 % clock error changes nothing; ±5 % slows it and 12 % of
  runs no longer hold 95 % (clocks pull apart faster than nudges fix them).
- **Movement:** up to 1.5 m/s no slowdown; moving even helps a little,
  because drones meet more neighbours.
- **Rogues:** one is harmless. With 3–5, most runs stay near 100 % but a
  few layouts break badly (likely where the rogues sit between two groups of drones; not yet checked).
- **Walls:** two rooms keep two separate rhythms; a 6 m doorway merges them
  in ~20 s. 2–3 m doorways often never merge (too few drones see through).


### size  (changing `drones`, 50 runs per value)

| value | synced | cycles to sync (mean ± std) | median |
|---|---|---|---|
| 5 | 100% | 10.9 ± 8.0 | 8.4 |
| 10 | 100% | 9.7 ± 5.2 | 9.0 |
| 20 | 100% | 9.3 ± 6.1 | 8.3 |
| 35 | 98% | 10.4 ± 5.7 | 9.5 |
| 50 | 96% | 12.6 ± 6.9 | 10.5 |

### loss  (changing `loss`, 50 runs per value)

| value | synced | cycles to sync (mean ± std) | median |
|---|---|---|---|
| 0.0 | 100% | 9.3 ± 6.1 | 8.3 |
| 0.1 | 100% | 10.0 ± 5.6 | 9.2 |
| 0.2 | 100% | 12.2 ± 6.7 | 11.2 |
| 0.3 | 100% | 13.4 ± 6.6 | 13.4 |
| 0.4 | 100% | 17.8 ± 9.9 | 15.3 |
| 0.5 | 98% | 20.6 ± 11.3 | 16.8 |

### drift  (changing `drift`, 50 runs per value)

| value | synced | cycles to sync (mean ± std) | median |
|---|---|---|---|
| 0.0 | 100% | 9.3 ± 6.1 | 8.3 |
| 0.01 | 100% | 9.4 ± 4.8 | 8.7 |
| 0.02 | 100% | 10.4 ± 5.9 | 9.1 |
| 0.05 | 88% | 18.5 ± 16.5 | 14.9 |

### speed  (changing `speed`, 50 runs per value)

| value | synced | cycles to sync (mean ± std) | median |
|---|---|---|---|
| 0.0 | 100% | 9.3 ± 6.1 | 8.3 |
| 0.5 | 100% | 9.0 ± 5.3 | 8.2 |
| 1.0 | 100% | 9.0 ± 5.4 | 8.1 |
| 1.5 | 100% | 8.1 ± 3.3 | 8.1 |

### rogues  (changing `rogues`, 50 runs per value)

| value | sync of healthy drones (mean ± std) | worst moment |
|---|---|---|
| 0 | 100.0% ± 0.0 | 100% |
| 1 | 100.0% ± 0.0 | 98% |
| 3 | 97.1% ± 12.1 | 6% |
| 5 | 86.9% ± 23.4 | 2% |

---

## Still to do (Phase 3b)

---

## What we measure

**Time to sync** — how long from a random start until every node fires
together within a small tolerance. Report in seconds and in cycles.

**Phase spread** — how far apart the nodes' phases are at a given moment.
Falls toward zero as they sync. This is the number plotted live in Phase 1.

**Steady-state error** — the phase spread that remains once things settle.
Shows sync quality, not just whether it happened.

**Did it sync at all** — under enough delay or loss, some runs never
converge. The fraction that fail is itself a result.

---

## The runs

Every experiment compares **simple pulse-coupled** against **Reachback**
under identical conditions. Repeat each setting at least 20 times and report
the average with the spread, because the simulation is random.

### 1. Delay

| Setting | Values |
|---------|--------|
| One-way delay | 0, 10, 25, 50, 100, 200 ms |
| Swarm size | 20 |
| Loss | 0% |

Expected: the simple rule degrades as delay rises; Reachback holds longer.

### 2. Packet loss

| Setting | Values |
|---------|--------|
| Loss | 0, 5, 10, 20, 40% |
| Delay | fixed at the value Phase 0 measured |
| Swarm size | 20 |

### 3. Swarm size

| Setting | Values |
|---------|--------|
| Drones | 5, 10, 20, 35, 50 |
| Delay, loss | fixed, realistic |

The question is the shape of the curve, not the exact numbers: does
cycles-to-sync stay bounded as the swarm grows, or blow up?

### 4. Late joiner

One drone joins a swarm that is already synced.

- How many cycles until it locks on?
- Does the phase spread of the existing swarm get worse while it joins?

---

## Hardware runs

Repeat experiments 1 and 2 with the real ESP32 in the loop, then plot
simulation and hardware on the same axes.

**Remember the measurement bias.** The laptop sees a fire only when the
message arrives, so the real drone always looks slightly late. Subtract half
the typical round-trip time from Phase 0, and verify once with slow-motion
video.

Where simulation and hardware disagree, the likely causes are Wi-Fi jitter
and the board's clock running slightly fast or slow. Saying so, with numbers,
is a better result than a perfect match.

---

## Figures for the report

1. Time-to-sync vs delay — two lines, simple vs Reachback
2. Steady-state phase spread vs packet loss — two lines
3. Cycles-to-sync vs swarm size
4. Phase spread over time for a late joiner
5. Simulation vs hardware on the same axes

All five generated by `scripts/plot_results.py` from logged data in `data/`.
Nothing hand-drawn, nothing typed in by hand.

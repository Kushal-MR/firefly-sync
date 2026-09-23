# firefly-sync

**Firefly-Inspired Timing Sync for Drone Swarms**

Bio-Inspired Engineering — Experiential Learning, RV College of Engineering.

---

## What this is

Fireflies flash in unison with no leader. Each one nudges its own rhythm
forward a little whenever it sees a neighbour flash, and the whole swarm
falls into step.

Indoor drone swarms have the same problem. Outdoors they use GPS as a shared
clock; inside warehouses, tunnels and mines GPS does not reach, and without
shared timing they talk over each other and lose messages.

This project builds a **virtual swarm of drones on a laptop** and connects
**one real drone — an ESP32 board with an LED — over Wi-Fi**, then measures
whether firefly synchronization still works on cheap, everyday hardware.

## The research gap

Firefly synchronization has been proved in maths (1990), demonstrated on
special sensor radios (2005), on FPGA research radios (2016), on electronic
firefly circuits and on real flying drones (2025). Every one of those used
specialised or costly hardware.

**Nobody has tested it on a cheap everyday Wi-Fi board like the ESP32.**
That is what we test. See `docs/ALGORITHM.md` for the papers.

## Repository layout

```
firefly-sync/
├── fireflysync/        the Python package (all the logic lives here)
│   ├── oscillator.py   the firefly rule itself — pure, no I/O
│   ├── swarm.py        N drones, positions, who can hear whom
│   ├── metrics.py      time-to-sync and phase spread
│   ├── view.py         live pygame window
│   ├── link.py         UDP link to the real ESP32
│   ├── channel.py      artificial delay and packet loss
│   ├── reachback.py    the Reachback Firefly Algorithm
│   └── sweep.py        headless runs for parameter sweeps
├── scripts/            things you actually run
├── firmware/           Arduino sketches for the ESP32
├── analysis/           plotting code
├── data/               run logs (not committed)
├── tests/              unit tests
└── docs/               PLAN, ALGORITHM, HARDWARE, EXPERIMENTS
```

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python scripts/run_sim.py     # Phase 1: virtual swarm only
```

## Status

Planning stage. No code written yet — every module is a stub describing what
goes in it. Read `docs/PLAN.md` before writing anything.

| Phase | What it delivers | State |
|-------|------------------|-------|
| 0 | Wi-Fi round-trip latency test (the risk check) | not started |
| 1 | Virtual swarm that synchronizes, on screen | not started |
| 2 | Real ESP32 + LED joins the swarm over Wi-Fi | not started |
| 3 | Reachback algorithm, experiments, graphs | not started |

## Team

| USN | Name |
|-----|------|
| 1RV25CS091 | Kushal M R |
| 1RV25CS093 | Lakkuru Ramteja |
| 1RV25CS089 | K Pushkar Sai |
| 1RV25CS083 | Kola Krishna Kaushal |

## Licence

MIT — see `LICENSE`.

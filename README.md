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

Leaderless synchronization has been shown in theory (Nature Communications,
2024), in drone-network simulations (IEEE Transactions on Wireless
Communications, 2024), across wired datacenter servers (ACM SIGCOMM, 2025),
on real drones with external tracking (IEEE BalkanCom, 2025) and on special
sensor radios (ACM SenSys, 2005).

**Nobody has tested leaderless firefly sync on cheap ESP32 Wi-Fi.**
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
pip install -r requirements.txt
python -m pytest                                   # 46 tests
python scripts/run_sim.py                          # virtual swarm in a window
python scripts/fake_esp32.py                       # terminal 1: pretend ESP32
python scripts/run_live.py --peer 127.0.0.1        # terminal 2: swarm + "ESP32"
```

With the real board, see `docs/DEMO.md`.

## Status

| Phase | What it delivers | State |
|-------|------------------|-------|
| 0 | Wi-Fi round-trip latency test (the risk check) | done - ESP32 connects over hotspot |
| 1 | Virtual swarm that synchronizes, on screen | done |
| 2 | Real ESP32 + LED joins the swarm over Wi-Fi | built and tested with a simulated ESP32; hardware test next |
| 3 | Reachback algorithm, experiments, graphs | not started |

## Licence

MIT — see `LICENSE`.

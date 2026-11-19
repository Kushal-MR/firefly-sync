# AGENTS.md — read this before changing anything

Guide for AI coding agents (and humans) working on this repo.

## What this project is

**FireSync** — firefly-inspired timing synchronization for drone swarms
(Bioinspired Engineering course project, RVCE).

A laptop simulates ~20 virtual drones on a 20 × 12 m floor plan. Each drone
is a Mirollo–Strogatz pulse-coupled oscillator: a phase rises 0 → 1, fires
("flash"), resets, and is nudged forward when a neighbour in radio range
fires. The swarm synchronizes with no leader. **A real ESP32 with six LEDs
joins over Wi-Fi (UDP); each LED is its own firefly** (`esp32-L1` …
`esp32-L6`) and falls into the same rhythm.

On top of that, six live scenarios test robustness: walls + doorway, rogue
drones, clock drift, moving drones, packet loss (and swarm size in the
experiments). Phase 3b (not started) compares the plain rule with the
**Reachback Firefly Algorithm** (Werner-Allen et al., 2005) under delay.

## Team split

- **Code** (this repo's Python, the window, experiments): Kushal + AI.
- **ESP team** (wiring, flashing, hotspot): `docs/HARDWARE.md` is their
  step-by-step guide; `docs/DEMO.md` is the evaluation script. If you are
  helping the ESP team, start there and do not change the protocol.

## The one architecture rule

**The algorithm must not know about the screen, the network, or the clock.**

| Layer | Files | May import |
|---|---|---|
| Pure core | `fireflysync/oscillator.py`, `swarm.py`, `geometry.py`, `metrics.py`, (3b) `channel.py`, `reachback.py` | each other, stdlib, numpy |
| I/O | `view.py` (pygame), `link.py` (UDP) | core |
| Orchestration | `session.py` (owns time + loop), `sweep.py`, `scripts/*` | anything |

- Core code is handed `dt` and told when a neighbour fired. It never calls
  `time.time()`, never opens sockets, never imports pygame.
- `view.py` only **reads** the session and draws. Keys come back from
  `View.handle_events()` as action strings (`"walls"`, `"door"`, `"rogue"`,
  `"drift"`, `"move"`, `"loss"`, `"scramble"`, `"pause"`, `"quit"`);
  `Session.apply(action)` changes the swarm and returns the toast text.
- Test of the rule: `python scripts/run_sim.py --no-window --seconds 60` must
  work, and importing `fireflysync.sweep` must not import pygame.

## File map

| Path | What it does | State |
|---|---|---|
| `fireflysync/oscillator.py` | One firefly: phase, fire, nudge (concave M-S curve), refractory window | done |
| `fireflysync/swarm.py` | Drones, positions, radio range + walls, cascades, external (real) nodes, scenarios: `set_walls/set_door/set_loss/set_drift/set_speed/set_rogues`, `healthy_phases` (excludes rogues and real LEDs) | done |
| `fireflysync/geometry.py` | `segments_cross`, `blocked`, `two_rooms(area, door_open, door_width=6.0)` (thin/solid logic is in `swarm._hears`) | done |
| `fireflysync/metrics.py` | Sync level (Kuramoto order parameter), circular mean, offset in ms, `time_to_sync`, `cycles`, `rhythm_groups` | done |
| `fireflysync/session.py` | Run loop (real-time or headless), adds each LED on its first FIRE, HELLO/PING timers, scenario `apply()`, sync clock, CSV log | done |
| `fireflysync/link.py` | UDP: FIRE parse/format, HELLO discovery, PING round-trip → `oneway_ms` | done |
| `fireflysync/view.py` | pygame UI, scales to any window (design 1280×720 × factor) | done |
| `fireflysync/sweep.py` | Headless experiments in parallel → `data/sweep_<name>.csv` | done |
| `analysis/plots.py`, `scripts/plot_results.py` | Figures + `summary.md` into `data/figures/` | done |
| `scripts/run_sweep.py` | Runs the experiments (`--experiment`, `--repeats 50`) | done |
| `scripts/run_sim.py` | Virtual swarm only; scenario flags | done |
| `scripts/run_live.py` | Swarm + ESP32; `--peer` optional, `--oneway-ms` optional | done |
| `scripts/fake_esp32.py` | Python twin of the firmware (6 LEDs) for testing without hardware | done |
| `scripts/_common.py` | Shared CLI flags and defaults | done |
| `scripts/latency_test.py` + `firmware/latency_test/` | Phase 0 Wi-Fi round-trip test | done |
| `firmware/esp32_firefly/esp32_firefly.ino` | The real board: N LEDs, each a firefly | written, **needs first compile + run on hardware** |
| `fireflysync/channel.py`, `reachback.py` | Artificial delay, Reachback | **stub — Phase 3b** |
| `*.bat` | Windows launchers, use `.venv\Scripts\python.exe` | done |
| `tests/` | pytest suite (80 tests) | done |
| `docs/` | `PLAN`, `ALGORITHM` (papers), `HARDWARE` (ESP team guide), `DEMO` (evaluation script), `EXPERIMENTS`, `results/` (committed figures) | |

## Invariants — do not break these

- **Settings must match between laptop and firmware**: period 1.0 s,
  coupling 0.01 (per flash), dissipation 3.0, refractory 0.05. Defaults live
  in `scripts/_common.py` and at the top of `esp32_firefly.ino`. Change both
  or neither (and `scripts/fake_esp32.py`).
- **UDP protocol** (laptop, firmware and fake must agree). ESP32 listens on
  **4210**, laptop on **4211**.
  - `FIRE|<node_id>|<seq>|<tx_delay_ms>` — both ways. Virtual drones are
    `v<index>`; LEDs are **`esp32-L<n>`**, n from 1. `tx_delay_ms` is 0 until
    Reachback uses it.
  - `HELLO|esp32|<n_leds>` — ESP32 broadcasts every 2 s to port 4211. The
    laptop takes the ESP32's IP from it (auto-discovery). `--peer` overrides.
  - `HELLO|laptop` — laptop every 2 s once it knows the peer.
  - `PING|<seq>` — laptop every 1 s; ESP32 echoes it unchanged. One-way delay
    = median RTT / 2 (last 30), used to correct the LED offsets.
- The laptop sends a virtual drone's flash to the ESP32 only if that drone
  is in radio range of **some** LED (and not behind a wall); packet loss
  applies to that link too. All LEDs hear each other directly on the board.
- **Phases are circular**: 0.99 and 0.01 are close. Use `metrics.wrap` /
  `circular_mean`, never plain subtraction or averaging.
- A node fires **at most once per step**; nodes that fired this step are not
  nudged again (Mirollo-Strogatz absorption).
- **Random streams**: positions/phases use `swarm.rng` only. Every scenario
  has its own stream seeded `f"{seed}-{tag}"` (loss, rogue, move, drift), so
  switching a scenario on never changes the default layout. Default
  `--seed 3` is the demo layout (syncs in 7.67 s, a test checks it).
- Walls: `wall_type` "solid" blocks radio; "thin" lets a link through only
  if the two drones are within `THIN_WALL_REACH` (0.5) × radio range, i.e.
  4.5 m. Drones never walk through either. W cycles off → solid → thin → off.
  Do not make solid walls "sync anyway": with zero links that would be faked.
- Scenario constants: doorway 6 m (narrower doesn't reliably merge), rogue
  steps 0/1/3/5 (best-connected drones first), loss steps 0/10/30/50 %,
  drift ±2 %, speed 0.8 m/s — in `session.py` / `geometry.py`.
- Sync level, rhythms and "synced" use **healthy** drones only (rogues and
  real LEDs excluded).
- Experiments use only connected layouts and grow the floor with the swarm
  in the size test (see `sweep.py` docstring). Keep that, or the results
  measure the layout instead of the algorithm.
- Firmware must never use `delay()` in `loop()`; it blocks packet handling.

## How to work

```
pip install -r requirements.txt     # or double-click run_sim.bat once
python -m pytest -p no:cacheprovider   # must stay green
python scripts/run_sim.py --no-window --seconds 30
python scripts/fake_esp32.py & python scripts/run_live.py --no-window --seconds 30
```

- New logic in the core → add tests in `tests/`. Use fixed seeds.
- After changing the algorithm, rerun `run_sweep.py` + `plot_results.py` and
  copy `data/figures/*` into `docs/results/` so the README numbers stay true.
- Keep commits small, one idea each, with a clear message.
- Do **not** add AI co-author or "generated by" lines to commits.
- Never commit `firmware/**/secrets.h` (Wi-Fi password; gitignored) or
  anything in `data/` (run output; gitignored).

## Out of scope — don't add these

Real flying drones, 3D graphics, machine learning, web or mobile apps,
optical/light-sensor coupling.


## Progress Update — Automatic ESP32 IP Discovery (Pushkar)

> **Status: DONE on `main`** (different design from the plan below: the ESP32
> broadcasts `HELLO|esp32|<n>` instead of answering `DISCOVER`, so the
> laptop never has to send a broadcast). `FIRE_BUTTON_PIN` rename kept.
> The `feature/auto-esp32-discovery` branch is superseded and can be deleted.
> Kept below as the record of the hardware test results.

### Completed
- Successfully cloned and configured the FireSync repository on Windows.
- Created and tested the Python virtual environment.
- Successfully launched the 20-drone simulation using `run_sim.bat`.
- Successfully tested the fake ESP32 using `demo_fake_esp32.bat`.
- Configured the physical ESP32 and verified GPIO2 LED blinking.
- Connected the ESP32 and laptop to the same 2.4 GHz mobile hotspot.
- Completed the UDP latency test:
  - 100/100 replies, 0% packet loss.
  - Median RTT: 51.3 ms.
  - 95th percentile RTT: 69.6 ms.
  - Estimated one-way latency: 25.7 ms.
  - Verdict: USABLE.
- Successfully launched `demo_esp32.bat` with the physical ESP32.
- ESP32 reported hearing 18 of 20 virtual drones.
- Created Git branch: `feature/auto-esp32-discovery`.
- Preserved the existing firmware modification (`BOOT_PIN` renamed to `FIRE_BUTTON_PIN`).
- Created a local firmware backup: `firmware/esp32_firefly/esp32_firefly_backup.ino`.

### Current Task — Automatic ESP32 Discovery

Goal: Eliminate manual ESP32 IP address entry when launching the live demo.

Current implementation requires:
- `demo_esp32.bat` to request the ESP32 IP manually.
- `scripts/run_live.py` to receive the IP through `--peer`.
- `fireflysync/link.py` to communicate with a previously known peer.

### Planned Changes

1. **ESP32 firmware (`firmware/esp32_firefly/esp32_firefly.ino`)**
   - Listen for `DISCOVER|esp32-1` on UDP port 4210.
   - Respond with `DISCOVER_REPLY|esp32-1` to the requesting laptop.
   - Preserve existing synchronization behavior.

2. **Python networking (`fireflysync/link.py`)**
   - Implement `discover_esp32()`.
   - Broadcast discovery requests.
   - Listen for ESP32 responses and identify its IP.
   - Handle discovery timeouts.

3. **Live runner (`scripts/run_live.py`)**
   - Make `--peer` optional.
   - Automatically discover the ESP32 if no IP is provided.

4. **Launcher (`demo_esp32.bat`)**
   - Remove the manual IP prompt.
   - Retain the one-way latency input.

### Implementation Requirements
- Preserve the existing FIRE message format and synchronization algorithm.
- Do not hardcode IP addresses.
- Keep UDP ports consistent.
- Do not break fake ESP32 functionality.
- Never commit Wi-Fi credentials or `secrets.h`.
- Test each modification incrementally.

### Remaining Work
- Implement and test UDP discovery.
- Integrate discovery into the live runner and launcher.
- Verify physical ESP32 synchronization and LED behavior.
- Retest fake ESP32 functionality.
- Commit changes and open a pull request into `main` after successful testing.

**Current status:** superseded — discovery, measured delay and multi-LED support are on `main`.

# Build Plan

Last updated: 2026-09-22

Three phases, plus a half-day risk check before them. Each phase ends with
something you can **show working**, not just code that exists.

---

## The one architecture rule

> **The algorithm must not know about the screen or the network.**

`oscillator.py` and `swarm.py` contain only the firefly rule: timers, fires
and nudges. They never draw, never open a socket, never call `time.time()`.
They are handed a time step (`dt`) and told when a neighbour fired.

Everything else — the pygame window, the UDP link, the experiment runner —
sits *around* that core and calls into it.

**Why this matters.** Phase 3 needs thousands of runs, each simulating
minutes of swarm behaviour in milliseconds. If the algorithm reads the real
clock or waits for a window to redraw, those runs are impossible and you
will end up rewriting everything. Getting this boundary right on day one is
the difference between a project that finishes and one that stalls.

A quick test of whether you got it right: *can you run the simulation with
no window open?* If not, the boundary is broken.

---

## Phase 0 — The risk check (half a day, do this first)

Do not build anything else until this works.

Everything in Phase 2 depends on the laptop and the ESP32 exchanging
messages quickly and reliably. If that fails, you want to find out now, not
in week 5.

**Build:** the smallest possible test. The laptop sends a message; the ESP32
replies immediately; the laptop measures the round trip and prints it.

- `scripts/latency_test.py` — laptop side
- `firmware/latency_test/latency_test.ino` — ESP32 side

**Done when:** you have 100 round-trip times printed, and you know the
typical value and the worst case.

**What the numbers mean.** Your fireflies will flash about once per second.
If the typical round trip is under about 50 ms, delay is small compared to
the flash period and sync will absorb it easily. If it is regularly above
200 ms, or wildly inconsistent, stop and tell the group — you would switch
to the USB cable fallback.

**Watch out for:** the ESP32 only sees 2.4 GHz Wi-Fi, and Wi-Fi power saving
is on by default and will add ragged delay. Both are covered in
`docs/HARDWARE.md`.

---

## Phase 1 — The virtual swarm

**Goal:** dots on a screen start blinking at random and end up blinking
together. No hardware involved at all.

### What gets built

| File | What it does |
|------|--------------|
| `fireflysync/oscillator.py` | One firefly. A phase that rises, fires at 1, resets, and jumps forward when nudged. |
| `fireflysync/swarm.py` | N fireflies with (x, y) positions on a floor plan, and a radio range deciding who hears whom. |
| `fireflysync/metrics.py` | Phase spread (how far apart they are) and time-to-sync. |
| `fireflysync/view.py` | A pygame window: dots that flash, plus a live phase-spread line. |
| `scripts/run_sim.py` | Puts it together and runs it. |
| `tests/test_oscillator.py` | Proves the rule behaves: rises, fires, resets, nudges. |

### Suggested order

1. `oscillator.py` first, with its test. It is about 30 lines. Do not move on
   until the test passes.
2. `swarm.py` — start with everyone hearing everyone, then add radio range.
3. `metrics.py` — phase spread is just how spread out the phases are on a
   circle. Print it each step; it should fall toward zero.
4. `view.py` last. It is the easiest to fiddle with and the easiest to lose a
   week to.

### Done when

- Running `scripts/run_sim.py` shows dots converging from chaos to unison.
- The phase-spread number falls to near zero and stays there.
- You can change the number of drones, the radio range and the coupling
  strength from the command line without editing code.
- It runs with the window switched off and still logs the same numbers.

### Do not build yet

3D, obstacles, drones that move, or anything to do with the ESP32.

---

## Phase 2 — The real drone joins

**Goal:** the LED on the ESP32 blinks out of step at first, then pulls into
rhythm with the swarm on screen.

This is the demo the evaluators will remember.

### What gets built

| File | What it does |
|------|--------------|
| `fireflysync/link.py` | Sends and receives the "I fired" messages over UDP. |
| `firmware/esp32_firefly/esp32_firefly.ino` | The same firefly rule, in C++, on the board. Lights the LED and broadcasts. |
| `scripts/run_live.py` | Runs the swarm with the real drone joined in. |

### The message

Keep it plain text, so both sides can parse it without a library:

```
FIRE|<node_id>|<sequence_number>|<tx_delay_ms>
```

For example: `FIRE|esp32-1|42|7`

`tx_delay_ms` is unused in Phase 2 (send 0). It exists now because Phase 3's
Reachback algorithm needs it, and adding a field later means changing both
sides at once.

### The trap to know about

The laptop only learns the ESP32 fired **when the message arrives**, which is
already late. So the laptop's own graph will always make the real drone look
slightly behind, even when it is perfectly in step.

Correct for it using the number Phase 0 gave you: subtract half the typical
round-trip time. Then sanity-check it once with a slow-motion phone video of
the LED and the screen in the same frame.

Spotting this is the difference between a "LEDs blinking" project and a
measured one. Put it in the report.

### Done when

- The LED visibly falls into rhythm with the screen within a few seconds.
- Unplug the ESP32 and plug it back in: it starts off-beat and re-syncs on
  its own, with nobody touching anything.
- The laptop logs every fire event, from virtual drones and the real one,
  with corrected timestamps.

### Keep a fallback

If Wi-Fi misbehaves on demo day, the same messages can go over the USB serial
cable. It is still real hardware syncing, with less delay. Also record a clean
video of the working demo the first time it works.

---

## Phase 3 — Experiments and results

**Goal:** the graphs. This is where the Phase 2 marks for innovation and
practical implementation actually come from.

### What gets built

| File | What it does |
|------|--------------|
| `fireflysync/channel.py` | Adds artificial delay and packet loss, so runs are repeatable. |
| `fireflysync/reachback.py` | The Reachback Firefly Algorithm — collect a cycle's fires, apply them at the start of the next. |
| `fireflysync/sweep.py` | Runs the simulation thousands of times, headless, over a grid of settings. |
| `scripts/run_sweep.py` | Kicks off a sweep and writes results to `data/`. |
| `analysis/plots.py` + `scripts/plot_results.py` | Turns those results into the figures. |

### The four experiments

1. **Delay.** Time-to-sync as delay rises, simple rule vs Reachback.
2. **Packet loss.** How much loss each method survives.
3. **Swarm size.** Cycles-to-sync for 5, 10, 20, 35, 50 drones. Does it stay
   bounded or blow up?
4. **Late joiner.** A drone joins an already-synced swarm. How fast does it
   lock on, and does it disturb the others?

Then repeat experiments 1 and 2 with the real ESP32 and compare against the
simulation. Where they differ, explain why — Wi-Fi jitter, and the board's
clock running slightly fast or slow, are the honest answers.

See `docs/EXPERIMENTS.md` for exactly what gets measured.

### Done when

- At least four figures exist, generated by a script from logged data, not
  drawn by hand.
- Every number in the report can be regenerated by re-running one command.

### An honest note on results

You expect Reachback to beat the simple rule under delay. If it does not, in
your setup, **that is still a valid result.** Report it and explain why.
Evaluators grade whether you tested something properly, not whether the
outcome matched your prediction. Do not massage numbers.

---

## Splitting the work

Four people, four lanes that barely block each other:

| Person | Owns |
|--------|------|
| A | `oscillator.py`, `swarm.py`, `channel.py`, `reachback.py` — the core |
| B | `view.py` and the live demo |
| C | `link.py` and the ESP32 firmware |
| D | `sweep.py`, `analysis/`, and the report |

Phase 0 is done by C, with everyone watching, because everything else depends
on it.

Person A should finish `oscillator.py` in the first two days — B, C and D all
import it.

---

## Out of scope

Written down so nobody quietly adds them:

- Real flying drones
- 3D visualisation
- Machine learning anything
- A web app or mobile app
- More than one physical ESP32 (unless Phase 3 finishes early)
- Optical coupling with light sensors (a stretch goal at best)

If someone proposes one of these, the answer is "after the graphs are done".

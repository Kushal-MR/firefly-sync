# The Algorithm

Two algorithms. Phase 1 and 2 use the first; Phase 3 adds the second.

---

## 1. Pulse-coupled oscillators (Mirollo & Strogatz, 1990)

The firefly rule, in four lines:

1. Every node has a **phase** that rises steadily from 0 to 1, like a
   loading bar.
2. When the phase reaches 1, the node **fires** — flashes its LED and
   broadcasts — then resets to 0.
3. When a node **hears** another node fire, it jumps its phase forward by a
   small amount, the **coupling strength**.
4. If that jump pushes it to 1, it fires immediately too.

Mirollo and Strogatz proved that from almost any random starting point, the
whole population ends up firing together.

### The parameters

| Name | What it controls | Getting it wrong |
|------|------------------|------------------|
| **Period** | How long the phase takes to go 0 → 1 (we use ~1 second) | Too fast and network delay stops being negligible |
| **Coupling strength** | How far a node jumps when it hears a fire | Too small: sync takes forever. Too large: nodes overshoot and can oscillate instead of settling |
| **Radio range** | How far a fire is heard on the floor plan | Too small: the swarm splits into groups that never agree |

Tune these in simulation first, where a test takes a second. Only then copy
the working values into the ESP32 firmware.

### The assumption that breaks

The 1990 proof assumes messages arrive **instantly** and are **never lost**.
Real radios do neither. That is the whole reason Phase 3 exists.

---

## 2. The Reachback Firefly Algorithm (Werner-Allen et al., 2005)

Built to fix what breaks on real hardware.

**Problem 1 — collisions.** Once nodes are nearly synced they all transmit at
the same instant, so the messages collide and are lost. Success causes the
failure.

**Fix:** each node waits a small **random delay** before broadcasting, and
puts that delay inside the message. The receiver subtracts it to recover when
the fire really happened. Transmissions spread out; collisions drop.

**Problem 2 — delay.** A node reacting the instant a message arrives is
reacting to something that already happened. Nodes end up chasing each other
and never settle.

**Fix — "reachback":** do not react immediately. **Collect every fire heard
during one cycle, then apply all the adjustments together at the start of the
next cycle**, reaching back to those past events.

That is the entire difference. In code it is a list that fills during a cycle
and is drained at the cycle boundary — which is why `reachback.py` is a thin
layer over `oscillator.py`, not a rewrite of it.

---

## Papers behind this project

| Paper | Contribution | Limitation |
|-------|-------------|------------|
| Mirollo & Strogatz (1990) | The maths — proved pulse-coupled oscillators synchronize | Assumes instant, lossless messages |
| Werner-Allen et al. (2005) | Reachback Firefly Algorithm, on real sensor nodes | Special low-power sensor radios |
| Brandner et al. (2016) | Real wireless tests under one microsecond; also corrects clocks ticking at different rates | Costly FPGA research radios; accuracy drops in sparse networks |
| Santillán (2025) | 40 electronic fireflies sensing each other by light | Optical, in a dark box — no network delay or loss |
| Quinn et al. (2025) | Coupled oscillators flying real drones, leaderless | Needs an external tracking system; cheap onboard Wi-Fi untested |

Full citations are on the References slide of the Phase 1 deck.

**The gap in one sentence:** every demonstration used specialised or costly
hardware; none tested a cheap everyday Wi-Fi board like the ESP32.

### Framing this honestly

We are not inventing an algorithm. We are testing two known algorithms on
hardware the literature has not covered, plus late-joining devices and how
closely simulation matches reality. For a first-year project that is a solid
contribution — and claiming more than that is how people get caught in a viva.

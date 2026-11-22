# Demo runbook (for the evaluation)

About 6 minutes. Practise it once end to end the day before.

## Before the teacher arrives

- [ ] Phone hotspot on, **2.4 GHz**. Laptop joined to it.
- [ ] ESP32 on a **power bank**, six LEDs blinking together.
- [ ] Laptop plugged in to power, window on the projector.
- [ ] `docs/results/fig_overview.png` open in another window.
- [ ] Spare: `demo_fake_esp32.bat` works with no hardware at all, if the
      Wi-Fi dies on the day.

## Launchers (double-click, in the repo folder)

| File | Runs |
|---|---|
| `run_sim.bat` | virtual swarm only (first run also sets up `.venv`) |
| `demo_fake_esp32.bat` | swarm + a pretend ESP32 with 6 LEDs, no hardware |
| `demo_esp32.bat` | swarm + the real ESP32, found automatically |
| `run_experiments.bat` | reruns all experiments live (~3 min) and opens the graphs |

## The script

1. **The idea (30 s).** "Fireflies flash together with no leader. Each one
   just nudges its own timer when it sees a neighbour flash. Indoor drones
   have no GPS clock, so we gave them the firefly rule."

2. **Start `demo_esp32.bat`.** Card shows *Searching…* then *found*, the six
   teal LEDs L1–L6 pop onto the floor plan. The ring climbs to 100 % and
   turns green, *Synced in ~8 s · 8 cycles*. Point at the real LEDs
   blinking in time with the screen. *6/6 LEDs in sync*.

   **Now point at the RADIO strip under the floor plan** - this is the
   payoff. "Every drone sends one data message per cycle, in its own time
   slot. At the start their clocks disagree, so messages overlap: red
   blocks, red rings around drones, ~50 % lost. Once they sync, the slots
   line up: a neat row of green blocks and **0 % lost**." The red line on
   the small graph falls as the yellow sync line rises.

   Then press **T** (random timing): same synced swarm, but no timetable -
   red again, ~50 % lost. Press **T** again: back to 0 %. "You need both:
   the timetable AND a shared clock. Firefly sync gives the shared clock
   without any leader."

3. **Press BOOT on the ESP32.** The six LEDs scatter, then pull back in.
   "It recovers on its own - no reset, no leader."

4. **R** - scramble the whole virtual swarm. Watch the phase map dots
   gather into one clump and the arrow grow. **Press R 4-5 more times**,
   waiting for green each time: the *Runs* table fills up and shows the
   average cycles ± spread. "These are live statistics, not a recording -
   every run starts from a new random scramble."
   Then **P** to 30 % loss and press R a couple of times: the new runs get
   their own average (the header shows which settings it is for).

5. **Walls.** Press **W**: a *solid* wall (like concrete). The rooms can't
   hear each other, so the card says **2 rhythms**. "No communication, no
   sync - that's physics, not a bug."
   Press **W** again: a *thin* wall (like drywall or glass). Radio gets
   through but weakened, only up to 4.5 m (the shaded band). A few drones near
   the wall are enough: the rooms merge into **1 rhythm** in about 30 s.
   "Our swarm only needs one weak path to stay in sync."
   (Or from the solid wall press **D** to open a doorway: same result.)
   Press **W** once more to remove the wall.

6. **X** - rogue drone (red), firing at random. One: nothing happens. Press
   X again for 3, then 5: sync dips, then mostly recovers. "A few broken
   drones can't wreck the swarm." Press X until it says *removed*.

7. **P** - packet loss. Press until **50 %**: half of all flashes are lost
   and it still syncs, just slower. **P** until *No packet loss*.

8. **C** clock drift (every clock runs a bit fast or slow) and **M** moving
   drones: both still sync. Turn them off again.

9. **The numbers (1 min).** Show `fig_overview.png` (and `fig_walls.png`): 50 runs per setting.
   If asked "where do these come from?": double-click `run_experiments.bat`,
   it reruns all ~1400 simulations in about 2 minutes and redraws them.
   Every single run is a row in `data/sweep_*.csv` (opens in Excel).
   Thin wall: 94 % of layouts still sync (15 cycles vs 9 with no wall).
   Bigger swarm 5→50 drones: 11→13 cycles. 50 % loss: still 98 % of runs
   sync. 1 rogue: harmless; 5 rogues: sync drops to ~87 %.

10. **Research gap.** "Firefly sync has been shown in theory and on special
    radios. We show it on a cheap ESP32 over ordinary phone-hotspot Wi-Fi,
    with the Wi-Fi delay measured live (top right of the ESP32 card)."

Other keys: **SPACE** pause · **L** show radio links · **F** fullscreen ·
**S** screenshot to `data/shots/` · **ESC** quit.

## If something goes wrong on the day

| Symptom | Fix |
|---|---|
| *Searching for the ESP32…* stays | Same hotspot? ESP32 Serial Monitor shows an IP? Then `demo_esp32.bat --peer <that IP>` |
| *ESP32 found - waiting* stays | Allow Python through Windows firewall (Private + Public) |
| Wi-Fi dead | Close it, double-click `demo_fake_esp32.bat`: identical screen, pretend board |
| Window too big/small | Drag to resize, or **F** for fullscreen; everything rescales |

Full hardware troubleshooting: `docs/HARDWARE.md`.

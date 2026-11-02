# Hardware day runbook

Everything on the software side is built and tested. This is the checklist
for getting the real ESP32 into the swarm.

**Shortcut:** in the repo folder, double-click

| File | Runs |
|---|---|
| `run_sim.bat` | the virtual swarm only (first run also sets up `.venv`) |
| `demo_fake_esp32.bat` | swarm + a pretend ESP32 - no hardware needed |
| `demo_esp32.bat` | swarm + the real ESP32 - asks for its IP |

They use `.venv\Scripts\python.exe` directly, so there is nothing to
activate. The steps below are what they do, by hand.

## 0. Laptop setup (once, ~5 min)

```
pip install -r requirements.txt
python -m pytest
```

All tests should pass. If `pip install pygame` fails (very new Python
versions), run `pip install pygame-ce` instead - same code, drop-in.

## 1. Try it with no hardware first (~2 min)

Terminal 1:
```
python scripts/fake_esp32.py
```
Terminal 2:
```
python scripts/run_live.py --peer 127.0.0.1
```

You should see the swarm converge, and "ESP32 off-beat" settle near 0 ms in
green. If this works, the laptop side is fine and any problem tomorrow is
on the ESP32 or Wi-Fi side.

## 2. Flash the ESP32 (~10 min)

1. Arduino IDE: board **ESP32 Dev Module**, correct COM port.
2. In `firmware/esp32_firefly/`, copy `secrets.h.example` to `secrets.h`
   and fill in the hotspot. **2.4 GHz only.**
3. Upload. "Failed to connect"? Hold **BOOT** while uploading.
4. Serial Monitor at **115200**. Note the IP it prints.
5. The LED should already blink about once a second on its own.

## 3. Join it to the swarm

Laptop on the **same hotspot**:
```
python scripts/run_live.py --peer <ESP32 IP> --oneway-ms <one-way from Phase 0>
```

Within a few seconds:
- the panel shows "ESP32 off-beat" with a number
- the number falls to within about +/-30 ms and turns green
- the real LED blinks at the same moment as the drones on screen

## 4. The demo, in order

1. Start `run_live.py`. Swarm starts scattered (red), converges (green).
2. Point at the real LED blinking with the screen.
3. **Press BOOT on the ESP32.** It jumps off-beat; watch it pull back in.
4. **Press R on the laptop.** The virtual swarm scatters and re-syncs, and
   the ESP32 re-syncs with it.
5. **Unplug the ESP32 and plug it back in.** It boots off-beat and rejoins
   on its own.
6. Press **L** to show the radio links - only drones in range talk.

Power the ESP32 from a power bank during the demo, so it is visibly not
wired to the laptop.

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Panel stays "ESP32 waiting..." | Laptop's packets not reaching it, or replies blocked | Same hotspot? Right IP? Allow Python through Windows firewall |
| LED blinks but never syncs | Settings differ between laptop and firmware | PERIOD, COUPLING, DISSIPATION, REFRACTORY must match `run_live.py` defaults |
| Off-beat number jumps around a lot | Ragged Wi-Fi | Move closer to the hotspot; try another phone; check `WiFi.setSleep(false)` |
| Off-beat steady but about +10 to +30 ms | Network delay not subtracted | Pass `--oneway-ms` from the Phase 0 test |
| Window too big / small | Screen size | edit `View(width, height)` in `run_live.py` |

## Settings that must match on both sides

| Setting | Laptop (`run_live.py`) | Firmware (`esp32_firefly.ino`) |
|---|---|---|
| Period | `--period 1.0` | `PERIOD_S = 1.0f` |
| Coupling per flash | `--coupling 0.01` | `COUPLING = 0.01f` |
| Dissipation | `--dissipation 3.0` | `DISSIPATION = 3.0f` |
| Refractory | `--refractory 0.05` | `REFRACTORY = 0.05f` |
| Node ID | `--node-id esp32-1` | `NODE_ID = "esp32-1"` |

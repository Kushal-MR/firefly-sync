# Hardware: the ESP32 with six firefly LEDs

For the ESP team. Follow it top to bottom the first time. Everything on the
laptop side is already built and tested; this page is only the board.

**What you are building:** one ESP32 board with six LEDs. Each LED is its
own little firefly with its own timer. They hear each other (they sit side
by side) and they hear the laptop's 20 virtual drones over Wi-Fi. Start them
out of step and they fall into one rhythm with each other and with the screen.

---

## 1. Parts

| Item | Qty | Notes |
|------|-----|-------|
| ESP32 dev board | 1 | ESP32-WROOM-32 "DevKit V1" (30 or 38 pin). |
| LEDs | 6 | Same colour looks best on stage (yellow/amber = fireflies). 5 mm. |
| 220 Ω resistors | 6 | One per LED. Anything 150–470 Ω works. |
| Breadboard + jumper wires | 1 set | Male–male wires. |
| USB cable | 1 | Must be a **data** cable. Charge-only cables cannot program the board. |
| Power bank | 1 | For the demo, so the board is visibly not wired to the laptop. |

No LEDs yet? The board still works: set `LED_PINS[] = {2};` (see step 3)
and it runs as one firefly on the built-in blue LED.

## 2. Wiring

Every LED is wired the same way, just to a different pin:

```
ESP32 pin ──▶ 220 Ω resistor ──▶ LED long leg (+)
                                 LED short leg (−) ──▶ GND rail ──▶ ESP32 GND
```

| LED | ESP32 pin | Printed on the board as |
|-----|-----------|-------------------------|
| L1  | GPIO 4    | D4  |
| L2  | GPIO 16   | RX2 (or D16) |
| L3  | GPIO 17   | TX2 (or D17) |
| L4  | GPIO 18   | D18 |
| L5  | GPIO 19   | D19 |
| L6  | GPIO 21   | D21 |
| all | GND       | GND (any of them) |

Put the six LEDs **in a row, in order L1 … L6**: the laptop screen draws
them as L1–L6 too, so people can match board to screen.

Pins to **never** use for LEDs: 0 (BOOT button), 2 (built-in LED, already
used), 6–11 (internal flash, the board crashes), 12 (stops it booting),
34–39 (input only). Want a different pin? Change `LED_PINS[]`; any pin not
in that list is fine. More or fewer LEDs also just means editing that list.

Built-in blue LED (GPIO 2) copies L1, so you can see the board is alive even
with nothing wired.

**Check:** long leg is +. If an LED never lights, turn it around. An LED
without its resistor works briefly and then dies.

## 3. Software (once per laptop, ~15 min)

1. Install the **Arduino IDE 2**.
2. File → Preferences → *Additional boards manager URLs*, add
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
3. Tools → Board → Boards Manager → search **esp32** → install
   "esp32 by Espressif Systems".
4. Plug in the ESP32. Tools → Board → **ESP32 Dev Module**, Tools → Port →
   the COM port that appeared (Windows: if none appears, install the
   CP210x or CH340 USB driver, whichever chip is on your board).

## 4. Wi-Fi password (never commit this)

In `firmware/esp32_firefly/` copy `secrets.h.example` to **`secrets.h`** and
fill in the hotspot name and password. `secrets.h` is in `.gitignore`, so it
stays on your laptop. Never paste the password into the `.ino` file.

**The ESP32 only sees 2.4 GHz Wi-Fi.** Phone hotspot: Android → Hotspot →
AP band → 2.4 GHz. iPhone → Personal Hotspot → turn on *Maximize
Compatibility*. The laptop must join the **same** hotspot.

## 5. Upload

1. Open `firmware/esp32_firefly/esp32_firefly.ino` in the Arduino IDE.
2. Click **Upload** (→). "Failed to connect"? Hold the **BOOT** button on
   the board until "Connecting…" turns into percentages, then let go.
3. Tools → Serial Monitor, set to **115200** baud. You should see:

```
Connecting to MyHotspot.....
Connected. IP address: 10.12.34.56
6 LED fireflies. On the laptop: double-click demo_esp32.bat
```

   Compile errors? Tell the code team the exact red line. (The sketch has
   been reviewed against the Python twin `scripts/fake_esp32.py`, which is
   fully tested, but it can only be compiled on a laptop with the ESP32
   board package.)

4. The six LEDs already blink about once a second, out of step at first,
   then together: they sync with each other even before the laptop joins.

## 6. Join the laptop swarm

On the laptop, on the same hotspot, double-click **`demo_esp32.bat`**
(first time ever: double-click `run_sim.bat` once to set things up).
Nothing to type: the laptop hears the board's HELLO, finds its IP, and
measures the Wi-Fi delay by itself.

On screen, the *Real drone · ESP32* card goes:
**Searching for the ESP32…** → **ESP32 found** → **6/6 LEDs in sync**.
Six teal bulbs L1–L6 appear on the floor plan and blink with the drones.

The Serial Monitor prints a status line every 5 s, e.g.
`fired 412  heard 2310  laptop connected` (`heard` = flashes from the
virtual drones, so it must keep going up).

## 7. If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Upload: "Failed to connect" | Board not in download mode | Hold BOOT while it says Connecting… |
| No COM port | Charge-only cable or missing driver | Other cable; CP210x / CH340 driver |
| Serial: stuck "Connecting to …" | 5 GHz hotspot, typo in `secrets.h` | Force 2.4 GHz; check name/password (case matters) |
| An LED never lights | Backwards, or wrong pin | Turn it around; check the table in step 2 |
| Screen: "Searching for the ESP32…" forever | Different networks, or hotspot blocks broadcast | Same hotspot? Else run `demo_esp32.bat --peer <IP from Serial Monitor>` |
| Screen: "ESP32 found - waiting" forever | Windows firewall blocking Python | Windows Security → Firewall → Allow an app → Python, tick Private **and** Public |
| LEDs sync with each other but not the screen | Settings differ | The 4 numbers at the top of the `.ino` must match `scripts/_common.py` (see AGENTS.md) |
| "x/6 in sync" keeps changing | Ragged Wi-Fi | Move closer to the phone; another phone; `WiFi.setSleep(false)` must stay |

Last resort fallback: carry the same messages over the USB serial cable
instead of Wi-Fi. Less delay, still real hardware, demo still valid.

## Settings that must match on both sides

| Setting | Laptop (`scripts/_common.py`) | Firmware (top of `esp32_firefly.ino`) |
|---|---|---|
| Period | `--period 1.0` | `PERIOD_S = 1.0f` |
| Coupling per flash | `--coupling 0.01` | `COUPLING = 0.01f` |
| Dissipation | `--dissipation 3.0` | `DISSIPATION = 3.0f` |
| Refractory | `--refractory 0.05` | `REFRACTORY = 0.05f` |
| Ports | ESP32 4210, laptop 4211 | `PORT = 4210`, `LAPTOP_PORT = 4211` |

Change both or neither.

# Hardware

Short version for now. Detailed build notes get added when Phase 2 starts.

---

## Parts

| Item | Qty | Notes |
|------|-----|-------|
| ESP32 dev board | 1 | ESP32-WROOM-32 DevKit v1 is the common one. Cheap on SP Road or online. |
| LED | 1 | Any colour. |
| 220 Ω resistor | 1 | Anything from 150 Ω to 470 Ω works. |
| Breadboard + jumper wires | 1 set | |
| USB cable | 1 | Must be a **data** cable. Charge-only cables will not program the board. |

Check whether the college lab already has ESP32 boards before buying.

## Wiring

That is the whole circuit:

```
ESP32 GPIO 2  ──▶  220 Ω resistor  ──▶  LED long leg (+)
                                        LED short leg (−)  ──▶  ESP32 GND
```

Most ESP32 boards also have a **built-in LED on GPIO 2**, so the very first
test can run with no wiring at all.

## Software setup

1. Install the **Arduino IDE** (already present on this machine).
2. Add the ESP32 boards package: File → Preferences → Additional Board
   Manager URLs, then Tools → Board → Boards Manager → install "esp32".
3. Select your board and the COM port it appears on.

## Two settings that will waste your evening if you miss them

**1. The ESP32 cannot see 5 GHz Wi-Fi.** It is 2.4 GHz only. If you use a
phone hotspot, force it to 2.4 GHz — on Android that is the "AP band"
setting, on iPhone it is "Maximize Compatibility".

**2. Wi-Fi power saving is on by default** and holds messages back in ragged
bursts, which is exactly the thing you are trying to measure. Turn it off:

```cpp
WiFi.setSleep(false);
```

Also allow Python through the Windows firewall the first time you run the
laptop script, or incoming messages are silently dropped.

## Safety and sanity

- Do not power servos or motors from the ESP32 pins. Not needed here, but
  worth knowing.
- An LED without its resistor will work briefly and then not.
- Long leg is positive. If it does not light, try turning it around.

## Fallback

If Wi-Fi proves unreliable, the same messages can be carried over the USB
serial cable instead. Less delay, still real hardware, demo still valid.

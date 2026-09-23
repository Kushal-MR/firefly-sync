/*
 * PHASE 0 - ESP32 side of the Wi-Fi round-trip test.
 *
 * The smallest useful program in this project: connect to Wi-Fi, listen on a
 * UDP port, and reply to whatever arrives immediately. The laptop measures
 * the round trip.
 *
 * Settings that matter (see docs/HARDWARE.md):
 *   - 2.4 GHz Wi-Fi only; the ESP32 cannot see 5 GHz
 *   - WiFi.setSleep(false);  power saving adds ragged delay
 *   - print the board's IP on the serial monitor so the laptop can find it
 *
 * TODO(phase-0): implement.
 */

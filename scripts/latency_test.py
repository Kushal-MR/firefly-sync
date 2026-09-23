"""PHASE 0 — laptop side of the Wi-Fi round-trip test.

Do this before writing anything else. See docs/PLAN.md, Phase 0.

Sends a small UDP message to the ESP32, waits for the immediate reply, and
records the round-trip time. Repeat ~100 times and report typical, worst and
how many were lost.

Usage (planned):
    python scripts/latency_test.py --peer 192.168.x.x --count 100

What the answer means:
    typical under ~50 ms   -> Phase 2 will work comfortably
    regularly over 200 ms, or wildly inconsistent -> tell the group; switch
                              to the USB cable fallback

TODO(phase-0): implement.
"""

"""PHASE 2 — run the swarm with the real ESP32 joined over Wi-Fi.

Same as run_sim.py, plus a UdpLink. The ESP32 appears as one more node in
the swarm, drawn differently so the audience can tell which one is real.

Usage (planned):
    python scripts/run_live.py --drones 20 --peer 192.168.x.x

Remember to subtract the one-way delay measured in Phase 0 before logging
the real drone's fire times, or it will always look late.

TODO(phase-2): implement.
"""

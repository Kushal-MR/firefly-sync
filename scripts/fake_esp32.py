"""A pretend ESP32, for testing run_live.py without hardware.

Behaves like firmware/esp32_firefly.ino: same firefly rule, same messages,
learns the laptop's address from the packets it receives, starts off-beat.
Run it in one terminal, run_live.py in another:

    python scripts/fake_esp32.py
    python scripts/run_live.py --peer 127.0.0.1

--delay-ms adds artificial one-way delay to its outgoing flashes, to see how
the swarm copes with a slow network.
"""
import argparse
import os
import random
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fireflysync.link import DEFAULT_ESP32_PORT, format_fire, parse_fire  # noqa: E402
from fireflysync.oscillator import Oscillator  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Pretend ESP32 firefly")
    ap.add_argument("--port", type=int, default=DEFAULT_ESP32_PORT)
    ap.add_argument("--node-id", default="esp32-1")
    ap.add_argument("--delay-ms", type=float, default=0.0)
    ap.add_argument("--seconds", type=float, default=None)
    args = ap.parse_args()

    osc = Oscillator(period=1.0, coupling=0.01, dissipation=3.0, refractory=0.05,
                     phase=random.random() * 0.999)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", args.port))
    sock.setblocking(False)
    laptop = None
    outbox = []                         # (send_at, payload) for artificial delay
    seq = 0
    start = last = time.perf_counter()
    print(f"fake ESP32 listening on UDP {args.port} (starting at phase {osc.phase:.2f})")

    def fire(now):
        nonlocal seq
        print(f"  * flash  t={now - start:6.2f}s")
        if laptop:
            outbox.append((now + args.delay_ms / 1000, format_fire(args.node_id, seq)))
            seq += 1

    while args.seconds is None or last - start < args.seconds:
        now = time.perf_counter()
        dt = now - last
        last = now
        if dt > 0 and osc.advance(min(dt, 0.5)):
            fire(now)
        while True:
            try:
                data, addr = sock.recvfrom(256)
            except (BlockingIOError, ConnectionResetError):
                break
            laptop = addr
            msg = parse_fire(data, now)
            if msg and msg.node_id != args.node_id and osc.on_neighbour_fired():
                fire(now)
        for item in [o for o in outbox if o[0] <= now]:
            sock.sendto(item[1], laptop)
            outbox.remove(item)
        time.sleep(0.001)


if __name__ == "__main__":
    main()

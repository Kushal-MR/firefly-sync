"""A pretend ESP32 with several LED fireflies, for testing without hardware.

Behaves like firmware/esp32_firefly/esp32_firefly.ino: one firefly per LED,
LEDs hear each other instantly and hear the laptop's drones over UDP, it
announces itself with HELLO, echoes PING, and starts out of step.

    python scripts/fake_esp32.py                 # 6 LEDs
    python scripts/fake_esp32.py --leds 1
    python scripts/fake_esp32.py --delay-ms 25   # pretend the Wi-Fi is slow

Then, in another terminal:  python scripts/run_live.py   (no --peer needed)
"""
import argparse
import os
import random
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fireflysync.link import DEFAULT_ESP32_PORT, DEFAULT_LAPTOP_PORT, format_fire, parse_fire  # noqa: E402
from fireflysync.oscillator import Oscillator  # noqa: E402

ID_PREFIX = "esp32-L"


def main():
    ap = argparse.ArgumentParser(description="Pretend ESP32 with LED fireflies")
    ap.add_argument("--leds", type=int, default=6)
    ap.add_argument("--port", type=int, default=DEFAULT_ESP32_PORT)
    ap.add_argument("--laptop", default="127.0.0.1", help="where to send HELLO (in addition to broadcast)")
    ap.add_argument("--delay-ms", type=float, default=0.0, help="artificial one-way delay")
    ap.add_argument("--seconds", type=float, default=None)
    args = ap.parse_args()

    leds = [Oscillator(period=1.0, coupling=0.01, dissipation=3.0, refractory=0.05,
                       phase=random.random() * 0.999) for _ in range(args.leds)]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", args.port))
    sock.setblocking(False)
    laptop = None
    outbox = []                                   # (send_at, payload, addr)
    seq = 0
    start = last = time.perf_counter()
    next_hello = start
    print(f"fake ESP32 with {args.leds} LEDs listening on UDP {args.port}")

    def send(payload, addr, now):
        outbox.append((now + args.delay_ms / 1000, payload, addr))

    def fire(i, now, fired):
        nonlocal seq
        fired.add(i)
        print(f"  * LED {i + 1} flash  t={now - start:6.2f}s")
        if laptop:
            send(format_fire(f"{ID_PREFIX}{i + 1}", seq), laptop, now)
            seq += 1

    def deliver(source, now, fired):
        queue = [source]
        while queue:
            src = queue.pop()
            for i, o in enumerate(leds):
                if i != src and i not in fired and o.on_neighbour_fired():
                    fire(i, now, fired)
                    queue.append(i)

    while args.seconds is None or last - start < args.seconds:
        now = time.perf_counter()
        dt = min(now - last, 0.5)
        last = now
        fired = set()
        if dt > 0:
            for i, o in enumerate(leds):
                if o.advance(dt) and i not in fired:
                    fire(i, now, fired)
                    deliver(i, now, fired)
        while True:
            try:
                data, addr = sock.recvfrom(256)
            except (BlockingIOError, ConnectionResetError):
                break
            laptop = addr
            if data.startswith(b"PING|"):
                send(data, addr, now)
                continue
            msg = parse_fire(data, now)
            if msg and not msg.node_id.startswith(ID_PREFIX):
                deliver(-1, now, fired)
        if now >= next_hello:
            hello = f"HELLO|esp32|{args.leds}".encode()
            for target in ((args.laptop, DEFAULT_LAPTOP_PORT), ("255.255.255.255", DEFAULT_LAPTOP_PORT)):
                try:
                    sock.sendto(hello, target)
                except OSError:
                    pass
            next_hello = now + 2.0
        for item in [o for o in outbox if o[0] <= now]:
            try:
                sock.sendto(item[1], item[2])
            except OSError:
                pass
            outbox.remove(item)
        time.sleep(0.001)


if __name__ == "__main__":
    main()

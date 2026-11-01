"""PHASE 0 - laptop side of the Wi-Fi round-trip test.

Sends small UDP messages to the ESP32, which echoes each one straight back,
and measures the round trip. Run it before building anything else: the whole
of Phase 2 depends on this link being quick and steady.

Usage:
    python scripts/latency_test.py --peer 192.168.43.57
    python scripts/latency_test.py --peer 192.168.43.57 --count 200 --csv data/latency.csv

Standard library only, so it runs before anything is pip-installed.
"""
import argparse
import csv
import socket
import statistics
import sys
import time


def measure(peer, port, count, timeout, interval):
    """Return a list of round-trip times in ms, with None for each lost ping."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    results = []
    try:
        for seq in range(count):
            msg = f"PING|{seq}".encode()
            start = time.perf_counter()
            sock.sendto(msg, (peer, port))
            rtt = None
            # A reply from an earlier ping can arrive late; skip it rather
            # than counting it against the current one.
            while True:
                remaining = timeout - (time.perf_counter() - start)
                if remaining <= 0:
                    break
                sock.settimeout(remaining)
                try:
                    data, _ = sock.recvfrom(128)
                except socket.timeout:
                    break
                if data == msg:
                    rtt = (time.perf_counter() - start) * 1000.0
                    break
            results.append(rtt)
            mark = "lost" if rtt is None else f"{rtt:6.1f} ms"
            print(f"  ping {seq:3d}: {mark}")
            time.sleep(interval)
    finally:
        sock.close()
    return results


def percentile(sorted_vals, p):
    idx = min(len(sorted_vals) - 1, int(round(p / 100 * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def summarise(results):
    got = sorted(r for r in results if r is not None)
    lost = len(results) - len(got)
    print()
    if not got:
        print("No replies at all. Check, in this order:")
        print("  1. Laptop and ESP32 are on the SAME hotspot (2.4 GHz)")
        print("  2. The IP you passed matches what Serial Monitor printed")
        print("  3. Windows firewall is allowing Python")
        return 2

    med = statistics.median(got)
    p95 = percentile(got, 95)
    print(f"Replies : {len(got)}/{len(results)}  (lost {lost}, {100 * lost / len(results):.1f}%)")
    print(f"Min     : {got[0]:.1f} ms")
    print(f"Median  : {med:.1f} ms   <- the typical round trip")
    print(f"95th pct: {p95:.1f} ms   <- the bad-but-common case")
    print(f"Max     : {got[-1]:.1f} ms")
    print(f"One-way : ~{med / 2:.1f} ms  (save this number - Phase 2 subtracts it)")
    print()

    # Fireflies flash about once a second, so judge delay against 1000 ms.
    if med < 50 and p95 < 150 and lost / len(results) < 0.05:
        print("Verdict: GOOD. Delay is tiny next to a 1 s flash period. Go ahead.")
        return 0
    if med < 200:
        print("Verdict: USABLE but rough. Try another phone's hotspot, move closer,")
        print("         and check WiFi.setSleep(false) is in the firmware.")
        return 0
    print("Verdict: TOO SLOW. Tell the group - switch to the USB cable fallback.")
    return 1


def main():
    ap = argparse.ArgumentParser(description="Wi-Fi round-trip test with the ESP32")
    ap.add_argument("--peer", required=True, help="ESP32 IP address (from Serial Monitor)")
    ap.add_argument("--port", type=int, default=4210)
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--timeout", type=float, default=1.0, help="seconds to wait per ping")
    ap.add_argument("--interval", type=float, default=0.05, help="seconds between pings")
    ap.add_argument("--csv", help="optional path to save every result")
    args = ap.parse_args()

    print(f"Pinging {args.peer}:{args.port} x{args.count}")
    results = measure(args.peer, args.port, args.count, args.timeout, args.interval)

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["seq", "rtt_ms"])
            for i, r in enumerate(results):
                w.writerow([i, "" if r is None else f"{r:.3f}"])
        print(f"Saved raw results to {args.csv}")

    sys.exit(summarise(results))


if __name__ == "__main__":
    main()

"""PHASE 2 - run the swarm with the real ESP32 joined over Wi-Fi.

    python scripts/run_live.py --peer 192.168.43.57
    python scripts/run_live.py --peer 192.168.43.57 --oneway-ms 9 --log

--peer       the ESP32's IP (printed on its Serial Monitor at boot)
--oneway-ms  one-way Wi-Fi delay from the Phase 0 test (median / 2). It is
             subtracted when measuring how off-beat the ESP32 is; without it
             the real drone always looks a little late.

Always runs in real time - the ESP32 lives in real time.
"""
import json

from _common import log_path, parse_area, swarm_args

from fireflysync.link import DEFAULT_ESP32_PORT, DEFAULT_LAPTOP_PORT, UdpLink
from fireflysync.session import Session
from fireflysync.swarm import Swarm


def main():
    ap = swarm_args("Run the swarm with the real ESP32 drone")
    ap.add_argument("--peer", required=True, help="ESP32 IP address")
    ap.add_argument("--peer-port", type=int, default=DEFAULT_ESP32_PORT)
    ap.add_argument("--listen-port", type=int, default=DEFAULT_LAPTOP_PORT)
    ap.add_argument("--oneway-ms", type=float, default=0.0, help="one-way delay from Phase 0")
    ap.add_argument("--node-id", default="esp32-1", help="must match NODE_ID in the firmware")
    args = ap.parse_args()

    swarm = Swarm(args.drones, period=args.period, coupling=args.coupling,
                  dissipation=args.dissipation, refractory=args.refractory,
                  radio_range=args.radio_range or None, area=parse_area(args.area), seed=args.seed)
    ext = swarm.add_external(args.node_id)
    if not swarm.neighbours_of(ext):
        raise SystemExit("The ESP32 has no virtual drones in radio range. Use a bigger --range.")
    if not swarm.is_connected():
        print("WARNING: some drones are out of everyone's range and may never sync.")

    link = UdpLink(args.peer, args.peer_port, args.listen_port)
    print(f"Talking to ESP32 at {args.peer}:{args.peer_port}, listening on {args.listen_port}")
    print(f"ESP32 hears {len(swarm.neighbours_of(ext))} of {args.drones} virtual drones")
    session = Session(swarm, dt=args.dt, link=link, external_index=ext, external_name=args.node_id,
                      oneway_delay=args.oneway_ms / 1000.0,
                      log_path=log_path("live") if args.log else None)

    if args.no_window:
        import threading

        def report():
            while not done.wait(5):
                print(session.status_line())
        done = threading.Event()
        threading.Thread(target=report, daemon=True).start()
        result = session.run_realtime(None, seconds=args.seconds)
        done.set()
    else:
        from fireflysync.view import View
        view = View(title="firefly-sync - live with ESP32")
        try:
            result = session.run_realtime(view, seconds=args.seconds)
        finally:
            view.close()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

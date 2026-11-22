"""Run the swarm with the real ESP32 (and every LED on it) joined over Wi-Fi.

    python scripts/run_live.py                    find the ESP32 automatically
    python scripts/run_live.py --peer 10.0.0.42   if your hotspot blocks broadcast
    python scripts/run_live.py --oneway-ms 26     override the measured delay

Nothing has to be typed normally: the ESP32 broadcasts HELLO every 2 s and
the laptop picks up its IP; the laptop then pings it every second to measure
the Wi-Fi delay. Each LED joins the swarm the first time it flashes.

Always runs in real time - the ESP32 lives in real time.
"""
import json

from _common import log_path, make_swarm, swarm_args

from fireflysync.link import DEFAULT_ESP32_PORT, DEFAULT_LAPTOP_PORT, UdpLink
from fireflysync.session import Session


def main():
    ap = swarm_args("Run the swarm with the real ESP32")
    ap.add_argument("--peer", default=None, help="ESP32 IP (optional: found automatically)")
    ap.add_argument("--peer-port", type=int, default=DEFAULT_ESP32_PORT)
    ap.add_argument("--listen-port", type=int, default=DEFAULT_LAPTOP_PORT)
    ap.add_argument("--oneway-ms", type=float, default=None,
                    help="one-way delay; leave out to measure it automatically")
    args = ap.parse_args()

    swarm = make_swarm(args)
    link = UdpLink(args.peer, args.peer_port, args.listen_port)
    print(f"Listening on UDP {args.listen_port}. " +
          (f"ESP32 at {args.peer}." if args.peer else "Searching for the ESP32 (it says hello every 2 s)..."))
    session = Session(swarm, dt=args.dt, link=link,
                      oneway_delay=None if args.oneway_ms is None else args.oneway_ms / 1000.0,
                      log_path=log_path("live") if args.log else None, print_runs=True)

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
        view = View(title="FireSync - live with ESP32")
        try:
            result = session.run_realtime(view, seconds=args.seconds)
        finally:
            view.close()
    print(json.dumps(result, indent=2))
    saved = session.save_runs(log_path("runs"))
    if saved:
        print(f"{len(session.runs)} runs saved to {saved}")


if __name__ == "__main__":
    main()

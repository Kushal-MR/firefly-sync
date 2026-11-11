"""Run the virtual swarm.

    python scripts/run_sim.py                           window, 20 drones
    python scripts/run_sim.py --drones 40 --range 6
    python scripts/run_sim.py --walls                   start with two rooms
    python scripts/run_sim.py --no-window --seconds 60  headless, prints progress

--no-window must keep working: it is what the experiments run on.
"""
import json

from _common import log_path, make_swarm, swarm_args

from fireflysync.session import Session


def main():
    args = swarm_args("Run the virtual firefly swarm").parse_args()
    swarm = make_swarm(args)
    if not swarm.is_connected() and not swarm.walls_on:
        print("WARNING: with this radio range some drones can't hear the rest - "
              "they may never sync. Try a bigger --range or fewer drones.")
    session = Session(swarm, dt=args.dt, log_path=log_path("sim") if args.log else None)

    if args.no_window:
        result = session.run_headless(args.seconds or 60)
    else:
        from fireflysync.view import View
        view = View(title="FireSync - virtual swarm")
        try:
            result = session.run_realtime(view, seconds=args.seconds)
        finally:
            view.close()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

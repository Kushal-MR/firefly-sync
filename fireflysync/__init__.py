"""firefly-sync — firefly-inspired timing synchronization for drone swarms.

Layering rule (see docs/PLAN.md):

    oscillator.py, swarm.py     pure logic, no I/O, no clock, no drawing
    metrics.py                  measurement, reads state only
    view.py, link.py            I/O layers that sit around the core
    channel.py, reachback.py    Phase 3 additions
    sweep.py                    runs the core thousands of times, headless

Nothing in the first group may import anything from the others.
"""

__version__ = "0.1.0"

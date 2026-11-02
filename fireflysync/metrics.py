"""Measuring how well the swarm is synchronized.

Phases live on a circle: 0.99 and 0.01 are 0.02 apart, not 0.98. So every
measure here treats a phase as a point on a circle (an angle), never as a
plain number on a line.
"""
import cmath
import math


def order_parameter(phases):
    """Sync level from 0 to 1. 1 = all flash together, 0 = spread evenly.

    Each phase becomes an arrow pointing round a circle; this is the length
    of their average. Arrows pointing the same way add up to 1; arrows
    pointing everywhere cancel towards 0.
    """
    phases = list(phases)
    if not phases:
        raise ValueError("no phases")
    z = sum(cmath.exp(2j * math.pi * p) for p in phases) / len(phases)
    return abs(z)


def phase_spread(phases):
    """How far apart the nodes are: 0 = perfectly together."""
    return 1.0 - order_parameter(phases)


def circular_mean(phases):
    """The swarm's average phase, in [0, 1)."""
    z = sum(cmath.exp(2j * math.pi * p) for p in phases)
    return (cmath.phase(z) / (2 * math.pi)) % 1.0


def wrap(x):
    """Map a phase difference into [-0.5, 0.5): the shortest way round."""
    return (x + 0.5) % 1.0 - 0.5


def offset_ms(swarm_mean_phase, period, oneway_delay=0.0):
    """How far off-beat a node that has JUST fired is from the swarm, in ms.

    A node that just fired is at phase 0. If the swarm's mean phase is 0.02,
    the swarm fired 2% of a period earlier, so the node is 20 ms late
    (positive). 0.98 means it is 20 ms early (negative).

    oneway_delay (s): the message took this long to arrive, so the node
    really fired that much earlier than we heard about it.
    """
    lag = swarm_mean_phase - oneway_delay / period
    return wrap(lag) * period * 1000.0


def time_to_sync(times, levels, threshold=0.95, hold=3.0):
    """First time the sync level reaches threshold and stays there for hold
    seconds. None if that never happens.

    "Stays there" matters: one lucky moment above threshold is not sync.
    """
    start = None
    for t, lvl in zip(times, levels):
        if lvl >= threshold:
            if start is None:
                start = t
            if t - start >= hold:
                return start
        else:
            start = None
    return None

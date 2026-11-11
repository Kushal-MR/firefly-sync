"""Tiny 2-D geometry for the floor plan: walls block radio and movement.

A wall is a line segment ((x1, y1), (x2, y2)). Two drones can hear each
other only if the straight line between them crosses no wall.
"""


def _orient(a, b, c):
    """>0 if a->b->c turns left, <0 if right, 0 if the three are in a line."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p):
    return (min(a[0], b[0]) - 1e-9 <= p[0] <= max(a[0], b[0]) + 1e-9 and
            min(a[1], b[1]) - 1e-9 <= p[1] <= max(a[1], b[1]) + 1e-9)


def segments_cross(p1, p2, q1, q2):
    """True if segment p1-p2 touches or crosses segment q1-q2."""
    d1, d2 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    d3, d4 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0)) and d1 != 0 and d2 != 0 and \
       ((d3 > 0) != (d4 > 0)) and d3 != 0 and d4 != 0:
        return True
    return ((d1 == 0 and _on_segment(q1, q2, p1)) or (d2 == 0 and _on_segment(q1, q2, p2)) or
            (d3 == 0 and _on_segment(p1, p2, q1)) or (d4 == 0 and _on_segment(p1, p2, q2)))


def blocked(a, b, walls):
    """True if any wall lies between points a and b."""
    return any(segments_cross(a, b, w0, w1) for w0, w1 in walls)


def two_rooms(area, door_open, door_width=6.0):
    """A wall down the middle of the floor, with a wide doorway in its centre.

    6 m out of 12: narrower doors connect so few drones that merging can take
    over a minute, or never happen, depending on where drones happen to sit.

    Door closed: one solid wall, the two rooms cannot hear each other.
    Door open:   the wall is split around a gap, radio passes through it.
    """
    w, h = area
    x = w / 2
    if not door_open:
        return [((x, 0.0), (x, h))]
    lo, hi = h / 2 - door_width / 2, h / 2 + door_width / 2
    return [((x, 0.0), (x, lo)), ((x, hi), (x, h))]

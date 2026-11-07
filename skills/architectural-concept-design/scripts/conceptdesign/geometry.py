"""Plan geometry in metres: x runs east, y runs north.

A rectangle is a tuple (x0, y0, x1, y1) with x0 < x1 and y0 < y1. Every wall, opening, room and
piece of furniture in a design model is axis-aligned, which keeps the checks exact and fast.
"""
from __future__ import annotations

import math

SIDES = ("N", "E", "S", "W")
DIRS = {"N": (0.0, 1.0), "S": (0.0, -1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
BEARING = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
EPS = 1e-6


def area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def is_horizontal(r):
    """True when a wall-like rectangle runs east-west (it is wider than it is deep)."""
    return (r[2] - r[0]) >= (r[3] - r[1])


def length(r):
    return max(r[2] - r[0], r[3] - r[1])


def thickness(r):
    return min(r[2] - r[0], r[3] - r[1])


def overlap(a, b, tol=0.0):
    """True when two rectangles share an area wider than tol in both directions."""
    return min(a[2], b[2]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[1], b[1]) > tol


def intersection(a, b):
    r = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    return r if r[2] - r[0] > EPS and r[3] - r[1] > EPS else None


def contains(r, p, tol=EPS):
    return r[0] - tol <= p[0] <= r[2] + tol and r[1] - tol <= p[1] <= r[3] + tol


def contains_rect(outer, inner, tol=1e-4):
    return (outer[0] - tol <= inner[0] and outer[1] - tol <= inner[1]
            and inner[2] <= outer[2] + tol and inner[3] <= outer[3] + tol)


def expand(r, d):
    return (r[0] - d, r[1] - d, r[2] + d, r[3] + d)


def bbox(rects):
    rects = list(rects)
    return (min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[2] for r in rects), max(r[3] for r in rects))


def rect_minus(r, holes):
    """A rectangle minus other rectangles, as a list of disjoint rectangles."""
    out = [tuple(r)]
    for h in holes:
        nxt = []
        for a in out:
            if h[0] >= a[2] or h[2] <= a[0] or h[1] >= a[3] or h[3] <= a[1]:
                nxt.append(a)
                continue
            if h[1] > a[1]:
                nxt.append((a[0], a[1], a[2], h[1]))
            if h[3] < a[3]:
                nxt.append((a[0], h[3], a[2], a[3]))
            y0, y1 = max(a[1], h[1]), min(a[3], h[3])
            if h[0] > a[0]:
                nxt.append((a[0], y0, h[0], y1))
            if h[2] < a[2]:
                nxt.append((h[2], y0, a[2], y1))
        out = nxt
    return [a for a in out if area(a) > EPS]


def split_rect(w, cuts):
    """The parts of wall rectangle w left after removing opening rectangles, along its long axis."""
    x0, y0, x1, y1 = w
    horizontal = is_horizontal(w)
    lo, hi = (x0, x1) if horizontal else (y0, y1)
    spans = [(lo, hi)]
    for c in cuts:
        if c[0] >= x1 or c[2] <= x0 or c[1] >= y1 or c[3] <= y0:
            continue
        a, b = (c[0], c[2]) if horizontal else (c[1], c[3])
        new = []
        for s, e in spans:
            if b <= s or a >= e:
                new.append((s, e))
                continue
            if a > s:
                new.append((s, a))
            if b < e:
                new.append((b, e))
        spans = new
    if horizontal:
        return [(s, y0, e, y1) for s, e in spans if e - s > EPS]
    return [(x0, s, x1, e) for s, e in spans if e - s > EPS]


# ------------------------------------------------------------------------- unions of rectangles
def grid(rects):
    """Sorted distinct x and y coordinates of the rectangles: the cells between them are uniform."""
    xs = sorted({round(v, 6) for r in rects for v in (r[0], r[2])})
    ys = sorted({round(v, 6) for r in rects for v in (r[1], r[3])})
    return xs, ys


def union_area(rects):
    """Exact area of a union of rectangles (coordinate compression)."""
    rects = [r for r in rects if area(r) > EPS]
    if not rects:
        return 0.0
    xs, ys = grid(rects)
    total = 0.0
    for i in range(len(xs) - 1):
        cx = (xs[i] + xs[i + 1]) / 2
        for j in range(len(ys) - 1):
            cy = (ys[j] + ys[j + 1]) / 2
            if any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in rects):
                total += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return total


def in_union(rects, p):
    return any(r[0] - EPS <= p[0] <= r[2] + EPS and r[1] - EPS <= p[1] <= r[3] + EPS for r in rects)


def outline_edges(rects):
    """The outline of a union of rectangles as merged edges.

    Returns (side, fixed, a, b): side is the outward direction (N, E, S, W); for N and S edges
    `fixed` is y and the edge runs from x=a to x=b, for E and W edges `fixed` is x and it runs
    from y=a to y=b. Courtyards produce edges too, facing into the courtyard."""
    xs, ys = grid(rects)
    nx, ny = len(xs) - 1, len(ys) - 1
    inside = [[any(r[0] < (xs[i] + xs[i + 1]) / 2 < r[2] and r[1] < (ys[j] + ys[j + 1]) / 2 < r[3]
                   for r in rects) for j in range(ny)] for i in range(nx)]

    def cell(i, j):
        return 0 <= i < nx and 0 <= j < ny and inside[i][j]

    raw = []
    for i in range(nx):
        for j in range(ny):
            if not inside[i][j]:
                continue
            if not cell(i, j + 1):
                raw.append(("N", ys[j + 1], xs[i], xs[i + 1]))
            if not cell(i, j - 1):
                raw.append(("S", ys[j], xs[i], xs[i + 1]))
            if not cell(i + 1, j):
                raw.append(("E", xs[i + 1], ys[j], ys[j + 1]))
            if not cell(i - 1, j):
                raw.append(("W", xs[i], ys[j], ys[j + 1]))
    merged = []
    for side, fixed, a, b in sorted(raw):
        last = merged[-1] if merged else None
        if last and last[0] == side and abs(last[1] - fixed) < EPS and abs(last[3] - a) < EPS:
            merged[-1] = (side, fixed, last[2], b)
        else:
            merged.append((side, fixed, a, b))
    return merged


def exterior_walls(rects, t):
    """Wall rectangles of thickness t inside the outline of a union of rectangles, each with the
    side it faces. Walls meet without overlaps or gaps at both outside and inside corners."""
    edges = outline_edges(rects)
    vertical = [e for e in edges if e[0] in ("E", "W")]

    def vertical_at(x, y, going):
        """A vertical edge with an end at (x, y) that runs up (going=+1) or down (-1) from it."""
        for _side, fx, a, b in vertical:
            if abs(fx - x) < EPS and ((going > 0 and abs(a - y) < EPS) or (going < 0 and abs(b - y) < EPS)):
                return True
        return False

    walls = []
    for side, fixed, a, b in edges:
        if side in ("N", "S"):
            inward = -1 if side == "N" else 1          # the building lies below a north edge
            x0, x1 = a, b
            # an inside (reflex) corner: the outline turns away, so extend this wall into it
            if vertical_at(a, fixed, -inward):
                x0 -= t
            if vertical_at(b, fixed, -inward):
                x1 += t
            y0, y1 = (fixed - t, fixed) if side == "N" else (fixed, fixed + t)
            walls.append(((x0, y0, x1, y1), side))
        else:
            y0, y1 = a, b
            horizontal = [e for e in edges if e[0] in ("N", "S")]
            for hs, hy, ha, hb in horizontal:
                touches = (side == "E" and abs(hb - fixed) < EPS) or (side == "W" and abs(ha - fixed) < EPS)
                if not touches:
                    continue
                # an outside (convex) corner: the north or south wall already covers it
                if hs == "N" and abs(hy - b) < EPS:
                    y1 = b - t
                if hs == "S" and abs(hy - a) < EPS:
                    y0 = a + t
            x0, x1 = (fixed - t, fixed) if side == "E" else (fixed, fixed + t)
            if y1 - y0 > EPS:
                walls.append(((x0, y0, x1, y1), side))
    return walls


# ------------------------------------------------------------------------- polygons (the site)
def polygon_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def point_in_polygon(p, pts):
    x, y = p
    inside = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y):
            xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if xc > x:
                inside = not inside
    return inside


def distance_point_segment(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def distance_rect_segment(r, a, b):
    """Shortest distance between a rectangle and a segment that does not cross it."""
    corners = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    best = min(distance_point_segment(c, a, b) for c in corners)
    for p in (a, b):
        dx = max(r[0] - p[0], 0.0, p[0] - r[2])
        dy = max(r[1] - p[1], 0.0, p[1] - r[3])
        best = min(best, math.hypot(dx, dy))
    return best

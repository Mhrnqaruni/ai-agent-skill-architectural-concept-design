"""Design rules, checked before anything is drawn.

Errors stop the build: a room nobody can reach, a door that swings into furniture, a floor over
its area limit, a building inside a setback. Warnings are reported and left to judgement: thin
daylight, a narrow door, an uncomfortable stair, rooms drawn over walls.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from . import areas
from . import geometry as g

STEP = 0.05                      # reachability grid, metres


@dataclass
class Finding:
    severity: str                # "error" or "warning"
    rule: str
    level: str
    message: str
    ref: dict = None             # indices into the level's lists, e.g. {"opening": 1, "furniture": 14}

    def as_dict(self):
        out = {"severity": self.severity, "rule": self.rule, "level": self.level, "message": self.message}
        if self.ref:
            out["ref"] = self.ref
        return out

    def __str__(self):
        where = f"[{self.level}] " if self.level else ""
        return f"{self.severity.upper():7s} {self.rule:12s} {where}{self.message}"


# ------------------------------------------------------------------------------ furniture shapes
def wc_rect(at, back):
    x, y = at
    facing = g.OPPOSITE[back]
    return {"N": (x - 0.225, y, x + 0.225, y + 0.68), "S": (x - 0.225, y - 0.68, x + 0.225, y),
            "E": (x, y - 0.225, x + 0.68, y + 0.225), "W": (x - 0.68, y - 0.225, x, y + 0.225)}[facing]


def dining_layout(item):
    """Chair positions (x, y, back) around a dining table: both long sides, ends if asked."""
    r = item.rect
    along_x = g.is_horizontal(r)
    long_len = (r[2] - r[0]) if along_x else (r[3] - r[1])
    per_side = max(1, int(long_len // 0.6))
    seats = int(item.extra.get("seats", 2 * per_side))
    ends = max(0, min(2, seats - 2 * per_side))
    per_side = min(per_side, max(1, (seats - ends + 1) // 2))
    chairs = []
    for k in range(per_side):
        t = (k + 0.5) / per_side
        if along_x:
            x = r[0] + t * (r[2] - r[0])
            chairs += [(x, r[1] - 0.2, "S"), (x, r[3] + 0.2, "N")]
        else:
            y = r[1] + t * (r[3] - r[1])
            chairs += [(r[0] - 0.2, y, "W"), (r[2] + 0.2, y, "E")]
    cx, cy = g.center(r)
    end_spots = [(r[0] - 0.2, cy, "W"), (r[2] + 0.2, cy, "E")] if along_x else [(cx, r[1] - 0.2, "S"), (cx, r[3] + 0.2, "N")]
    return chairs + end_spots[:ends]


def footprints(item):
    """Plan rectangles an item occupies, for clash checks. Rugs lie flat and are left out."""
    t, r = item.type, item.rect
    if t == "rug":
        return []
    if t == "wc":
        return [wc_rect(item.at, item.back)]
    if t in ("chair", "barstool", "plant", "tank"):
        half = {"chair": 0.23, "barstool": 0.18}.get(t) or float(item.extra.get("size", 0.2)) * (1.6 if t == "plant" else 1.0)
        return [(item.at[0] - half, item.at[1] - half, item.at[0] + half, item.at[1] + half)]
    if t == "stools":
        n, sides = int(item.extra["count"]), item.extra["sides"]
        step = (r[2] - r[0]) / n
        out = []
        for k in range(n):
            x = r[0] + (k + 0.5) * step
            if "S" in sides:
                out.append((x - 0.18, r[1] - 0.28, x + 0.18, r[1]))
            if "N" in sides:
                out.append((x - 0.18, r[3], x + 0.18, r[3] + 0.28))
        return out
    if t == "dining_table":
        return [r] + [(x - 0.22, y - 0.22, x + 0.22, y + 0.22) for x, y, _ in dining_layout(item)]
    return [r]


# ------------------------------------------------------------------------------ door swings
def swing_discs(op):
    """The quarter disc a hinged door sweeps: ((cx, cy), radius, angle_a, angle_b)."""
    if op.kind != "door":
        return []
    x0, y0, x1, y1 = op.rect
    s, at_end = op.swing, op.at_end
    if g.is_horizontal(op.rect):
        w, face = x1 - x0, (y1 if s > 0 else y0)
        return [((x1 if at_end else x0, face), w, 90 if s > 0 else 270, 180 if at_end else 0)]
    w, face = y1 - y0, (x1 if s > 0 else x0)
    return [((face, y1 if at_end else y0), w, 0 if s > 0 else 180, 270 if at_end else 90)]


def in_quarter(pt, q):
    (cx, cy), r, a, b = q
    dx, dy = pt[0] - cx, pt[1] - cy
    if math.hypot(dx, dy) > r:
        return False
    ang = math.degrees(math.atan2(dy, dx)) % 360
    lo, hi = sorted((a % 360, b % 360))
    return (ang >= hi or ang <= lo) if hi - lo == 270 else lo <= ang <= hi


def disc_points(q, rings=24, step=3):
    (cx, cy), r = q[0], q[1]
    pts = ((cx + r * i / rings * math.cos(math.radians(t)), cy + r * i / rings * math.sin(math.radians(t)))
           for i in range(1, rings + 1) for t in range(0, 360, step))
    return [p for p in pts if in_quarter(p, q)]


def _inside(pt, r, m=0.01):
    return r[0] + m < pt[0] < r[2] - m and r[1] + m < pt[1] < r[3] - m


def check_swings(lv, out):
    cuts = [op.rect for op in lv.openings]
    pieces = [p for w in lv.all_walls for p in g.split_rect(w, cuts)]
    items = [(it, fp) for it in lv.furniture for fp in footprints(it)]
    discs = [(op, q, disc_points(q)) for op in lv.openings for q in swing_discs(op)]
    for op, q, pts in discs:
        where = f"door openings[{op.index}] {list(op.rect)}"
        struck = {}
        for it, fp in items:
            if any(_inside(p, fp) for p in pts):
                struck.setdefault(it.index, it)
        for it in struck.values():
            out.append(Finding("error", "door-swing", lv.id,
                               f"{where} swings into {it.type} furniture[{it.index}] {_rect(it)}",
                               {"opening": op.index, "furniture": it.index}))
        for wp in pieces:
            if any(_inside(p, wp) for p in pts):
                out.append(Finding("error", "door-swing", lv.id, f"{where} swings into the wall at {list(wp)}",
                                   {"opening": op.index}))
                break
        for op2, q2, _ in discs:
            if op2 is not op and op2.index > op.index and any(in_quarter(p, q2) for p in pts):
                out.append(Finding("error", "door-swing", lv.id,
                                   f"{where} and door openings[{op2.index}] swing into each other",
                                   {"opening": op.index, "other_opening": op2.index}))
    for k, (it, a) in enumerate(items):
        for it2, b in items[k + 1:]:
            if it2 is not it and g.overlap(a, b, 0.01):
                out.append(Finding("error", "clash", lv.id,
                                   f"{it.type} furniture[{it.index}] overlaps {it2.type} furniture[{it2.index}]",
                                   {"furniture": it.index, "other_furniture": it2.index}))
        if any(g.overlap(a, wp, 0.01) for wp in pieces):
            out.append(Finding("error", "clash", lv.id, f"{it.type} furniture[{it.index}] stands in a wall",
                               {"furniture": it.index}))


def _rect(it):
    return [round(v, 3) for v in (it.rect or it.at)]


# ------------------------------------------------------------------------------ reachability
def reach_grid(lv):
    x0, y0, x1, y1 = lv.bbox
    nx, ny = max(1, math.ceil((x1 - x0) / STEP)), max(1, math.ceil((y1 - y0) / STEP))
    blocked = [[True] * ny for _ in range(nx)]

    def span(a, b, origin, n):
        i0 = max(0, math.ceil((a - origin) / STEP - 0.5 - 1e-9))
        i1 = min(n - 1, math.floor((b - origin) / STEP - 0.5 + 1e-9))
        return range(i0, i1 + 1)

    for r in lv.footprint:
        for i in span(r[0], r[2], x0, nx):
            for j in span(r[1], r[3], y0, ny):
                blocked[i][j] = False
    walled = set()
    for w in lv.all_walls:
        for i in span(w[0], w[2], x0, nx):
            for j in span(w[1], w[3], y0, ny):
                if not blocked[i][j]:
                    blocked[i][j] = True
                    walled.add((i, j))
    for op in lv.openings:
        if op.passable:
            for i in span(op.rect[0], op.rect[2], x0, nx):
                for j in span(op.rect[1], op.rect[3], y0, ny):
                    if (i, j) in walled:
                        blocked[i][j] = False
    return blocked, (x0, y0, nx, ny)


def check_reach(lv, out):
    start, desc = lv.start()
    if start is None:
        out.append(Finding("error", "reach", lv.id, "has no entrance and no stair to start from"))
        return
    blocked, (x0, y0, nx, ny) = reach_grid(lv)

    def cell(p):
        return (min(nx - 1, max(0, int((p[0] - x0) / STEP))), min(ny - 1, max(0, int((p[1] - y0) / STEP))))

    si, sj = cell(start)
    if blocked[si][sj]:
        free = [(i, j) for i in range(max(0, si - 6), min(nx, si + 7)) for j in range(max(0, sj - 6), min(ny, sj + 7))
                if not blocked[i][j]]
        if not free:
            out.append(Finding("error", "reach", lv.id, f"{desc} at {list(start)} is inside a wall"))
            return
        si, sj = min(free, key=lambda c: (c[0] - si) ** 2 + (c[1] - sj) ** 2)
    seen = [[False] * ny for _ in range(nx)]
    seen[si][sj] = True
    q = deque([(si, sj)])
    while q:
        i, j = q.popleft()
        for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= a < nx and 0 <= b < ny and not seen[a][b] and not blocked[a][b]:
                seen[a][b] = True
                q.append((a, b))
    def reached(p):
        i, j = cell(p)
        return seen[i][j] and not blocked[i][j]

    reachable = [room for room in lv.rooms if reached(room.label_at)]
    targets = [(f"room {room.name!r}", room.label_at, room) for room in lv.rooms if room.access == "inside"]
    targets += [(f"the stair up to {s.to!r}", g.center(s.rect), None) for s in lv.stairs_up]
    for name, p, room in targets:
        i, j = cell(p)
        if blocked[i][j]:
            out.append(Finding("error", "reach", lv.id, f"the label point of {name} lies inside a wall",
                               {"room": room.index} if room else None))
        elif not seen[i][j]:
            hint = ""
            if room is not None:
                hint = door_hint(lv, room, reachable)
            out.append(Finding("error", "reach", lv.id,
                               f"{name} cannot be reached from {desc}: add a door or an opening{hint}",
                               {"room": room.index} if room else None))


def door_hint(lv, room, reachable):
    """Where a door would connect an unreachable room: a partition it shares with a reached room."""
    for other in reachable:
        shared = g.intersection(g.expand(room.rect, 0.06), g.expand(other.rect, 0.06))
        if not shared or g.length(shared) < 0.8:
            continue
        for w in lv.walls:
            if g.overlap(w, shared, 0.0):
                return f"; it shares the wall {list(w)} with {other.name!r}"
    return ""


# ------------------------------------------------------------------------------ other rules
def glazing(lv, room, model):
    zone = g.expand(room.rect, model.exterior_wall + 0.05)
    ext = [w for w, _ in lv.ext_walls]
    total = 0.0
    for op in lv.openings:
        if op.kind not in ("window", "sliding") or not g.overlap(op.rect, zone, 0.01):
            continue
        if op.kind == "sliding" and not any(g.overlap(op.rect, w, 0.01) for w in ext):
            continue
        clear = min(op.head, lv.height - 0.25) - op.sill
        total += max(0.0, clear) * op.width
    return total


def check_rooms(model, lv, out, net):
    rules = model.rules
    walls = lv.all_walls
    for room in lv.rooms:
        a = net.get(room.index, 0.0)
        over = sum(g.area(x) for reg in room.regions for w in walls if (x := g.intersection(reg, w)))
        if over > 0.02:
            out.append(Finding("warning", "room-walls", lv.id,
                               f"{room.name!r} overlaps walls by {over:.2f} m2: draw rooms between wall faces"))
        if room.habitable:
            glz = glazing(lv, room, model)
            ratio = glz / a if a > 0 else 0.0
            if glz <= 0:
                out.append(Finding("warning", "daylight", lv.id, f"{room.name!r} has no window"))
            elif ratio < rules["daylight_ratio"] - 1e-9:
                out.append(Finding("warning", "daylight", lv.id,
                                   f"{room.name!r} glazing is {ratio:.0%} of its floor area "
                                   f"(target {rules['daylight_ratio']:.0%})"))
        if room.use == "bedroom" and a < rules["min_bedroom_area"]:
            out.append(Finding("warning", "room-size", lv.id,
                               f"bedroom {room.name!r} is {a:.1f} m2 (minimum {rules['min_bedroom_area']} m2)"))
    for k, ra in enumerate(lv.rooms):
        for rb in lv.rooms[k + 1:]:
            common = sum(g.area(x) for p in ra.regions for q in rb.regions if (x := g.intersection(p, q)))
            if common > 0.02:
                out.append(Finding("warning", "room-overlap", lv.id,
                                   f"{ra.name!r} and {rb.name!r} overlap by {common:.2f} m2"))


def check_openings(model, lv, out):
    ext = [w for w, _ in lv.ext_walls]
    for op in lv.openings:
        if op.kind in ("door", "sliding") and op.width < model.rules["min_door_width"] - 1e-9:
            out.append(Finding("warning", "door-width", lv.id,
                               f"openings[{op.index}] is {op.width:.2f} m wide "
                               f"(minimum {model.rules['min_door_width']:.2f} m)"))
        if op.kind == "window" and op.head > lv.height - 0.2:
            out.append(Finding("warning", "window", lv.id,
                               f"window openings[{op.index}] head {op.head:.2f} m is above the ceiling zone"))
    if lv.entrance:
        doors = [op for op in lv.openings if op.kind in ("door", "sliding")
                 and any(g.overlap(op.rect, w, 0.01) for w in ext)]
        near = [op for op in doors if math.dist(lv.entrance, g.center(op.rect)) <= 1.5]
        if not near:
            out.append(Finding("warning", "entrance", lv.id,
                               "no outside door within 1.5 m of the entrance point"))


def check_stairs(model, lv, out):
    rules = model.rules
    lo, hi = rules["stair_comfort"]
    for s in lv.stairs_up:
        stride = 2 * s.rise + s.going
        if s.rise > rules["max_riser"] + 1e-9:
            out.append(Finding("warning", "stair", lv.id, f"stairs[{s.index}] rise {s.rise * 100:.1f} cm is too steep"))
        if s.going < rules["min_going"] - 1e-9:
            out.append(Finding("warning", "stair", lv.id,
                               f"stairs[{s.index}] going {s.going * 100:.1f} cm is too short: make the stair longer"))
        if not lo - 1e-9 <= stride <= hi + 1e-9:
            out.append(Finding("warning", "stair", lv.id,
                               f"stairs[{s.index}] 2 x rise + going = {stride * 100:.1f} cm "
                               f"(comfortable: {lo * 100:.0f}-{hi * 100:.0f} cm)"))
        if s.width < rules["min_stair_width"] - 1e-9:
            out.append(Finding("warning", "stair", lv.id, f"stairs[{s.index}] flights are {s.width:.2f} m wide"))


def check_site(model, out):
    site = model.site
    if not site:
        return
    rects = [r for lv in model.levels for r in lv.footprint]
    for r in rects:
        for corner in ((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])):
            if not g.point_in_polygon(corner, site.boundary):
                out.append(Finding("error", "site", "", f"the building corner {list(corner)} is outside the site"))
                return
    if site.setbacks:
        pts = site.boundary
        for k, need in enumerate(site.setbacks):
            if need is None:
                continue
            a, b = pts[k], pts[(k + 1) % len(pts)]
            d = min(g.distance_rect_segment(r, a, b) for r in rects)
            if d < need - 0.005:
                out.append(Finding("error", "setback", "",
                                   f"the building is {d:.2f} m from boundary edge {k} (needs {need:.2f} m)"))


def check_labels(lv, out, net):
    """Room labels must fit inside their room and not overlap, at the scale the plan prints."""
    from .plans import label_box, plan_scale
    scale = plan_scale(lv)
    boxes = []
    for room in lv.rooms:
        box = label_box(room, net.get(room.index, 0.0), scale)
        corners = ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))
        if not all(any(g.contains(reg, c, 0.02) for reg in room.regions) for c in corners):
            out.append(Finding("warning", "label", lv.id,
                               f"the label of {room.name!r} ({box[2] - box[0]:.1f} x {box[3] - box[1]:.1f} m "
                               f"at 1:{scale}) does not fit inside the room: shorten the name or move label_at",
                               {"room": room.index}))
        boxes.append((room, box))
    for k, (ra, a) in enumerate(boxes):
        for rb, b in boxes[k + 1:]:
            if g.overlap(a, b, 0.0):
                out.append(Finding("warning", "label", lv.id,
                                   f"the labels of {ra.name!r} and {rb.name!r} overlap at 1:{scale}: move label_at",
                                   {"room": ra.index, "other_room": rb.index}))


def run(model):
    """Every rule on every level. Returns a list of Finding, errors first."""
    out = [Finding("warning", "model", "", w) for w in model.warnings]
    for lv in model.levels:
        net = areas.net_areas(lv)
        if lv.area_limit and lv.built_area > lv.area_limit + 1e-6:
            out.append(Finding("error", "area-limit", lv.id,
                               f"built area {lv.built_area:.2f} m2 is over the limit of {lv.area_limit:.2f} m2"))
        check_reach(lv, out)
        check_swings(lv, out)
        check_rooms(model, lv, out, net)
        check_labels(lv, out, net)
        check_openings(model, lv, out)
        check_stairs(model, lv, out)
    check_site(model, out)
    return sorted(out, key=lambda f: f.severity != "error")


def report(model, findings):
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    lines = [str(f) for f in findings]
    built = ", ".join(f"{lv.id} {lv.built_area:.2f}" for lv in model.levels)
    lines.append(f"check: {len(errors)} errors, {len(warnings)} warnings | built areas (m2): {built}")
    return "\n".join(lines)

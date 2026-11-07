"""The 3D scene for the viewer, built from the design model.

Every level gets two wall sets. 'cut' walls stop at 2.4 m for the furnished floor views, and each
outside wall also has a low 0.6 m version grouped by the side it faces, so the viewer can drop the
walls between the camera and the rooms. 'full' walls rise to the next floor for the whole-building
view. Plan metres: x east, y north, z up. Groups: '<level>.cut', '<level>.hi<side>',
'<level>.lo<side>', '<level>.full', '<level>' (shared), 'R' (roof) and 'S' (site).
"""
from __future__ import annotations

import math

from . import elevations
from . import geometry as g
from .plans import flights, kitchen_sink, stair_across, stair_frame
from .rules import dining_layout

CUT, LOW, SLAB = 2.4, 0.6, 0.25
FACADE = {"render": "render", "brick": "brick", "stone": "stone", "timber": "cladding"}
RUGS = ["rugA", "rugB", "rugC"]


class Scene:
    def __init__(self):
        self.boxes, self.prisms, self.quads, self.ao, self.items, self.labels = [], [], [], [], [], []

    def box(self, x0, y0, z0, x1, y1, z1, m, grp):
        if x1 - x0 > 1e-3 and y1 - y0 > 1e-3 and z1 - z0 > 1e-3:
            self.boxes.append([round(v, 3) for v in (x0, y0, z0, x1, y1, z1)] + [m, grp])

    def rbox(self, r, z0, z1, m, grp):
        self.box(r[0], r[1], z0, r[2], r[3], z1, m, grp)


def touching(walls, r, tol=0.06):
    sides = set()
    for w in walls:
        if min(r[2], w[2]) - max(r[0], w[0]) > 0.05:
            if abs(r[1] - w[3]) <= tol:
                sides.add("S")
            if abs(r[3] - w[1]) <= tol:
                sides.add("N")
        if min(r[3], w[3]) - max(r[1], w[1]) > 0.05:
            if abs(r[0] - w[2]) <= tol:
                sides.add("W")
            if abs(r[2] - w[0]) <= tol:
                sides.add("E")
    return sides


def is_exterior(lv, rect):
    return any(g.overlap(rect, w, 0.01) for w, _ in lv.ext_walls)


# ------------------------------------------------------------------------------ walls
def glazing(s, r, z0, z1, grp, wide_bar):
    fw, fd = 0.05, 0.07
    if g.is_horizontal(r):
        ym = (r[1] + r[3]) / 2
        s.box(r[0], ym - 0.012, z0, r[2], ym + 0.012, z1, "glass", grp)
        for a, b in ((r[0], r[0] + fw), (r[2] - fw, r[2])):
            s.box(a, ym - fd / 2, z0, b, ym + fd / 2, z1, "frame", grp)
        s.box(r[0], ym - fd / 2, z0, r[2], ym + fd / 2, z0 + fw, "frame", grp)
        s.box(r[0], ym - fd / 2, z1 - fw, r[2], ym + fd / 2, z1, "frame", grp)
        if r[2] - r[0] > 1.6 or wide_bar:
            xm = (r[0] + r[2]) / 2
            s.box(xm - fw / 2, ym - fd / 2, z0, xm + fw / 2, ym + fd / 2, z1, "frame", grp)
    else:
        xm = (r[0] + r[2]) / 2
        s.box(xm - 0.012, r[1], z0, xm + 0.012, r[3], z1, "glass", grp)
        for a, b in ((r[1], r[1] + fw), (r[3] - fw, r[3])):
            s.box(xm - fd / 2, a, z0, xm + fd / 2, b, z1, "frame", grp)
        s.box(xm - fd / 2, r[1], z0, xm + fd / 2, r[3], z0 + fw, "frame", grp)
        s.box(xm - fd / 2, r[1], z1 - fw, xm + fd / 2, r[3], z1, "frame", grp)
        if r[3] - r[1] > 1.6 or wide_bar:
            ym = (r[1] + r[3]) / 2
            s.box(xm - fd / 2, ym - fw / 2, z0, xm + fd / 2, ym + fw / 2, z1, "frame", grp)


def build_wall(s, w, ops, z0, height, mat, grp, cut, exterior):
    """Wall rectangle w from z0 to z0 + height with its openings. In cut views, doors and plain
    openings run to the top of the cut, so they read clearly from above."""
    cuts = []
    for op in ops:
        if not g.overlap(op.rect, w, 0.0):
            continue
        r = g.intersection(op.rect, w)
        if r is None:
            continue
        cuts.append(op.rect)
        if op.kind in ("door", "opening"):
            if not cut:
                s.box(r[0], r[1], z0 + op.head, r[2], r[3], z0 + height, mat, grp)
            continue
        if op.kind == "sliding" and not exterior:
            top = min(op.head, height)
            if g.is_horizontal(r):
                ym = (r[1] + r[3]) / 2
                s.box(r[0], ym - 0.02, z0, r[2], ym + 0.02, z0 + top, "door", grp)
            else:
                xm = (r[0] + r[2]) / 2
                s.box(xm - 0.02, r[1], z0, xm + 0.02, r[3], z0 + top, "door", grp)
            if not cut and height > op.head:
                s.box(r[0], r[1], z0 + op.head, r[2], r[3], z0 + height, mat, grp)
            continue
        h0, h1 = (op.sill, op.head) if op.kind == "window" else (0.0, op.head)
        if h0 > 0:
            s.box(r[0], r[1], z0, r[2], r[3], z0 + min(h0, height), mat, grp)
        if h1 < height:
            s.box(r[0], r[1], z0 + h1, r[2], r[3], z0 + height, mat, grp)
        if h0 < height:
            glazing(s, r, z0 + h0, z0 + min(h1, height), grp, op.kind == "sliding")
    for piece in g.split_rect(w, cuts):
        s.box(piece[0], piece[1], z0, piece[2], piece[3], z0 + height, mat, grp)


def walls(s, model, lv, full_height):
    facade = FACADE.get(model.facade, "render")
    for w, side in lv.ext_walls:
        build_wall(s, w, lv.openings, lv.z, min(CUT, lv.height - 0.3), "wall", f"{lv.id}.hi{side}", True, True)
        build_wall(s, w, lv.openings, lv.z, LOW, "wall", f"{lv.id}.lo{side}", True, True)
        mat = facade if lv.z + full_height > 0.05 else "stone"
        build_wall(s, w, lv.openings, lv.z, full_height, mat, f"{lv.id}.full", False, True)
    for w in lv.walls:
        build_wall(s, w, lv.openings, lv.z, min(CUT, lv.height - 0.3), "wall", f"{lv.id}.cut", True, False)
        build_wall(s, w, lv.openings, lv.z, min(full_height, lv.height) - 0.02, "wall", f"{lv.id}.full", False, False)


def floored(lv, x, y):
    if not g.in_union(lv.footprint, (x, y)):
        return False
    if any(g.contains(v, (x, y), 0) for v in lv.voids):
        return False
    return not any(w[0] < x < w[2] and w[1] < y < w[3] for w in lv.all_walls)


def wall_shadows(s, lv):
    """Soft shadow strips on the floor along the foot of every wall."""
    cuts = [op.rect for op in lv.openings]
    width = 0.32
    for w in lv.all_walls:
        for p in g.split_rect(w, cuts):
            if g.is_horizontal(p):
                if p[2] - p[0] < 0.12:
                    continue
                xm = (p[0] + p[2]) / 2
                if floored(lv, xm, p[3] + 0.15):
                    s.ao.append([p[0], p[3], p[2], p[3] + width, lv.z, "N", lv.id])
                if floored(lv, xm, p[1] - 0.15):
                    s.ao.append([p[0], p[1] - width, p[2], p[1], lv.z, "S", lv.id])
            else:
                if p[3] - p[1] < 0.12:
                    continue
                ym = (p[1] + p[3]) / 2
                if floored(lv, p[2] + 0.15, ym):
                    s.ao.append([p[2], p[1], p[2] + width, p[3], lv.z, "E", lv.id])
                if floored(lv, p[0] - 0.15, ym):
                    s.ao.append([p[0] - width, p[1], p[0], p[3], lv.z, "W", lv.id])


# ------------------------------------------------------------------------------ floors and doors
def floors(s, lv):
    for r in lv.footprint:
        for p in g.rect_minus(r, lv.voids):
            s.rbox(g.expand(p, -0.03), lv.z - SLAB, lv.z, "slab", lv.id)     # kept off the facade
            s.quads.append([p[0], p[1], p[2], p[3], lv.z + 0.001, lv.finish, lv.id])
    for room in lv.rooms:
        if room.finish == lv.finish:
            continue
        for reg in room.regions:
            for p in g.rect_minus(g.expand(reg, 0.05), lv.voids):
                s.quads.append([p[0], p[1], p[2], p[3], lv.z + 0.002, room.finish, lv.id])


def door_leaves(s, lv):
    """Inside doors stand open at 90 degrees, inside the swing kept clear on the plans; outside
    doors are shown shut."""
    for op in lv.openings:
        if op.kind != "door":
            continue
        x0, y0, x1, y1 = op.rect
        h = op.head - 0.02
        if is_exterior(lv, op.rect):
            side = next(sd for w, sd in lv.ext_walls if g.overlap(op.rect, w, 0.01))
            for grp, top in ((f"{lv.id}.hi{side}", min(h, CUT - 0.01)), (f"{lv.id}.lo{side}", min(h, LOW - 0.01)),
                             (f"{lv.id}.full", h)):
                if g.is_horizontal(op.rect):
                    ym = (y0 + y1) / 2
                    s.box(x0 + 0.01, ym - 0.03, lv.z, x1 - 0.01, ym + 0.03, lv.z + top, "doorext", grp)
                else:
                    xm = (x0 + x1) / 2
                    s.box(xm - 0.03, y0 + 0.01, lv.z, xm + 0.03, y1 - 0.01, lv.z + top, "doorext", grp)
            continue
        t, sw = 0.04, op.swing
        if g.is_horizontal(op.rect):
            width, face = x1 - x0, (y1 if sw > 0 else y0)
            hx = x1 if op.at_end else x0
            xa, xb = (hx - t, hx) if op.at_end else (hx, hx + t)
            ya, yb = sorted((face, face + sw * (width - 0.02)))
        else:
            width, face = y1 - y0, (x1 if sw > 0 else x0)
            hy = y1 if op.at_end else y0
            ya, yb = (hy - t, hy) if op.at_end else (hy, hy + t)
            xa, xb = sorted((face, face + sw * (width - 0.02)))
        s.box(xa, ya, lv.z, xb, yb, lv.z + h, "door", lv.id)


# ------------------------------------------------------------------------------ stairs
def stair_boxes(stair, z0):
    """(plan rect, top z) for every tread and the landing."""
    f = stair_frame(stair)
    out = []

    def rect(ua, ub, va, vb):
        (xa, ya), (xb, yb) = f(ua, va), f(ub, vb)
        return (min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb))

    for v0, v1, ua, ub, n, frac in flights(stair):
        going = (ub - ua) / (n - 1)
        zf = z0 + frac * stair.rise_total
        for i in range(n - 1):
            a, b = ua + i * going, ua + (i + 1) * going
            out.append((rect(min(a, b), max(a, b), v0 + 0.02, v1 - 0.02), zf + (i + 1) * stair.rise, "tread"))
    if stair.kind == "u":
        end = stair.run_length - stair.landing
        out.append((rect(end, stair.run_length, 0.0, stair_across(stair)), z0 + stair.rise_total / 2, "landing"))
    return out


def stairs(s, model, lv):
    for st in lv.stairs_up:
        above = model.level(st.to)
        for r, top, kind in stair_boxes(st, lv.z):
            grps = [f"{lv.id}.full"]
            if top <= lv.z + CUT:
                grps.append(f"{lv.id}.cut")
            if top >= above.z - 1.2:
                grps.append(f"{above.id}.cut")
            for grp in grps:
                if kind == "landing":
                    s.rbox(r, top - 0.2, top - 0.04, "slabedge", grp)
                s.rbox(r, top - 0.05, top, "oak", grp)
        if st.kind == "u":
            f = stair_frame(st)
            half = (stair_across(st) - 0.1) / 2
            end = st.run_length - st.landing
            (xa, ya), (xb, yb) = f(0.0, half), f(end, half + 0.1)
            spine = (min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb))
            for grp, za, zb in ((f"{lv.id}.full", lv.z, above.z), (f"{lv.id}.cut", lv.z, lv.z + CUT),
                                (f"{above.id}.cut", above.z - 1.2, above.z + 1.0)):
                s.rbox(spine, za, zb, "wall", grp)
        stairwell(s, model, above, st)
        s.labels.append({"en": "Stairs", "alt": "", "p": [*g.center(st.rect), lv.z + 0.05], "f": lv.id})


def stairwell(s, model, above, st):
    """Seen from the floor above: lining walls down to the flight below, and glass guards on the
    open edges of the stair opening, except where people step off the stair."""
    x0, y0, x1, y1 = st.rect
    za, zb = above.z - 1.25, above.z - SLAB
    grp = f"{above.id}.cut"
    for r in ((x0 - 0.1, y0 - 0.1, x1 + 0.1, y0), (x0 - 0.1, y1, x1 + 0.1, y1 + 0.1),
              (x0 - 0.1, y0, x0, y1), (x1, y0, x1 + 0.1, y1)):
        s.rbox(r, za, zb, "wall", grp)
    s.rbox(st.rect, za - 0.05, za, "slab", grp)
    f = stair_frame(st)
    width, length = stair_across(st), st.run_length
    if st.kind == "u":
        half = (width - 0.1) / 2
        first = (0.0, half) if st.turn == "right" else (half + 0.1, width)
        edges = [((0.0, first[0]), (0.0, first[1])), ((0.0, 0.0), (length, 0.0)),
                 ((0.0, width), (length, width)), ((length, 0.0), (length, width))]
    else:
        edges = [((0.0, 0.0), (0.0, width)), ((0.0, 0.0), (length, 0.0)), ((0.0, width), (length, width))]
    for (ua, va), (ub, vb) in edges:
        (xa, ya), (xb, yb) = f(ua, va), f(ub, vb)
        line = (min(xa, xb) - 0.02, min(ya, yb) - 0.02, max(xa, xb) + 0.02, max(ya, yb) + 0.02)
        if any(g.overlap(line, g.expand(w, 0.03), 0.0) and g.length(g.intersection(line, g.expand(w, 0.03)) or line) >
               0.5 * g.length(line) for w in above.all_walls):
            continue
        s.rbox(line, above.z, above.z + 1.0, "glass", above.id)
        s.box(line[0], line[1], above.z + 0.97, line[2], line[3], above.z + 1.02, "frame", above.id)


# ------------------------------------------------------------------------------ furniture
def furniture(s, lv):
    walls_ = lv.all_walls
    for k, it in enumerate(lv.furniture):
        item = {"k": it.builder, "f": lv.id, "z": lv.z}
        if it.rect:
            item["r"] = [round(v, 3) for v in it.rect]
        if it.at:
            item["p"] = [round(v, 3) for v in it.at]
        if it.back:
            item["d"] = g.OPPOSITE[it.back]
        t = it.type
        if t == "rug":
            item["c"] = {"a": "rugA", "b": "rugB", "c": "rugC"}.get(str(it.extra.get("color", "")), RUGS[k % 3])
        elif t == "plant":
            item["s"], item["h"] = float(it.extra.get("size", 0.17)), float(it.extra.get("height", 1.4))
        elif t == "tank":
            item["s"] = float(it.extra.get("size", 0.24))
        elif t == "stools":
            item["n"], item["sides"] = int(it.extra["count"]), it.extra["sides"]
        elif t == "shoe_cabinet":
            item["h"] = float(it.extra.get("height", 1.0))
        elif t == "kitchen":
            item["sink"] = [round(v, 3) for v in kitchen_sink(lv, it)]
        elif t == "dining_table":
            item["chairs"] = [[round(x, 3), round(y, 3), g.OPPOSITE[back]] for x, y, back in dining_layout(it)]
        elif t == "shower":
            item["open"] = sorted(set(g.SIDES) - touching(walls_, it.rect))
        s.items.append(item)


def labels(s, model, lv):
    for room in lv.rooms:
        s.labels.append({"en": room.name, "alt": room.alt_name, "p": [*room.label_at, lv.z + 0.05], "f": lv.id})
    if lv.entrance:
        doors = [op for op in lv.openings if op.kind in ("door", "sliding") and is_exterior(lv, op.rect)]
        if doors:
            door = min(doors, key=lambda op: math.dist(g.center(op.rect), lv.entrance))
            side = next(sd for w, sd in lv.ext_walls if g.overlap(door.rect, w, 0.01))
            dx, dy = g.DIRS[side]
            cx, cy = g.center(door.rect)
            s.labels.append({"en": "Entrance", "alt": "", "p": [cx + dx * 1.2, cy + dy * 1.2, lv.z + 1.3], "f": "S"})


# ------------------------------------------------------------------------------ roof and site
def roof(s, model):
    top = model.top
    facade = FACADE.get(model.facade, "render")
    if model.roof["type"] == "flat":
        zw = model.wall_top
        p = model.roof.get("parapet", 0.5)
        for r in top.footprint:
            s.rbox(r, zw, zw + 0.3, "slab", "R")
        for w, _side in top.ext_walls:
            s.rbox(w, zw + 0.3, zw + 0.3 + p, facade, "R")
            s.rbox(g.expand(w, 0.02), zw + 0.3 + p, zw + 0.36 + p, "frame", "R")
        return {"type": "flat"}
    r = elevations.roof_geometry(model)
    bx0, by0, bx1, by1 = model.bbox
    axis = model.roof["ridge"]
    o = r["o"]
    lo, hi = r["across"]
    u0, u1 = ((bx0, bx1) if axis == "x" else (by0, by1))
    gable_faces = ("W", "E") if axis == "x" else ("S", "N")
    for w, side in top.ext_walls:
        if side not in gable_faces:
            continue
        on_edge = (side == "W" and abs(w[0] - bx0) < 1e-6) or (side == "E" and abs(w[2] - bx1) < 1e-6) or \
                  (side == "S" and abs(w[1] - by0) < 1e-6) or (side == "N" and abs(w[3] - by1) < 1e-6)
        if not on_edge:
            continue
        outer = [[lo, r["zw"]], [hi, r["zw"]], [r["mid"], r["ridge"] - 0.03]]
        if axis == "x":
            s.prisms.append({"axis": "x", "a0": w[0], "a1": w[2], "outer": outer, "holes": [],
                             "m": facade, "g": f"{top.id}.full"})
        else:
            s.prisms.append({"axis": "y", "a0": w[1], "a1": w[3], "outer": outer, "holes": [],
                             "m": facade, "g": f"{top.id}.full"})
    return {"type": "gable", "axis": axis, "u0": u0 - o, "u1": u1 + o, "vS": lo - o, "vM": r["mid"],
            "vN": hi + o, "zE": r["edge"], "zR": r["ridge"], "t": r["t"]}


def auto_trees(model):
    """Trees around the building: not on the street side, not close in front of any facade (so
    the renders stay clear), not on paving and not against the boundary."""
    site = model.site
    bx0, by0, bx1, by1 = model.bbox
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    street = g.DIRS[site.street_side] if site else (0, -1)
    out = []
    for k in range(32):
        ang = k * 2 * math.pi / 32
        for ring in (6.5, 10.0, 14.0):
            x = cx + math.cos(ang) * ((bx1 - bx0) / 2 + ring)
            y = cy + math.sin(ang) * ((by1 - by0) / 2 + ring)
            if site and not g.point_in_polygon((x, y), site.boundary):
                continue
            if site and min(g.distance_point_segment((x, y), a, b)
                            for a, b in zip(site.boundary, site.boundary[1:] + site.boundary[:1])) < 1.6:
                continue
            if (x - cx) * street[0] + (y - cy) * street[1] > 0:
                continue
            facing_x = bx0 - 1.0 < x < bx1 + 1.0 and min(abs(y - by0), abs(y - by1)) < 9.0
            facing_y = by0 - 1.0 < y < by1 + 1.0 and min(abs(x - bx0), abs(x - bx1)) < 9.0
            if facing_x or facing_y:
                continue
            if any(g.overlap((x - 1.6, y - 1.6, x + 1.6, y + 1.6), p, 0) for p in (site.paving if site else [])):
                continue
            if all(math.dist((x, y), (t[0], t[1])) > 4.2 for t in out):
                out.append([round(x, 2), round(y, 2), round(0.9 + 0.3 * ((k * 7) % 5) / 4, 2)])
    return out[:8]


def site(s, model):
    st = model.site
    bx0, by0, bx1, by1 = model.bbox
    low = min(lv.z for lv in model.levels)
    if st:
        xs_b = [p[0] for p in st.boundary]
        ys_b = [p[1] for p in st.boundary]
        ext = (min(xs_b) - 14, min(ys_b) - 14, max(xs_b) + 14, max(ys_b) + 14)
    else:
        ext = (bx0 - 22, by0 - 22, bx1 + 22, by1 + 22)
    edges_x = {round(v, 3) for r in model.levels[0].footprint for v in (r[0] + 0.06, r[0] + 0.07, r[2] - 0.07, r[2] - 0.06)}
    edges_y = {round(v, 3) for r in model.levels[0].footprint for v in (r[1] + 0.06, r[1] + 0.07, r[3] - 0.07, r[3] - 0.06)}
    xs = sorted({round(ext[0] + i, 3) for i in range(int(ext[2] - ext[0]) + 2)} | edges_x)
    ys = sorted({round(ext[1] + j, 3) for j in range(int(ext[3] - ext[1]) + 2)} | edges_y)
    inner = [g.expand(r, -0.065) for r in model.levels[0].footprint]
    z = [[(low - 0.35 if g.in_union(inner, (x, y)) else 0.0) for x in xs] for y in ys]
    out = {"terrain": {"xs": xs, "ys": ys, "z": z}, "plot": st.boundary if st else None,
           "bound": {"h": st.boundary_wall, "gaps": [list(gp) for gp in st.gates]} if st else None,
           "cars": [], "trees": [], "conifers": [], "patio": None}
    if st:
        for r in st.paving:
            s.rbox(r, -0.04, 0.02, "pave", "S")
        for k, (r, facing) in enumerate(st.parking):
            s.rbox(r, -0.035, 0.015, "concrete", "S")
            cx, cy = g.center(r)
            along = facing in ("E", "W")
            car = (cx - 2.35, cy - 0.95, cx + 2.35, cy + 0.95) if along else (cx - 0.95, cy - 2.35, cx + 0.95, cy + 2.35)
            out["cars"].append({"r": [round(v, 3) for v in car], "d": facing, "c": "carA" if k % 2 == 0 else "carB"})
        if st.trees == "auto":
            out["trees"] = auto_trees(model)
        elif isinstance(st.trees, list):
            out["trees"] = [[float(t[0]), float(t[1]), float(t[2]) if len(t) > 2 else 1.0] for t in st.trees]
        if st.patio_set:
            out["patio"] = list(st.patio_set)
        for name, alt, p in st.labels:
            s.labels.append({"en": name, "alt": alt, "p": [p[0], p[1], 0.1], "f": "S"})
    else:
        out["trees"] = auto_trees(model)
    return out


def build(model):
    s = Scene()
    for i, lv in enumerate(model.levels):
        nxt = model.levels[i + 1] if i + 1 < len(model.levels) else None
        full = (nxt.z - lv.z) if nxt else lv.height
        walls(s, model, lv, full)
        wall_shadows(s, lv)
        floors(s, lv)
        door_leaves(s, lv)
        stairs(s, model, lv)
        furniture(s, lv)
        labels(s, model, lv)
    roof_data = roof(s, model)
    site_data = site(s, model)
    bx0, by0, bx1, by1 = model.bbox
    street = model.site.street_side if model.site else "S"
    front = g.BEARING[street] + 35
    low = min(lv.z for lv in model.levels)
    return {
        "project": {"title": model.project.get("title", ""), "subtitle": model.project.get("subtitle", ""),
                    "alt_title": model.project.get("alt_title", "")},
        "center": [round((bx0 + bx1) / 2, 3), round((by0 + by1) / 2, 3)],
        "house": [bx0, by0, bx1, by1],
        "bounds": [bx0 - 2.5, by0 - 2.5, max(low, -0.5), bx1 + 2.5, by1 + 2.5, elevations.top_height(model)],
        "levels": [{"id": lv.id, "name": lv.name, "alt": lv.alt_name, "z": lv.z, "height": lv.height}
                   for lv in model.levels],
        "views": {"front": front % 360, "rear": (front + 180) % 360},
        "cut": CUT,
        "boxes": s.boxes, "prisms": s.prisms, "quads": s.quads, "ao": s.ao, "items": s.items,
        "labels": s.labels, "roof": roof_data, **site_data,
    }

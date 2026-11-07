"""Elevations of the four faces and a building section, projected from the design model.

Pens here work in (u, z): u runs left to right as seen by the viewer, z is the level in metres.
"""
from __future__ import annotations

import math

from . import geometry as g
from .plans import flights, level_text, stair_frame

SLAB = 0.25
ROOF_T = 0.25


def face_axis(model, face):
    """For a face (the side the viewer stands on): plan -> u mapping, and whether x or y is along it."""
    x0, y0, x1, y1 = model.bbox
    return {"S": (lambda x, y: x, "x"), "N": (lambda x, y: x0 + x1 - x, "x"),
            "E": (lambda x, y: y, "y"), "W": (lambda x, y: y0 + y1 - y, "y")}[face]


def intervals(rects, axis):
    """Merged [a, b] spans of rectangles projected on an axis."""
    spans = sorted((r[0], r[2]) if axis == "x" else (r[1], r[3]) for r in rects)
    out = []
    for a, b in spans:
        if out and a <= out[-1][1] + 1e-6:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def roof_geometry(model):
    """Gable roof heights: wall top, eave edge, ridge, the underside at any across-coordinate."""
    roof = model.roof
    x0, y0, x1, y1 = model.bbox
    across = (y0, y1) if roof.get("ridge") == "x" else (x0, x1)
    tan = math.tan(math.radians(roof.get("pitch", 30)))
    zw = model.wall_top
    mid = (across[0] + across[1]) / 2
    half = (across[1] - across[0]) / 2

    def under(v):
        return zw + (half - abs(v - mid)) * tan

    o = roof.get("overhang", 0.5)
    return {"zw": zw, "edge": zw - o * tan, "ridge": zw + half * tan, "mid": mid, "across": across,
            "under": under, "o": o, "t": ROOF_T / math.cos(math.atan(tan))}


def top_height(model):
    if model.roof["type"] == "gable":
        r = roof_geometry(model)
        return r["ridge"] + r["t"]
    return model.wall_top + 0.3 + model.roof.get("parapet", 0.5)


def draw_elevation(pen, model, face):
    to_u, axis = face_axis(model, face)
    bx0, by0, bx1, by1 = model.bbox
    ends = sorted((to_u(bx0, by0), to_u(bx1, by1)))
    pen.line((ends[0] - 2.0, 0.0), (ends[1] + 2.0, 0.0), "A-SITE")
    eave_face = model.roof["type"] == "gable" and model.roof["ridge"] == axis
    for lv in model.levels:
        top = lv.z + lv.height if lv is not model.top else model.wall_top
        if lv is model.top and eave_face:          # the eave overhang hides the top of the wall
            top = roof_geometry(model)["edge"]
        hidden = top <= 0.05
        layer = "A-ELEV-HIDD" if hidden else "A-ELEV"
        for a, b in intervals(lv.footprint, axis):
            ua, ub = sorted((to_u(a, a), to_u(b, b)))
            z0 = max(lv.z, 0.0) if not hidden else lv.z
            pts = [(ua, z0), (ub, z0), (ub, top), (ua, top)]
            pen.poly(pts, layer, close=True, **({"linetype": "DASHED", "ltscale": 3} if hidden else {}))
        if hidden:
            continue
        for w, side in lv.ext_walls:
            if side != face:
                continue
            for op in lv.openings:
                if not g.overlap(op.rect, w, 0.01):
                    continue
                a, b = (op.rect[0], op.rect[2]) if axis == "x" else (op.rect[1], op.rect[3])
                ua, ub = sorted((to_u(a, a), to_u(b, b)))
                if op.kind == "window":
                    z0, z1 = lv.z + op.sill, lv.z + min(op.head, lv.height - SLAB)
                    pen.rect((ua, z0, ub, z1), "A-GLAZ")
                    pen.rect((ua + 0.05, z0 + 0.05, ub - 0.05, z1 - 0.05), "A-GLAZ")
                    if ub - ua > 1.2:
                        pen.line(((ua + ub) / 2, z0 + 0.05), ((ua + ub) / 2, z1 - 0.05), "A-GLAZ")
                    pen.line((ua - 0.05, z0), (ub + 0.05, z0), "A-ELEV")
                elif op.kind in ("door", "sliding"):
                    z1 = lv.z + op.head
                    pen.rect((ua, lv.z, ub, z1), "A-DOOR")
                    pen.line(((ua + ub) / 2, lv.z), ((ua + ub) / 2, z1), "A-DOOR")
    draw_roof_elevation(pen, model, face, to_u, axis)
    marks = [(lv.z, level_text(lv.z)) for lv in model.levels if lv.z >= -0.01]
    marks.append((top_height(model), level_text(top_height(model))))
    for z, text in marks:
        level_flag(pen, ends[1] + 1.2, z, text)


def draw_roof_elevation(pen, model, face, to_u, axis):
    bx0, by0, bx1, by1 = model.bbox
    if model.roof["type"] == "flat":
        top = model.wall_top + 0.3 + model.roof.get("parapet", 0.5)
        for a, b in intervals(model.top.footprint, axis):
            ua, ub = sorted((to_u(a, a), to_u(b, b)))
            pen.rect((ua, model.wall_top, ub, top), "A-ROOF")
        return
    r = roof_geometry(model)
    o = r["o"]
    ridge_along_view = (model.roof["ridge"] == axis)
    if ridge_along_view:                       # the eave side: the roof slope rises behind the eave
        ua, ub = sorted((to_u(bx0, by0), to_u(bx1, by1)))
        pen.poly([(ua - o, r["edge"]), (ub + o, r["edge"]), (ub + o, r["ridge"] + r["t"]),
                  (ua - o, r["ridge"] + r["t"])], "A-ROOF", close=True)
        pen.line((ua - o, r["edge"] + r["t"]), (ub + o, r["edge"] + r["t"]), "A-ROOF")
    else:                                      # the gable end: a triangle over the end wall
        lo, hi = r["across"]
        ua, ub = sorted((to_u(lo, lo), to_u(hi, hi)))
        um = (ua + ub) / 2
        pen.poly([(ua, r["zw"]), (um, r["ridge"]), (ub, r["zw"])], "A-ELEV")
        pen.poly([(ua - o, r["edge"]), (um, r["ridge"]), (ub + o, r["edge"]), (ub + o, r["edge"] + r["t"]),
                  (um, r["ridge"] + r["t"]), (ua - o, r["edge"] + r["t"])], "A-ROOF", close=True)


def level_flag(pen, u, z, text):
    pen.poly([(u - 0.18, z + 0.3), (u + 0.18, z + 0.3), (u, z)], "A-ANNO-SYMB", close=True)
    pen.line((u - 0.5, z), (u + 0.5, z), "A-ANNO-SYMB")
    pen.text(text, (u + 0.3, z + 0.32), h=2.0, align="MIDDLE_LEFT")


# ------------------------------------------------------------------------------ section
def section_cut(model):
    """Where section A-A cuts: building.section if given; otherwise across the ridge, through the
    first flight of the lowest stair (or the middle of the building)."""
    if model.section:
        return model.section
    bx0, by0, bx1, by1 = model.bbox
    axis = "x" if model.roof["type"] != "gable" or model.roof["ridge"] == "x" else "y"
    # axis 'x' = a north-south cut line at some x (viewer looks west); 'y' = an east-west line
    stair = next((s for lv in model.levels for s in lv.stairs_up), None)
    if stair is not None:
        fl = flights(stair)[0]
        f = stair_frame(stair)
        cx, cy = f(stair.run_length / 3, (fl[0] + fl[1]) / 2)
        value = cx if axis == "x" else cy
    else:
        value = (bx0 + bx1) / 2 if axis == "x" else (by0 + by1) / 2
    return axis, round(value, 3)


def draw_section(pen, model, cut):
    axis, v = cut
    # u along the section: looking west (cut at x) u = y; looking north (cut at y) u = x
    def crossing(r):
        return r[0] < v < r[2] if axis == "x" else r[1] < v < r[3]

    def span(r):
        return (r[1], r[3]) if axis == "x" else (r[0], r[2])

    bx0, by0, bx1, by1 = model.bbox
    lo, hi = (by0, by1) if axis == "x" else (bx0, bx1)
    pen.line((lo - 2.0, 0.0), (hi + 2.0, 0.0), "A-SITE")
    for lv in model.levels:
        top = lv.z + lv.height if lv is not model.top else model.wall_top
        floor_spans = intervals([r for r in lv.footprint if crossing(r)], "y" if axis == "x" else "x")
        voids = [span(s.rect) for s in lv.stairs_down if crossing(s.rect)]
        for a, b in floor_spans:
            pieces = [(a, b)]
            for va, vb in voids:
                pieces = [p for (pa, pb) in pieces for p in ((pa, min(pb, va)), (max(pa, vb), pb)) if p[1] - p[0] > 1e-6]
            for pa, pb in pieces:
                pen.fill_rect((pa, lv.z - SLAB, pb, lv.z), "A-SECT-PATT", color=8)
                pen.rect((pa, lv.z - SLAB, pb, lv.z), "A-SECT")
        for w in lv.all_walls:
            if not crossing(w):
                continue
            a, b = span(w)
            ops = [op for op in lv.openings if crossing(op.rect) and g.overlap(op.rect, w, 0.005)]
            parts = [(lv.z, top)]
            for op in ops:
                if op.kind == "window":
                    parts = [(z0, z1) for (p0, p1) in parts
                             for (z0, z1) in ((p0, min(p1, lv.z + op.sill)), (max(p0, lv.z + op.head), p1))
                             if z1 - z0 > 1e-6]
                    pen.line(((a + b) / 2, lv.z + op.sill), ((a + b) / 2, lv.z + op.head), "A-GLAZ")
                else:
                    parts = [(max(p0, lv.z + op.head), p1) for (p0, p1) in parts if p1 > lv.z + op.head]
            for z0, z1 in parts:
                pen.fill_rect((a, z0, b, z1), "A-SECT-PATT", color=8)
                pen.rect((a, z0, b, z1), "A-SECT")
        for s in lv.stairs_up:
            if crossing(s.rect):
                draw_stair_profile(pen, s, lv.z, axis)
        for room in lv.rooms:
            if crossing(room.rect):
                a, b = span(room.rect)
                pen.text(room.name, ((a + b) / 2, lv.z + 1.3), h=1.8)
    draw_roof_section(pen, model, axis, v, lo, hi)
    for lv in model.levels:
        level_flag(pen, lo - 1.4, lv.z, level_text(lv.z))
    level_flag(pen, lo - 1.4, top_height(model), level_text(top_height(model)))
    zs = [lv.z for lv in model.levels] + [model.wall_top]
    for a, b in zip(zs, zs[1:]):
        pen.dim((hi + 1.0, a), (hi + 1.0, b), 0.0, vertical=True)


def draw_stair_profile(pen, stair, z, axis):
    """The flight the cut passes through, as a saw-tooth of risers and treads."""
    along_cut = (stair.up in ("N", "S")) == (axis == "x")
    if not along_cut:
        return
    r = stair.rect
    start = {"N": r[1], "S": r[3], "E": r[0], "W": r[2]}[stair.up]
    sign = 1 if stair.up in ("N", "E") else -1
    n = stair.risers if stair.kind == "straight" else stair.risers // 2
    rise, going = stair.rise, stair.going
    pts, u, h = [(start, z)], start, z
    for k in range(n):
        h += rise
        pts.append((u, h))
        if k < n - 1:
            u += sign * going
            pts.append((u, h))
    pen.poly(pts, "A-SECT")
    pen.line((start, z), (u, h - rise * 0.6), "A-SECT")


def draw_roof_section(pen, model, axis, v, lo, hi):
    if model.roof["type"] == "flat":
        top = model.wall_top
        pen.fill_rect((lo, top, hi, top + 0.3), "A-SECT-PATT", color=8)
        pen.rect((lo, top, hi, top + 0.3), "A-SECT")
        p = model.roof.get("parapet", 0.5)
        t = model.exterior_wall
        for a in (lo, hi - t):
            pen.rect((a, top + 0.3, a + t, top + 0.3 + p), "A-SECT")
        return
    r = roof_geometry(model)
    o = r["o"]
    if (model.roof["ridge"] == "x") == (axis == "x"):        # cut across the ridge: the triangle
        a, b = r["across"]
        m = r["mid"]
        outline = [(a - o, r["edge"]), (m, r["ridge"]), (b + o, r["edge"]), (b + o, r["edge"] + r["t"]),
                   (m, r["ridge"] + r["t"]), (a - o, r["edge"] + r["t"])]
        pen.fill(outline, "A-SECT-PATT", color=8)
        pen.poly(outline, "A-SECT", close=True)
    else:                                                    # cut along the ridge: a band
        z = r["under"](v)
        pen.fill_rect((lo - o, z, hi + o, z + r["t"]), "A-SECT-PATT", color=8)
        pen.rect((lo - o, z, hi + o, z + r["t"]), "A-SECT")

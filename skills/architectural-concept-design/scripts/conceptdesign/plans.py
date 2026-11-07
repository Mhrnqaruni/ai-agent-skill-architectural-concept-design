"""One floor plan: walls, openings, stairs, furniture, room labels, dimensions and level marks."""
from __future__ import annotations

from . import areas
from . import geometry as g
from .cad import arc_between, ellipse, text_width


def level_text(z):
    return "±0.00" if abs(z) < 0.005 else f"{z:+.2f}"


# ------------------------------------------------------------------------------ walls and openings
def draw_walls(pen, lv):
    cuts = [op.rect for op in lv.openings]
    for w in lv.all_walls:
        for piece in g.split_rect(w, cuts):
            pen.fill_rect(piece, "A-WALL-PATT", color=250)
            pen.rect(piece, "A-WALL")


def draw_door(pen, op):
    x0, y0, x1, y1 = op.rect
    s, at_end = op.swing, op.at_end
    if g.is_horizontal(op.rect):
        width, face = x1 - x0, (y1 if s > 0 else y0)
        hinge = (x1 if at_end else x0, face)
        leaf = (hinge[0], face + s * width)
        a_leaf, a_closed = (90 if s > 0 else 270), (180 if at_end else 0)
    else:
        width, face = y1 - y0, (x1 if s > 0 else x0)
        hinge = (face, y1 if at_end else y0)
        leaf = (face + s * width, hinge[1])
        a_leaf, a_closed = (0 if s > 0 else 180), (270 if at_end else 90)
    pen.line(hinge, leaf, "A-DOOR")
    pen.arc(hinge, width, *arc_between(a_leaf, a_closed), "A-DOOR")


def draw_sliding(pen, op):
    x0, y0, x1, y1 = op.rect
    if g.is_horizontal(op.rect):
        ym, length = (y0 + y1) / 2, x1 - x0
        pen.line((x0, ym - 0.03), (x0 + length * 0.55, ym - 0.03), "A-DOOR")
        pen.line((x1 - length * 0.55, ym + 0.03), (x1, ym + 0.03), "A-DOOR")
    else:
        xm, length = (x0 + x1) / 2, y1 - y0
        pen.line((xm - 0.03, y0), (xm - 0.03, y0 + length * 0.55), "A-DOOR")
        pen.line((xm + 0.03, y1 - length * 0.55), (xm + 0.03, y1), "A-DOOR")


def draw_window(pen, op):
    x0, y0, x1, y1 = op.rect
    if g.is_horizontal(op.rect):
        ym = (y0 + y1) / 2
        for y in (y0, y1, ym - 0.025, ym + 0.025):
            pen.line((x0, y), (x1, y), "A-GLAZ")
    else:
        xm = (x0 + x1) / 2
        for x in (x0, x1, xm - 0.025, xm + 0.025):
            pen.line((x, y0), (x, y1), "A-GLAZ")


def draw_openings(pen, lv):
    for op in lv.openings:
        {"door": draw_door, "sliding": draw_sliding, "window": draw_window}.get(op.kind, lambda *_: None)(pen, op)


# ------------------------------------------------------------------------------ stairs
def stair_frame(stair):
    """Map stair-local (u along the climb from the bottom end, v across from the left) to plan."""
    x0, y0, x1, y1 = stair.rect
    up = stair.up
    if up == "N":
        return lambda u, v: (x0 + v, y0 + u)
    if up == "S":
        return lambda u, v: (x1 - v, y1 - u)
    if up == "E":
        return lambda u, v: (x0 + u, y1 - v)
    return lambda u, v: (x1 - u, y0 + v)


def stair_across(stair):
    return (stair.rect[2] - stair.rect[0]) if stair.along_y else (stair.rect[3] - stair.rect[1])


def flights(stair):
    """Flights as (v0, v1, u_from, u_to, risers, z_from_fraction): straight = 1, U = 2."""
    width, length = stair_across(stair), stair.run_length
    if stair.kind == "straight":
        return [(0.0, width, 0.0, length, stair.risers, 0.0)]
    half = (width - 0.1) / 2
    left, right = (0.0, half), (half + 0.1, width)
    first, second = (left, right) if stair.turn == "right" else (right, left)
    end = length - stair.landing
    n = stair.risers // 2
    return [(first[0], first[1], 0.0, end, n, 0.0), (second[0], second[1], end, 0.0, n, 0.5)]


def draw_stair(pen, stair, label, down=False):
    """Treads, the walking line and an arrow. Going up, the arrow starts at the bottom step; on the
    floor above (down=True) it starts where people step onto the stair to go down."""
    f = stair_frame(stair)
    width, length = stair_across(stair), stair.run_length

    def poly(pts, close=False):
        pen.poly([f(u, v) for u, v in pts], "A-FLOR-STRS", close=close)

    poly([(0, 0), (length, 0), (length, width), (0, width)], close=True)
    fl = flights(stair)
    for v0, v1, ua, ub, n, _ in fl:
        going = (ub - ua) / (n - 1) if n > 1 else 0
        for k in range(1, n - 1 if stair.kind == "u" else n):
            u = ua + k * going
            poly([(u, v0), (u, v1)])
    if stair.kind == "u":
        end = length - stair.landing
        half = (width - 0.1) / 2
        poly([(0, half), (end, half), (end, half + 0.1), (0, half + 0.1)], close=True)
        poly([(end, 0), (end, width)])
        a, b = (fl[0][0] + fl[0][1]) / 2, (fl[1][0] + fl[1][1]) / 2
        mid = end + stair.landing / 2
        path = [(0.15, a), (mid, a), (mid, b), (0.45, b)]
        top = (-0.18, b)
    else:
        a = width / 2
        path = [(0.15, a), (length - 0.3, a)]
        top = (length + 0.18, a)
    if down:
        path = path[::-1]
        path[-1] = (path[-1][0] + (0.15 if path[-1][0] < 1 else -0.15), path[-1][1])
    poly(path)
    (ua, va), (ub, vb) = path[-2], path[-1]
    du, dv = ub - ua, vb - va
    n = (du * du + dv * dv) ** 0.5 or 1.0
    du, dv = du / n, dv / n
    tip = (ub + du * 0.15, vb + dv * 0.15)
    poly([(tip[0] - du * 0.2 - dv * 0.12, tip[1] - dv * 0.2 + du * 0.12), tip,
          (tip[0] - du * 0.2 + dv * 0.12, tip[1] - dv * 0.2 - du * 0.12)])
    where = top if down else (-0.18, fl[0][0] + (fl[0][1] - fl[0][0]) / 2)
    pen.text(label, f(*where), h=1.8, layer="A-ANNO-TEXT")


def draw_stairs(pen, lv):
    drawn = []
    for s in lv.stairs_up:
        both = any(g.overlap(s.rect, d.rect, 0.05) for d in lv.stairs_down)
        draw_stair(pen, s, "UP / DN" if both else "UP")
        drawn.append(s.rect)
    for s in lv.stairs_down:
        if any(g.overlap(s.rect, r, 0.05) for r in drawn):
            continue
        draw_stair(pen, s, "DN", down=True)


# ------------------------------------------------------------------------------ furniture
def local(pen, origin, facing, pts, layer="A-FURN", close=True):
    """Points as (across, along) the facing direction, from origin."""
    fx, fy = g.DIRS[facing]
    pen.poly([(origin[0] + a * fy + b * fx, origin[1] - a * fx + b * fy) for a, b in pts], layer, close=close)


def kitchen_sink(lv, item):
    """Where the sink goes along a kitchen run: under the middle of a window behind it, else the middle."""
    r = item.rect
    if "sink_at" in item.extra:
        return tuple(item.extra["sink_at"])
    zone = g.expand(r, 0.5)
    for op in lv.openings:
        if op.kind == "window" and g.overlap(op.rect, zone, 0.01):
            if g.is_horizontal(r) and min(op.rect[2], r[2]) - max(op.rect[0], r[0]) > 0.5:
                return ((max(op.rect[0], r[0]) + min(op.rect[2], r[2])) / 2, (r[1] + r[3]) / 2)
            if not g.is_horizontal(r) and min(op.rect[3], r[3]) - max(op.rect[1], r[1]) > 0.5:
                return ((r[0] + r[2]) / 2, (max(op.rect[1], r[1]) + min(op.rect[3], r[3])) / 2)
    return g.center(r)


def inset(r, d):
    return (r[0] + d, r[1] + d, r[2] - d, r[3] - d)


def back_line(r, back, d):
    """A line parallel to the back side of r, d metres in from it."""
    x0, y0, x1, y1 = r
    return {"N": ((x0, y1 - d), (x1, y1 - d)), "S": ((x0, y0 + d), (x1, y0 + d)),
            "E": ((x1 - d, y0), (x1 - d, y1)), "W": ((x0 + d, y0), (x0 + d, y1))}[back]


def draw_item(pen, lv, it):
    from .rules import dining_layout
    t, r = it.type, it.rect
    if t == "wc":
        x, y = it.at
        facing = g.OPPOSITE[it.back]
        local(pen, (x, y), facing, [(-0.225, 0), (0.225, 0), (0.225, 0.2), (-0.225, 0.2)])
        local(pen, (x, y), facing, [(a, b + 0.44) for a, b in ellipse((0, 0), 0.18, 0.24)])
        return
    if t in ("chair",):
        x, y = it.at
        pen.rect((x - 0.22, y - 0.22, x + 0.22, y + 0.22), "A-FURN")
        pen.line(*back_line((x - 0.22, y - 0.22, x + 0.22, y + 0.22), it.back, 0.06), "A-FURN")
        return
    if t in ("barstool", "plant", "tank"):
        size = {"barstool": 0.18}.get(t) or float(it.extra.get("size", 0.2)) * (1.4 if t == "plant" else 1.0)
        pen.circle(it.at, size, "A-FURN")
        return
    if t == "stools":
        n, sides = int(it.extra["count"]), it.extra["sides"]
        step = (r[2] - r[0]) / n
        for k in range(n):
            x = r[0] + (k + 0.5) * step
            if "S" in sides:
                pen.circle((x, r[1] - 0.1), 0.17, "A-FURN")
            if "N" in sides:
                pen.circle((x, r[3] + 0.1), 0.17, "A-FURN")
        return
    if t == "rug":
        pen.rect(r, "A-FURN", linetype="DASHED", ltscale=0.4)
        return
    pen.rect(r, "A-FURN")
    if t == "bed":
        pen.line(*back_line(r, it.back, 0.35), "A-FURN")
    elif t in ("sofa", "armchair"):
        pen.line(*back_line(r, it.back, 0.2), "A-FURN")
    elif t in ("bathtub", "billiards"):
        pen.rect(inset(r, 0.1), "A-FURN")
    elif t == "shower":
        pen.line((r[0], r[1]), (r[2], r[3]), "A-FURN")
        pen.circle(g.center(r), 0.04, "A-FURN")
    elif t == "basin":
        c = g.center(r)
        pen.poly(ellipse(c, (r[2] - r[0]) * 0.32, (r[3] - r[1]) * 0.32), "A-FURN", close=True)
    elif t == "fridge":
        pen.rect(inset(r, 0.04), "A-FURN")
        pen.text("REF", g.center(r), h=1.3, layer="A-FURN")
    elif t == "wardrobe":
        pen.line((r[0], r[1]), (r[2], r[3]), "A-FURN")
        pen.line((r[0], r[3]), (r[2], r[1]), "A-FURN")
    elif t == "hanging_rail":
        pen.line(*back_line(r, it.back, (g.thickness(r)) / 2), "A-FURN")
    elif t == "tv":
        a, b = back_line(r, it.back, 0.06)
        pen.line(a, b, "A-FURN")
    elif t == "kitchen":
        sx, sy = kitchen_sink(lv, it)
        horizontal = g.is_horizontal(r)
        sink = (sx - 0.3, sy - 0.2, sx + 0.3, sy + 0.2) if horizontal else (sx - 0.2, sy - 0.3, sx + 0.2, sy + 0.3)
        pen.rect(sink, "A-FURN")
        hob_c = (sx + 0.95, sy) if horizontal else (sx, sy + 0.95)
        if not g.contains(r, hob_c):
            hob_c = (sx - 0.95, sy) if horizontal else (sx, sy - 0.95)
        for dx, dy in ((-0.14, -0.13), (0.14, -0.13), (-0.14, 0.13), (0.14, 0.13)):
            pen.circle((hob_c[0] + dx, hob_c[1] + dy), 0.08, "A-FURN")
    elif t == "laundry":
        pen.circle(g.center(r), min(r[2] - r[0], r[3] - r[1]) * 0.32, "A-FURN")
    elif t == "dining_table":
        for x, y, back in dining_layout(it):
            chair = (x - 0.21, y - 0.21, x + 0.21, y + 0.21)
            pen.rect(chair, "A-FURN")
            pen.line(*back_line(chair, back, 0.05), "A-FURN")
    elif t == "sauna":
        pen.line(*back_line(r, "N", 0.55), "A-FURN")


def draw_furniture(pen, lv):
    for it in lv.furniture:
        draw_item(pen, lv, it)


# ------------------------------------------------------------------------------ scale and labels
SHEET_BOX = (305.0, 223.0)       # free drawing area on an A3 plan sheet, millimetres
PLAN_MARGIN = 1.9                # metres around a plan for dimension chains and section marks


def fit_scale(width_m, height_m, box_w, box_h, options=(50, 100, 200)):
    for s in options:
        if width_m * 1000 / s <= box_w and height_m * 1000 / s <= box_h:
            return s
    return options[-1]


def plan_scale(lv):
    """The scale a level's plan sheet uses: 1:50 when it fits on A3, else 1:100 or 1:200."""
    x0, y0, x1, y1 = lv.bbox
    return fit_scale(x1 - x0 + 2 * PLAN_MARGIN, y1 - y0 + 2 * PLAN_MARGIN, *SHEET_BOX)


def label_lines(room, area, scale):
    """The lines of a room label as (text, paper height in mm, offset in metres), and the label's
    width and height in metres. Text is a little smaller on 1:100 plans, where rooms are small."""
    f = 1.0 if scale <= 50 else 0.8
    sizes = (1.5, 1.6, 1.4, 4.0) if area < 3.6 else (2.2, 2.4, 1.8, 6.4)      # name, alt, area, line gap
    h1, h2, h3, gap = (v * f for v in sizes)
    m = scale / 1000.0                                                          # metres per paper mm
    area_text = f"{area:.1f} m²"
    if room.alt_name:
        lines = [(room.name, h1, gap * m), (room.alt_name, h2, 0.0), (area_text, h3, -gap * m)]
    else:
        lines = [(room.name, h1, gap * m / 2), (area_text, h3, -gap * m / 2)]
    width = max(text_width(text, h) for text, h, _ in lines) * m
    height = max(dy for *_, dy in lines) - min(dy for *_, dy in lines) + max(h for _, h, _ in lines) * m
    return lines, (width, height)


def label_box(room, area, scale):
    _, (w, h) = label_lines(room, area, scale)
    x, y = room.label_at
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def draw_room_labels(pen, lv):
    net = areas.net_areas(lv)
    for room in lv.rooms:
        lines, _ = label_lines(room, net.get(room.index, 0.0), pen.scale)
        x, y = room.label_at
        for text, h, dy in lines:
            pen.text(text, (x, y + dy), h=h, layer="A-AREA-IDEN")


def chain(values, minimum=0.45):
    out = []
    for v in sorted(values):
        if not out or v - out[-1] >= minimum:
            out.append(round(v, 3))
    return out


def auto_chains(lv):
    """Dimension chains along the north face (x) and the west face (y): outline corners plus the
    partitions that meet those faces."""
    x0, y0, x1, y1 = lv.bbox
    xs = {r[0] for r in lv.footprint} | {r[2] for r in lv.footprint}
    ys = {r[1] for r in lv.footprint} | {r[3] for r in lv.footprint}
    north = [w for w, side in lv.ext_walls if side == "N"]
    west = [w for w, side in lv.ext_walls if side == "W"]
    for w in lv.walls:
        if not g.is_horizontal(w) and any(abs(w[3] - n[1]) < 0.03 and n[0] <= w[0] <= n[2] for n in north):
            xs.add((w[0] + w[2]) / 2)
        if g.is_horizontal(w) and any(abs(w[0] - s[2]) < 0.03 and s[1] <= w[1] <= s[3] for s in west):
            ys.add((w[1] + w[3]) / 2)
    return chain(xs), chain(ys)


def draw_dims(pen, lv):
    x0, y0, x1, y1 = lv.bbox
    pen.dim((x0, y0), (x1, y0), -1.3)
    pen.dim((x1, y0), (x1, y1), 1.3, vertical=True)
    xs, ys = auto_chains(lv)
    xs, ys = lv.dims.get("x", xs), lv.dims.get("y", ys)
    if len(xs) > 2:                              # a two-point chain only repeats the overall size
        for a, b in zip(xs, xs[1:]):
            pen.dim((a, y1), (b, y1), 0.9)
    if len(ys) > 2:
        for a, b in zip(ys, ys[1:]):
            pen.dim((x0, a), (x0, b), -0.9, vertical=True)


def draw_level_mark(pen, at, text, r=0.15):
    x, y = at
    pen.circle(at, r, "A-FLOR-LEVL")
    pen.line((x - r * 1.4, y), (x + r * 1.4, y), "A-FLOR-LEVL")
    pen.line((x, y - r * 1.4), (x, y + r * 1.4), "A-FLOR-LEVL")
    for sx, sy in ((1, 1), (-1, -1)):
        pts = [(x, y)] + [(x + sx * r * c, y + sy * r * s) for c, s in
                          ((1, 0), (0.92, 0.38), (0.71, 0.71), (0.38, 0.92), (0, 1))]
        pen.fill(pts, "A-FLOR-LEVL")
    pen.text(text, (x + r * 2.0, y), h=2.0, layer="A-FLOR-LEVL", align="MIDDLE_LEFT")


def level_mark_point(lv, scale=50):
    """A clear spot for the floor level mark, as close as possible to the entrance or the stairs:
    inside a room and clear of walls, door swings, stairs, room labels and furniture. If no room has
    space, furniture may be crossed; failing that, the mark goes just outside the building, between
    the wall and the overall dimension line."""
    from .rules import footprints, swing_discs
    m = scale / 1000.0
    width, half = 0.3 + 11.0 * m, max(0.22, 0.14 * scale / 50)       # symbol plus "FFL ±0.00"
    net = areas.net_areas(lv)
    hard = [g.expand(w, 0.05) for w in lv.all_walls]
    hard += [(c[0] - r, c[1] - r, c[0] + r, c[1] + r) for op in lv.openings for c, r, _, _ in swing_discs(op)]
    hard += [g.expand(s.rect, 0.1) for s in lv.stairs_up + lv.stairs_down]
    hard += [g.expand(label_box(room, net.get(room.index, 0.0), scale), 0.1) for room in lv.rooms]
    soft = [g.expand(fp, 0.12) for it in lv.furniture for fp in footprints(it)]
    stair = (lv.stairs_down + lv.stairs_up or [None])[0]
    anchor = lv.entrance or (g.center(stair.rect) if stair else g.center(lv.bbox))
    for obstacles in (hard + soft, hard):
        best = None
        for room in lv.rooms:
            for reg in room.regions:
                x = reg[0] + 0.35
                while x + width < reg[2]:
                    y = reg[1] + half + 0.1
                    while y + half < reg[3]:
                        box = (x - 0.25, y - half, x + width, y + half)
                        if g.contains_rect(reg, box) and not any(g.overlap(box, o) for o in obstacles):
                            d = (x - anchor[0]) ** 2 + (y - anchor[1]) ** 2
                            if best is None or d < best[0]:
                                best = (d, (x, y))
                        y += 0.2
                    x += 0.2
        if best:
            return best[1]
    x0, y0, _, _ = lv.bbox
    return (x0 + 0.4, y0 - 0.65)


def draw_section_line(pen, lv, cut):
    """Section mark: cut = ('x', value) cuts along a north-south line, ('y', value) an east-west one."""
    x0, y0, x1, y1 = lv.bbox
    axis, v = cut
    # the marks sit outside the dimension chains (0.9 m) and the overall dimensions (1.3 m)
    if axis == "y":
        a, b, look = (x0 - 1.5, v), (x1 + 1.9, v), (0, 1)
    else:
        a, b, look = (v, y0 - 1.9), (v, y1 + 1.5), (-1, 0)
    pen.poly([a, b], "A-ANNO-SYMB", linetype="DASHDOT", ltscale=4)
    for end in (a, b):
        pen.circle(end, 0.32, "A-ANNO-SYMB")
        pen.text("A", end, h=3.0, layer="A-ANNO-SYMB")
        tip = (end[0] + look[0] * 0.75, end[1] + look[1] * 0.75)
        side = (look[1] * 0.25, -look[0] * 0.25)
        base = (end[0] + look[0] * 0.32, end[1] + look[1] * 0.32)
        pen.fill([(base[0] + side[0], base[1] + side[1]), tip, (base[0] - side[0], base[1] - side[1])],
                 "A-ANNO-SYMB")


def draw_roof_edge(pen, model):
    if model.roof["type"] != "gable":
        return
    x0, y0, x1, y1 = model.bbox
    o = model.roof["overhang"]
    pen.rect((x0 - o, y0 - o, x1 + o, y1 + o), "A-ROOF", linetype="DASHED", ltscale=6)


def draw_plan(pen, model, lv, cut=None):
    draw_walls(pen, lv)
    draw_openings(pen, lv)
    draw_stairs(pen, lv)
    draw_furniture(pen, lv)
    draw_room_labels(pen, lv)
    draw_dims(pen, lv)
    draw_level_mark(pen, level_mark_point(lv, pen.scale), f"FFL {level_text(lv.z)}")
    if lv is model.top:
        draw_roof_edge(pen, model)
    if cut:
        draw_section_line(pen, lv, cut)

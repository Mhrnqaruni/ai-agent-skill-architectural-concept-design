"""The A3 drawing set: cover and area schedule, site plan, floor plans, elevations and a section.

Each sheet is written as DXF R2018 on AIA / NCS layers, rendered to PDF and PNG with the ezdxf
drawing add-on, and re-read in recovery mode for an audit. A combined PDF and a true-size DXF of
every plan in metres complete the set.
"""
from __future__ import annotations

import datetime as dt
import math
import re
from pathlib import Path

import fitz
from ezdxf import recover
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, pymupdf

from . import areas, elevations, plans
from . import geometry as g
from .cad import Pen, fit_height, new_doc, put_text

W, H = 420.0, 297.0
FRAME = (20.0, 10.0, 410.0, 287.0)
STRIP_X = 345.0
BOX = (30.0, 55.0, 335.0, 278.0)              # free drawing area left of the title strip
PNG_DPI = 150
NOTES = ["Dimensions in metres; levels relative to ±0.00.",
         "Concept stage: sizes approximate until design development.",
         "Structure, foundations and building services",
         "to be designed by licensed engineers.",
         "Furniture and fixtures shown schematically."]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def t(msp, s, x, y, h, align="MIDDLE_LEFT", layer="A-ANNO-TEXT"):
    if s:
        put_text(msp, s, (x, y), h, layer=layer, align=align)


def hline(msp, x0, x1, y, layer="A-ANNO-TTLB"):
    msp.add_line((x0, y), (x1, y), dxfattribs={"layer": layer})


def box(msp, x0, y0, x1, y1, layer="A-ANNO-TTLB"):
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": layer})


def frame(msp, model, number, title, alt_title, scale_text):
    p = model.project
    msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True,
                       dxfattribs={"layer": "A-ANNO-NPLT", "true_color": 0xFFFFFF})
    box(msp, *FRAME)
    x0, x1 = STRIP_X, FRAME[2]
    msp.add_line((x0, FRAME[1]), (x0, FRAME[3]), dxfattribs={"layer": "A-ANNO-TTLB"})
    cx = (x0 + x1) / 2
    room = x1 - x0 - 6                                     # usable width of the strip
    t(msp, p.get("title", ""), cx, 272, fit_height(p.get("title", ""), 4.2, room), align="MIDDLE_CENTER")
    t(msp, p.get("alt_title", ""), cx, 264, fit_height(p.get("alt_title", ""), 4.0, room), align="MIDDLE_CENTER")
    t(msp, p.get("subtitle", ""), cx, 256, fit_height(p.get("subtitle", ""), 2.0, room), align="MIDDLE_CENTER")
    hline(msp, x0, x1, 249)
    box(msp, x0 + 3, 236, x1 - 3, 246)
    stage = (p.get("stage") or "CONCEPT DESIGN - NOT FOR CONSTRUCTION").upper()
    t(msp, stage, cx, 241, fit_height(stage, 1.6, room - 4), align="MIDDLE_CENTER")
    t(msp, "NOTES", x0 + 3, 228, 2.2)
    for i, note in enumerate(p.get("notes") or NOTES):
        t(msp, note, x0 + 3, 222 - i * 4.2, fit_height(note, 1.55, room))
    rows = [("Drawing", title), ("", alt_title), ("Scale", scale_text),
            ("Date", str(p.get("date") or dt.date.today().isoformat())),
            ("Revision", str(p.get("revision") or "A")), ("Sheet", number)]
    if p.get("author"):
        rows.insert(3, ("Designer", p["author"]))
    y = 92 + (9 if p.get("author") else 0)
    hline(msp, x0, x1, y + 6)
    for label, value in rows:
        if label:
            t(msp, label, x0 + 3, y, 1.8)
        if label == "" and value:
            t(msp, value, x1 - 3, y, fit_height(value, 2.6, room), align="MIDDLE_RIGHT")
        elif label == "Sheet":
            t(msp, value, x1 - 3, y - 6, 9.0, align="MIDDLE_RIGHT")
        elif value:
            t(msp, value, x1 - 3, y, fit_height(value, 3.0 if label == "Drawing" else 2.6, room - 16),
              align="MIDDLE_RIGHT")
        if label == "" and not value:
            continue
        y -= 9 if label != "Sheet" else 0
        hline(msp, x0, x1, y + 4.5)


def north_arrow(msp, x, y, rot=0.0, r=9.0):
    msp.add_circle((x, y), r, dxfattribs={"layer": "A-ANNO-SYMB"})
    a = math.radians(-rot)

    def rp(px, py):
        return (x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a))

    pts = [rp(0, r * 0.95), rp(-r * 0.35, -r * 0.6), rp(0, -r * 0.25), rp(r * 0.35, -r * 0.6)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-ANNO-SYMB"})
    h = msp.add_hatch(color=7, dxfattribs={"layer": "A-ANNO-SYMB"})
    h.paths.add_polyline_path(pts[:3], is_closed=True)
    tx, ty = rp(0, r + 4)
    t(msp, "N", tx, ty, 3.5, align="MIDDLE_CENTER", layer="A-ANNO-SYMB")


def scale_bar(msp, x, y, scale, metres=None):
    metres = metres or {50: 5, 100: 10, 200: 20}.get(scale, 10)
    step = 1 if metres <= 5 else (2 if metres <= 10 else 5)
    k = 1000.0 / scale
    n = metres // step
    for i in range(n):
        x0 = x + i * step * k
        pts = [(x0, y), (x0 + step * k, y), (x0 + step * k, y + 2), (x0, y + 2)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-ANNO-SYMB"})
        if i % 2 == 0:
            h = msp.add_hatch(color=7, dxfattribs={"layer": "A-ANNO-SYMB"})
            h.paths.add_polyline_path(pts, is_closed=True)
        t(msp, str(i * step), x0, y - 3, 1.8, align="MIDDLE_CENTER", layer="A-ANNO-SYMB")
    t(msp, f"{metres} m", x + metres * k, y - 3, 1.8, align="MIDDLE_CENTER", layer="A-ANNO-SYMB")


def view_title(msp, x, y, title, alt_title, scale_text):
    t(msp, title.upper(), x, y, 3.2)
    msp.add_line((x, y - 2.8), (x + 120, y - 2.8), dxfattribs={"layer": "A-ANNO-TEXT"})
    t(msp, alt_title, x + 120, y, 3.2, align="MIDDLE_RIGHT")
    t(msp, scale_text, x, y - 6, 2.0)


fit_scale = plans.fit_scale


# ------------------------------------------------------------------------------ sheets
def plan_sheet(msp, model, lv, number, cut):
    scale = plans.plan_scale(lv)
    title = f"{lv.name} plan"
    frame(msp, model, number, title, lv.alt_name, f"1:{scale} (A3)")
    pen = Pen(msp, origin=((BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2), scale=scale,
              world_origin=g.center(lv.bbox))
    plans.draw_plan(pen, model, lv, cut)
    view_title(msp, 40, 42, title, lv.alt_name, f"Scale 1:{scale}")
    scale_bar(msp, 40, 24, scale)
    north_arrow(msp, 320, 32, model.site.north_deg if model.site else 0.0)


def elevation_sheet(msp, model, number, faces):
    names = {"S": "South", "N": "North", "E": "East", "W": "West"}
    title = "Elevations: " + " and ".join(names[f].lower() for f in faces)
    bx0, by0, bx1, by1 = model.bbox
    low = min(0.0, min(lv.z for lv in model.levels))
    tall = elevations.top_height(model) - low + 0.8
    wide = max(bx1 - bx0, by1 - by0) + 2 * (model.roof.get("overhang", 0.5)) + 5.0
    scale = fit_scale(wide, tall, BOX[2] - BOX[0], 104.0)
    frame(msp, model, number, title, "", f"1:{scale} (A3)")
    for face, (cy, ty) in zip(faces, ((222.0, 160.0), (104.0, 42.0))):
        to_u, _axis = elevations.face_axis(model, face)
        ua, ub = sorted((to_u(bx0, by0), to_u(bx1, by1)))
        pen = Pen(msp, origin=((BOX[0] + BOX[2]) / 2, cy), scale=scale,
                  world_origin=((ua + ub) / 2 + 0.6, (elevations.top_height(model) + low) / 2))
        elevations.draw_elevation(pen, model, face)
        view_title(msp, 40, ty, f"{names[face]} elevation", "", f"Scale 1:{scale}")


def section_sheet(msp, model, number, cut):
    axis, _v = cut
    bx0, by0, bx1, by1 = model.bbox
    lo, hi = (by0, by1) if axis == "x" else (bx0, bx1)
    low = min(lv.z for lv in model.levels) - 0.5
    tall = elevations.top_height(model) - low + 1.0
    scale = fit_scale(hi - lo + 6.0, tall, BOX[2] - BOX[0], BOX[3] - BOX[1])
    frame(msp, model, number, "Section A-A", "", f"1:{scale} (A3)")
    pen = Pen(msp, origin=((BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2), scale=scale,
              world_origin=((lo + hi) / 2, (elevations.top_height(model) + low) / 2))
    elevations.draw_section(pen, model, cut)
    look = "looking west" if axis == "x" else "looking north"
    view_title(msp, 40, 42, "Section A-A", "", f"{look.capitalize()}. Scale 1:{scale}")
    scale_bar(msp, 40, 24, scale)


def site_sheet(msp, model, number):
    site = model.site
    xs = [p[0] for p in site.boundary]
    ys = [p[1] for p in site.boundary]
    w, h = max(xs) - min(xs) + 6, max(ys) - min(ys) + 6
    scale = fit_scale(w, h, BOX[2] - BOX[0], BOX[3] - BOX[1], options=(100, 200, 250, 500, 1000))
    frame(msp, model, number, "Site plan", "", f"1:{scale} (A3)")
    pen = Pen(msp, origin=((BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2), scale=scale,
              world_origin=((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    draw_site(pen, model)
    view_title(msp, 40, 42, "Site plan", "", f"Scale 1:{scale}")
    scale_bar(msp, 40, 24, scale, metres=10 if scale <= 200 else 50)
    north_arrow(msp, 320, 32, site.north_deg)


def draw_site(pen, model):
    site = model.site
    pts = site.boundary
    pen.poly(pts, "A-SITE", close=True, lineweight=50)
    for k, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1])):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        if 90 < ang <= 270 or -270 <= ang < -90:
            ang -= 180
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        n = math.hypot(nx, ny) or 1
        inside = (mid[0] + nx / n * 0.6, mid[1] + ny / n * 0.6)
        if not g.point_in_polygon(inside, pts):
            inside = (mid[0] - nx / n * 0.6, mid[1] - ny / n * 0.6)
        pen.text(f"{math.dist(a, b):.2f}", inside, h=1.8, rot=ang)
        if site.setbacks and site.setbacks[k] is not None:
            # a quarter of the way along the edge, clear of an entrance in the middle of the frontage
            q = (a[0] + (b[0] - a[0]) * 0.25, a[1] + (b[1] - a[1]) * 0.25)
            deeper = (q[0] + (inside[0] - mid[0]) * 2.6, q[1] + (inside[1] - mid[1]) * 2.6)
            pen.text(f"setback {site.setbacks[k]:.1f} m", deeper, h=1.6, rot=ang, layer="A-ANNO-TEXT")
    zone = buildable_zone(site)
    if zone:
        pen.poly(zone, "A-SITE", close=True, linetype="DASHED", ltscale=1.5)
    for r in site.paving:
        pen.rect(r, "A-SITE-PLNT")
    for r, _facing in site.parking:
        pen.rect(r, "A-SITE", linetype="DASHED", ltscale=2)
        pen.text("P", g.center(r), h=3.0)
    from .scene import auto_trees
    trees = auto_trees(model) if site.trees == "auto" else (site.trees if isinstance(site.trees, list) else [])
    for t_ in trees:
        size = float(t_[2]) if len(t_) > 2 else 1.0
        pen.circle((t_[0], t_[1]), 1.3 * size, "A-SITE-PLNT")
        pen.circle((t_[0], t_[1]), 0.12, "A-SITE-PLNT")
    ground = model.levels[0]
    for lv in model.levels:
        if lv.entrance:
            ground = lv
    for w, _side in ground.ext_walls:
        pen.fill_rect(w, "A-WALL-PATT", color=250)
    for r in model.top.footprint:
        pen.rect(r, "A-ELEV")
    plans.draw_roof_edge(pen, model)
    for r in ground.footprint:
        pen.rect(r, "A-WALL")
    bx0, by0, bx1, by1 = model.bbox
    # building dimensions on the sides away from the street, where the entrance arrow is not
    if site.street_side == "S":
        pen.dim((bx0, by1), (bx1, by1), 1.2)
    else:
        pen.dim((bx0, by0), (bx1, by0), -1.2)
    if site.street_side == "E":
        pen.dim((bx0, by0), (bx0, by1), -1.2, vertical=True)
    else:
        pen.dim((bx1, by0), (bx1, by1), 1.2, vertical=True)
    door = entrance_door(ground)
    if door:
        (cx, cy), side = door
        dx, dy = g.DIRS[side]
        start, end = (cx + dx * 3.2, cy + dy * 3.2), (cx + dx * 0.5, cy + dy * 0.5)
        pen.line(start, end, "A-ANNO-SYMB")
        pen.fill([(end[0] - dy * 0.35 + dx * 0.6, end[1] + dx * 0.35 + dy * 0.6), end,
                  (end[0] + dy * 0.35 + dx * 0.6, end[1] - dx * 0.35 + dy * 0.6)], "A-ANNO-SYMB")
        pen.text("ENTRANCE", (cx + dx * 2.2 - dy * 1.6, cy + dy * 2.2 + dx * 1.6), h=2.0, rot=90 if dx else 0)
    street = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}[site.street_side]
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    half_w = (max(p[0] for p in pts) - min(p[0] for p in pts)) / 2
    half_h = (max(p[1] for p in pts) - min(p[1] for p in pts)) / 2
    pen.text("STREET", (cx + street[0] * (half_w + 1.6), cy + street[1] * (half_h + 1.6)), h=3.0,
             rot=90 if street[0] else 0)
    for name, _alt, p in site.labels:
        pen.text(name, p, h=2.0)


def entrance_door(lv):
    """(centre, outward side) of the outside door nearest the entrance point."""
    if not lv.entrance:
        return None
    best = None
    for op in lv.openings:
        if op.kind not in ("door", "sliding"):
            continue
        for w, side in lv.ext_walls:
            if g.overlap(op.rect, w, 0.01):
                d = math.dist(g.center(op.rect), lv.entrance)
                if best is None or d < best[0]:
                    best = (d, (g.center(op.rect), side))
    return best[1] if best else None


def buildable_zone(site):
    """The site boundary moved inwards by each edge's setback (convex sites)."""
    pts = site.boundary
    if not site.setbacks or len(pts) < 3:
        return None
    ccw = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) > 0
    lines = []
    for k, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1])):
        d = site.setbacks[k] or 0.0
        ex, ey = b[0] - a[0], b[1] - a[1]
        n = math.hypot(ex, ey) or 1.0
        nx, ny = (-ey / n, ex / n) if ccw else (ey / n, -ex / n)
        lines.append(((a[0] + nx * d, a[1] + ny * d), (ex, ey)))
    out = []
    for k in range(len(lines)):
        (p, r), (q, s) = lines[k - 1], lines[k]
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-9:
            return None
        t_ = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
        out.append((p[0] + t_ * r[0], p[1] + t_ * r[1]))
    return out


def cover_sheet(msp, model, sheet_list, findings):
    p = model.project
    frame(msp, model, "A-000", "Cover and area schedule", "", "-")
    title = p.get("title", "").upper()
    t(msp, title, 40, 262, fit_height(title, 8.0, 290))
    t(msp, p.get("alt_title", ""), 330, 255, fit_height(p.get("alt_title", ""), 5.0, 140), align="MIDDLE_RIGHT")
    subtitle = p.get("subtitle", "") or "Concept design drawings"
    t(msp, subtitle, 40, 250, fit_height(subtitle, 3.8, 200))
    hline(msp, 40, 330, 243, layer="A-ANNO-TEXT")
    total = sum(lv.built_area for lv in model.levels)
    built = " + ".join(f"{lv.built_area:.2f}" for lv in model.levels) + f" = {total:.2f} m²" \
        if len(model.levels) > 1 else f"{total:.2f} m²"
    facts = [("Levels", ", ".join(f"{lv.name} {plans.level_text(lv.z)}" for lv in model.levels)),
             ("Built area", built),
             ("Roof", f"gable, {model.roof['pitch']:.0f}°" if model.roof["type"] == "gable" else "flat")]
    if model.site:
        site_area = g.polygon_area(model.site.boundary)
        footprint = g.union_area([r for lv in model.levels for r in lv.footprint])
        facts.append(("Site", f"{site_area:.1f} m²; building footprint {footprint:.1f} m² "
                              f"({footprint / site_area:.0%} coverage)"))
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    applied = ["reachability", "door swings", "furniture clashes"]      # only what this model gives rules for
    if any(lv.area_limit for lv in model.levels):
        applied.append("area limits")
    if any(room.habitable for lv in model.levels for room in lv.rooms):
        applied.append("daylight")
    if any(lv.stairs_up for lv in model.levels):
        applied.append("stairs")
    if model.site:
        applied.append("setbacks" if model.site.setbacks else "site boundary")
    facts.append(("Design rules", f"{errors} errors, {warnings} warnings; checked: {', '.join(applied)}"))
    for i, (k, v) in enumerate(facts):
        t(msp, k, 40, 235 - i * 6, 2.3)
        t(msp, v, 72, 235 - i * 6, 2.3)
    top = 235 - len(facts) * 6 - 6
    t(msp, "DRAWING LIST", 40, top, 3.0)
    hline(msp, 40, 178, top - 4, layer="A-ANNO-TEXT")
    for i, (num, title) in enumerate(sheet_list):
        y = top - 10 - i * 6.5
        t(msp, num, 40, y, 2.4)
        t(msp, title, 58, y, 2.4)
        hline(msp, 40, 178, y - 3.2, layer="A-ANNO-NPLT")
    t(msp, "AREA SCHEDULE (m²; rows add up to the built area)", 190, top, 3.0)
    hline(msp, 190, 330, top - 4, layer="A-ANNO-TEXT")
    rows = []
    for lv in model.levels:
        s = areas.schedule(lv)
        limit = f", limit {lv.area_limit:.2f}" if lv.area_limit else ""
        rows.append(("head", f"{lv.name}: built {s['built']:.2f}{limit}", ""))
        rows += [("row", room.name, f"{a:.2f}") for room, a in s["rooms"]]
        rows += [("row", label, f"{s[key]:.2f}") for key, label in
                 (("stairs", "Stairs"), ("circulation", "Circulation"), ("walls", "Walls")) if s[key] > 0]
    step = min(3.6, (top - 10 - 20) / max(1, len(rows)))
    y = top - 9
    for kind, name, value in rows:
        if kind == "head":
            y -= step * 0.4
            t(msp, name, 190, y, min(2.3, step * 0.7))
        else:
            t(msp, name, 194, y, min(1.9, step * 0.6))
            t(msp, value, 300, y, min(1.9, step * 0.6), align="MIDDLE_RIGHT")
        y -= step


# ------------------------------------------------------------------------------ output
def render_sheet(doc, stem, out):
    backend = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                               lineweight_policy=config.LineweightPolicy.ABSOLUTE)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace())
    page = layout.Page(W, H, layout.Units.mm, margins=layout.Margins.all(0))
    (out / "pdf" / f"{stem}.pdf").write_bytes(backend.get_pdf_bytes(page))
    (out / "png" / f"{stem}.png").write_bytes(backend.get_pixmap_bytes(page, fmt="png", dpi=PNG_DPI))
    doc.saveas(out / "dxf" / f"{stem}.dxf")


def audit_dxf(path):
    """Re-read a written DXF in recovery mode and audit it; a clean file returns []."""
    doc, auditor = recover.readfile(path)
    second = doc.audit()
    return [f"{Path(path).name}: {e.message}" for e in auditor.errors + auditor.fixes + second.errors + second.fixes]


def sheet_plan(model):
    """(number, title, draw function) for every sheet in the set."""
    cut = elevations.section_cut(model)
    sheets = []
    if model.site:
        sheets.append(("A-100", "Site plan", lambda m: site_sheet(m, model, "A-100")))
    for i, lv in enumerate(model.levels):
        number = f"A-{101 + i}"
        sheets.append((number, f"{lv.name} plan",
                       (lambda lv_, n_: (lambda m: plan_sheet(m, model, lv_, n_, cut)))(lv, number)))
    sheets.append(("A-201", "Elevations: south and north", lambda m: elevation_sheet(m, model, "A-201", ("S", "N"))))
    sheets.append(("A-202", "Elevations: east and west", lambda m: elevation_sheet(m, model, "A-202", ("E", "W"))))
    sheets.append(("A-301", "Section A-A", lambda m: section_sheet(m, model, "A-301", cut)))
    return sheets


def true_size_model(model, path):
    """Every plan in metres, side by side, for downstream CAD work."""
    doc = new_doc(units=6)
    doc.header["$LTSCALE"] = 0.05
    msp = doc.modelspace()
    dx = 0.0
    bx0, by0, bx1, by1 = model.bbox
    for lv in model.levels:
        # text sized as on the plan sheet, so labels and the level mark sit where they do on paper
        pen = Pen(msp, origin=(dx, 0.0), world_origin=(bx0, by0), true_size=True, scale=plans.plan_scale(lv))
        plans.draw_plan(pen, model, lv)
        pen.text(f"{lv.name.upper()} {plans.level_text(lv.z)}", ((bx0 + bx1) / 2, by0 - 3.0), h=5.0)
        dx += (bx1 - bx0) + 8.0
    doc.saveas(path)


def build(model, out_dir, findings, log=print):
    """Write the drawing set into <out_dir>/drawings. Returns (files, audit problems)."""
    out = Path(out_dir) / "drawings"
    for sub in ("pdf", "png", "dxf"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    plan = sheet_plan(model)
    sheet_list = [("A-000", "Cover and area schedule")] + [(n, title) for n, title, _ in plan]
    stems, problems = [], []
    for number, title, draw in [("A-000", "Cover and area schedule",
                                 lambda m: cover_sheet(m, model, sheet_list, findings))] + plan:
        doc = new_doc()
        draw(doc.modelspace())
        stem = f"{number}_{slug(title)}"
        render_sheet(doc, stem, out)
        problems += audit_dxf(out / "dxf" / f"{stem}.dxf")
        stems.append(stem)
        log(f"  sheet {stem}")
    book = fitz.open()
    for stem in stems:
        with fitz.open(out / "pdf" / f"{stem}.pdf") as part:
            book.insert_pdf(part)
    book.set_metadata({"title": f"{model.project.get('title', '')} - concept drawings",
                       "author": model.project.get("author", ""), "creator": "conceptdesign", "producer": ""})
    book.save(out / "concept-drawings.pdf")
    true_size_model(model, out / "model_1to1_metres.dxf")
    problems += audit_dxf(out / "model_1to1_metres.dxf")
    files = [out / "concept-drawings.pdf", out / "model_1to1_metres.dxf"] + \
        [out / sub / f"{stem}.{sub}" for stem in stems for sub in ("dxf", "pdf", "png")]
    log(f"drawing set: {len(stems)} sheets, DXF audit "
        + ("clean" if not problems else f"{len(problems)} problems"))
    return files, problems

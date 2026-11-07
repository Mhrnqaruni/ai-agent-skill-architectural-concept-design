"""Area schedule: every square centimetre of a floor belongs to exactly one row.

Rows are rooms, stairs, circulation (floor area outside any room) and walls. They are measured
exactly on the grid formed by every rectangle edge, so they always add up to the built area.
"""
from __future__ import annotations

from . import geometry as g


def schedule(level):
    """Rows for one level: {'rooms': [(room, area)], 'stairs', 'circulation', 'walls', 'built'}."""
    walls = level.all_walls
    stairs = [s.rect for s in level.stairs_up + level.stairs_down]
    rooms = [(room, room.regions) for room in level.rooms]
    rects = list(level.footprint) + walls + stairs + [r for room, regs in rooms for r in regs + [room.rect]]
    xs, ys = g.grid(rects)
    totals = {"stairs": 0.0, "circulation": 0.0, "walls": 0.0}
    room_area = {room.index: 0.0 for room, _ in rooms}

    def hit(rs, cx, cy):
        return any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in rs)

    for i in range(len(xs) - 1):
        cx, dx = (xs[i] + xs[i + 1]) / 2, xs[i + 1] - xs[i]
        for j in range(len(ys) - 1):
            cy, dy = (ys[j] + ys[j + 1]) / 2, ys[j + 1] - ys[j]
            if not hit(level.footprint, cx, cy):
                continue
            a = dx * dy
            if hit(walls, cx, cy):
                totals["walls"] += a
            elif hit(stairs, cx, cy):
                totals["stairs"] += a
            else:
                owner = next((room for room, regs in rooms if hit(regs, cx, cy)), None)
                if owner is None:
                    totals["circulation"] += a
                else:
                    room_area[owner.index] += a
    return {"rooms": [(room, round(room_area[room.index], 2)) for room, _ in rooms],
            "stairs": round(totals["stairs"], 2), "circulation": round(totals["circulation"], 2),
            "walls": round(totals["walls"], 2), "built": round(level.built_area, 2)}


def net_areas(level):
    """Room index -> area inside the walls, as printed on the plans and in the schedule."""
    return {room.index: a for room, a in schedule(level)["rooms"]}


def rows(model):
    """Flat table for reports: (level id, level name, row name, alt name, area)."""
    out = []
    for lv in model.levels:
        s = schedule(lv)
        for room, a in s["rooms"]:
            out.append((lv.id, lv.name, room.name, room.alt_name, a))
        for key, label in (("stairs", "Stairs"), ("circulation", "Circulation"), ("walls", "Walls")):
            if s[key] > 0:
                out.append((lv.id, lv.name, label, "", s[key]))
        out.append((lv.id, lv.name, "Built area", "", s["built"]))
    return out


def markdown(model):
    lines = ["| Level | Space | Area (m²) |", "|---|---|---:|"]
    for lv in model.levels:
        s = schedule(lv)
        for room, a in s["rooms"]:
            lines.append(f"| {lv.name} | {room.name} | {a:.2f} |")
        for key, label in (("stairs", "Stairs"), ("circulation", "Circulation"), ("walls", "Walls")):
            if s[key] > 0:
                lines.append(f"| {lv.name} | {label} | {s[key]:.2f} |")
        limit = f" (limit {lv.area_limit:.2f})" if lv.area_limit else ""
        lines.append(f"| **{lv.name}** | **Built area{limit}** | **{s['built']:.2f}** |")
    total = sum(lv.built_area for lv in model.levels)
    lines.append(f"| **All levels** | **Total built area** | **{total:.2f}** |")
    return "\n".join(lines) + "\n"


def csv(model):
    lines = ["level,space,alt_name,area_m2"]
    for lid, _name, space, alt, a in rows(model):
        lines.append(f'{lid},"{space}","{alt}",{a:.2f}')
    return "\n".join(lines) + "\n"

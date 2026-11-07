"""Load, validate and normalise a design model (design.json).

The JSON file is the single source of truth. This module turns it into plain Python objects and
reports every problem with its JSON path, so an agent or a person can fix the file directly.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import geometry as g

SCHEMA_VERSION = 1
OPENING_TYPES = ("door", "sliding", "opening", "window")
ROOM_USES = ("living", "dining", "kitchen", "bedroom", "study", "bath", "wc", "hall", "corridor",
             "storage", "utility", "laundry", "closet", "garage", "plant", "terrace", "other")
HABITABLE = {"living", "dining", "kitchen", "bedroom", "study"}
FINISHES = ("wood", "tile", "stone", "concrete", "deck")
DEFAULT_FINISH = {"bath": "tile", "wc": "tile", "laundry": "tile", "utility": "tile", "plant": "concrete",
                  "garage": "concrete", "storage": "concrete", "hall": "stone", "terrace": "deck"}
FACADES = ("render", "brick", "stone", "timber")
ROOF_TYPES = ("gable", "flat")

# furniture type: (shape, has a back side, 3D builder)
FURNITURE = {
    "bed": ("rect", True, "bed"), "nightstand": ("rect", True, "nightstand"),
    "wardrobe": ("rect", True, "wardrobe"), "hanging_rail": ("rect", True, "hanging"),
    "shoe_cabinet": ("rect", True, "shoe"), "desk": ("rect", True, "desk"),
    "shelves": ("rect", True, "shelves"), "sofa": ("rect", True, "sofa"),
    "armchair": ("rect", True, "armchair"), "coffee_table": ("rect", False, "coffee"),
    "dining_table": ("rect", False, "dining"), "tv": ("rect", True, "tv"), "rug": ("rect", False, "rug"),
    "kitchen": ("rect", True, "kitchen"), "island": ("rect", False, "island"),
    "fridge": ("rect", True, "fridge"), "laundry": ("rect", True, "laundry"), "bar": ("rect", True, "bar"),
    "basin": ("rect", True, "basin"), "shower": ("rect", False, "shower"),
    "bathtub": ("rect", False, "bathtub"), "sauna": ("rect", False, "sauna"),
    "billiards": ("rect", False, "billiards"), "boiler": ("rect", True, "boiler"),
    "stools": ("rect", False, "stools"), "wc": ("point", True, "wc"), "chair": ("point", True, "chair"),
    "barstool": ("point", False, "barstool"), "plant": ("point", False, "plant"),
    "tank": ("point", False, "tank"),
}
DEFAULT_RULES = {
    "daylight_ratio": 0.125,          # glazed area / floor area in habitable rooms
    "min_door_width": 0.7,
    "min_bedroom_area": 7.0,
    "max_riser": 0.19,
    "min_going": 0.25,
    "stair_comfort": [0.60, 0.65],    # 2 x rise + going, in metres
    "min_stair_width": 0.85,
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,16}$")


class ModelError(Exception):
    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class Opening:
    kind: str
    rect: tuple
    at_end: bool = False          # doors: the hinge is at the x1 / y1 end of the opening
    swing: int = 1                # doors: +1 opens towards +y (east-west wall) or +x (north-south wall)
    sill: float = 0.0
    head: float = 2.1
    index: int = 0

    @property
    def width(self):
        return g.length(self.rect)

    @property
    def passable(self):
        return self.kind in ("door", "sliding", "opening")


@dataclass
class Room:
    name: str
    rect: tuple
    alt_name: str = ""
    cutouts: list = field(default_factory=list)
    label_at: tuple = (0.0, 0.0)
    use: str = "other"
    finish: str = "wood"
    access: str = "inside"
    index: int = 0

    @property
    def regions(self):
        return g.rect_minus(self.rect, self.cutouts)

    @property
    def habitable(self):
        return self.use in HABITABLE


@dataclass
class Stair:
    rect: tuple
    kind: str
    up: str
    turn: str
    level: str
    to: str
    rise_total: float
    index: int = 0

    @property
    def along_y(self):
        return self.up in ("N", "S")

    @property
    def run_length(self):
        return (self.rect[3] - self.rect[1]) if self.along_y else (self.rect[2] - self.rect[0])

    @property
    def width(self):
        across = (self.rect[2] - self.rect[0]) if self.along_y else (self.rect[3] - self.rect[1])
        return (across - 0.1) / 2 if self.kind == "u" else across

    @property
    def risers(self):
        n = max(2, round(self.rise_total / 0.175))
        return n + (n % 2) if self.kind == "u" else n

    @property
    def rise(self):
        return self.rise_total / self.risers

    @property
    def landing(self):
        return max(self.width, 0.9) if self.kind == "u" else 0.0

    @property
    def going(self):
        if self.kind == "u":
            return (self.run_length - self.landing) / (self.risers // 2 - 1)
        return self.run_length / (self.risers - 1)


@dataclass
class Item:
    type: str
    rect: tuple = None
    at: tuple = None
    back: str = None
    extra: dict = field(default_factory=dict)
    index: int = 0

    @property
    def builder(self):
        return FURNITURE[self.type][2]


@dataclass
class Level:
    id: str
    name: str
    z: float
    height: float
    footprint: list
    alt_name: str = ""
    ext_walls: list = field(default_factory=list)        # [(rect, side)]
    walls: list = field(default_factory=list)
    openings: list = field(default_factory=list)
    rooms: list = field(default_factory=list)
    stairs_up: list = field(default_factory=list)
    stairs_down: list = field(default_factory=list)
    furniture: list = field(default_factory=list)
    entrance: tuple = None
    area_limit: float = None
    finish: str = "wood"
    dims: dict = field(default_factory=dict)
    index: int = 0

    @property
    def bbox(self):
        return g.bbox(self.footprint)

    @property
    def all_walls(self):
        return [w for w, _ in self.ext_walls] + self.walls

    @property
    def voids(self):
        """Openings in this floor's slab: the stairs that arrive from the level below."""
        return [s.rect for s in self.stairs_down]

    @property
    def built_area(self):
        return g.union_area(self.footprint)

    def start(self):
        """Where people arrive on this level: the entrance, else the stairs."""
        if self.entrance:
            return self.entrance, "the entrance"
        stair = (self.stairs_down + self.stairs_up or [None])[0]
        if stair:
            return g.center(stair.rect), "the stairs"
        return None, None


@dataclass
class Site:
    boundary: list
    north_deg: float = 0.0
    street_side: str = "S"
    setbacks: list = None
    boundary_wall: float = 1.2
    gates: list = field(default_factory=list)
    paving: list = field(default_factory=list)
    parking: list = field(default_factory=list)
    trees: object = "auto"
    labels: list = field(default_factory=list)
    patio_set: tuple = None


@dataclass
class Model:
    project: dict
    levels: list
    site: Site = None
    exterior_wall: float = 0.3
    partition: float = 0.1
    facade: str = "render"
    roof: dict = field(default_factory=lambda: {"type": "flat", "parapet": 0.5})
    section: tuple = None            # ('x', value): a north-south cut line; ('y', value): east-west
    rules: dict = field(default_factory=lambda: dict(DEFAULT_RULES))
    warnings: list = field(default_factory=list)
    path: Path = None

    @property
    def bbox(self):
        return g.bbox([r for lv in self.levels for r in lv.footprint])

    @property
    def top(self):
        return self.levels[-1]

    @property
    def wall_top(self):
        return self.top.z + self.top.height

    def level(self, level_id):
        return next(lv for lv in self.levels if lv.id == level_id)


# ----------------------------------------------------------------------------------- validation
class _Checker:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, path, msg):
        self.errors.append(f"{path}: {msg}")

    def warn(self, path, msg):
        self.warnings.append(f"{path}: {msg}")

    def number(self, v, path, lo=None, hi=None, required=True, default=None):
        if v is None:
            if required:
                self.error(path, "is required (a number in metres)")
            return default
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            self.error(path, f"must be a number, got {v!r}")
            return default
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            self.error(path, f"must be between {lo} and {hi}, got {v}")
        return float(v)

    def point(self, v, path, required=True):
        if v is None and not required:
            return None
        if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(a, (int, float)) for a in v)):
            self.error(path, f"must be [x, y], got {v!r}")
            return None
        return (float(v[0]), float(v[1]))

    def rect(self, v, path):
        if not (isinstance(v, (list, tuple)) and len(v) == 4
                and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in v)):
            self.error(path, f"must be [x0, y0, x1, y1], got {v!r}")
            return None
        r = tuple(float(a) for a in v)
        if r[2] <= r[0] or r[3] <= r[1]:
            self.error(path, f"needs x0 < x1 and y0 < y1, got {list(v)}")
            return None
        return r

    def choice(self, v, path, options, default=None, required=False):
        if v is None:
            if required:
                self.error(path, f"is required, one of {', '.join(options)}")
            return default
        if v not in options:
            self.error(path, f"must be one of {', '.join(options)}, got {v!r}")
            return default
        return v

    def text(self, v, path, required=True, default=""):
        if v is None or v == "":
            if required:
                self.error(path, "is required")
            return default
        if not isinstance(v, str):
            self.error(path, f"must be text, got {v!r}")
            return default
        return v


def _infer_back(rect, walls, tol=0.08):
    """The side of rect that stands against a wall face (its long side first)."""
    sides = set()
    for w in walls:
        if min(rect[2], w[2]) - max(rect[0], w[0]) > 0.05:
            if abs(rect[1] - w[3]) <= tol:
                sides.add("S")
            if abs(rect[3] - w[1]) <= tol:
                sides.add("N")
        if min(rect[3], w[3]) - max(rect[1], w[1]) > 0.05:
            if abs(rect[0] - w[2]) <= tol:
                sides.add("W")
            if abs(rect[2] - w[0]) <= tol:
                sides.add("E")
    long_sides = ("S", "N") if g.is_horizontal(rect) else ("W", "E")
    for side in long_sides:
        if side in sides:
            return side
    return next(iter(sorted(sides)), None)


def _point_back(p, walls, tol=0.06):
    """For a point on a wall face (a WC cistern), the side the wall is on."""
    for w in walls:
        if w[0] - tol <= p[0] <= w[2] + tol:
            if abs(p[1] - w[3]) <= tol:
                return "S"
            if abs(p[1] - w[1]) <= tol:
                return "N"
        if w[1] - tol <= p[1] <= w[3] + tol:
            if abs(p[0] - w[2]) <= tol:
                return "W"
            if abs(p[0] - w[0]) <= tol:
                return "E"
    return None


def _opening(c, d, path, index):
    if not isinstance(d, dict):
        c.error(path, "must be an object")
        return None
    kind = c.choice(d.get("type"), f"{path}.type", OPENING_TYPES, required=True)
    rect = c.rect(d.get("at"), f"{path}.at")
    if not kind or not rect:
        return None
    op = Opening(kind, rect, index=index)
    horizontal = g.is_horizontal(rect)
    if kind == "door":
        hinges, opens = (("W", "E"), ("N", "S")) if horizontal else (("S", "N"), ("E", "W"))
        hinge = c.choice(d.get("hinge"), f"{path}.hinge", hinges, required=True)
        side = c.choice(d.get("opens"), f"{path}.opens", opens, required=True)
        op.at_end = hinge in ("E", "N")
        op.swing = 1 if side in ("N", "E") else -1
        op.head = c.number(d.get("head"), f"{path}.head", 1.9, 3.5, required=False, default=2.1)
    elif kind == "sliding":
        op.head = c.number(d.get("head"), f"{path}.head", 1.9, 3.5, required=False, default=2.2)
    elif kind == "opening":
        op.head = c.number(d.get("head"), f"{path}.head", 1.9, 4.0, required=False, default=2.1)
    else:
        op.sill = c.number(d.get("sill"), f"{path}.sill", 0.0, 3.0, required=False, default=0.9)
        op.head = c.number(d.get("head"), f"{path}.head", 0.3, 4.0, required=False, default=2.2)
        if op.head is not None and op.sill is not None and op.head <= op.sill:
            c.error(path, "window head must be above its sill")
    return op


def _room(c, d, path, index):
    if not isinstance(d, dict):
        c.error(path, "must be an object")
        return None
    name = c.text(d.get("name"), f"{path}.name")
    rect = c.rect(d.get("rect"), f"{path}.rect")
    if not rect:
        return None
    cutouts = [r for k, v in enumerate(d.get("cutouts") or [])
               if (r := c.rect(v, f"{path}.cutouts[{k}]"))]
    use = c.choice(d.get("use"), f"{path}.use", ROOM_USES, default="other")
    room = Room(name, rect, alt_name=c.text(d.get("alt_name"), f"{path}.alt_name", required=False),
                cutouts=cutouts, use=use, index=index,
                finish=c.choice(d.get("finish"), f"{path}.finish", FINISHES,
                                default=DEFAULT_FINISH.get(use, "wood")),
                access=c.choice(d.get("access"), f"{path}.access", ("inside", "outside"), default="inside"))
    label = c.point(d.get("label_at"), f"{path}.label_at", required=False)
    room.label_at = label or g.center(max(room.regions, key=g.area) if room.regions else rect)
    if not any(g.contains(r, room.label_at) for r in room.regions):
        c.error(f"{path}.label_at", "must lie inside the room (and outside its cutouts)")
    return room


def _item(c, d, path, index, walls):
    if not isinstance(d, dict):
        c.error(path, "must be an object")
        return None
    kind = c.choice(d.get("type"), f"{path}.type", tuple(FURNITURE), required=True)
    if not kind:
        return None
    shape, oriented, _ = FURNITURE[kind]
    item = Item(kind, index=index)
    if shape == "rect":
        item.rect = c.rect(d.get("rect"), f"{path}.rect")
        if not item.rect:
            return None
    else:
        item.at = c.point(d.get("at"), f"{path}.at")
        if not item.at:
            return None
    if oriented:
        item.back = c.choice(d.get("back"), f"{path}.back", g.SIDES)
        if not item.back:
            item.back = _infer_back(item.rect, walls) if item.rect else _point_back(item.at, walls)
        if not item.back:
            if kind in ("wc",):
                c.error(f"{path}.back", "is required: the WC must stand against a wall face")
            else:
                item.back = "N" if not item.rect or g.is_horizontal(item.rect) else "W"
    for key in ("color", "size", "height", "count", "sides", "seats", "sink_at"):
        if key in d:
            item.extra[key] = d[key]
    if kind == "stools":
        item.extra.setdefault("count", max(1, round((item.rect[2] - item.rect[0]) / 0.55)))
        item.extra.setdefault("sides", "S")
        if item.extra["sides"] not in ("N", "S", "NS"):
            c.error(f"{path}.sides", "must be N, S or NS")
    return item


def _site(c, d):
    if not isinstance(d, dict):
        c.error("site", "must be an object")
        return None
    pts = d.get("boundary")
    boundary = [p for k, v in enumerate(pts or []) if (p := c.point(v, f"site.boundary[{k}]"))]
    if len(boundary) < 3:
        c.error("site.boundary", "needs at least three [x, y] points")
        return None
    site = Site(boundary,
                north_deg=c.number(d.get("north_deg"), "site.north_deg", -360, 360, required=False, default=0.0),
                street_side=c.choice(d.get("street_side"), "site.street_side", g.SIDES, default="S"),
                boundary_wall=c.number(d.get("boundary_wall"), "site.boundary_wall", 0, 3, required=False,
                                       default=1.2))
    setbacks = d.get("setbacks")
    if setbacks is not None:
        if not (isinstance(setbacks, list) and len(setbacks) == len(boundary)):
            c.error("site.setbacks", "must list one distance per boundary edge (use null for none)")
        else:
            site.setbacks = [None if v is None else c.number(v, f"site.setbacks[{k}]", 0, 100)
                             for k, v in enumerate(setbacks)]
    for k, gate in enumerate(d.get("gates") or []):
        if not (isinstance(gate, list) and len(gate) == 3):
            c.error(f"site.gates[{k}]", "must be [edge_index, from_m, to_m]")
            continue
        site.gates.append((int(gate[0]), float(gate[1]), float(gate[2])))
    site.paving = [r for k, v in enumerate(d.get("paving") or []) if (r := c.rect(v, f"site.paving[{k}]"))]
    for k, car in enumerate(d.get("parking") or []):
        r = c.rect((car or {}).get("rect"), f"site.parking[{k}].rect")
        facing = c.choice((car or {}).get("facing"), f"site.parking[{k}].facing", g.SIDES, default="N")
        if r:
            site.parking.append((r, facing))
    trees = d.get("trees", "auto")
    if trees not in ("auto", "none") and not isinstance(trees, list):
        c.error("site.trees", 'must be "auto", "none" or a list of [x, y, size]')
    site.trees = trees
    for k, lab in enumerate(d.get("labels") or []):
        p = c.point((lab or {}).get("at"), f"site.labels[{k}].at")
        if p:
            site.labels.append((c.text(lab.get("name"), f"site.labels[{k}].name"),
                                lab.get("alt_name") or "", p))
    site.patio_set = c.point(d.get("patio_set"), "site.patio_set", required=False)
    return site


def parse(data, path=None):
    """Validate a design model (a dict loaded from JSON). Raises ModelError listing every problem."""
    c = _Checker()
    if not isinstance(data, dict):
        raise ModelError(["the design model must be a JSON object"])
    version = data.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        c.error("schema_version", f"this engine reads version {SCHEMA_VERSION}, got {version!r}")
    project = data.get("project") or {}
    c.text(project.get("title"), "project.title")
    building = data.get("building") or {}
    model = Model(project=project, levels=[], path=Path(path) if path else None)
    model.exterior_wall = c.number(building.get("exterior_wall"), "building.exterior_wall", 0.1, 0.8,
                                   required=False, default=0.3)
    model.partition = c.number(building.get("partition"), "building.partition", 0.05, 0.4,
                               required=False, default=0.1)
    model.facade = c.choice(building.get("facade"), "building.facade", FACADES, default="render")
    roof = dict(building.get("roof") or {"type": "flat"})
    roof["type"] = c.choice(roof.get("type"), "building.roof.type", ROOF_TYPES, default="flat")
    if roof["type"] == "gable":
        roof["ridge"] = c.choice(roof.get("ridge"), "building.roof.ridge", ("x", "y"), default=None)
        roof["pitch"] = c.number(roof.get("pitch"), "building.roof.pitch", 5, 60, required=False, default=30.0)
        roof["overhang"] = c.number(roof.get("overhang"), "building.roof.overhang", 0, 1.5, required=False,
                                    default=0.5)
    else:
        roof["parapet"] = c.number(roof.get("parapet"), "building.roof.parapet", 0, 1.5, required=False,
                                   default=0.5)
    model.roof = roof
    section = building.get("section")
    if section is not None:
        if not isinstance(section, dict):
            c.error("building.section", 'must be {"line": "north-south" or "east-west", "at": number}')
        else:
            line = c.choice(section.get("line"), "building.section.line", ("north-south", "east-west"), required=True)
            at = c.number(section.get("at"), "building.section.at", -1e4, 1e4)
            if line and at is not None:
                model.section = ("x" if line == "north-south" else "y", at)
    rules = dict(DEFAULT_RULES)
    for key, value in (data.get("rules") or {}).items():
        if key not in DEFAULT_RULES:
            c.warn(f"rules.{key}", "is not a known rule setting and is ignored")
            continue
        rules[key] = value
    model.rules = rules

    raw_levels = data.get("levels")
    if not isinstance(raw_levels, list) or not raw_levels:
        c.error("levels", "needs at least one level")
        raise ModelError(c.errors)
    seen = set()
    for i, d in enumerate(raw_levels):
        p = f"levels[{i}]"
        if not isinstance(d, dict):
            c.error(p, "must be an object")
            continue
        lid = c.text(d.get("id"), f"{p}.id")
        if lid and not ID_PATTERN.match(lid):
            c.error(f"{p}.id", "use 1-16 letters, digits or _")
        if lid in seen:
            c.error(f"{p}.id", f"{lid!r} is used twice")
        seen.add(lid)
        footprint = [r for k, v in enumerate(d.get("footprint") or []) if (r := c.rect(v, f"{p}.footprint[{k}]"))]
        if not footprint:
            c.error(f"{p}.footprint", "needs at least one [x0, y0, x1, y1] rectangle (outside faces)")
            continue
        lv = Level(id=lid, name=c.text(d.get("name"), f"{p}.name", required=False, default=lid),
                   alt_name=c.text(d.get("alt_name"), f"{p}.alt_name", required=False),
                   z=c.number(d.get("elevation"), f"{p}.elevation", -20, 200),
                   height=c.number(d.get("height"), f"{p}.height", 2.2, 8.0, required=False, default=3.0),
                   footprint=footprint, index=i,
                   finish=c.choice(d.get("finish"), f"{p}.finish", FINISHES, default="wood"))
        lv.area_limit = c.number(d.get("area_limit"), f"{p}.area_limit", 1, 1e6, required=False)
        lv.entrance = c.point(d.get("entrance"), f"{p}.entrance", required=False)
        lv.ext_walls = g.exterior_walls(footprint, model.exterior_wall or 0.3)
        lv.walls = [r for k, v in enumerate(d.get("walls") or []) if (r := c.rect(v, f"{p}.walls[{k}]"))]
        for k, w in enumerate(lv.walls):
            if not g.contains_rect(lv.bbox, w):
                c.error(f"{p}.walls[{k}]", "lies outside the level's footprint")
        lv.openings = [o for k, v in enumerate(d.get("openings") or [])
                       if (o := _opening(c, v, f"{p}.openings[{k}]", k))]
        for o in lv.openings:
            if not any(g.overlap(o.rect, w, 0.01) for w in lv.all_walls):
                c.error(f"{p}.openings[{o.index}]", "does not cut any wall: span the wall's full thickness")
        lv.rooms = [r for k, v in enumerate(d.get("rooms") or []) if (r := _room(c, v, f"{p}.rooms[{k}]", k))]
        for room in lv.rooms:
            if not all(g.in_union(footprint, pt) for pt in ((room.rect[0], room.rect[1]), (room.rect[2], room.rect[3]),
                                                            (room.rect[0], room.rect[3]), (room.rect[2], room.rect[1]))):
                c.error(f"{p}.rooms[{room.index}]", f"{room.name!r} extends outside the footprint")
        lv.furniture = [it for k, v in enumerate(d.get("furniture") or [])
                        if (it := _item(c, v, f"{p}.furniture[{k}]", k, lv.all_walls))]
        dims = d.get("dimensions") or {}
        lv.dims = {axis: sorted(float(v) for v in dims.get(axis, [])) for axis in ("x", "y") if dims.get(axis)}
        lv._raw_stairs = d.get("stairs") or []
        model.levels.append(lv)
    if c.errors:
        raise ModelError(c.errors)

    for a, b in zip(model.levels, model.levels[1:]):
        if b.z <= a.z:
            c.error(f"levels[{b.index}].elevation", "levels must be listed from the lowest up")
        elif b.z - a.z < a.height - 1e-6:
            c.error(f"levels[{a.index}].height", f"is taller than the gap to {b.id!r} ({b.z - a.z:.2f} m)")
    for i, lv in enumerate(model.levels):
        for k, d in enumerate(lv._raw_stairs):
            p = f"levels[{lv.index}].stairs[{k}]"
            if not isinstance(d, dict):
                c.error(p, "must be an object")
                continue
            rect = c.rect(d.get("rect"), f"{p}.rect")
            kind = c.choice(d.get("type"), f"{p}.type", ("straight", "u"), default="straight")
            up = c.choice(d.get("up"), f"{p}.up", g.SIDES, required=True)
            turn = c.choice(d.get("turn"), f"{p}.turn", ("left", "right"), default="right")
            if not rect or not up:
                continue
            if i + 1 >= len(model.levels):
                c.error(p, "the top level cannot have a stair going up")
                continue
            above = model.levels[i + 1]
            stair = Stair(rect, kind, up, turn, lv.id, above.id, above.z - lv.z, index=k)
            if not all(g.in_union(above.footprint, pt) for pt in ((rect[0], rect[1]), (rect[2], rect[3]))):
                c.error(p, f"must lie inside the footprint of {above.id!r} as well")
            if stair.run_length <= (stair.landing + 0.5):
                c.error(f"{p}.rect", "is too short for a stair in the 'up' direction")
            lv.stairs_up.append(stair)
            above.stairs_down.append(stair)
        del lv._raw_stairs
    if not any(lv.entrance for lv in model.levels):
        c.error("levels", "one level needs an 'entrance': a point just inside the main entrance door")
    for lv in model.levels:
        if lv.entrance and not g.in_union(lv.footprint, lv.entrance):
            c.error(f"levels[{lv.index}].entrance", "must lie inside the footprint")
    if model.section:
        axis, at = model.section
        b = model.bbox
        lo, hi = (b[0], b[2]) if axis == "x" else (b[1], b[3])
        if not lo < at < hi:
            c.error("building.section.at", f"must cross the building ({lo:.2f} to {hi:.2f})")
    if roof["type"] == "gable" and not roof.get("ridge"):
        b = model.bbox
        roof["ridge"] = "x" if (b[2] - b[0]) >= (b[3] - b[1]) else "y"
    if roof["type"] == "gable" and len(model.top.footprint) > 1:
        c.warn("building.roof", "a gable roof covers the bounding box of a non-rectangular top floor")
    if "site" in data and data["site"] is not None:
        model.site = _site(c, data["site"])
    if c.errors:
        raise ModelError(c.errors)
    model.warnings = c.warnings
    return model


def load(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ModelError([f"{path.name}: not valid JSON ({e.msg} at line {e.lineno}, column {e.colno})"]) from e
    return parse(data, path)

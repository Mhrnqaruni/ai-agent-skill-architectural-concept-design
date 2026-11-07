"""DXF helpers: AIA / US National CAD Standard layers, text, and a Pen that maps metres onto paper."""
from __future__ import annotations

import math
import re
from functools import lru_cache

import ezdxf
from ezdxf.enums import TextEntityAlignment

try:                                     # optional: joined glyphs for right-to-left labels
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:                      # pragma: no cover - depends on the environment
    arabic_reshaper = None

# (name, ACI colour, lineweight in 1/100 mm)
LAYERS = [
    ("A-WALL", 7, 50), ("A-WALL-PATT", 8, 0), ("A-DOOR", 7, 25), ("A-GLAZ", 5, 18),
    ("A-FLOR-STRS", 7, 18), ("A-FLOR-LEVL", 7, 13), ("A-FURN", 8, 13), ("A-AREA-IDEN", 7, 18),
    ("A-ANNO-DIMS", 7, 13), ("A-ANNO-TEXT", 7, 18), ("A-ANNO-SYMB", 7, 25), ("A-ANNO-TTLB", 7, 35),
    ("A-ANNO-NPLT", 9, 13), ("A-SITE", 7, 25), ("A-SITE-PLNT", 8, 13), ("A-ELEV", 7, 35),
    ("A-ELEV-HIDD", 8, 13), ("A-SECT", 7, 50), ("A-SECT-PATT", 8, 0), ("A-ROOF", 7, 25),
]
RTL = re.compile(r"[֐-ࣿיִ-﷿ﹰ-﻿]")


def new_doc(units=4):
    """A DXF R2018 document with the standard layers (units 4 = millimetres on paper, 6 = metres)."""
    doc = ezdxf.new("R2018", setup=True, units=units)
    for name, color, lw in LAYERS:
        doc.layers.add(name, color=color, lineweight=lw)
    doc.styles.add("EN", font="arial.ttf")
    doc.styles.add("ALT", font="tahoma.ttf")
    setup_dimstyle(doc)
    return doc


def is_rtl(text):
    return bool(text and RTL.search(text))


@lru_cache(maxsize=4096)
def text_width(text, height):
    """Width in drawing units of text with a cap height, measured with the font the sheets use."""
    try:
        from ezdxf.fonts import fonts
        return fonts.make_font("tahoma.ttf" if is_rtl(text) else "arial.ttf", cap_height=height).text_width(text)
    except Exception:                    # pragma: no cover - font tools unavailable
        return len(text) * 0.77 * height


def fit_height(text, height, width):
    """The largest cap height, up to `height`, at which text fits in `width`."""
    w = text_width(text, height) if text else 0.0
    return height if w <= width else height * width / w


def shape(text):
    """Right-to-left scripts are pre-shaped, because CAD text engines don't join those letters."""
    if is_rtl(text) and arabic_reshaper is not None:
        return get_display(arabic_reshaper.reshape(text))
    return text


def put_text(msp, s, at, h, layer="A-ANNO-TEXT", align="MIDDLE_LEFT", rot=0.0):
    rtl = is_rtl(s)
    t = msp.add_text(shape(s), height=h, rotation=rot,
                     dxfattribs={"layer": layer, "style": "ALT" if rtl else "EN"})
    t.set_placement(at, align=TextEntityAlignment[align])
    return t


def setup_dimstyle(doc):
    ds = doc.dimstyles.new("PLAN")
    ds.dxf.dimtxt = 2.0
    ds.dxf.dimasz = 1.4
    ds.dxf.dimblk = "ARCHTICK"
    ds.dxf.dimexe = 1.0
    ds.dxf.dimexo = 1.0
    ds.dxf.dimdec = 2
    ds.dxf.dimtad = 1
    ds.dxf.dimgap = 0.6
    ds.dxf.dimtxsty = "EN"
    ds.dxf.dimzin = 0
    ds.dxf.dimdsep = ord(".")


class Pen:
    """Draws plan geometry (metres) at a scale onto paper (millimetres), or 1:1 in metres."""

    def __init__(self, msp, origin=(0.0, 0.0), scale=100, world_origin=(0.0, 0.0), true_size=False):
        self.msp, self.ox, self.oy = msp, origin[0], origin[1]
        self.scale = scale
        self.k = 1.0 if true_size else 1000.0 / scale      # drawing units per metre
        self.ts = scale / 1000.0 if true_size else 1.0      # paper millimetres -> drawing units
        self.wx, self.wy = world_origin

    def p(self, x, y):
        return (self.ox + (x - self.wx) * self.k, self.oy + (y - self.wy) * self.k)

    def line(self, a, b, layer, **attrs):
        self.msp.add_line(self.p(*a), self.p(*b), dxfattribs={"layer": layer, **attrs})

    def poly(self, pts, layer, close=False, **attrs):
        return self.msp.add_lwpolyline([self.p(*q) for q in pts], close=close, dxfattribs={"layer": layer, **attrs})

    def rect(self, r, layer, **attrs):
        x0, y0, x1, y1 = r
        return self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, close=True, **attrs)

    def fill(self, pts, layer, color=None):
        h = self.msp.add_hatch(color=color or 7, dxfattribs={"layer": layer})
        h.paths.add_polyline_path([self.p(*q) for q in pts], is_closed=True)
        return h

    def fill_rect(self, r, layer, color=None):
        x0, y0, x1, y1 = r
        return self.fill([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, color)

    def arc(self, c, r, a0, a1, layer):
        self.msp.add_arc(self.p(*c), r * self.k, a0, a1, dxfattribs={"layer": layer})

    def circle(self, c, r, layer):
        self.msp.add_circle(self.p(*c), r * self.k, dxfattribs={"layer": layer})

    def text(self, s, at, h=2.5, layer="A-ANNO-TEXT", align="MIDDLE_CENTER", rot=0.0):
        """h is the height on paper in millimetres, so labels read the same at every scale."""
        if not s:
            return None
        return put_text(self.msp, s, self.p(*at), h * self.ts, layer=layer, align=align, rot=rot)

    def dim(self, a, b, offset, vertical=False, layer="A-ANNO-DIMS"):
        """A linear dimension between plan points a and b, offset in metres."""
        if vertical:
            base, angle = (a[0] + offset, (a[1] + b[1]) / 2), 90
        else:
            base, angle = ((a[0] + b[0]) / 2, a[1] + offset), 0
        d = self.msp.add_linear_dim(base=self.p(*base), p1=self.p(*a), p2=self.p(*b), angle=angle,
                                    dimstyle="PLAN", override={"dimlfac": 1.0 / self.k, "dimscale": self.ts},
                                    dxfattribs={"layer": layer})
        d.render()


def arc_between(a_from, a_to):
    """Order two angles so the counter-clockwise arc between them is the 90 degree sweep."""
    if (a_to - a_from) % 360 == 90:
        return a_from, a_to
    return a_to, a_from


def ellipse(c, ax, ay, n=28):
    return [(c[0] + ax * math.cos(2 * math.pi * i / n), c[1] + ay * math.sin(2 * math.pi * i / n)) for i in range(n)]

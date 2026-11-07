"""Compose the README figures from the example project's build.

    python skills/architectural-concept-design/scripts/concept.py build examples/family-house/design.json --renders
    python tools/make_figures.py
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "family-house" / "output"
FIG = ROOT / "docs" / "figures"
RENDERS = OUT / "model" / "renders"
SHEETS = OUT / "drawings" / "png"
MUTED, BG, FLOOR_BG = (101, 109, 118), (255, 255, 255), (242, 242, 240)


def font(size):
    for name in ("segoeui.ttf", "DejaVuSans.ttf"):
        for folder in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
            if (folder / name).exists():
                return ImageFont.truetype(str(folder / name), size)
    return ImageFont.load_default()


def trim(img, bg, margin=20):
    """Crop to the drawn content: everything that differs from the background colour."""
    diff = ImageChops.difference(img.convert("RGB"), Image.new("RGB", img.size, bg)).convert("L")
    box = diff.point(lambda v: 255 if v > 10 else 0).getbbox()
    x0, y0, x1, y1 = box
    return img.crop((max(0, x0 - margin), max(0, y0 - margin), min(img.width, x1 + margin),
                     min(img.height, y1 + margin)))


def fit_h(img, h):
    return img.resize((round(img.width * h / img.height), h), Image.LANCZOS)


def fit_w(img, w):
    return img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)


def row(panels, labels, h, gap=48, pad=32, caption=46):
    panels = [fit_h(p, h) for p in panels]
    w = pad * 2 + sum(p.width for p in panels) + gap * (len(panels) - 1)
    canvas = Image.new("RGB", (w, pad + h + (caption if labels else 0) + pad // 2), BG)
    d, f = ImageDraw.Draw(canvas), font(24)
    x = pad
    for p, label in zip(panels, labels or [None] * len(panels)):
        canvas.paste(p, (x, pad))
        if label:
            d.text((x, pad + h + 12), label, fill=MUTED, font=f)
        x += p.width + gap
    return canvas


def save(img, name, **kw):
    FIG.mkdir(parents=True, exist_ok=True)
    path = FIG / name
    img.save(path, **kw)
    print(f"{path.relative_to(ROOT)}: {img.width} x {img.height}, {path.stat().st_size // 1024} KB")


def sheet(stem):
    return Image.open(SHEETS / f"{stem}.png").convert("RGB")


def main():
    plan = trim(sheet("A-101_ground-floor-plan").crop((120, 130, 2020, 1500)), BG)
    ground = trim(Image.open(RENDERS / "05_ground-floor.png").convert("RGB"), FLOOR_BG)
    save(row([plan, ground], ["Ground floor plan, 1:50  (DXF / PDF)", "The same floor in the 3D model  (three.js)"],
             760), "plan-to-model.png", optimize=True)

    levels = [trim(Image.open(RENDERS / n).convert("RGB"), FLOOR_BG)
              for n in ("03_first-floor.png", "06_ground-floor-rear.png")]
    save(row(levels, ["First floor", "Ground floor, from the garden side"], 620), "levels.png", optimize=True)

    exterior = [Image.open(RENDERS / n).convert("RGB").crop((140, 80, 1780, 1160))
                for n in ("01_building-front.png", "02_building-rear.png")]
    save(row(exterior, ["Street side", "Garden side"], 600), "exterior.jpg", quality=88, optimize=True)

    names = [("A-100_site-plan", "A-100  Site plan"), ("A-101_ground-floor-plan", "A-101  Ground floor plan"),
             ("A-102_first-floor-plan", "A-102  First floor plan"),
             ("A-201_elevations-south-and-north", "A-201  Elevations"), ("A-301_section-a-a", "A-301  Section A-A"),
             ("A-000_cover-and-area-schedule", "A-000  Cover and area schedule")]
    thumbs = [fit_w(sheet(n), 700) for n, _ in names]
    tw, th, gap, pad, cap = thumbs[0].width, thumbs[0].height, 36, 32, 44
    grid = Image.new("RGB", (pad * 2 + tw * 3 + gap * 2, pad * 2 + (th + cap) * 2 + gap), BG)
    d, f = ImageDraw.Draw(grid), font(24)
    for i, (img, (_, label)) in enumerate(zip(thumbs, names)):
        x, y = pad + (i % 3) * (tw + gap), pad + (i // 3) * (th + cap + gap)
        grid.paste(img, (x, y))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(208, 215, 222), width=2)
        d.text((x, y + th + 10), label, fill=MUTED, font=f)
    save(grid, "drawing-set.png", optimize=True)


if __name__ == "__main__":
    main()

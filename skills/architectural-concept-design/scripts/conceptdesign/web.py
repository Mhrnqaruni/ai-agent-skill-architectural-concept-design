"""The furnished 3D model as one offline HTML page, and headless renders of its views."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import scene as scene_mod
from .sheets import slug

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "viewer"
VENDOR = ASSETS / "three-r147"


def _js(path):
    return path.read_text(encoding="utf-8").replace("</script", "<\\/script")


def build_page(model, out_dir, log=print):
    """Write <out_dir>/model/index.html: three.js, its controls, the scene data and the viewer."""
    data = scene_mod.build(model)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = (ASSETS / "viewer.html").read_text(encoding="utf-8")
    for key, text in (("/*THREE*/", _js(VENDOR / "three.min.js")), ("/*ORBIT*/", _js(VENDOR / "OrbitControls.js")),
                      ("/*CSS2D*/", _js(VENDOR / "CSS2DRenderer.js")), ("/*SCENE*/", payload),
                      ("/*APP*/", _js(ASSETS / "viewer.js"))):
        page = page.replace(key, text, 1)
    out = Path(out_dir) / "model" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    log(f"3D model: {out} ({out.stat().st_size / 1024:.0f} KB, {len(data['boxes'])} parts, "
        f"{len(data['items'])} furniture items)")
    return out


def views(model):
    """(URL hash, file stem) for every render: the building from the front and the rear, then each
    level from the top down, from two sides."""
    out = [("house", "01_building-front"), ("house-rear", "02_building-rear")]
    for k, lv in enumerate(reversed(model.levels)):
        n = 3 + 2 * k
        out.append((f"level-{lv.id}", f"{n:02d}_{slug(lv.name)}"))
        out.append((f"level-{lv.id}-rear", f"{n + 1:02d}_{slug(lv.name)}-rear"))
    return out


def find_browser():
    """A Chromium-based browser for headless renders (Edge, Chrome or Chromium)."""
    candidates = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    return None


def render(page, model, out_dir, size=(1920, 1200), log=print):
    """One PNG per view, with SwiftShader WebGL so no GPU is needed. Returns the files written."""
    browser = find_browser()
    if not browser:
        log("renders skipped: no Edge, Chrome or Chromium found (the HTML model is still complete)")
        return []
    out = (Path(out_dir) / "model" / "renders").resolve()     # the browser needs absolute paths
    out.mkdir(parents=True, exist_ok=True)
    url = Path(page).resolve().as_uri()
    files = []
    for view, stem in views(model):
        target = out / f"{stem}.png"
        target.unlink(missing_ok=True)
        cmd = [browser, "--headless=new", "--hide-scrollbars", "--enable-unsafe-swiftshader",
               "--use-angle=swiftshader", "--no-first-run", "--no-default-browser-check",
               f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=20000",
               f"--screenshot={target}", f"{url}#{view}-still"]
        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=240)
        except subprocess.TimeoutExpired:
            pass
        if target.exists():
            files.append(target)
            log(f"  render {stem}")
        else:
            log(f"  render FAILED: {stem}")
    return files

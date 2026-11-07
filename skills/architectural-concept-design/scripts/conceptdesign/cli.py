"""Command-line interface of the concept design engine.

    concept.py init <folder> [--title "..."]      start a project from the templates
    concept.py check <design.json> [--json]       validate the model and run the design rules
    concept.py build <design.json> [--renders]    drawings, 3D model, area schedule and report
    concept.py schedule <design.json>             print the area schedule (md, csv or json)
    concept.py render <index.html> <design.json>  render the 3D views to PNG
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__, areas, rules
from .model import ModelError, load

TEMPLATES = Path(__file__).resolve().parents[2] / "assets" / "templates"


def _load(path):
    try:
        return load(path)
    except FileNotFoundError:
        print(f"error: {path} not found", file=sys.stderr)
    except ModelError as e:
        print(f"error: {path} is not a valid design model:", file=sys.stderr)
        for problem in e.problems:
            print(f"  - {problem}", file=sys.stderr)
    return None


def cmd_init(args):
    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for name in ("design.json", "brief.md", "specification.md"):
        target = folder / name
        if target.exists() and not args.force:
            print(f"kept existing {target} (use --force to overwrite)")
            continue
        shutil.copyfile(TEMPLATES / name, target)
        written.append(target)
    if args.title and (folder / "design.json") in written:
        # replace the title in place, keeping the template's compact one-line rectangles
        path = folder / "design.json"
        text = path.read_text(encoding="utf-8").replace('"title": "New Project"',
                                                        '"title": ' + json.dumps(args.title, ensure_ascii=False), 1)
        path.write_text(text, encoding="utf-8")
    for target in written:
        print(f"wrote {target}")
    return 0


def cmd_check(args):
    model = _load(args.design)
    if model is None:
        return 2
    findings = rules.run(model)
    if args.json:
        print(json.dumps({"errors": sum(f.severity == "error" for f in findings),
                          "warnings": sum(f.severity == "warning" for f in findings),
                          "findings": [f.as_dict() for f in findings],
                          "built_area": {lv.id: round(lv.built_area, 2) for lv in model.levels}}, indent=2))
    else:
        print(rules.report(model, findings))
    errors = [f for f in findings if f.severity == "error"]
    return 1 if errors or (args.strict and findings) else 0


def cmd_schedule(args):
    model = _load(args.design)
    if model is None:
        return 2
    if args.format == "csv":
        print(areas.csv(model), end="")
    elif args.format == "json":
        print(json.dumps([dict(zip(("level", "level_name", "space", "alt_name", "area_m2"), row))
                          for row in areas.rows(model)], indent=2, ensure_ascii=False))
    else:
        print(areas.markdown(model), end="")
    return 0


def cmd_build(args):
    model = _load(args.design)
    if model is None:
        return 2
    findings = rules.run(model)
    print(rules.report(model, findings))
    if any(f.severity == "error" for f in findings) or (args.strict and findings):
        print("Fix the problems above, then build again. Nothing was written.", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else Path(args.design).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    report = {"design": str(Path(args.design).resolve()), "engine": __version__,
              "checks": {"errors": 0, "warnings": len(findings), "findings": [f.as_dict() for f in findings]},
              "outputs": {}}
    audit = []
    if not args.skip_drawings:
        from . import sheets
        files, audit = sheets.build(model, out, findings)
        report["outputs"]["drawings_pdf"] = str(out / "drawings" / "concept-drawings.pdf")
        report["outputs"]["true_size_dxf"] = str(out / "drawings" / "model_1to1_metres.dxf")
        report["outputs"]["sheets"] = sorted({str(f.with_suffix("").name) for f in files if f.suffix == ".dxf"
                                              and f.parent.name == "dxf"})
        report["dxf_audit"] = audit
    if not args.skip_model:
        from . import web
        page = web.build_page(model, out)
        report["outputs"]["model_html"] = str(page)
        if args.renders:
            report["outputs"]["renders"] = [str(f) for f in web.render(page, model, out)]
    (out / "area-schedule.md").write_text(areas.markdown(model), encoding="utf-8")
    (out / "area-schedule.csv").write_text(areas.csv(model), encoding="utf-8")
    report["outputs"]["area_schedule"] = str(out / "area-schedule.md")
    report["built_area"] = {lv.id: round(lv.built_area, 2) for lv in model.levels}
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"outputs in {out}  (summary: {out / 'report.json'})")
    if audit:
        print("The DXF audit reported problems; see report.json.", file=sys.stderr)
        return 1
    return 0


def cmd_render(args):
    model = _load(args.design)
    if model is None:
        return 2
    from . import web
    page = Path(args.page)
    out = page.resolve().parent.parent
    return 0 if web.render(page, model, out) else 1


def build_parser():
    p = argparse.ArgumentParser(prog="concept.py", description="Architectural concept design engine: "
                                "validate a design model, check its design rules, and build its drawings and 3D model.")
    p.add_argument("--version", action="version", version=f"conceptdesign {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("init", help="start a project folder from the templates")
    s.add_argument("folder")
    s.add_argument("--title")
    s.add_argument("--force", action="store_true", help="overwrite existing files")
    s.set_defaults(func=cmd_init)
    s = sub.add_parser("check", help="validate the model and run the design rules")
    s.add_argument("design")
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.add_argument("--strict", action="store_true", help="treat warnings as errors")
    s.set_defaults(func=cmd_check)
    s = sub.add_parser("build", help="check, then write drawings, 3D model, schedule and report")
    s.add_argument("design")
    s.add_argument("--out", help="output folder (default: output/ next to the design file)")
    s.add_argument("--renders", action="store_true", help="also render PNG views (needs Chrome, Edge or Chromium)")
    s.add_argument("--skip-drawings", action="store_true")
    s.add_argument("--skip-model", action="store_true")
    s.add_argument("--strict", action="store_true", help="treat warnings as errors")
    s.set_defaults(func=cmd_build)
    s = sub.add_parser("schedule", help="print the area schedule")
    s.add_argument("design")
    s.add_argument("--format", choices=("md", "csv", "json"), default="md")
    s.set_defaults(func=cmd_schedule)
    s = sub.add_parser("render", help="render the views of a built 3D model to PNG")
    s.add_argument("page", help="the model's index.html")
    s.add_argument("design")
    s.set_defaults(func=cmd_render)
    return p


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):      # never crash on a console that lacks a character
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)

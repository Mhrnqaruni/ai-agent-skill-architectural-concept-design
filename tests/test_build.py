import json

import pytest
from conftest import EXAMPLE, TEMPLATE

from conceptdesign import sheets
from conceptdesign.cli import main


def test_check_command_exit_codes(tmp_path, template, capsys):
    assert main(["check", str(TEMPLATE)]) == 0
    template["levels"][0]["area_limit"] = 40
    over = tmp_path / "over.json"
    over.write_text(json.dumps(template), encoding="utf-8")
    assert main(["check", str(over)]) == 1
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json", encoding="utf-8")
    assert main(["check", str(broken)]) == 2
    capsys.readouterr()
    assert main(["check", "--json", str(TEMPLATE)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["errors"] == 0 and result["built_area"] == {"G": 50.4}


def test_build_writes_the_whole_package(tmp_path):
    out = tmp_path / "out"
    assert main(["build", str(TEMPLATE), "--out", str(out)]) == 0
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["dxf_audit"] == []
    assert (out / "drawings" / "concept-drawings.pdf").stat().st_size > 10_000
    assert (out / "drawings" / "model_1to1_metres.dxf").exists()
    stems = {p.stem for p in (out / "drawings" / "dxf").glob("*.dxf")}
    assert {"A-000_cover-and-area-schedule", "A-101_ground-floor-plan", "A-201_elevations-south-and-north",
            "A-202_elevations-east-and-west", "A-301_section-a-a"} <= stems
    page = (out / "model" / "index.html").read_text(encoding="utf-8")
    assert "window.SCENE = {" in page and "Living + kitchen" in page
    assert "| **All levels** | **Total built area** | **50.40** |" in (out / "area-schedule.md").read_text(encoding="utf-8")


def test_build_refuses_a_model_with_errors(tmp_path, template):
    template["levels"][0]["area_limit"] = 40
    bad = tmp_path / "design.json"
    bad.write_text(json.dumps(template), encoding="utf-8")
    assert main(["build", str(bad)]) == 1
    assert not (tmp_path / "output").exists()


@pytest.mark.slow
def test_example_drawing_set_is_valid_dxf(tmp_path):
    from conceptdesign import rules
    from conceptdesign.model import load
    model = load(EXAMPLE)
    files, problems = sheets.build(model, tmp_path, rules.run(model), log=lambda *_: None)
    assert problems == []
    assert sum(1 for f in files if f.suffix == ".pdf") == 8        # 7 sheets and the combined set


def test_init_copies_the_templates(tmp_path):
    assert main(["init", str(tmp_path / "p"), "--title", "Cabin"]) == 0
    data = json.loads((tmp_path / "p" / "design.json").read_text(encoding="utf-8"))
    assert data["project"]["title"] == "Cabin"
    assert (tmp_path / "p" / "brief.md").exists() and (tmp_path / "p" / "specification.md").exists()

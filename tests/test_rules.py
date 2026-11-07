import pytest

from conceptdesign import areas, rules
from conceptdesign.model import parse


def findings(data, severity=None):
    out = rules.run(parse(data))
    return [f for f in out if severity is None or f.severity == severity]


def messages(data, severity):
    return "\n".join(f"{f.rule}: {f.message}" for f in findings(data, severity))


def test_example_and_template_pass_every_rule(example, template):
    assert findings(example) == []
    assert findings(template) == []


def test_unreachable_room(example):
    ground = example["levels"][0]
    ground["openings"] = [op for op in ground["openings"] if op["type"] != "opening"]
    text = messages(example, "error")
    assert "reach: room 'Kitchen + dining' cannot be reached from the entrance" in text


def test_door_swinging_into_furniture(template):
    # a nightstand placed inside the bedroom door's swing
    template["levels"][0]["furniture"].append({"type": "nightstand", "rect": [5.2, 2.7, 5.6, 3.1], "back": "W"})
    assert "door-swing: door openings[1]" in messages(template, "error")


def test_overlapping_furniture(template):
    template["levels"][0]["furniture"].append({"type": "armchair", "rect": [3.7, 1.5, 4.4, 2.2], "back": "E"})
    assert "clash: sofa furniture[3] overlaps armchair furniture[14]" in messages(template, "error")


def test_area_limit(template):
    template["levels"][0]["area_limit"] = 45
    assert "area-limit: built area 50.40" in messages(template, "error")


def test_setback(example):
    example["site"]["setbacks"][1] = 4.0                   # east side needs 4.0 m, the house is 3.3 m away
    assert "setback: the building is 3.30 m from boundary edge 1 (needs 4.00 m)" in messages(example, "error")


def test_building_outside_the_site(example):
    example["site"]["boundary"] = [[0, 0], [18, 0], [18, 20], [0, 20]]
    example["site"]["setbacks"] = None
    assert "is outside the site" in messages(example, "error")


def test_daylight_warning(template):
    lv = template["levels"][0]
    lv["openings"] = [op for op in lv["openings"] if op["at"] != [6.2, 5.7, 7.6, 6.0]]
    assert "daylight: 'Bedroom' has no window" in messages(template, "warning")


def test_narrow_door_warning(template):
    template["levels"][0]["openings"][2]["at"] = [5.0, 1.4, 5.1, 2.0]
    assert "door-width: openings[2] is 0.60 m wide" in messages(template, "warning")


def test_label_that_does_not_fit_its_room(template):
    template["levels"][0]["rooms"][1]["label_at"] = [5.25, 4.95]      # hard against the bedroom's west wall
    assert "label: the label of 'Bedroom'" in messages(template, "warning")


def test_reach_error_suggests_the_shared_wall(template):
    lv = template["levels"][0]
    lv["openings"] = [op for op in lv["openings"] if op["at"] != [5.0, 1.3, 5.1, 2.0]]
    assert "it shares the wall [5.0, 0.3, 5.1, 5.7] with 'Living + kitchen'" in messages(template, "error")


def test_steep_stair_warning(example):
    example["levels"][0]["stairs"][0]["rect"] = [7.7, 19.6, 8.7, 22.8]
    assert "stair:" in messages(example, "warning")


@pytest.mark.parametrize("level", [0, 1])
def test_area_schedule_adds_up_to_the_built_area(example, level):
    lv = parse(example).levels[level]
    s = areas.schedule(lv)
    total = sum(a for _room, a in s["rooms"]) + s["stairs"] + s["circulation"] + s["walls"]
    assert total == pytest.approx(s["built"], abs=0.02)
    assert s["walls"] > 0 and s["stairs"] == pytest.approx(4.2)


def test_schedule_on_an_l_shaped_floor(template):
    lv = template["levels"][0]
    lv["footprint"] = [[0.0, 0.0, 8.4, 6.0], [0.0, 6.0, 4.0, 9.0]]
    lv["openings"] = [op for op in lv["openings"] if op["at"] != [1.2, 5.7, 2.4, 6.0]]
    model = parse(template)
    s = areas.schedule(model.levels[0])
    total = sum(a for _room, a in s["rooms"]) + s["stairs"] + s["circulation"] + s["walls"]
    assert s["built"] == pytest.approx(62.4)
    assert total == pytest.approx(62.4, abs=0.02)

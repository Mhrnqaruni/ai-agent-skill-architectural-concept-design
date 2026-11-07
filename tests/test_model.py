import pytest

from conceptdesign.model import ModelError, parse


def problems(data):
    with pytest.raises(ModelError) as e:
        parse(data)
    return "\n".join(e.value.problems)


def test_example_and_template_are_valid(example, template):
    for data in (example, template):
        model = parse(data)
        assert model.levels and model.levels[0].ext_walls


def test_stairs_link_two_levels(example):
    model = parse(example)
    ground, first = model.levels
    assert ground.stairs_up[0].to == "F" and first.stairs_down[0].level == "G"
    assert first.voids == [ground.stairs_up[0].rect]


def test_missing_title_is_reported_with_its_path(template):
    del template["project"]["title"]
    assert "project.title: is required" in problems(template)


def test_bad_rectangle(template):
    template["levels"][0]["walls"][0] = [5.0, 0.3, 4.0, 5.7]
    assert "levels[0].walls[0]: needs x0 < x1" in problems(template)


def test_door_hinge_must_suit_the_wall(template):
    template["levels"][0]["openings"][0]["hinge"] = "N"      # the front door is in an east-west wall
    assert "levels[0].openings[0].hinge: must be one of W, E" in problems(template)


def test_opening_must_cut_a_wall(template):
    template["levels"][0]["openings"].append({"type": "window", "at": [2.0, 2.0, 3.0, 2.3]})
    assert "does not cut any wall" in problems(template)


def test_unknown_furniture_type(template):
    template["levels"][0]["furniture"].append({"type": "piano", "rect": [1, 1, 2, 2]})
    assert "furniture[14].type: must be one of" in problems(template)


def test_room_label_outside_the_room(template):
    template["levels"][0]["rooms"][1]["label_at"] = [1.0, 1.0]
    assert "rooms[1].label_at: must lie inside the room" in problems(template)


def test_stair_on_the_top_level(template):
    template["levels"][0]["stairs"] = [{"rect": [1, 1, 2, 5], "up": "N"}]
    assert "top level cannot have a stair going up" in problems(template)


def test_levels_listed_bottom_up(example):
    example["levels"][1]["elevation"] = -3.0
    assert "levels must be listed from the lowest up" in problems(example)


def test_an_entrance_is_required(template):
    del template["levels"][0]["entrance"]
    assert "needs an 'entrance'" in problems(template)


def test_section_line_can_be_set(example):
    example["building"]["section"] = {"line": "east-west", "at": 20.0}
    assert parse(example).section == ("y", 20.0)
    example["building"]["section"]["at"] = 40.0
    assert "building.section.at: must cross the building" in problems(example)


def test_back_side_is_inferred_from_the_wall(template):
    del template["levels"][0]["furniture"][0]["back"]     # kitchen run along the north wall
    model = parse(template)
    assert model.levels[0].furniture[0].back == "N"

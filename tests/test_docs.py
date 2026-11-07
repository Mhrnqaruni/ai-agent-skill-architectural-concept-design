"""The documentation stays true: JSON in the references parses, the schema accepts the examples,
and SKILL.md meets the Agent Skills limits."""
import json
import re

import pytest
from conftest import EXAMPLE, ROOT, SKILL, TEMPLATE

from conceptdesign.model import FURNITURE, parse


def frontmatter():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    head = text.split("---", 2)[1]
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(head), text


def test_skill_frontmatter_meets_the_spec():
    meta, text = frontmatter()
    assert meta["name"] == SKILL.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", meta["name"]) and len(meta["name"]) <= 64
    assert 1 <= len(meta["description"]) <= 1024
    assert len(meta.get("compatibility", "")) <= 500
    assert len(text.splitlines()) < 500


def test_every_linked_reference_exists():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for link in re.findall(r"\]\((references/[^)]+)\)", text):
        assert (SKILL / link).exists(), link


def test_worked_example_in_the_reference_is_valid():
    doc = (SKILL / "references" / "design-model.md").read_text(encoding="utf-8")
    block = doc.split("## Worked example", 1)[1].split("```json", 1)[1].split("```", 1)[0]
    parse(json.loads(block))


def test_reference_lists_every_furniture_type():
    doc = (SKILL / "references" / "design-model.md").read_text(encoding="utf-8")
    for kind in FURNITURE:
        assert f"`{kind}`" in doc, kind


@pytest.mark.parametrize("path", [EXAMPLE, TEMPLATE], ids=["example", "template"])
def test_json_schema_accepts_the_examples(path):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((SKILL / "assets" / "design-model.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), schema)


def test_readme_names_the_skill():
    assert "architectural-concept-design" in (ROOT / "README.md").read_text(encoding="utf-8")

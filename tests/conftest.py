import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architectural-concept-design"
sys.path.insert(0, str(SKILL / "scripts"))

EXAMPLE = ROOT / "examples" / "family-house" / "design.json"
TEMPLATE = SKILL / "assets" / "templates" / "design.json"


@pytest.fixture
def example():
    return copy.deepcopy(json.loads(EXAMPLE.read_text(encoding="utf-8")))


@pytest.fixture
def template():
    return copy.deepcopy(json.loads(TEMPLATE.read_text(encoding="utf-8")))

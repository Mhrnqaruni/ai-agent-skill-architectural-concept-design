#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["ezdxf>=1.4,<2", "PyMuPDF>=1.24"]
# ///
"""Architectural concept design engine.

    python scripts/concept.py init my-house               # design.json, brief.md, specification.md
    python scripts/concept.py check my-house/design.json  # validate and run the design rules
    python scripts/concept.py build my-house/design.json --renders

With uv installed, `uv run scripts/concept.py ...` installs the dependencies by itself.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conceptdesign.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

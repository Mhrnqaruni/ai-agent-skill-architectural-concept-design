"""Fail when the version numbers in the repository disagree (run in CI and before a release).

    python tools/check_versions.py            # all files agree
    python tools/check_versions.py v1.0.0     # ...and match this tag
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architectural-concept-design"


def versions():
    found = {}
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    found["SKILL.md metadata.version"] = re.search(r'version:\s*"?([0-9][^"\s]*)"?', skill_md).group(1)
    init = (SKILL / "scripts" / "conceptdesign" / "__init__.py").read_text(encoding="utf-8")
    found["conceptdesign.__version__"] = re.search(r'__version__\s*=\s*"([^"]+)"', init).group(1)
    for manifest in sorted(ROOT.glob(".*-plugin/plugin.json")) + sorted(ROOT.glob("plugin.json")):
        found[str(manifest.relative_to(ROOT))] = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    for market in sorted(ROOT.glob(".*-plugin/marketplace.json")):
        data = json.loads(market.read_text(encoding="utf-8"))
        for plugin in data.get("plugins", []):
            if "version" in plugin:
                found[f"{market.relative_to(ROOT)} ({plugin['name']})"] = plugin["version"]
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    found["CITATION.cff"] = re.search(r"^version:\s*(\S+)", cff, re.M).group(1)
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    found["CHANGELOG.md"] = re.search(r"^## \[(\d[^\]]*)\]", changelog, re.M).group(1)
    return found


def main(argv):
    found = versions()
    expected = argv[1].lstrip("v") if len(argv) > 1 else found["SKILL.md metadata.version"]
    width = max(map(len, found))
    bad = [name for name, v in found.items() if v != expected]
    for name, v in found.items():
        print(f"{name:{width}s}  {v}{'' if v == expected else '   <-- expected ' + expected}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

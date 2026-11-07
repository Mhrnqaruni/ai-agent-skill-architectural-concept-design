"""Zip the skill folder for upload to Claude apps or manual installs.

    python tools/package_skill.py            # dist/architectural-concept-design.zip

The archive holds one top-level folder, architectural-concept-design/, with SKILL.md inside. It
leaves out caches and the evals (an installed skill doesn't need its own test cases and graders).
The output is deterministic: the same files give the same bytes.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architectural-concept-design"
SKIP = {"__pycache__", ".pytest_cache", "output", "evals"}


def main():
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"{SKILL.name}.zip"
    files = sorted(p for p in SKILL.rglob("*") if p.is_file() and not SKIP & set(p.relative_to(SKILL).parts)
                   and p.suffix not in (".pyc", ".pyo"))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            info = zipfile.ZipInfo(str(Path(SKILL.name) / p.relative_to(SKILL)).replace("\\", "/"),
                                   date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())
    print(f"{target.relative_to(ROOT)}: {len(files)} files, {target.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()

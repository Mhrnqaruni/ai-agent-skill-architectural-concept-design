# Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first to agree on
the approach.

## Layout

- `skills/architectural-concept-design/` is the skill: only files an agent uses (SKILL.md,
  references, scripts, assets, evals). It must stay installable by copying this one folder.
- Everything else (README, tests, examples, figures, CI) supports development and stays out of
  the skill folder.

## Development setup

```bash
git clone https://github.com/Mhrnqaruni/ai-agent-skill-architectural-concept-design.git
cd ai-agent-skill-architectural-concept-design
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r skills/architectural-concept-design/scripts/requirements.txt pytest jsonschema pyyaml pillow
pytest
python skills/architectural-concept-design/scripts/concept.py build examples/family-house/design.json --renders
```

## Guidelines

- **Keep SKILL.md short.** Stay under 500 lines; put detail in `references/`, one level deep, and
  link every reference from SKILL.md.
- **Rules come with tests.** Every new rule gets a negative test in `tests/test_rules.py` that
  shows it catching the problem.
- **Schema, engine and docs move together.** When you add a field or a furniture type, update
  `model.py`, `assets/design-model.schema.json` and `references/design-model.md`. The tests check
  that the three agree.
- **Evals for behaviour changes.** If you change the workflow in SKILL.md, add or update a case
  in `skills/architectural-concept-design/evals/` (the `claude plugin eval` layout). Run them with
  `claude plugin eval skills/architectural-concept-design --allow-tools Write,Edit,Bash`.
- **No network access in the engine**, and no new runtime dependencies without discussion.

## Releasing

1. Bump the version in `SKILL.md` (`metadata.version`), `scripts/conceptdesign/__init__.py`,
   both plugin manifests, `CITATION.cff` and `CHANGELOG.md`.
2. Tag `vX.Y.Z`. The release workflow checks that the versions agree, builds the skill zip and
   the example outputs, and attaches them to the GitHub release.

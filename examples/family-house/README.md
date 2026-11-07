# Example: Two-Storey Family House

A compact three-bedroom house on an 18 x 30 m plot, with the street to the north. It shows every
artefact the skill produces, and it is the source of the figures in the main README.

| File | Workflow step |
|---|---|
| [brief.md](brief.md) | requirement matrix, decision questions, assumptions |
| [specification.md](specification.md) | site strategy, levels, spaces, circulation, openings, open issues |
| [design.json](design.json) | the design model: two levels, a straight stair, a gable roof, site with parking and terrace |

Build it from the repository root:

```bash
python skills/architectural-concept-design/scripts/concept.py check examples/family-house/design.json
python skills/architectural-concept-design/scripts/concept.py build examples/family-house/design.json --renders
```

The outputs land in `examples/family-house/output/`, which is not tracked. The same files are
attached to every [release](https://github.com/Mhrnqaruni/ai-agent-skill-architectural-concept-design/releases)
as `family-house-*`.

Key figures:

- 82.08 m² built per floor, under the 85 m² limit
- three bedrooms, with the main one en-suite
- stair of 17 risers of 176 mm, going 262 mm
- check result: 0 errors, 0 warnings

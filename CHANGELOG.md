# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-11-08

### Added

- `agents/openai.yaml`, which supplies the skill's display name, description and default prompt
  in Codex.
- A root `plugin.json` (Agent Plugins 1.0.0) for agents that install plugins from a repository.
- Install instructions for agents that read `.agents/skills/`: Codex, GitHub Copilot, Cursor,
  Gemini CLI, OpenCode, Goose and Amp. Also `gh skill install` and the one-command Claude Code
  install.

### Changed

- CI validates the skill with the official `skills-ref`, installed from the Agent Skills
  repository.
- Claude apps upload location updated to Customize > Skills.

## [1.0.0] - 2026-11-08

### Added

- `architectural-concept-design` skill following the Agent Skills specification: a workflow from
  brief to checked concept design, five reference guides, and templates for the brief,
  specification and design model.
- Concept design engine (`scripts/concept.py`) with `init`, `check`, `build`, `schedule` and
  `render`.
- Design model in JSON, with a JSON Schema: site, levels, partitions, typed openings, rooms with
  cutouts, straight and U stairs, 30 furniture types, gable and flat roofs, and footprints that
  are unions of rectangles.
- Design rules:
  - errors: reachability, door-swing clearance, furniture clashes, area limits, site boundary
    and setbacks
  - warnings: daylight ratio, door widths, bedroom size, stair comfort and width, rooms drawn
    over walls
- Drawing set:
  - an A3 cover with an exact area schedule, a site plan with the buildable zone, a plan per
    level, four elevations and section A-A
  - each sheet as DXF R2018 on AIA / NCS layers, PDF and PNG, with an audit of every DXF
  - a true-size DXF of every plan
- Furnished 3D model as one offline HTML file (three.js r147): cutaway levels, the whole
  building with roof and site, deep links, and headless renders.
- Evaluation cases in the `claude plugin eval` layout, an engine test suite, CI, and an example
  project.

[1.0.1]: https://github.com/Mhrnqaruni/ai-agent-skill-architectural-concept-design/releases/tag/v1.0.1
[1.0.0]: https://github.com/Mhrnqaruni/ai-agent-skill-architectural-concept-design/releases/tag/v1.0.0

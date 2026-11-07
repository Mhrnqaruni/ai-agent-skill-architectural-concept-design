# Standards and defaults

The engine produces concept-stage design. Use this page for scope, defaults when local rules are
unknown, and the drafting conventions the drawings follow. Always prefer the rules of the
project's jurisdiction when the user gives them, and say which defaults you used.

## Design stage

- **RIBA Plan of Work 2020, Stage 2 (Concept Design):** site strategy, spaces and sizes, levels,
  facades, an area schedule, and open issues.
- **AIA Schematic Design:** the US equivalent: plans, elevations, sections, area tabulation.
- This stage excludes structure, foundations, building services, detailed code compliance and
  construction documents. Every output carries "Concept design - not for construction".

## Defaults used by the rules

| Topic | Default | Basis |
|---|---|---|
| Habitable-room glazing | at least 1/8 of floor area | common rule of thumb in building regulations |
| Door width | at least 0.7 m (0.8 rooms, 0.9 entrance) | common minimums |
| Bedroom area | at least 7 m² | common minimum for a single bedroom |
| Stair rise | at most 0.19 m | common residential maximum |
| Stair going | at least 0.25 m | common residential minimum |
| Stair comfort | 2 x rise + going = 0.60-0.65 m | Blondel's rule |
| Stair width | at least 0.85 m | common residential minimum |
| Door swings | clear of furniture, walls and other swings | functional requirement |
| Reachability | every room reachable from the entrance or the stairs | functional requirement |

## Other common limits to ask about

Local rules differ. Ask the user, or say that these are typical values:

- Setbacks from front, side and rear boundaries (often 3-6 m front, 1.5-3 m side)
- Site coverage and floor-area ratio
- Building height, number of storeys, roof pitch
- Minimum ceiling height (often 2.4-2.6 m in habitable rooms)
- Parking spaces per dwelling and the size of each space (about 2.5 x 5.0 m)
- Accessibility (a step-free entrance, a WC on the entrance level, 0.9 m doors)
- Fire escape from upper-floor bedrooms (egress windows)

## Drafting conventions

| Convention | Applied as |
|---|---|
| Sheet size | A3 landscape, with a title block strip on the right |
| Sheet numbers | A-000 cover and area schedule; A-100 site; A-101 and up plans (lowest level first); A-201/A-202 elevations; A-301 section |
| Scales | plans 1:50 (1:100 if large); elevations and section 1:50-1:200 to fit; site 1:100-1:500 |
| Layers | AIA CAD Layer Guidelines / US National CAD Standard: `A-WALL`, `A-DOOR`, `A-GLAZ`, `A-FURN`, `A-FLOR-STRS`, `A-FLOR-LEVL`, `A-AREA-IDEN`, `A-ANNO-DIMS`, `A-ANNO-TEXT`, `A-ANNO-SYMB`, `A-ANNO-TTLB`, `A-SITE`, `A-ELEV`, `A-SECT`, `A-ROOF` |
| Units and levels | metres; finished floor levels relative to ±0.00, marked on each plan |
| Dimensions | overall dimensions plus chains along the north and west faces |
| Symbols | filled wall sections, door swings as arcs, sliding doors, windows with sill and head, stairs with the walking line and an UP/DN arrow, section marks, north arrow, scale bar |
| Files | DXF R2018 per sheet, audited after writing; PDF and PNG renders; a true-size DXF in metres |

## Areas

- **Built area** of a level: the area of its footprint (outside faces). Area limits are checked
  against it.
- **Room areas:** inside wall faces, measured from the model, not typed in.
- **Area schedule:** rooms + stairs + circulation + walls = built area for every level. It is
  computed exactly on the grid of all rectangle edges.

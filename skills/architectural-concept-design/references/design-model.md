# The design model (design.json)

The single source of truth for a project. Units are metres; levels are relative to ±0.00.

## Contents

- [Conventions](#conventions)
- [Top level](#top-level)
- [project](#project)
- [site](#site)
- [building](#building)
- [rules](#rules)
- [levels](#levels)
- [walls](#walls)
- [openings](#openings)
- [rooms](#rooms)
- [stairs](#stairs)
- [furniture](#furniture)
- [Worked example](#worked-example)
- [Validation messages](#validation-messages)

## Conventions

- **Axes.** x runs east and y runs north in plan; z is up. Plan north is +y.
  `site.north_deg` rotates only the north arrow, for sites where true north differs.
- **Rectangles** are `[x0, y0, x1, y1]` with x0 < x1 and y0 < y1, always axis-aligned.
- **Sides** are `N`, `E`, `S`, `W`.
- **Footprint** rectangles are outside faces. The engine generates the outside walls inside that
  outline at `building.exterior_wall` thickness, so never list outside walls yourself.
- **Partitions** in `walls` are thin rectangles, 0.10 m across by default, that run between wall
  faces.
- **Rooms** are drawn between wall faces (clear internal size). Their areas are measured, not typed in.
- **Openings** are rectangles that span the full thickness of the wall they cut.
- Keep coordinates on a 5 cm grid. Round numbers make the model easy to read and to fix.

## Top level

```json
{"schema_version": 1, "project": {}, "site": {}, "building": {}, "rules": {}, "levels": []}
```

`project` and `levels` are required. `site`, `building` and `rules` are optional.

## project

| Field | Type | Notes |
|---|---|---|
| `title` | text, required | shown on every sheet and on the 3D page |
| `subtitle` | text | for example "Concept study" or a neutral site description |
| `alt_title` | text | the title in a second language (right-to-left scripts are shaped) |
| `stage` | text | default "Concept design - not for construction" |
| `revision`, `date`, `author` | text | title block fields |
| `notes` | list of text | replaces the default sheet notes |

## site

Optional. It adds the site plan sheet, setback checks, and the site in the 3D view (terrain,
boundary wall, paving, cars and trees).

| Field | Type | Notes |
|---|---|---|
| `boundary` | list of `[x, y]`, at least 3 | plot polygon; edges run from point k to point k+1 |
| `street_side` | side | where the street is; sets the 3D front view |
| `setbacks` | list, one per edge | minimum distance from the building to each edge, or `null` for none |
| `north_deg` | number | true north, clockwise from +y (north arrow only) |
| `boundary_wall` | number | wall height in the 3D view, default 1.2; 0 for none |
| `gates` | list of `[edge, from, to]` | openings in the boundary wall, in metres along that edge from its first point |
| `paving` | rectangles | paths, terraces, driveways |
| `parking` | list of `{"rect", "facing"}` | one car per rectangle, about 2.4 x 5.0 m |
| `trees` | `"auto"`, `"none"` or `[[x, y, size]]` | the crown radius is about 1.3 x `size` (0.8-1.2 is typical). `auto` places up to 8 trees, away from the street side, the facades and the paving; small plots may get few or none |
| `patio_set` | `[x, y]` | an outdoor table with chairs and an umbrella |
| `labels` | list of `{"name", "at"}` | site labels in the 3D view and on the site plan |

Renders use fixed cameras. The front view looks at the building from the street side, about 35°
off square. The rear view looks from the opposite side. Each level is shown from the street side
and from the rear. Keep trees and parking out of those sight lines if a facade matters.

## building

| Field | Default | Notes |
|---|---|---|
| `exterior_wall` | 0.3 | outside wall thickness |
| `partition` | 0.1 | informational; partitions take their size from their rectangles |
| `facade` | `"render"` | `render`, `brick`, `stone` or `timber` |
| `roof` | flat | `{"type": "gable", "ridge": "x" or "y", "pitch": 35, "overhang": 0.5}` or `{"type": "flat", "parapet": 0.5}` |
| `section` | automatic | `{"line": "north-south" or "east-west", "at": 8.2}`: where section A-A cuts |

A gable roof spans the bounding box of the whole building. If you leave out `ridge`, it runs
along the longer side. Use a flat roof for strongly non-rectangular top floors.

Without `section`, section A-A cuts across the ridge (north-south for a ridge along x), through
the first flight of the lowest stair, or through the middle of the building if there is no stair.
Set it to cut through the most telling part of the plan, avoiding room labels on the cut line.

## rules

Optional overrides of the rule settings:

| Setting | Default | Checked as |
|---|---|---|
| `daylight_ratio` | 0.125 | warning when the glazing of a habitable room is below this share of its floor area |
| `min_door_width` | 0.7 | warning for narrower doors and sliding doors |
| `min_bedroom_area` | 7.0 | warning for smaller bedrooms |
| `max_riser`, `min_going` | 0.19, 0.25 | stair warnings |
| `stair_comfort` | [0.60, 0.65] | warning when 2 x rise + going falls outside this range |
| `min_stair_width` | 0.85 | stair flight width warning |

Area limits and setbacks are errors. Set them on the levels and the site.

## levels

List levels from the lowest up. A basement has a negative elevation.

| Field | Type | Notes |
|---|---|---|
| `id` | text, required | 1-16 letters, digits or `_`, for example `B`, `G`, `F1` |
| `name` | text | "Ground floor", shown on sheets and in the 3D buttons |
| `alt_name` | text | second-language name |
| `elevation` | number, required | finished floor level |
| `height` | number | floor to floor, default 3.0; on the top floor, floor to the eaves. The section shows the top floor open to the roof; whether to ceil it flat or leave it vaulted is a specification choice |
| `footprint` | rectangles, required | outside faces; several rectangles make L, U or courtyard plans |
| `area_limit` | number | error when the built area (footprint area) exceeds it |
| `entrance` | `[x, y]` | a point just inside the main entrance door; at least one level needs it |
| `finish` | text | base floor finish: `wood`, `tile`, `stone`, `concrete` or `deck` |
| `walls`, `openings`, `rooms`, `stairs`, `furniture` | lists | described below |
| `dimensions` | `{"x": [...], "y": [...]}` | optional dimension chains along the north and west faces |

Reachability starts at `entrance`, or on upper floors at the stairs. Every room must be reachable
from there through doors, sliding doors and openings.

## walls

Partitions only, as rectangles: `[7.6, 17.3, 7.7, 23.9]` is a 0.10 m north-south wall. Run them
face to face with the outside walls and with each other, so there are no gaps. A door needs a wall
to sit in.

## openings

```json
{"type": "door",    "at": [8.85, 23.9, 9.75, 24.2], "hinge": "E", "opens": "S"}
{"type": "sliding", "at": [10.6, 17.0, 13.6, 17.3]}
{"type": "opening", "at": [9.8, 19.4, 9.9, 21.0]}
{"type": "window",  "at": [4.4, 23.9, 6.6, 24.2], "sill": 0.9, "head": 2.2}
```

- `at` spans the wall it cuts: its full thickness across, and the opening width along it.
- **door:** in an east-west wall, `hinge` is `W` or `E` and `opens` is `N` or `S`. In a
  north-south wall, `hinge` is `S` or `N` and `opens` is `E` or `W`. The door swings into the
  side named by `opens`. Its swing is a quarter disc centred on the hinge end of the opening, at
  the wall face on the `opens` side, with a radius equal to the door width. For example, a door
  at `[x0, y0, x1, y1]` in an east-west wall with `hinge: "W"` and `opens: "N"` sweeps the
  square from `(x0, y1)` to `(x1, y1 + width)`. Typical widths: 0.9 for the entrance, 0.8 for
  rooms, 0.7 for WCs. Optional `head`, default 2.1.
- **sliding:** a glazed slider in an outside wall, or a solid pocket or barn door inside. Head
  2.2. It does not swing.
- **opening:** a doorless passage. Head 2.1.
- **window:** `sill` and `head` above the floor, defaults 0.9 and 2.2. Keep the head at least
  0.2 below the level height. Use high sills (1.5) in WCs and bathrooms, and 1.05 above kitchen
  counters.

## rooms

```json
{"name": "Hall", "rect": [7.7, 18.6, 9.8, 23.9], "cutouts": [[7.7, 18.6, 8.7, 22.8]],
 "use": "hall", "label_at": [9.25, 21.6]}
```

| Field | Notes |
|---|---|
| `name` | required |
| `rect` | between wall faces; it must not overlap walls (that raises a warning) |
| `cutouts` | rectangles removed from the room, such as a stair or a shaft, for L-shaped or open-plan rooms |
| `use` | `living`, `dining`, `kitchen`, `bedroom`, `study` (habitable rooms, checked for daylight), `bath`, `wc`, `hall`, `corridor`, `storage`, `utility`, `laundry`, `closet`, `garage`, `plant`, `terrace`, `other` |
| `label_at` | the centre of the label (name, then area): inside the room and clear of furniture; defaults to the room's centre |
| `finish` | default from use: tile for wet rooms, stone for halls, concrete for garages, deck for terraces, wood otherwise |
| `access` | `"outside"` exempts a room reached only from outside (a plant room) from reachability |
| `alt_name` | second-language label |

Floor area that belongs to no room counts as circulation in the schedule.

**Label size.** Names print about 0.08 m wide per character at 1:50, and about 0.12 m at 1:100.
A two-line label is about 0.45 m tall at 1:50 and 0.7 m at 1:100. A plan prints at 1:50 when the
footprint is up to about 11.4 x 7.3 m; larger footprints print at 1:100. `check` warns
(`label`) when a label would not fit inside its room or would overlap another label. Shorten the
name (Hall, not Entrance hall) or move `label_at`. The floor-level mark is placed automatically
in a clear spot near the entrance or the stairs.

## stairs

```json
{"rect": [7.7, 18.6, 8.7, 22.8], "type": "straight", "up": "S"}
{"rect": [7.1, 20.7, 9.3, 23.9], "type": "u", "up": "N", "turn": "right"}
```

- A stair belongs to the level where it starts and rises to the next level up. It cuts a void in
  the floor above, and the engine adds guards around the void.
- `up` is the direction you face while climbing. A straight stair starts at the opposite edge;
  leave free floor in front of that start.
- A U stair has two flights side by side with a landing at the far end, and it arrives back at
  the starting edge. With `turn: "right"`, the first flight takes the left half as you climb.
- Risers number round(height / 0.175); a U stair rounds up to an even count. Size the rectangle
  so that 2 x rise + going lands between 0.60 and 0.65 m:

| Floor to floor | Straight (length x width) | U (length x width) |
|---|---|---|
| 2.8 m | 3.9 x 1.0 | 3.0 x 2.2 |
| 3.0 m | 4.2 x 1.0 | 3.2 x 2.2 |
| 3.2 m | 4.5 x 1.0 | 3.3 x 2.2 |

## furniture

Rectangle items take `rect`; point items take `at`. Oriented items take `back`: the side their
back stands against, such as a headboard, the back of a sofa, the back of a counter or the wall
behind a WC cistern. Leave `back` out and the engine infers it from the nearest wall face.

| Type | Shape | Typical size (m) | Notes |
|---|---|---|---|
| `bed` | rect, back | 1.6 x 2.0 double, 0.9 x 2.0 single | back = headboard wall |
| `nightstand` | rect, back | 0.45 x 0.45 | |
| `wardrobe` | rect, back | 0.6 deep | |
| `hanging_rail` | rect, back | 0.55 deep | open rail for walk-in closets |
| `shoe_cabinet` | rect, back | 0.32 deep | optional `height` |
| `desk` | rect, back | 1.2 x 0.6 | a chair is added in front |
| `shelves` | rect, back | 0.35 deep | |
| `sofa` | rect, back | 2.2 x 0.9 | back may face the room (floating sofa) |
| `armchair` | rect, back | 0.8 x 0.8 | |
| `coffee_table` | rect | 0.6 x 1.0 | |
| `dining_table` | rect | 0.9-1.0 deep, 0.6 per seat | chairs are added on both long sides; give it 0.8 clear all round; optional `seats` |
| `tv` | rect, back | 0.45 deep unit | back = the wall the screen hangs on |
| `rug` | rect | | flat; ignored by clash checks; `color` a, b or c |
| `kitchen` | rect, back | 0.6 deep run | sink goes under a window behind it, or `sink_at`; the hob is placed beside it |
| `island` | rect | 0.9 deep | keep 1.0-1.2 to the counter |
| `stools` | rect | the island's rect | `count`, `sides` (`S`, `N` or `NS`); stools sit on the north or south side, so islands with stools run east-west |
| `fridge` | rect, back | 0.65 x 0.6 | full height |
| `laundry` | rect, back | 0.6 x 0.6 | washer and dryer stack |
| `bar` | rect, back | 0.6 deep | |
| `basin` | rect, back | 0.6 x 0.45 | |
| `wc` | point `at`, back | | `at` = middle of the wall face behind the cistern; needs 0.68 in front of the wall |
| `shower` | rect | 0.9 x 0.9 | glass on the sides that are not against walls |
| `bathtub` | rect | 1.7 x 0.75 | |
| `sauna`, `billiards` | rect | | |
| `boiler` | rect, back | | |
| `tank` | point `at` | | optional `size` (radius) |
| `chair`, `barstool` | point `at` | | chair takes `back` |
| `plant` | point `at` | | optional `size` (pot radius, default 0.17) and `height` |

The clash check covers every item except rugs. Items must not overlap each other or stand in a
wall, and no door may swing into one.

## Worked example

A shortened version of the `init` template, a single-level 8.4 x 6.0 m cottage:

```json
{
  "schema_version": 1,
  "project": {"title": "New Project", "subtitle": "Concept study"},
  "building": {"exterior_wall": 0.3, "roof": {"type": "flat", "parapet": 0.5}},
  "levels": [{
    "id": "G", "name": "Ground floor", "elevation": 0.0, "height": 2.9,
    "footprint": [[0.0, 0.0, 8.4, 6.0]],
    "entrance": [1.35, 0.8],
    "walls": [[5.0, 0.3, 5.1, 5.7], [5.1, 2.3, 8.1, 2.4]],
    "openings": [
      {"type": "door", "at": [0.9, 0.0, 1.8, 0.3], "hinge": "W", "opens": "N"},
      {"type": "door", "at": [5.0, 2.6, 5.1, 3.4], "hinge": "S", "opens": "E"},
      {"type": "window", "at": [2.4, 0.0, 4.4, 0.3], "sill": 0.9, "head": 2.2}
    ],
    "rooms": [
      {"name": "Living + kitchen", "rect": [0.3, 0.3, 5.0, 5.7], "use": "living"},
      {"name": "Bedroom", "rect": [5.1, 2.4, 8.1, 5.7], "use": "bedroom"}
    ],
    "furniture": [
      {"type": "bed", "rect": [6.1, 3.0, 8.1, 4.6], "back": "E"},
      {"type": "wc", "at": [8.1, 1.75], "back": "E"}
    ]
  }]
}
```

For a two-storey house with a stair, a gable roof and a site, see
`examples/family-house/design.json` in the skill's repository, which is also the source of its
README figures.

## Validation messages

Problems with the file itself stop before any rule runs. Each message names its JSON path:

```
levels[0].openings[2].hinge: must be one of W, E, got 'N'
levels[1].rooms[3].label_at: must lie inside the room (and outside its cutouts)
levels[0].openings[5]: does not cut any wall: span the wall's full thickness
```

Fix the field the path points to, and run `check` again.

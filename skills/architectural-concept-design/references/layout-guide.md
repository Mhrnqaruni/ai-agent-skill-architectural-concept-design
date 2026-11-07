# Layout guide

How to turn a program into coordinates that pass the checks on the first or second run.

## Contents

- [Method](#method)
- [Grid and bands](#grid-and-bands)
- [Zoning](#zoning)
- [Circulation](#circulation)
- [Stairs](#stairs)
- [Wet rooms](#wet-rooms)
- [Doors](#doors)
- [Furniture clearances](#furniture-clearances)
- [Room sizes](#room-sizes)
- [Daylight and windows](#daylight-and-windows)
- [Multi-level alignment](#multi-level-alignment)
- [Roof and massing](#roof-and-massing)

## Method

1. **Size the footprint.** The area limit is the gross built area: the footprint to its outside
   faces. Use nearly all of it for the footprint, and expect about 85% of it as room area once
   the walls are drawn. Pick a depth of 7-10 m for a house (rooms get daylight from two sides)
   and derive the length.
2. **Place it on the site.** Respect the setbacks, put the entrance on the street side and the
   living spaces towards the sun and the garden.
3. **Draw bands.** Split the inside into two or three strips parallel to the long side, for
   example a 3.0 m service band and a 3.6-4.2 m living band.
4. **Cut the bands into rooms** with partitions placed face to face.
5. **Fix the core**: the stair, the wet rooms stacked over each other, and the hall that
   connects them.
6. **Add openings**: doors from circulation into every room, then windows.
7. **Furnish**, keeping every door swing clear.
8. **Run `check` and fix.** Then build and look at the plans and renders.

A 1:50 A3 plan fits a footprint of up to about 11.4 x 7.3 m. Larger or squarer footprints print
at 1:100, where labels take more room: keep room names short and check the `label` warnings.

## Grid and bands

- Work on a 0.05 m grid; partitions 0.10 m, outside walls 0.30 m.
- Write down the inner faces first. For a footprint `[x0, y0, x1, y1]` with 0.3 m walls, the
  inside runs from x0+0.3 to x1-0.3. Then place partitions as `[x, a, x+0.1, b]`, where a and b
  are the inner faces they meet.
- Use the same partition lines on every floor where possible. Structure and services stack, and
  the plans read clearly.

## Zoning

- **Day zone** (living, dining, kitchen) on the garden side, ideally facing the sun (south in
  the northern hemisphere).
- **Entry zone** (hall, WC, coats, stair) on the street side.
- **Night zone** (bedrooms) upstairs, or in a separate wing on single-storey plans.
- Put kitchens next to dining and near the entrance (shopping) or the garden (terrace).
- Bathrooms go next to bedrooms; a guest WC goes near the entrance.

## Circulation

- Every room needs a door or opening into circulation (a hall, corridor or landing), or into a
  room that is itself reached. Avoid routes through bedrooms; en-suites may open from their
  bedroom.
- Corridors: at least 0.9 m clear; 1.0-1.2 m is comfortable. Halls with a door: 1.2 m or more in
  front of the door.
- Open-plan living may be one room. An L-shaped room is one rectangle with `cutouts`.
- Keep the hall small but not mean. On a two-storey house, hall plus landing is typically 8-12%
  of the floor area.

## Stairs

- Straight stairs need floor to floor / 0.175 risers. A 3.0 m storey takes 17 risers and a 4.2 m
  run. Leave at least 1.0 m of free floor in front of the first step and at the top.
- U stairs (two flights and a landing) fit 3.2 x 2.2 m for 3.0 m storeys and arrive back at the
  starting edge. The upper landing is then next to the stair's start, above it.
- On the floor above, the stair is a void. Rooms on the far side of a long void can only be
  reached around its ends. Plan the upper corridor along the open side of the void, and place
  doors at the void's ends.

## Wet rooms

- Stack bathrooms and WCs over each other and keep them near the kitchen wall where possible.
- **WC:** 0.8-0.9 m wide cubicle minimum. `at` sits on the wall face behind the cistern, and the
  WC needs 0.68 m in front of that wall plus 0.6 m of clear space.
- **Shower** 0.9 x 0.9; **bathtub** 1.7 x 0.75; **basin** 0.6 x 0.45. Basins and WCs sit
  against walls; showers go in corners.
- Small WCs: open the door outwards, or hinge it so the swing misses the WC.

## Doors

- Widths: 0.9 entrance, 0.8 rooms, 0.7 WC and storage. Place the hinge 0.1-0.2 m from the
  adjacent wall, so the door folds back against that wall.
- A door's swing is a quarter disc as wide as the door, on the `opens` side. Keep it free of
  furniture, other swings and walls. If space is short, use `sliding`.
- Front doors open inwards. Doors to small rooms can open outwards into wide corridors.

## Furniture clearances

| Item | Clearance |
|---|---|
| Bed | 0.6-0.7 m on the access sides, 0.8 m at the foot |
| Wardrobe | 0.8-0.9 m in front |
| Kitchen run to island | 1.0-1.2 m |
| Dining table | 0.8 m behind chairs (0.6 if against a wall) |
| Sofa to coffee table | 0.4-0.5 m |
| Desk | 0.8 m behind the chair |
| WC and basin | 0.6 x 0.7 m clear in front |

## Room sizes

Comfortable concept-stage sizes (internal):

| Room | Area (m²) | Minimum width (m) |
|---|---|---|
| Double bedroom | 12-16 | 2.8 |
| Single bedroom | 8-10 | 2.4 |
| Living room | 18-30 | 3.6 |
| Kitchen (closed) | 8-12 | 2.4 |
| Kitchen + dining | 20-30 | 3.4 |
| Bathroom | 4.5-7 | 1.6 |
| En-suite shower room | 3-4.5 | 1.5 |
| WC | 1.5-2.5 | 0.9 |
| Study | 7-10 | 2.4 |

## Daylight and windows

- Habitable rooms need glazing of at least one-eighth of their floor area (a warning below that).
  Living rooms are better at one-sixth or more.
- Window sills: 0.9 standard, 0.6 for low windows to the garden, 1.05 over kitchen counters, 1.5
  in WCs and bathrooms.
- Put the sink under a window; the engine centres it under the window behind the counter.
- Keep TVs and headboards on walls without windows. If a bedroom has no other place for the
  bed, a high window (sill 1.5) above the headboard is acceptable. Use two orientations in corner
  rooms.

## Multi-level alignment

- Every level lists its own `footprint`. Upper floors may be smaller (terraces) or larger
  (cantilevers).
- A stair's rectangle must lie inside both levels' footprints.
- Upper-floor rooms over the stair void: none. The void is part of circulation, and the engine
  guards its open edges.
- Keep outside walls continuous between floors; that keeps the elevations simple.

## Roof and massing

- Gable roofs suit rectangular plans: 30-40° pitch, 0.4-0.6 m overhang, ridge along the long
  side.
- Flat roofs suit L, U and courtyard plans and cubic modern houses; use a 0.5 m parapet.
- The top floor's `height` is floor to eaves: 2.6-2.8 m under a gable, 2.8-3.0 m under a flat
  roof.

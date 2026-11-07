# Review checklist

Run this after `build --renders`, before presenting. Open the images; don't review from memory
of the JSON.

## Plans (output/drawings/png/A-1xx_*.png)

- [ ] Each room has a sensible shape: no corridor-like bedrooms, and no room narrower than the
      minimum widths in the layout guide.
- [ ] Route from the entrance: hall, then living, kitchen and stairs, without passing through
      bedrooms.
- [ ] Doors fold back against walls and don't block each other or the furniture.
- [ ] Wet rooms are stacked and grouped; the guest WC is near the entrance.
- [ ] Furniture fits with the clearances in the layout guide (beds, wardrobes, kitchen aisle,
      dining).
- [ ] Labels are readable, and no label sits on top of a wall or a fixture symbol. Move
      `label_at` if it does.
- [ ] Stairs: UP on the lower floor, DN on the upper floor, a free landing at both ends.

## Elevations and section (A-2xx, A-301)

- [ ] Window rhythm is calm: heads aligned per floor, similar sizes on one facade.
- [ ] Sills suit the room behind: high in bathrooms, low to the garden.
- [ ] The street facade has a clear entrance.
- [ ] The section shows comfortable ceiling heights and a stair that fits under the floor above.

## 3D walk-through (output/model/renders/*.png)

- [ ] Whole building, front and rear: proportions, roof, facade material and entrance read well.
- [ ] Each level, from two sides: every room is furnished and usable, and nothing floats or
      intersects.
- [ ] Kitchen: the sink is under a window, there is worktop on both sides of the hob, the fridge
      is at the end of the run, and the aisle is 1.0 m or more.
- [ ] Living: the TV is not against a window, and the sofa faces the TV and the view.
- [ ] Bedrooms: the headboard is not against a low window or under a sloping roof, and the
      wardrobe can open.
- [ ] Stairwell: guards on the open sides, and headroom over the flight.

## Presenting

Give the user:

1. the drawing set PDF and the 3D model (it opens in any browser),
2. two or three renders,
3. the area schedule against each limit,
4. the check summary (errors 0; any remaining warnings, with reasons),
5. the assumptions and open issues.

Keep it factual. Say that this is concept-stage design and that structure, services and code
compliance follow with licensed professionals.

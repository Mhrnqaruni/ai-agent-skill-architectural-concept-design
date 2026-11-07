# Brief: Two-Storey Family House

## Source

Example brief written for this repository: a family of four, a suburban plot, and a budget-driven
compact house.

> Three bedrooms, the main one with its own shower room. One family bathroom. Open kitchen and
> dining room to the garden, a separate living room, a guest WC near the door. Two parking spaces
> on the plot. At most 85 m² built per floor. Plot 18 x 30 m, street to the north. Setbacks 5 m
> to the street, 6 m at the rear, 3 m at the sides.

## Requirement matrix

| # | Requirement | Type | Value or limit | Source | Status |
|---|---|---|---|---|---|
| R1 | Built area per floor | limit | at most 85 m² | brief | met (82.08 per floor) |
| R2 | Bedrooms | program | 3; the main one with an en-suite | brief | met |
| R3 | Family bathroom | program | 1 | brief | met (5.7 m²) |
| R4 | Kitchen + dining | program | open, towards the garden | brief | met (29.7 m², south) |
| R5 | Living room | program | separate from the kitchen | brief | met (26.4 m²) |
| R6 | Guest WC | program | near the entrance | brief | met (2.5 m²) |
| R7 | Parking | program | 2 cars on the plot | brief | met (front yard) |
| R8 | Setbacks | limit | street 5 m, rear 6 m, sides 3 m | brief | met (5.8 / 17.0 / 3.3) |
| R9 | Plot | site | 18 x 30 m, street on the north | brief | recorded |

## Decision questions

### Q1. Stair type?

- **A.** A straight stair in the hall (4.2 x 1.0 m).
- **B.** A U stair (3.2 x 2.2 m).
- **C.** An open stair in the living room.
- **Recommendation:** A, because a central hall can hold it and the living room stays quiet.
- **Answer:** assumed A.

### Q2. Where does the kitchen go?

- **A.** On the garden side, open to dining.
- **B.** On the street side, closed.
- **C.** In the middle, with an island.
- **Recommendation:** A, because the brief asks for kitchen and dining towards the garden.
- **Answer:** assumed A, with an island facing the dining table.

### Q3. Roof?

- **A.** Gable, ridge along the long side.
- **B.** Flat.
- **C.** Hipped.
- **Recommendation:** A, because it suits a rectangular two-storey house and sheds rain simply.
- **Answer:** assumed A (35°, 0.5 m overhang).

## Assumptions

- Plot level and flat; ±0.00 at the front door.
- Floor-to-floor 3.0 m on the ground floor; 2.8 m to the eaves upstairs.
- Parking in the front yard, inside the street setback, which local rules usually allow.

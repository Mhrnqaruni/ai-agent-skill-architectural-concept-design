# Briefing: requirement matrix, decision questions, specification

## Contents

- [Requirement matrix](#requirement-matrix)
- [Decision questions](#decision-questions)
- [Assumptions](#assumptions)
- [Specification](#specification)

## Requirement matrix

Read the whole brief before writing anything. Keep the client's own words for key requirements,
and record your interpretation next to them. One row per requirement:

| # | Requirement | Type | Value or limit | Source | Status |
|---|---|---|---|---|---|
| R1 | Built area per floor | limit | at most 85 m² | brief, line 2 | met (82.1) |
| R2 | Bedrooms | program | 3; main bedroom with en-suite | brief | met |
| R3 | Day rooms face the garden | preference | south | conversation | met |
| R4 | Parking | program | 2 cars on the plot | brief | met |
| R5 | Front setback | limit | at least 5 m | local plan | met (5.8) |

- **Types:** program (spaces and fixtures), limit (areas, heights, setbacks), preference
  (orientation, adjacency, look), site (survey facts).
- **Ambiguous figures:** record how you read them. For example, "16 x 24 m" is usually frontage
  x depth, so 16 m along the street. Write the reading in the Source column and ask if it
  matters.
- **Status:** open, met, conflict, dropped. Update it after every `check`.
- Two requirements that cannot both be met make a **conflict**. Raise it with the user as a
  decision question; don't settle it silently.

## Decision questions

Ask only questions whose answer changes the layout. Group them into one message, keep each one
short, and always give:

- three options (A, B, C) that are genuinely different,
- one recommendation,
- one reason, in one sentence.

Example:

> **Q2. Stair type?**
> A. Straight stair in the hall (4.2 x 1.0 m) - simple, cheap, takes a long wall.
> B. U stair (3.2 x 2.2 m) - compact, the landing arrives next to the start.
> C. Open stair in the living room - spacious, but noise and heat move upstairs.
> **Recommendation: A**, because the hall is long enough and it keeps the living room quiet.

Good questions cover:

- stair type and position
- open or closed kitchen
- number of bathrooms
- parking (open, carport, garage)
- roof form
- where the main bedroom goes
- a study or guest room
- whether to keep a terrace

Avoid questions with an obvious answer, cosmetic questions (paint colours) and anything the
engine decides (dimension placement).

## Assumptions

If the user does not answer, or asks you to just proceed, adopt your recommendations and list
them as assumptions. Never assume site facts: the boundary, north, levels, setbacks and area
limits. Ask for these, or mark them as placeholders in the specification and on the drawings
(`project.subtitle`, for example "Placeholder site - dimensions to be confirmed").

## Specification

Write `specification.md` from the template before the design model, and keep the two in step.
A good specification:

- explains each major decision in one sentence (why the living room is south-west, why the
  stair is in the hall)
- lists every space with its size, area and position, and says the areas come from `check` or
  `schedule`
- states the stair geometry (risers, rise, going, width) and the roof (type, pitch, overhang)
- ends with open issues, such as structure, services and items still to be decided with the user

After every design change: run `check`, update the matrix statuses and the specification
tables, and rebuild.

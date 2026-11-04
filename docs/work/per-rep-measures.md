# per-rep-measures: weight, distance and duration apply to each rep

Resolves TODO #7.

## Intent

### Goal
Write down, and encode in the data model, that a set's weight, distance and duration each apply to
**every rep** in the set. Totals multiply by reps.

| Line | Meaning | Total |
|---|---|---|
| `pullup: 24kg 3x5` | 24kg on each of 15 reps | 360kg volume |
| `pavel-sprints: 3x6 50yd` | each of 18 sprints is 50yd | 900yd |
| `hang: BW 3x5 PT30S` | each of 15 hangs is 30s | 7m30s |
| `plank: BW PT45S 3x1` | one 45s hold per set | 2m15s |
| `run: 5km PT25M` | one set of one rep | 5km, 25m |

### Why
- SPEC "What works today" only says the fields are "independent per-set fields", and the `sets`
  table stores one `distance_magnitude` per set row next to `reps`, so the meaning isn't written
  anywhere. A plugin author summing `distance_magnitude` would get 150yd for the sprints line.
- Weight already works this way (`TrainingSet.volume = reps × weight`, and the `volume` plugin
  uses `SUM(reps * weight)`). Distance and duration should follow the same rule.
- Duration decided 2026-11-04: `3x5 PT30S` is 30s per rep. Every existing use (`plank: BW PT45S
  3x1`, `run-interval: 3x1 PT1M`, `run: PT30M`) has one rep per set, so nothing in the examples or
  existing logs changes meaning.

### Constraints
- No grammar, parser or DB schema change. The stored values are already per rep; only their
  documented meaning and the derived totals change.
- With no rep scheme a set has `reps=1` (`process_details`), so per rep and per set agree there.

### Out of scope
- Pace, speed and work rate (SPEC "Direction: Richer analysis"). They'll build on this rule.
- A distance/duration plugin, or new columns in the `training` view. SQL users write
  `reps * distance_magnitude`, which the docs will show.
- Duration *per set* (e.g. "3 sets of 5 inside a 30s window"). If that's ever needed it gets its
  own syntax.

### SPEC sections touched
- "What works today" ("Set fields" bullet).

### Decisions (intent review, 2026-11-04)
1. Weight, distance and duration are all per rep (duration settled by the user).
2. **Totals in code.** Add `TrainingSet.total_distance` / `total_duration` and `Movement.total_distance()`
   / `total_duration()`, mirroring `volume` / `total_volume()`, so the rule lives in code and
   tests, not just docs. No current code computes these totals, so nothing has to be "fixed".

## Plan

Two commits: the decision in docs, then the code that encodes it.

1. **`per-rep-measures: document per-rep weight, distance, duration` (Sonnet)**
   - `SPEC.md` "What works today", "Set fields" bullet: add "each applies to every rep in the set,
     so totals multiply by reps".
   - `docs/getting-started.md` "Duration and distance": a short paragraph after the examples with
     the `3x6 50yd` → 900yd and `3x5 PT30S` → 7m30s examples. Check the example comments still
     read correctly (e.g. "3 sets, 45-second hold each").
   - `CLAUDE.md` `.ox File Format` notes (the paragraph after the code block): same rule in one
     sentence.
   - `src/ox/data.py` `TrainingSet` docstring: `weight`, `duration`, `distance` described as per
     rep ("Time for each rep", not "Time under load for this set").
   - `docs/api-reference.md`: note the rule by `TrainingSet`, and in the SQL example show
     `reps * distance_magnitude`.
   - Docs-only commit, so it needs approval before committing.
2. **`per-rep-measures: add distance and duration totals` (Sonnet)**
   - `src/ox/data.py`: `TrainingSet.total_distance` (`distance * reps`, `None` without distance) and
     `TrainingSet.total_duration` (`duration * reps`, `None` without duration). Then
     `Movement.total_distance()` and `Movement.total_duration()` summing over sets that have one,
     `None` if none do. Pint adds compatible length units, so mixed units sum correctly.
   - `tests/test_data.py`, using the golden values from the Intent table (hand-computed, not taken
     from the code): `3x6 50yd` → 900yd; `3x5 PT30S` → 450s; `PT45S 3x1` → 135s; `run: 5km PT25M`
     → 5km and 1500s; `100m/200m/400m` (no rep scheme) → 700m; a movement with no distance → `None`;
     mixed units, `run: 400m/0.25mi` → 802.336m (0.25mi = 402.336m exactly). Build the
     movements by parsing the line, so the tests also cover `process_details`' reps.
   - `docs/api-reference.md`: add the new properties/methods to the `TrainingSet` and `Movement`
     lists.
   - Close-out: delete TODO #7 from `docs/work/TODO.md`; add a line to the unreleased section of
     `CHANGELOG.md` (create it if no other unit has).
   - `uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest`.

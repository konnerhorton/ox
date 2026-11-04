# srpe-guard: reject a session sRPE rating without a duration

Resolves TODO #2.

## Intent

### Goal
`TrainingSession` refuses, at construction, any combination of sRPE fields that can't be written
back as a valid `srpe:` line. A rating and a duration come together or not at all, and a note
needs both.

### Why
- A session built in code (by a plugin) with `srpe_rating=5, srpe_duration=None` builds fine and
  then crashes later in `to_ox()` at `format_iso_duration(None)`, far from the mistake.
- The grammar requires `srpe: <rating> <duration> ["note"]`, so the dataclass should accept only
  what the format can express. Failing at construction points at the code that made the bad
  session.
- `db.py` would also store a rating with a NULL duration, and the `srpe` plugin would silently
  skip that row (`WHERE ... srpe_duration_seconds IS NOT NULL`).

### Constraints
- The parser must never trip the check. `get_srpe` (`src/ox/parse.py`) already returns either all
  `None` or a rating with a duration, so parsed logs are unaffected.
- No range check on the rating. An out-of-range rating (e.g. `srpe: 11 PT45M`) parses and gets a
  lint *warning* (`_srpe_out_of_range`), so raising on it would break loading a log that lint
  only warns about.

### Out of scope
- Validating `srpe_rating` (range, type) or `srpe_duration` (positive) beyond the pairing rule.
- Similar checks on other dataclasses.

### SPEC sections touched
- None. Only `CHANGELOG.md` changes, since plugin authors can now get a `ValueError` they didn't
  get before.

## Plan

One build commit, then close-out in the same commit.

1. **`srpe-guard: require sRPE rating and duration together` (Sonnet)**
   - `src/ox/data.py`: add `TrainingSession.__post_init__` that raises `ValueError` when exactly
     one of `srpe_rating` / `srpe_duration` is `None` ("srpe_rating and srpe_duration must be
     given together"), or when `srpe_note` is set without them ("srpe_note requires srpe_rating
     and srpe_duration"). Add a `Raises:` section to the class docstring stating the rule.
   - `tests/test_data.py`, next to the existing sRPE tests (~line 454): rating without duration
     raises; duration without rating raises; note without rating/duration raises; rating +
     duration, and rating + duration + note, still build and serialize (the existing
     `test_emits_srpe_line*` tests cover the output).
   - Check that nothing else builds a bad combination: `uv run pytest` must pass unchanged
     (includes parsing `examples/advanced.ox`, which has sRPE lines).
   - Close-out: delete TODO #2 from `docs/work/TODO.md`; add an unreleased section at the top of
     `CHANGELOG.md` (v0.6.1 is tagged) with a one-line entry.
   - `uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest`.

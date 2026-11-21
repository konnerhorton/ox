# time-windows: limit plugin output to a time window with `--since` and `--until`

## Intent

### Goal
Plugins that report over time take two shared flags, `--since` and `--until`, that limit their output to a window:
`volume -m squat --since 8w`, `srpe --since 3m`, `weighin --since 2026-01-01`, and for a past block
`e1rm -m squat --since 2025-01-01 --until 2025-12-31`. Parsing the values and turning them into start and end dates
is one helper in `ox.sql_utils`, so builtins and user plugins accept the same spellings and behave the same at the
boundaries.

### Why
- Every time-based builtin (`volume`, `e1rm`, `srpe`, `weighin`) reports the whole log. The author's log covers about
  two years and 600+ sessions, so a weekly `volume` or `srpe` table is mostly history; seeing the last two months
  means scrolling or writing SQL with `query`.
- Looking back is just as common as looking at the recent past ("what did I do last year?"), and with no end bound
  it still means writing SQL.
- The units after this one need windows too (`repl-summary` decision 13): `movements` counts over a short and a long
  window (decision 10), the `srpe` load output compares the last 7 days to a recent average (decision 8), and the
  summary's panels are commands with windowed args (`srpe -o acwr --since 4w`). Doing it once here means one
  spelling and one boundary rule rather than one per plugin.

### Constraints
- **A panel is a command you could type** (`repl-summary` constraint): the window is ordinary plugin flags parsed
  by `parse_plugin_args`, not a REPL setting or global state.
- **Plugin flags** (CLAUDE.md conventions): param `name`s are Python identifiers, flags are `--since` and `--until`;
  no new `PluginContext` field (`PluginContext(db, log)` stays as is).
- **No new dependencies.**
- **User plugins get it for free:** the helper is public in `ox.sql_utils` and documented in `docs/plugins.md`
  "Helpers", next to `time_bin_expr`.
- **Not breaking:** with neither flag, every plugin's output is unchanged.

### Out of scope
- Calendar-aligned windows ("this week so far", "this month") and short forms for them (`--since 2025` for a whole
  year). The scaled short week of `repl-summary` decision 8 belongs to the `srpe` load unit.
- `wendler531 --start-date`: it sets a cycle's start, not a reporting window, and keeps its name.
- `weighin --window`: that is a rolling-average length in days, not a filter, and keeps its name.
- `formats`: reports a vocabulary, not a time series.
- The new plugins (`movements`, `mix`, `progress`): they adopt the helper in their own units.

### SPEC sections touched
- "Plugins": a new bullet, the shared `--since`/`--until` window and its rules (below), so later plugins follow it.
- `docs/plugins.md` "Helpers" and each adopting builtin's docs; `CHANGELOG.md` Unreleased.

### Decisions
1. **Spellings:** a count and a unit, `d` `w` `m` `y` (`30d`, `8w`, `6m`, `1y`), or an ISO date (`2026-01-01`).
   Nothing else: no ISO 8601 durations (`P8W`).
2. **Anchored to today, not the last entry.** `8w` means the 56 days ending today, so a log that has gone quiet
   shows a short or empty window rather than an old one that looks current; that is what staleness panels need. The
   helper takes `today` as an argument (default `date.today()`) so tests fix it.
3. **Inclusive, counting today:** `--since 7d` keeps dates from today − 6 to today, matching `weighin`'s rolling
   average `[D − (n − 1), D]`. `m` and `y` are calendar months and years back from today (2026-11-19 `3m` →
   2026-08-20), clamped at month end.
4. **The window filters what is shown, not what is computed.** Rolling outputs (`srpe -o acwr`, `weighin -w 7`)
   still use the days before the start, so the first row in the window has the same value as without `--since`. A
   binned output (`volume`, weekly) keeps the bins that hold the start and the end, so the first and last bins may
   be partial.
5. **Which builtins adopt it here:** `volume`, `e1rm`, `srpe`, `weighin`. Short flags `-s` and `-u` where free.
6. **Shared param dicts,** e.g. `SINCE_PARAM` and `UNTIL_PARAM` in `ox.sql_utils`, so every plugin declares the
   flags identically (short flag, type, default) and a user plugin adds them with one line each.
7. **Bad values fail like any bad flag:** `--since 8x` raises `ValueError` with the accepted spellings, through
   the same path as an unknown flag. So does a window whose start is after its end.
8. **`--until`, the end bound:** inclusive (`--until 2025-12-31` keeps Dec 31), takes the same spellings as
   `--since` with relative values also counted back from today (`--since 2y --until 1y` is the year that ended a
   year ago), and either flag works alone (`--until 2025-06-30` is everything up to that date). `since <= until` is
   enforced (decision 7).

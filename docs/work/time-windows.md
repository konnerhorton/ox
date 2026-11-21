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

## Spec

### Changes
- **`src/ox/sql_utils.py`:**
  - `Window`, a frozen dataclass (`slots=True`): `start: date | None`, `end: date | None`, both inclusive, `None`
    meaning unbounded. `contains(d)` takes a `date` or an ISO string and returns whether it falls in the window.
    `sql(col="date")` returns `(clause, params)` for a `WHERE`: `"{col} >= ? AND {col} <= ?"` with the bounds that
    are set as ISO strings, or `"1 = 1"` and `()` when neither is.
  - `time_window(since=None, until=None, today=None) -> Window`: parses both values (rules below), `today`
    defaulting to `date.today()`. Raises `ValueError` for a bad value or a start after the end.
  - `SINCE_PARAM = {"name": "since", "type": str, "default": None, "required": False, "short": "s"}` and
    `UNTIL_PARAM = {"name": "until", "type": str, "default": None, "required": False}`. The values reach the plugin
    as strings; the plugin calls `time_window(since, until)`, so a bad value raises inside the plugin call, which
    `cli.py` already catches with flag errors (one `except ValueError`, red message).
  - The module docstring lists the new names.
- **`src/ox/builtins/volume.py`, `e1rm.py`:** add `since=None, until=None` and both params; `window.sql()` joins
  the query's `WHERE`.
- **`src/ox/builtins/srpe.py`:** add both. `table`, `plot`, `monotony` and `strain` filter the extracted rows by
  the window before grouping. `acwr` computes over every row, then keeps the rows the window contains.
- **`src/ox/builtins/weighin.py`:** add both. `table` and the plot's points keep the rows in the window. The plot's
  rolling average is computed over every row, then filtered. `stats` aggregates the rows in the window (its count,
  min, max, average and trend are of the window; `current` is the last weigh-in in it). "Not enough data to plot"
  is checked after filtering.
- **`docs/plugins.md`:** each of the four builtins documents `--since`/`--until` with one example; "Helpers"
  documents `time_window`, `Window`, `SINCE_PARAM` and `UNTIL_PARAM`, and the `tonnage` example gains a window.
- **`SPEC.md`** "Plugins" (changed in this commit): a new bullet, below.
- **`CHANGELOG.md`** Unreleased: `--since` and `--until` on `volume`, `e1rm`, `srpe` and `weighin`; `time_window`
  for user plugins.

### Decisions
1. **A relative value names a boundary N units before today; `--since` starts the day after it, `--until` ends on
   it.** So `--since 7d` is today − 6 to today (intent decision 3), and `--since 2y --until 1y` covers 365 or 366 days
   with no gap or overlap against `--since 1y`. Adjacent windows tile.
2. **Units:** `d` days, `w` 7 days, `m` calendar months, `y` calendar years. Months and years step back by
   calendar and clamp to the last day of a shorter month (2026-03-31 − 1m = 2026-02-28; 2028-02-29 − 1y =
   2027-02-28). Lowercase only. The count is a whole number of at least 1: `0d` is an error, since it would make an
   empty `--since` window.
3. **ISO dates are exactly `YYYY-MM-DD`** and must be real dates (`2026-02-30` is an error). Python's
   `date.fromisoformat` alone would also accept `20260101` and `2026-W01-1`. Dates in the future are allowed: an
   empty window, not an error.
4. **`start == end` is allowed** (one day). A start after the end raises `ValueError`.
5. **Error messages** name the flag and the accepted forms:
   `--since: '8x' isn't a window. Use a count and unit (30d, 8w, 6m, 1y) or a date (2026-01-01)`, and
   `--since 2026-02-01 is after --until 2026-01-01`. The flags appear as `--since`/`--until` because they are only
   ever passed by those names.
6. **`--until` has no short flag.** `-u` is `--unit` in `volume`, `e1rm` and `weighin`. A short flag for only some
   plugins would contradict one shared `UNTIL_PARAM`, and `--until` is the rarer flag. `-s` is free in all four.
7. **The parsing stays in the plugin, not in the param's `type`.** A `type` that turns `8w` into a date would
   evaluate `today` when the args are parsed, which is the same thing, but plugins would then get `date`s from some
   flags and strings from others, and tests couldn't fix `today`. Plugins call `time_window` with the strings.
8. **Empty windows** give each output's existing empty result (an empty table, or the plot's "No ... data found."
   message), not an error.

### SPEC.md bullet (Plugins)
- **Time windows are two shared flags.** A plugin that reports over time takes `--since` and `--until`
  (`time_window` in `ox.sql_utils`): a count and unit (`30d`, `8w`, `6m`, `1y`) counted back from today, or an ISO
  date; both ends inclusive. The window limits what's shown, not what's computed: rolling values still use earlier
  data, and bins at the edges may be partial.

### Acceptance criteria
Golden values use `today = 2026-11-19`, worked by hand from decisions 1–3.

1. **Relative `--since`:** `7d` → start 2026-11-13; `1d` → 2026-11-19; `8w` → 2026-09-25 (today − 55 days);
   `3m` → 2026-08-20; `1y` → 2025-11-20. End is `None` in each.
2. **Relative `--until`:** `7d` → end 2026-11-12; `1y` → 2025-11-19. `--since 2y --until 1y` → 2024-11-20 to
   2025-11-19.
3. **Month-end clamping:** with today 2026-03-31, `--since 1m` → 2026-03-01 and `--until 1m` → 2026-02-28; with
   today 2028-02-29, `--since 1y` → 2027-03-01.
4. **ISO dates:** `--since 2025-01-01 --until 2025-12-31` → exactly those bounds; `--until 2025-06-30` alone → start
   `None`.
5. **Bad values raise `ValueError` with decision 5's message:** `8x`, `8W`, `0d`, `-3d`, `8`, `w`, `20260101`,
   `2026-02-30`, `""`. A start after the end raises the second message; equal bounds don't.
6. **`Window`:** `contains` is true at both bounds and false one day outside each, for a `date` and for an ISO
   string; an unbounded window contains everything; `sql()` with one, both or neither bound gives the clause and
   params of the Changes section, and running it against `simple_db` selects the expected rows.
7. **`volume` and `e1rm`:** on a fixture log, `--since`/`--until` dates keep only the matching rows. A weekly
   `volume` with `--since` mid-week has a first row holding only that week's in-window days (partial bin kept).
8. **`srpe`:** `table` with `--since` mid-week has a partial first bin. For `acwr`, every row inside the window has
   the same acute, chronic, ACWR and zone as the same date without `--since`, and no row falls outside it.
9. **`weighin`:** `table` keeps only rows in the window; `stats` counts only them; the `-w 7` plot's rolling average
   for the first point in the window equals the unfiltered average for that date (checked through `_rolling_avg`
   applied to the filtered dates, not by reading the plot).
10. **Through the CLI:** `parse_plugin_args` accepts `-s 8w`, `--since 8w` and `--until 2025-12-31` for each of the
    four; `-u` still means `--unit`; `volume -m squat --since 8x` prints the red error, and the REPL carries on.
11. **No flags, no change:** each of the four, with neither flag, returns the same result as before on
    `example.ox` and `advanced.ox`.
12. **User plugins:** a fixture plugin that adds `SINCE_PARAM` and `UNTIL_PARAM` and calls `time_window` filters
    like the builtins; `docs/plugins.md`'s windowed `tonnage` example runs.
13. Full test suite and ruff pass.

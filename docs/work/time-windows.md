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

## Plan

Six build commits, all on Opus: the helper and its boundary rules come first, then one plugin per commit in rising
order of difficulty (SQL filters, then the outputs that compute over rows outside the window), then docs and
close-out. Steps 1–3 and 4–6 fit one session each; start a new session before step 4. Each commit passes
`uv run pytest` and `uv run ruff check src/ tests/`. The new tests live in `tests/test_time_windows.py`, except
where a step names another file.

Plugins call `time_window(since, until)` first, before any query or other validation, so a bad value fails before
any work. In `weighin` the `Window` can't be called `window` (that param is the rolling-average length): call it
`span` in every plugin, for one name throughout.

### 1. `time-windows: snapshot plugin output with no window` (Opus)
- `tests/data/no_window.json` (new): the output of the current code, before any plugin changes, on `example.ox` and
  `advanced.ox`: `volume -m <m>` (weekly and monthly), `e1rm -m <m>` (table and plot; a movement with `^rm` sets),
  `srpe` with each of its five outputs, `weighin` with `table`, `stats`, `plot` and `plot -w 7`. Tables as
  `[columns, rows]`, plots as their lines (plot sizes are fixed defaults in `ox.plot`, so lines are deterministic).
  Generated once from a scratch script run through `ox.cli.load_log` and `parse_plugin_args`, which isn't committed.
- `tests/test_time_windows.py` (new): `test_no_flags_unchanged`, parametrized over the snapshot's cases, runs each
  through `parse_plugin_args` and compares, JSON-normalised (tuples → lists).
- Tests: AC 11, held green by every later step. This is a characterization of existing output, not golden values
  for new behavior. 🟡 Proposed: delete the snapshot and its test in step 6, since later units (`srpe` load output,
  `progress`) change these outputs on purpose and shouldn't have to regenerate it; the commit history keeps the
  evidence. The alternative is keeping it as a general regression test.

### 2. `time-windows: add time_window and Window to sql_utils` (Opus)
- `src/ox/sql_utils.py`: `Window` (frozen, slots) with `contains` and `sql`; `time_window(since, until, today)`;
  `SINCE_PARAM`, `UNTIL_PARAM`; module docstring lists them.
  - Parsing: a strict regex for each form, `^([1-9]\d*)([dwmy])$` and `^\d{4}-\d{2}-\d{2}$`, then
    `date.fromisoformat` for the date (which rejects `2026-02-30`). Spec decision 3: the regex is what stops
    `20260101` and `2026-W01-1`.
  - A relative value gives a boundary `b` (today − N days/weeks, or calendar months/years back with month-end
    clamping, via a private `_months_back(d, n)`; years are `12n` months). `--since` → `b + 1 day`, `--until` → `b`
    (spec decision 1). An ISO date is the bound itself.
  - `_months_back` clamps with `calendar.monthrange` (stdlib; no new dependency).
  - Errors: spec decision 5's two messages, word for word. The flag name is passed in by `time_window`.
  - `sql(col)`: build the clause from the bounds that are set (`{col} >= ?`, `{col} <= ?`, joined by `AND`), or
    `"1 = 1"`, `()`. `col` is interpolated, like `time_bin_expr`'s; params are ISO strings.
- Tests: AC 1–4 as golden tables (today 2026-11-19, 2026-03-31, 2028-02-29); AC 5, one parametrized test over the
  nine bad values asserting the full message, plus start-after-end and equal bounds; AC 6, `contains` at and one
  day outside each bound for `date` and `str`, unbounded, and `sql()` for none/since/until/both, run against
  `simple_db` (`SELECT date FROM training WHERE …`, dates 2025-01-10/11/12) for the expected rows.

### 3. `time-windows: --since and --until on volume and e1rm` (Opus)
- `src/ox/builtins/volume.py`: `since=None, until=None`; `span.sql("date")` joins `WHERE movement_name = ?` with
  `AND`, its params appended. `SINCE_PARAM`, `UNTIL_PARAM` in `params`. Usage docstring gains `volume -m squat -s 8w`.
- `src/ox/builtins/e1rm.py`: the same, on `t.date`.
- Tests: AC 7, on `example.ox`: ISO `--since`/`--until` keep only the matching rows for each plugin; a weekly
  `volume` with `--since` on a mid-week date (pick a week with sessions on both sides of it) has a first row whose
  totals are only the in-window days, checked against a sum worked from the log's lines. AC 10 for these two: `-s
  8w`, `--since 8w`, `--until 2025-12-31` parse, `-u kg` still lands in `unit`; `run_plugin(ctx, "volume", "-m squat
  --since 8x")` returns normally and `capsys` holds the decision-5 message.

### 4. `time-windows: --since and --until on srpe` (Opus)
- `src/ox/builtins/srpe.py`: `srpe_report(ctx, bin, output, since=None, until=None)`. For `acwr`: `_acwr_report`
  over all of `data`, then keep the rows `span.contains(row[0])`. For every other output: filter `data` by the
  window first, then the existing code, so an empty window takes the existing empty branch ("No sRPE data
  found." for `plot`; spec decision 8). Monotony and strain bucket the filtered days, so their edge weeks are
  partial too, as the spec says for binned output.
- Tests: AC 8 on `advanced.ox` (8 weeks from 2025-01-06): `table` with a mid-week `--since` has a partial first bin
  (sessions and total AU worked from the log); `acwr` with `--since 2025-02-03` has exactly the unwindowed rows on
  or after that date, value for value, and none before. That date is 4 weeks in, so its acute and chronic values
  differ from recomputing over filtered data, and the test would catch filtering first. An empty window (a future
  `--since`) gives each output's empty result. AC 10 for `srpe`.

### 5. `time-windows: --since and --until on weighin` (Opus)
- `src/ox/builtins/weighin.py`: `weigh_in_report(ctx, unit, output, window, since=None, until=None)`. Convert all
  rows to `data` as now, then `shown = [r for r in data if span.contains(r[0])]`. The empty-result block moves
  below and tests `shown`, so an empty window gives the existing empty results. `table`, `stats`, and the plot's
  scatter series use `shown`; "Not enough data to plot" tests `len(shown)`. The rolling line comes from a new
  `_windowed_rolling_avg(data, window_days, span)`: `_rolling_avg` over all of `data`, then filtered.
- `tests/test_weighin.py`: AC 9 on `weigh_in_multi_scale_db`: `table` rows and `stats` counts are only the window's;
  `stats`' `current` is the last weigh-in in it. `_windowed_rolling_avg`'s first point equals `_rolling_avg(data)`
  at that date and differs from `_rolling_avg(shown)` there (choose a `--since` with weigh-ins in the 6 days before
  it, so the two differ). One weigh-in in the window gives "Not enough data to plot."; none gives "No weigh-in data
  found.". AC 10 for `weighin`, including `-w 7` still meaning `--window`.

### 6. `time-windows: document time windows, close out` (Opus)
- `docs/plugins.md`: `-s/--since` and `--until` rows and one example in each of the four builtins' sections;
  "Helpers" documents `time_window`, `Window` (`contains`, `sql`), `SINCE_PARAM`, `UNTIL_PARAM` and the boundary
  rules in brief; the `tonnage` example takes `since`/`until`, adds the two params, and joins `span.sql()` to its
  `WHERE`. `weighin`'s table gives `-w/--window`'s default as `0` (no rolling line), matching the code; it said `7`.
- Tests: AC 12: a fixture plugin in `tmp_path` that adds both params and calls `time_window` filters like `volume`,
  loaded through `@plugin` and `load_log`; a test extracts the `tonnage` code block from `docs/plugins.md`, writes it
  to `tmp_path`, loads it and runs it with `--since`, so the docs example can't rot. AC 13: the full suite and ruff.
- Close-out: `CHANGELOG.md` Unreleased entry (spec Changes); `STATUS.md` "Next" moves to the next `repl-summary`
  prerequisite and Done gains time windows; `CLAUDE.md` Project Structure's `sql_utils.py` line adds
  `time_window`; `SPEC.md` is already updated (spec commit). Step 1's snapshot goes, if the 🟡 above stands.

### Notes from the build
- Step 1: neither example log has `^rm` sets, so the `e1rm` snapshot cases run on a new `tests/data/rm_sets.ox`
  (squat and deadlift, Jan–Mar 2025, mixed units); step 3's `e1rm` tests use it too.
- Step 1: plots are snapshotted as the arguments each plugin passes to `ox.plot` (`scatter`, `bar`,
  `multi_series`, recorded by a monkeypatch in `tests/test_time_windows.py`), not as rendered lines. Plotext's
  bar-chart x-label decimation depends on `PYTHONHASHSEED`, so `srpe -o plot` renders differently across processes
  (TODO #18).
- Step 6: the 🟡 in step 1 stood, so the snapshot and `test_no_flags_unchanged` are deleted; AC 11 held through
  steps 2–5 (`b4eb775` is the last commit with it). `rm_sets.ox` and the `ox.plot` recorder stay for the window
  tests. `tests/test_time_windows.py` calls `load_plugins()` before looking up builtins, since other tests clear
  `PLUGINS` (now a `CLAUDE.md` note).

# public-helpers: make the shared helpers public (TODO #16, #17)

## Intent

### Goal
Helpers that other modules or user plugins import have public names. That covers the `sql_utils`
plugin helpers (TODO #17) and the movement index (TODO #16). The plugin helpers are documented in
`docs/plugins.md`.

### Why
- **#17:** `volume.py` imports `_weight_sql_expr` and `_time_bin_expr`, and user plugins are meant to
  use them too (`CLAUDE.md` calls them "Helpers for plugins"). `completion.py` imports `_flag_name`.
  The leading underscore says "private", and `docs/plugins.md` mentions none of them, so a plugin
  author has to find them by reading `volume.py`.
- **#16:** `completion._movement_index` is imported by `add.py`, `cli.py` and the tests. The parked
  `repl-summary` unit adds a `movements` builtin with a "last trained" column, which would make a
  fourth user.
- `STATUS.md` puts both items ahead of `repl-summary`, which adds builtins that use these helpers.

### Constraints
- **No behavior change.** This unit only renames and moves code and adds docs. Completion and
  `add` offer the same names, in the same order, with the same notes. Existing tests change only
  where they call the renamed or moved helpers.
- Data structures live in `data.py`, and tree-sitter handling lives in `parse.py` (`CLAUDE.md`
  conventions). A new return type for the index follows the frozen, `slots=True` dataclass
  convention.
- Plugin flag naming is unchanged: `name` with `_` → `-` (`CLAUDE.md` conventions).

### Out of scope
- The `movements` builtin and the rest of `repl-summary`. They stay on their parked branch, whose
  intent gets rewritten when it resumes (`STATUS.md` Open).
- Other private names imported across modules. Fix one only if this unit's changes touch it.
- Aliases or deprecation warnings for the old names (D2).

### SPEC sections touched
- None. `SPEC.md` has no section on the plugin API surface. The public helper names are documented
  in `docs/plugins.md`.
- Other docs: `docs/plugins.md` (a new "Helpers" section under "Writing a Plugin"), the `sql_utils`
  line in `CLAUDE.md`'s project structure, `CHANGELOG.md` Unreleased (the helpers become public),
  `STATUS.md` and `docs/work/TODO.md` (remove #16 and #17).

### Decisions (intent review, 2026-11-17)
1. **New names drop the underscore:** `weight_sql_expr`, `time_bin_expr` and `flag_name` stay in
   `sql_utils.py`; the movement index becomes `TrainingLog.movement_index()` (D3).
2. **No aliases for the old names.** The only user of ox plugins is the author, so there are no
   outside plugins to keep working. Every caller is updated here, and the old names are gone.
   This replaces the "Don't break user plugins" concern, and TODO #17's "keeping the old names as
   aliases".
3. **The movement index becomes a `TrainingLog` method.** `TrainingLog.movement_index()` in
   `data.py`, next to `movement_history` and `most_recent_session`. It returns frozen
   `MovementIndexEntry(name, last: date | None, status)` rows in the current order, where status
   is `trained`, `planned` or `defined`, and `completion.py` builds its note from them. The
   `(name, note)` string pairs only suited completion, so a later caller gets real dates. The
   parked `repl-summary` spec (D9) computes `last` in the `movements` builtin's own SQL
   `GROUP BY`, so that panel may not need the index after all. Its rewritten intent decides that.
   The index moves anyway, because `add.py` and `cli.py` import it and it isn't about completion.
   Rejected: a plain rename in `completion.py`, which keeps the completion-only shape; and
   dropping #16, which leaves a private name imported across modules.

## Spec

### Changes
- **`src/ox/sql_utils.py`:** `_weight_sql_expr` → `weight_sql_expr`, `_time_bin_expr` →
  `time_bin_expr`, `_flag_name` → `flag_name`. Signatures, SQL and errors are unchanged. The module
  docstring names the helpers plugins may use.
- **`src/ox/data.py`:** new `MovementIndexEntry` and `TrainingLog.movement_index()` (D1–D3 below).
- **`src/ox/completion.py`:** `_movement_index` and `movement_names` are removed. `ReplCompleter`
  and `MovementLineCompleter` take `list[MovementIndexEntry]` instead of `(name, note)` pairs and
  build each note with a private `_movement_note(entry)`. It imports `flag_name`.
- **`src/ox/cli.py`, `src/ox/add.py`:** pass `log.movement_index()` to the completers.
- **`src/ox/builtins/volume.py`:** imports the new names.
- **Tests:** `test_reports.py` and `test_completion.py` use the new names. `test_movement_names_order`
  becomes a `movement_index` test (AC 1).
- **`docs/plugins.md`:** a new `### Helpers` section under "Writing a Plugin" documents
  `weight_sql_expr` and `time_bin_expr`, with a short example plugin that uses both (D6).
- **`CLAUDE.md`:** the `sql_utils.py` line in Project Structure lists the new names.
- **`CHANGELOG.md`** Unreleased: one entry saying the two helpers are documented and renamed.
- **`STATUS.md`:** "Next" stops pointing at #16 and #17. **`docs/work/TODO.md`:** #16 and #17 are
  removed.

### Decisions
1. **`MovementIndexEntry`** is a frozen, `slots=True` dataclass in `data.py` with the fields
   `name: str`, `last: date | None` and `status: Literal["trained", "planned", "defined"]`.
   `last` is the date of the latest completed session that has the movement, and it is set exactly
   when `status` is `trained`.
2. **`TrainingLog.movement_index() -> list[MovementIndexEntry]`** keeps today's rules. A movement
   in any completed session is `trained`, even if it also appears in a planned session or an
   `@movement` block. Of the rest, one in a planned session is `planned`, and one only in an
   `@movement` block is `defined`. The order is trained entries by `last` descending, ties by
   name, then the rest by name.
3. **The note format stays in `completion.py`.** `_movement_note` returns the ISO date for
   `trained` and the status word otherwise, which are exactly today's notes. Display wording is
   completion's concern, not the data layer's.
4. **`movement_names` is removed, not moved.** Its only caller is a test, and
   `[e.name for e in log.movement_index()]` replaces it in one line.
5. **`flag_name` gets a public name but no docs.** It is the flag-spelling rule that
   `parse_plugin_args` and completion share, and plugins never need to call it. The rule itself is
   already documented under "Parameter".
6. **The helper docs say what each helper covers.** `weight_sql_expr` converts the units stored
   in the DB, `kilogram` and `pound`, and passes any other stored unit through unconverted. A
   target unit Pint doesn't know raises `ValueError`; a non-mass one (`meter`) raises Pint's
   `DimensionalityError`, as today: this unit renames, it doesn't change errors. `time_bin_expr` takes a bin name from
   `TIME_BINS` (`daily`, `weekly`, `weekly-num`, `monthly`) and raises `ValueError` for any other.

### Acceptance criteria
1. **Index golden values:** on `test_completion.py`'s `FIXTURE`, `log.movement_index()` returns
   `squat` (2025-01-08, trained), `bench-press` (2025-01-03, trained), `deadlift` (None, planned)
   and `front-squat` (None, defined), in that order. `squat` is also in the planned session, and
   it still counts as trained. These values come from reading the fixture: squat was last completed
   on 01-08, bench-press on 01-03, deadlift appears only in the `completed: false` session, and
   front-squat only in `@movement`.
2. **Index tie order:** two movements last trained on the same date are listed by name.
3. **Completion unchanged:** every existing completion and `add` test passes with its expected
   names, order and notes unchanged. In particular, the movement notes are `2025-01-08`,
   `2025-01-03`, `planned` and `defined`.
4. **Helpers unchanged:** the existing `time_bin_expr` tests pass under the new name, including
   the `ValueError` for `yearly`. `weight_sql_expr("x", "y", "blorp")` raises `ValueError`
   naming the unit. `volume` output on `examples/example.ox` is the same before and
   after.
5. **Old names gone:** `grep -rnE '_weight_sql_expr|_time_bin_expr|_flag_name|_movement_index|movement_names'`
   over `src/ tests/ docs/*.md CLAUDE.md examples/` finds nothing. Merged work files under
   `docs/work/` are history and are left as they are.
6. **Docs example runs:** the example plugin in `docs/plugins.md`'s Helpers section, loaded with
   `@plugin` against `examples/example.ox`, returns a table without error. This is checked by hand
   at the test step.

## Plan

Three commits, each with `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/` and
`uv run pytest` green. Steps 1 and 2 are refactors with no behavior change. Step 3 is docs and
close-out. Steps 1 and 2 run in one Sonnet session; start a new Opus session for step 3.

### 1. `public-helpers: make the sql_utils plugin helpers public` (Sonnet)
- `src/ox/sql_utils.py`: rename `_weight_sql_expr` → `weight_sql_expr`, `_time_bin_expr` →
  `time_bin_expr`, `_flag_name` → `flag_name`, including the internal calls in
  `parse_plugin_args` and `plugin_usage`. The module docstring lists `parse_plugin_args`,
  `plugin_usage`, `weight_sql_expr` and `time_bin_expr` as the helpers plugins may use.
- `src/ox/builtins/volume.py`, `src/ox/completion.py`: import the new names.
- `tests/test_reports.py`: `TestTimeBins` uses `time_bin_expr`. Add a `TestWeightSqlExpr`
  covering `weight_sql_expr("x", "y", "blorp")` → `ValueError` matching `blorp` (AC 4).
  `test_volume_values` stays as it is and proves `volume` output is unchanged (AC 4).

### 2. `public-helpers: move the movement index to TrainingLog` (Sonnet)
- `src/ox/data.py`: add `MovementIndexEntry` (frozen, `slots=True`; `status` typed with
  `Literal`) before `TrainingLog`. Add `TrainingLog.movement_index()`, moved from
  `completion._movement_index` with the rules in Spec D2, comparing `date`s instead of ISO strings.
  Its docstring states the status rules and the order.
- `src/ox/completion.py`: delete `_movement_index` and `movement_names`. Add
  `_movement_note(entry) -> str` (Spec D3). `ReplCompleter.__init__` and
  `MovementLineCompleter.__init__` take `list[MovementIndexEntry]` and build the note with
  `_movement_note`. Update the docstring that mentions `_movement_index`.
- `src/ox/cli.py` (`build_completer`), `src/ox/add.py` (the `MovementLineCompleter` call): pass
  `log.movement_index()` and drop the `_movement_index` import.
- `tests/test_completion.py`: the three completer constructions pass `log.movement_index()`.
  Replace `test_movement_names_order` with `test_movement_index`, which asserts the four entries
  of AC 1 field by field. Add `test_movement_index_tie_order`: two movements completed on the
  same date are listed by name (AC 2). The existing completion and `add` tests stay unchanged and
  prove AC 3. `tests/test_add.py` and `tests/test_cli_add.py` need no changes unless they import
  the old name.

### 3. `public-helpers: document the plugin helpers, close out` (Opus)
- `docs/plugins.md`: add `### Helpers` after "Descriptor fields" covering
  `from ox.sql_utils import weight_sql_expr, time_bin_expr`, each helper's arguments, what it
  covers and its errors (Spec D6), and a short example plugin: weekly volume in a chosen unit
  that uses both helpers.
- AC 6, by hand: write that example to the scratchpad, load it with `@plugin` from a copy of
  `examples/example.ox`, and run it. It returns a table without error.
- AC 5: run the grep from AC 5 and get no output.
- Close-out:
  - `CLAUDE.md`: the `sql_utils.py` line lists `weight_sql_expr` and `time_bin_expr`.
  - `CHANGELOG.md` Unreleased: an entry saying plugins can import `weight_sql_expr` and
    `time_bin_expr` from `ox.sql_utils`, now documented, and that the underscore names are gone.
  - `STATUS.md`: "Next" no longer points at #16 and #17, and the `repl-summary` line drops
    "TODO #16 and #17 come first".
  - `docs/work/TODO.md`: delete #16 and #17. Decisions that need a permanent home go in the
    docs above, not `SPEC.md` (intent: no SPEC section touched).
  - Ask whether to run `project-checkpoint`: the last checkpoint was after `micro-syntax`, two
    units back.

### Notes from the build
- All three steps ran on Opus in one session, at the user's request, not Sonnet for steps 1 and 2.
- AC 4 and AC 6 were checked with a script calling `load_log` and the plugin function, since the REPL
  ignores piped stdin. `volume` output on `examples/example.ox` (three flag sets) matched HEAD~ exactly.
- AC 5's pattern has no word boundaries and also matches unrelated names (`lsp._collect_movement_names`,
  `test_movement_index`, a local `movement_names` in `test_integration.py`). With `grep -w`, the only hit is
  that local variable, so no old name remains.

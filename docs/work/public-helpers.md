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

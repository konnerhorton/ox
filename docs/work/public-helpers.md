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

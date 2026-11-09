# repl-completion: complete movement names and plugin flags in the REPL

First of two units for TODO #10 (`add`); `repl-add` follows and reuses this completer.
`repl-summary` is on hold (intent and spec committed on its branch, not merged).

## Intent

### Goal
Tab completion in the `ox>` prompt knows where the cursor is: the first word completes commands
and plugin names, the words after a plugin name complete that plugin's flags, and the value after
a movement flag (`-m`, `--movement`) completes movement names from the loaded log. The movement
part is a reusable piece that `add` uses to complete the start of each movement line.

### Why
- SPEC "What's incomplete" lists "CLI movement autocompletion (tab-complete movement names, not
  just commands)". Today `cli.py` builds one flat `WordCompleter` over commands and plugin names,
  so `volume -m sq<Tab>` offers nothing, and a misspelled movement just returns an empty table.
- `add` (TODO #10) needs movement completion on every line it prompts for. Building and testing
  the completer on its own keeps `repl-add` focused on the write path.
- Movement names are long and hyphenated (`kb-oh-press`, `bench-press`), and the log is the only
  place that defines them. That makes them the most useful thing to complete.

### Constraints
- **No new dependencies.** `prompt_toolkit` (already used) supplies the `Completer` API.
- **Driven by plugin metadata, not a list of plugin names.** A plugin's flags come from its
  `params` (long flag = `name` with `_` → `-`, plus `short`), the same rules `parse_plugin_args`
  uses (CLAUDE.md conventions). User plugins get completion with no changes to them.
- **Movement names come from the loaded log**, the same set the LSP offers: every movement in
  sessions, single-line entries and templates, plus `@movement` definitions. `reload` refreshes it.
- **Completion only suggests.** Typing a name the log doesn't contain still works as it does now.

### Out of scope
- The `add` command, prefill, and anything that writes to the log (`repl-add`, next unit).
- Fuzzy matching. Completion matches prefixes, case-insensitively, like now.
- Completing values other than movement names and stored query names (dates, units, `-o` choices).
- Changes to the LSP's completion.

### SPEC sections touched
- "What works today": the CLI bullet's "tab completion" covers flags and movement names.
- "What's incomplete": the "CLI movement autocompletion" bullet is removed.
- `docs/cli-reference.md`: describes what Tab completes.

### Decisions (intent review, 2026-11-09)
1. **Two units: `repl-completion`, then `repl-add`.** Each fits in one review, and the completer
   can be tested without a write path. A single unit was considered and rejected as too large.
2. **`add` doesn't wait for the REPL overhaul.** TODO #10 said its UI depends on the
   dashboard-style REPL; with `repl-summary` on hold, `add` runs in the plain prompt as guided
   prompts (date, name, one movement line per prompt, preview, confirm).
3. **`repl-add` includes both prefill levels from TODO #10:** a movement line gets that movement's
   last weight and reps, and a session name already used prefills every movement from its most
   recent instance.

### Open questions (🟡 Proposed)
1. 🟡 **What makes a flag a movement flag.** Any param named `movement` (all three current
   movement params are named that). The alternative, a `"complete": "movement"` key in the param
   dict, is more explicit but needs every plugin to change. Proposed: the name, for now.
2. 🟡 **Order of movement suggestions.** Most recently trained first, so the lifts you're doing now
   come before ones you stopped training. The alternative is alphabetical, like the LSP. Recency
   matters more for `add`.
3. 🟡 **`query <Tab>` completes stored query names.** Cheap, uses the same mechanism, and it's
   the other place where a name from the log gets typed at the prompt.
4. 🟡 **Shared source of names.** One function, used by both the REPL and the LSP, that returns
   movement names from a parsed `TrainingLog`. The LSP could keep its tree walk (it completes
   in files that may not parse fully), so this may stay REPL-only.

## Spec

### Changes
- **`src/ox/completion.py` (new):** `movement_names(log)` (the reusable source of names, also for
  `repl-add`) and `ReplCompleter`, a `prompt_toolkit` `Completer` built from the command list, the
  plugin registry, movement names and stored query names.
- **`src/ox/cli.py`:** startup and `reload` build the completer with one helper in place of the
  two copies of the command list; the flat `WordCompleter` is removed.
- **`docs/cli-reference.md`:** the Tab row and a short "Tab completion" section say what completes where.

### Decisions
1. **Movement params are named `movement` or `movements`.** These are the three current ones:
   `volume` and `e1rm` (`movement`), `wendler531` (`movements`, e.g. `squat:315,deadlift:405`).
   The value after `-m`/`--movement`/`--movements` (whichever flags the param has) completes movement names. A
   `"complete"` key in the param dict was considered and rejected for now: it needs every plugin to
   change, and the naming convention covers every case today. (Resolves open question 1.)
2. **Lists are completed per item.** In a movement value, only the text after the last `,` is
   completed, so `-m squat:315,dead<Tab>` offers `deadlift`. If that text contains `:` (a value is
   being typed), nothing is offered.
3. **Names come from the parsed log:** movements in every session (completed, planned, single-line
   entries) and `@movement` definitions. `@template` blocks are not in `TrainingLog` (SPEC "What's
   incomplete"), so names that appear only in templates aren't offered. The LSP keeps its own
   tree walk because it has to work on files that don't parse fully. (Resolves open question 4: REPL only.)
4. **Order: most recently trained first.** Names are ordered by their latest *completed* session
   date, newest first. Names with no completed session (only planned, or only defined) follow,
   alphabetically. Ties are broken by name. Planned dates don't count, because a future-dated plan
   would otherwise always come first. (Resolves open question 2.)
5. **What completes where.** The cursor's position is worked out from the text before it, split on
   whitespace:
   - First word: commands and plugin names, the same list as today.
   - After a plugin name, a word starting with `-`: that plugin's long flags (`--` + name with
     `_` → `-`), skipping flags already used on the line. Short flags aren't offered; they are one
     letter and shown in `plugins`.
   - The word right after one of a plugin's movement flags (short or long): movement names (D1, D2).
   - The second word after `query`: stored query names. (Resolves open question 3.)
   - Anywhere else: nothing. This is a change: today the flat completer offers command names in
     any position, e.g. after `volume -m`.
6. **Matching is a case-insensitive prefix match**, as now. An empty prefix offers everything that
   fits that position.
7. **Completions carry a short note** (`display_meta`, shown dim beside each suggestion in the menu):
   - movement: date last trained, `planned` (no completed session), or `defined` (only an `@movement` block)
   - flag: `required` or `default: <value>`
   - stored query: nothing
8. **Rebuilt on `reload`**, so new movements, plugins and queries show up.

### Acceptance criteria
Fixture: squat completed on 2025-01-01 and 2025-01-08, bench-press completed on 2025-01-03, a
planned session on 2025-02-01 with deadlift and squat, an `@movement front-squat` block with no
sessions, and a stored query `recent`.

1. **Names and order:** `movement_names(log)` returns `squat, bench-press, deadlift, front-squat`.
2. **First word:** `vo` completes to `volume`; an empty line offers every command and plugin.
3. **Flags:** `volume --` offers `--movement`, `--bin`, `--unit`; `volume -m squat --` offers
   `--bin`, `--unit`. The `--bin` note reads `default: weekly`; `--movement` reads `required`.
4. **Movement value:** `volume -m ` offers the four names in order (AC 1); `e1rm --movement s`
   offers `squat`; the notes read `2025-01-08`, `2025-01-03`, `planned`, `defined`.
5. **Lists:** `wendler531 -m squat:315,de` offers `deadlift`; `wendler531 -m squat:3` offers nothing.
6. **Queries:** `query r` offers `recent`; `query SELECT * FROM r` offers nothing.
7. **Nothing elsewhere:** `volume -m squat --bin w`, `tables `, and `bogus -m ` offer nothing.
8. **User plugins:** a user plugin registered with a `movement` param gets movement completion
   with no change to the plugin.
9. **Case:** `volume -m SQ` offers `squat`.
10. **Reload:** after a movement is added to the file, `reload` makes it completable (checked by
    building the completer from the reloaded log, as `reload` does).
11. **No regressions:** existing REPL commands behave as before; full test suite and ruff pass.

## Plan

Context: implements `## Spec` above (D1–D8, AC 1–11). This is a small unit, so the whole build
is one Sonnet session, and an Opus session closes it.

### Step 1 (Sonnet): `repl-completion: add movement_names and ReplCompleter`
Files: `src/ox/completion.py` (new), `tests/test_completion.py` (new).

- `_movement_index(log) -> list[tuple[str, str]]`: `(name, note)` pairs in D4 order.
  - Collect names from `log.sessions` (all sessions) and `log.movement_definitions`.
  - For each name, take its latest completed `session.date`.
  - Note: the ISO date if trained; `planned` if it appears only in planned sessions; `defined` if
    it appears only in `@movement`.
  - Sort trained names by date descending, then name; the rest follow, sorted by name.
- `movement_names(log) -> list[str]`: the names from `_movement_index`, the public helper `repl-add` reuses.
- `ReplCompleter(Completer)`, built as `ReplCompleter(commands, plugins, movements, queries)`:
  - `plugins`: a `dict[str, dict]` shaped like `PLUGINS`, passed in rather than read from the
    global so tests can use a fake user plugin (AC 8).
  - `movements`: the `(name, note)` pairs.
  - `get_completions(document, event)` takes `words = text_before_cursor.split()` and appends
    `""` when the text is empty or ends in whitespace. `word = words[-1]`.
    - `len(words) == 1` → commands whose lowercase starts with `word.lower()`.
    - `words[0] == "query"` and `len(words) == 2` → query names.
    - `words[0]` in `plugins`, with params `ps`:
      - The previous word is a movement flag: `-{short}` or `--{_flag_name(p)}` (reuse
        `ox.sql_utils._flag_name`) of a param named `movement` or `movements`. Complete
        `seg = word.rsplit(",", 1)[-1]`; nothing if `":" in seg`; `start_position=-len(seg)`.
      - Otherwise, a word starting with `-` → long flags `--{_flag_name(p)}`, leaving out any
        param whose short or long flag already appears in `words[1:-1]`.
      - Flag note: `required` if `p.get("required")`; else `default: {p['default']}`, or
        `optional` when the default is `None` (e.g. `wendler531 --start-date`).
    - Anything else → nothing.
  - Each suggestion is `Completion(text, start_position=-len(prefix), display_meta=note)`.
- Tests: one fixture log as text, written to `tmp_path` and loaded with `ox.cli.parse_file`: the
  spec's fixture (squat 2025-01-01 / 2025-01-08, bench-press 2025-01-03, planned 2025-02-01
  deadlift + squat, `@movement front-squat`, stored query `recent`).
  - Build the completer with `PLUGINS` after `load_plugins()`; for AC 8, a dict with a fake
    plugin entry.
  - Helper: `complete(c, text) -> list[(text, meta)]` via `Document(text)` + `CompleteEvent()`.
  - Proves AC 1–9.

### Step 2 (Sonnet): `repl-completion: use ReplCompleter in the REPL`
Files: `src/ox/cli.py`, `tests/test_completion.py`.

- Add a module constant `REPL_COMMANDS` (the eight names now listed twice) and
  `build_completer(log) -> ReplCompleter`, which combines it with `PLUGINS`,
  `_movement_index(log)` and `[q.name for q in log.queries]`.
- Startup: `PromptSession(completer=build_completer(log))`. `reload`:
  `session.completer = build_completer(log)`. Drop the `WordCompleter` import.
- Test AC 10: write the fixture, build, append a `2025-01-09 T kb-swing: 24kg 5x10` line,
  `parse_file` again, build again → `volume -m kb` offers `kb-swing`. Also check that `build_completer` offers
  every `REPL_COMMANDS` entry on an empty line (AC 11, since `help`, `exit` etc. stay completable).

### Step 3 (Sonnet): `repl-completion: document tab completion`
Files: `docs/cli-reference.md`, `SPEC.md`, `CLAUDE.md`.

- `docs/cli-reference.md`: change the Tab row to "Auto-complete commands, plugin flags, movement
  names and stored queries", and add a short "Tab completion" section listing the D5 positions,
  the order of movement suggestions (D4), and the convention that a plugin param named
  `movement`/`movements` gets movement completion (also add a line to `docs/plugins.md` where
  params are documented).
- `SPEC.md`: in "What works today", the CLI bullet says the completion is context-aware
  (movement names, flags, stored queries); remove the "CLI movement autocompletion" bullet from
  "What's incomplete".
- `CLAUDE.md`: add `completion.py` to Project Structure and `test_completion.py` to tests; add
  the movement/movements param-name convention under Conventions.
- `docs/work/TODO.md` #10: rewrite the "depends on the REPL overhaul" sentence to point at
  `repl-add` and the intent's D2–D3 (guided prompts, both prefill levels, movement completion done).

### Close (Opus, new session)
- Run `uv run pytest` and `uv run ruff check src/ tests/`.
- Use `ReplCompleter` built from `examples/advanced.ox` in a short script to print completions
  for `volume -m `, `e1rm --`, `query `, and look at the order and notes by eye.
- Run `ox examples/advanced.ox` interactively once (the user, or `! ox …`) to see the menu
  rendering.
- Report each AC as met or not, then merge `--no-ff` into `main` after approval.

### Verification
- `uv run pytest tests/test_completion.py` after each step; full suite + ruff before each commit.

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

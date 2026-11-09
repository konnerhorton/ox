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

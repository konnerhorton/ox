# repl-add: append a session to the log from the REPL

## Intent

### Goal
`add` at the `ox>` prompt walks through a session (date, name, format, one movement line per
prompt, srpe, note), shows the result as `.ox` text, and on confirmation appends it to the log file
and reloads. Lines come prefilled from history: a movement gets its last recorded weight and reps, and a session name
already used prefills every movement from that session's most recent instance.

### Why
- TODO #10. Today logging means opening an editor, finding the end of the file, and retyping
  yesterday's numbers. Most sessions repeat a previous one with small changes, and the log already
  knows what those were.
- `repl-completion` built the reusable pieces: `movement_names(log)` / `_movement_index(log)` for
  completing names, and `TrainingSession.to_ox()` / `Movement.to_ox()` already serialize a session
  back to `.ox` text.
- It's the REPL's first write path, so the rules it sets (which file, what gets validated, append
  only) bind any later write command.

### Constraints
- **Plain text is the source of truth** (SPEC "Core Principles"). `add` only appends to the end of
  a file; it never rewrites, reorders or reformats existing text.
- **What's written must parse.** The new text is parsed with the same grammar before writing; if it
  has a syntax error, nothing is written.
- **Prompts run in the plain `ox>` REPL** (`repl-completion` intent decision 2): guided prompts,
  no full-screen UI. Ctrl+C at any prompt cancels the whole `add` with nothing written.
- **No new dependencies.** `prompt_toolkit`'s `prompt(default=...)` supplies editable prefilled text.
- **Planning stays out of the single-line form** (CLAUDE.md format notes): whatever `add` writes,
  the existing `to_ox()` rules decide block vs single line.

### Out of scope
- Editing or deleting existing entries; anything other than appending.
- Adding weigh-ins, standalone notes, stored queries or `@movement` blocks (`add` writes one session).
- A non-interactive `ox add ...` shell command.
- Prefill from `@template` blocks or `format:` (TODO #6; templates aren't in `TrainingLog`).
- The dashboard-style REPL overhaul.

### SPEC sections touched
- "What works today": the CLI bullet gains `add`.
- `docs/cli-reference.md`: a new `add` section.
- `CHANGELOG.md` Unreleased; TODO #10 deleted at close.

### Decisions (intent review, 2026-11-09)
1. **Target file: the root file passed to `ox`.** With `@include`, the session goes to the end of
   the file you opened, not into an included one. Simple and predictable; a configurable target
   (e.g. a directive in the root file) can come later if a split-by-year layout needs it. The
   preview names the file before writing.
2. **Flow:**
   1. `date [2026-11-09]:` Enter for today; any ISO date accepted.
   2. `name:` optional; Tab completes session names already in the log (most recent first).
   3. `format:` optional; prefilled from the named session's most recent completed instance.
   4. If the name was used before, each movement from that instance is offered in turn as an
      editable line (e.g. `squat: 185lb 5x5`): Enter keeps it, edit to change, clear it to drop it.
   5. New movement lines until an empty line ends the movements.
   6. `srpe:` optional, `<rating> <duration> ["note"]` as in the format.
   7. `note:` optional, free text.
   8. Preview the `.ox` text and the target file, then `Append? [Y/n]`.
3. **Movement-level prefill through completion.** On a movement line, Tab completes the name and
   inserts the whole line from the last completed instance: `sq<Tab>` → `squat: 185lb 5x5`, ready
   to edit. Typing the line by hand works too. Two prompts per movement (name, then details with a
   default) was rejected: it doubles the keystrokes per line.
4. **"Last recorded" means the latest completed session**; planned ones don't count, matching
   `repl-completion` spec decision 4. Prefill text comes from `Movement.to_ox()` without the
   movement's note, which describes that day, not this one.
5. **Prompted session fields: date, name, format, movements, srpe, note.** `completed: false` is
   not prompted: `add` records training that happened. srpe and note aren't prefilled, since
   they describe the day.
6. **Each line is validated as it's entered.** A movement or `srpe:` line that doesn't parse is
   reported and re-prompted with the text kept, rather than failing the whole session at the end.
   The full session is parsed once more before writing.
7. **Appending:** if the file doesn't end with a newline, one is added first; then a blank line,
   then the session. After writing, the log is reloaded as `reload` does, so the new session is
   immediately in queries and completion.

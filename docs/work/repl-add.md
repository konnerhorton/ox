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

## Spec

### Changes
- **`src/ox/add.py` (new):** the `add` flow. Pure pieces that tests call directly (prefill lookups,
  line validation, building and appending the text) and one driver that runs the prompts through
  an injected prompt function, so tests can script the answers.
- **`src/ox/completion.py`:** a completer for movement lines and one for session names, built from
  the same index as `ReplCompleter`.
- **`src/ox/cli.py`:** `add` in `REPL_COMMANDS` and `help`; the REPL calls the driver, then reloads.
  Startup and `reload` share one load helper so `add` can reuse it.
- **`docs/cli-reference.md`:** an `add` section with an example session.
- **`SPEC.md`** "What works today": the CLI bullet lists `add`.

### Decisions
1. **Prompts, in order.** Each is one line, edited with the usual prompt_toolkit keys.

   | Prompt | Default (prefilled, editable) | Empty input | Checked |
   |---|---|---|---|
   | `date` | today, ISO | today | `YYYY-MM-DD`, a real calendar date. Past and future both accepted |
   | `name` | none | ad hoc session | none (the grammar takes any text up to the newline) |
   | `format` | the named session's last `format:` | no format | none |
   | movement lines (prefilled) | one per movement of the named session's last instance | drops that movement | parsed (D5) |
   | movement lines (new) | none | ends the movements | parsed (D5) |
   | `srpe` | none | no sRPE | parsed as `srpe: <text>` (D5) |
   | `note` | none | no note | must not contain `"` |

   The `srpe` prompt takes the line without its `srpe:` keyword (`7 PT1H "felt strong"`); the
   `note` prompt takes the text without quotes, and `add` writes the quotes.
2. **The named session's last instance** is the completed session with exactly that name (case
   matters, as in the log) and the latest date; on a tie, the one later in the log. If there is
   none, `format` and the prefilled movement lines are skipped and new movement lines follow `name`.
3. **A movement's last instance** is the same rule applied to movements in completed sessions:
   latest date, later in the log on a tie. Its prefill text is `Movement.to_ox()` of that
   movement with the note removed. A prefilled session line uses the same rule but takes its
   movements from the named session (D2), not from each movement's own latest instance, so the
   session comes back as you last did it.
4. **Movement-line completion.** While the cursor is in the name part of a movement line (no `:`
   typed yet), Tab offers movement names in `_movement_index` order with the same notes
   (`repl-completion` spec D4, D7). Accepting a name with a completed instance replaces the
   whole line with its prefill text (D3), e.g. `sq` → `squat: 185lb 5x5`; a name with none
   (`planned`, `defined`) inserts `name: `. After the `:`, nothing is offered. The menu shows the
   bare name, not the inserted line.
5. **A line is checked by parsing it inside a minimal block**
   (`@session` / `date: <date>` / line / `@end`) with the grammar. If `collect_diagnostics`
   reports anything, its first message is shown (so the lint hints such as `135lbs` → `135lb`
   appear here too) and the same prompt comes back with the text kept.
6. **Session-name completion.** At `name`, Tab offers names of completed sessions, latest first,
   with the date as the note; then names used only in planned sessions, alphabetically, noted
   `planned`. A planned-only name gets no prefill (D2).
7. **What gets written** is `TrainingSession(...).to_ox()` with `completed=True`. One movement with
   no name, format, sRPE or note becomes a single-line entry; anything else is a block. A session
   with no movements is written if it has an sRPE or note (a game or a class logged by effort
   only). With no movements, sRPE or note, `add` prints `Nothing to add.` and writes nothing.
8. **Before writing**, the text is parsed on its own. It must give no diagnostics and exactly one
   session equal to the one built; otherwise `add` prints the problem and writes nothing (a guard
   against a `to_ox()` bug, not something a user should hit).
9. **Preview and confirm.** The text is printed as it will be written, then
   `Append to <path>? [Y/n]`. Enter or `y` writes; `n` prints `Not written.`
10. **Appending** opens the root file (intent decision 1) in append mode. If the file is non-empty
    and doesn't end with `\n`, a `\n` is written first; if non-empty, a blank line follows; then the
    session text and a final `\n`. Nothing before the end of the file changes.
11. **After writing**, the log is reloaded exactly as `reload` does (parse, DB, plugins,
    completer, summary line), and `add` prints `Added <date> <name or "session"> to <path>.`
12. **Cancelling.** Ctrl+C or Ctrl+D at any prompt ends `add` with `Cancelled.`, writes nothing,
    and returns to `ox>` (Ctrl+D doesn't exit the REPL here).
13. **`add` takes no arguments.** `add <anything>` prints `Usage: add` and does nothing.

### Acceptance criteria
Fixture log (root file, with an `@include` of a second file holding the 2025-01-03 session):
- 2025-01-01 `Upper Day`, `format: 5/3/1 wave`: `bench-press: 135lb 5x5 "easy"`, `pullups: BW 3x8`
- 2025-01-03 single-line `squat: 185lb 5x5`
- 2025-01-08 `Upper Day`, `format: 5/3/1 wave`: `bench-press: 140lb 5x5`, `pullups: BW 3x10`
- 2025-02-01 planned `Lower Day`: `squat: 200lb 5x5`, `deadlift: 225lb 1x5`

1. **Session prefill:** name `Upper Day` prefills `format` with `5/3/1 wave` and offers
   `bench-press: 140lb 5x5` then `pullups: BW 3x10` (2025-01-08, not 2025-01-01).
2. **Movement prefill:** on a new movement line, completing `sq` replaces the line with
   `squat: 185lb 5x5` (from the included file); completing `bench` gives `bench-press: 140lb 5x5`;
   completing `dead` inserts `deadlift: ` (planned only). Notes are dropped: a log whose last bench
   is `bench-press: 135lb 5x5 "easy"` prefills `bench-press: 135lb 5x5`.
3. **Session-name completion:** `U` offers `Upper Day` (note `2025-01-08`); empty offers
   `Upper Day` then `Lower Day` (`planned`). `Lower Day` gets no prefill.
4. **Single line:** date `2025-03-01`, no name, one line `squat: 190lb 5x5`, no sRPE or note →
   appends `2025-03-01 T squat: 190lb 5x5`.
5. **Block:** date `2025-03-02`, `Upper Day`, prefills kept except pullups cleared, new line
   `dips: BW 3x10`, sRPE `7 PT1H "felt strong"`, note `deload` → appends
   ```
   @session
   date: 2025-03-02
   name: Upper Day
   format: 5/3/1 wave
   srpe: 7 PT1H "felt strong"
   note: "deload"
   bench-press: 140lb 5x5
   dips: BW 3x10
   @end
   ```
6. **Effort-only session:** no movements, sRPE `6 PT1H30M` → a block with `date:` and `srpe:`.
   No movements, sRPE or note → `Nothing to add.`, file unchanged.
7. **Line validation:** `squat: 185lbs 5x5` is rejected with the lint hint for `lbs` and
   re-prompted with the text kept; `5.5 PT1H` at `srpe` is rejected with the srpe hint; a note
   containing `"` is rejected; `2025-02-30` at `date` is rejected.
8. **Date default:** empty `date` uses today (the driver takes `today` as a parameter for tests).
9. **Append only:** for a root file without a trailing newline, and for one with, the result is the
   original bytes unchanged, then `\n` if needed, a blank line, the session and `\n`. An empty file
   gets just the session and `\n`. The included file is never touched.
10. **Confirm:** `n` leaves the file byte-identical and prints `Not written.`
11. **Cancel:** Ctrl+C or Ctrl+D at each prompt (`date`, a movement line, `srpe`, confirm) leaves
    the file byte-identical, prints `Cancelled.`, and the REPL keeps running.
12. **Reload:** after `add`, `query SELECT ...` sees the new session and `volume -m <new movement>`
    and movement completion know a movement first logged by `add`.
13. **Round trip:** every appended text in ACs 4–6 re-parses to the session that was built (D8).
14. **Usage:** `add foo` prints `Usage: add` and doesn't prompt.
15. **No regressions:** existing REPL commands behave as before; full test suite and ruff pass.

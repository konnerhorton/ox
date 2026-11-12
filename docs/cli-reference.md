---
icon: material/console
---

# CLI Reference

## Usage

```bash
ox training.ox
```

Opens an interactive REPL. Parse errors are summarized on load — run `lint` for details.

## Commands

### `plugins`

List available plugins with their descriptions and usage strings.

```
ox> plugins
```

### Running a plugin

Invoke a plugin by name. Plugins receive the parsed log plus a SQLite connection and return a table, text, or plot.

```
ox> volume -m squat --bin monthly
ox> e1rm -m deadlift
ox> wendler531 -m squat:315,bench:225
```

Typing a plugin's name with no args prints its usage. See [Plugins](plugins.md) for details.

### `query SQL`

Run raw SQL against the training database. Use named queries defined in your `.ox` file or write inline SQL.

```
ox> query SELECT * FROM sessions LIMIT 10
ox> query SELECT movement_name, COUNT(*) FROM movements GROUP BY movement_name
```

### `add`

Add a session to the end of the log file, one prompt at a time. Every prompt is an editable line:
Enter accepts it as shown, and Ctrl+C or Ctrl+D cancels the whole `add` with nothing written.

| Prompt | Starts with | Leave it empty to |
|---|---|---|
| `date` | today | use today. Any `YYYY-MM-DD` date, past or future |
| `name` | nothing; Tab offers session names from the log | log an ad hoc session |
| `format` | the format from the last time you did that session | leave it out |
| `-` (one per movement) | each movement from the last time you did that session | drop that movement |
| `-` (new movements) | nothing; Tab completes a movement with its last sets | finish the movements |
| `srpe` | nothing. Type `<rating> <duration> ["note"]`, e.g. `7 PT1H` | leave it out |
| `note` | nothing. Type the text without quotes | leave it out |

`format` and the prefilled movements appear only when the name matches a session you've completed
before, using its most recent instance.

On a movement line, Tab completes the movement name and fills in the rest of the line from the
last time you did it, so `sq<Tab>` becomes `squat: 185lb 5x5`, ready to edit. The note from that
day isn't copied. A movement you've only planned completes to just its name, `deadlift: `.

Each line is checked as you enter it. A line with a mistake is reported with the same message
`lint` gives, and the prompt comes back with your text so you can fix it:

```
ox> add
date: 2025-03-02
name: Upper Day
format: 5/3/1 wave
Movements: Tab completes a name with its last sets; an empty line ends.
- bench-press: 140lb 5x5
- pullups: BW 3x10
- dips: BW 3x10lbs
Unknown unit `lbs`: use `lb`
- dips: BW 3x10
-
srpe: 7 PT1H "felt strong"
note: deload

@session
date: 2025-03-02
name: Upper Day
format: 5/3/1 wave
srpe: 7 PT1H "felt strong"
note: "deload"
bench-press: 140lb 5x5
pullups: BW 3x10
dips: BW 3x10
@end

Append to training.ox? [Y/n]
```

`add` shows the session as it will be written, then asks before writing. A lone movement with no
name, format, sRPE or note is written as a single line (`2025-03-02 T squat: 190lb 5x5`); anything
else is a `@session` block. A session with no movements is fine if it has an sRPE or note, e.g. a
class logged by effort only.

`add` only ever appends: it adds a blank line and the session at the end of the file, and leaves
everything before it untouched. It writes to the file you opened with `ox`, even when that file
`@include`s others. The log then reloads, so queries and completion see the new session at once.

### `tables [-h]`

List database tables and views. Use `-h` to show column details.

```
ox> tables
ox> tables -h
```

### `lint`

Show parse errors in the log file. Common mistakes are named, with the fix:

```
ox> lint
Line 12, col 31: Unknown unit `lbs`: use `lb`
Line 40, col 6: Curly quote: use a straight double quote (")
Line 57, col 0: sRPE line is `srpe: <whole-number rating> <duration> ["note"]`, e.g. `srpe: 5 PT45M`
```

Anything else is reported as `Syntax error`. The LSP shows the same messages in your editor.

### `reload`

Re-parse the log file from disk.

```
ox> reload
```

### `help`

Show available commands.

### `exit` / `quit`

Exit the REPL. `Ctrl+D` also works.

## Keyboard Shortcuts

| Key | Action |
|---|---|
| Tab | Auto-complete commands, plugin flags, movement names and stored queries |
| Ctrl+C | Cancel current input (inside `add`, cancel the whole `add`) |
| Ctrl+D | Exit (inside `add`, cancel the whole `add`) |
| Up/Down | Command history |

### Tab completion

What Tab offers depends on where the cursor is:

- **First word:** commands and plugin names.
- **After a plugin name, a word starting with `-`:** the plugin's long flags (`--movement`, `--bin`, …),
  leaving out flags already on the line. Each shows `required` or its default beside it.
- **After a movement flag** (`-m`, `--movement`, `--movements`): movement names from the loaded log.
  In a comma-separated list (`wendler531 -m squat:315,dead`), the item after the last comma completes.
- **After `query`:** stored query names.

Movement names come from every session and `@movement` definition in the log, most recently trained
first, with the date last trained beside each. Names that only appear in planned sessions (`planned`)
or `@movement` blocks (`defined`) follow, alphabetically. Names that only appear in `@template` blocks
aren't offered. `reload` picks up new movements, plugins and queries.

Matching is a case-insensitive prefix match. Completion only suggests: any name can still be typed.

## CLI Options

```bash
ox --version    # show version
ox --help       # show help
```

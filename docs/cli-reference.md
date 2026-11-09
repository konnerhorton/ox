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
| Ctrl+C | Cancel current input |
| Ctrl+D | Exit |
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

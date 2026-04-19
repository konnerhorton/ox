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

### `run [NAME [OPTIONS]]`

List or run plugins. Plugins receive the parsed log plus a SQLite connection and return a table, text, or plot.

```
ox> run                                         # list available plugins
ox> run volume -m squat --bin monthly
ox> run e1rm -m deadlift
ox> run wendler531 -m squat:315,bench:225
```

Plugin names also work directly — `volume -m squat` is equivalent to `run volume -m squat`.

See [Plugins](plugins.md) for details.

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

Show parse errors in the log file.

```
ox> lint
```

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
| Tab | Auto-complete commands |
| Ctrl+C | Cancel current input |
| Ctrl+D | Exit |
| Up/Down | Command history |

## CLI Options

```bash
ox --version    # show version
ox --help       # show help
```

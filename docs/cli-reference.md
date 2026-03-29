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

### `report [NAME [OPTIONS]]`

List or run reports. Reports query the SQLite database and return tables.

```
ox> report                              # list available reports
ox> report volume -m squat --bin monthly
ox> report e1rm -m deadlift
```

See [Reports & Plugins](plugins.md) for details.

### `generate [NAME [OPTIONS]]`

List or run generators. Generators produce `.ox` text for planning.

```
ox> generate                                    # list available generators
ox> generate wendler531 -m squat:315,bench:225
```

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

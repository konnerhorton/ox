---
icon: material/console
---

# CLI Reference

Ox provides an interactive command-line interface for analyzing your training logs.

## Installation

The CLI is included when you install ox:

```bash
pip install ox
```

## Basic Usage

Start the interactive analyzer by providing your training log file:

```bash
ox training.ox
```

You'll see a prompt like this:

```
Loading training.ox...
✓ Loaded 45 sessions

Type 'help' for commands, 'exit' to quit

ox>
```

## Commands

### `stats`

Show summary statistics for all exercises in your log.

**Usage:**
```
ox> stats
```

**Output:**
```
Training Statistics
Exercise              Sessions    Total Reps    Last Session
squat                 12          180           2024-01-20
bench-press           10          150           2024-01-19
kb-swing              8           600           2024-01-18
pullup                15          300           2024-01-21

Total sessions: 45
Unique exercises: 12
```

### `history`

Show detailed training history for a specific exercise.

**Usage:**
```
ox> history EXERCISE
```

**Example:**
```
ox> history squat
```

**Output:**
```
History: squat
Date          Sets × Reps       Top Weight    Volume
2024-01-15    5 + 5 + 5 + 5 + 5    135 lbs      3375 lb
2024-01-17    5 + 5 + 5 + 5 + 5    140 lbs      3500 lb
2024-01-19    5 + 5 + 5 + 5 + 5    145 lbs      3625 lb
```

**Notes:**
- Exercise names must match exactly (case-sensitive)
- Use the name as it appears in your log (e.g., `kb-swing`, not `kettlebell swing`)

### `help`

Display available commands.

**Usage:**
```
ox> help
```

### `exit` or `quit`

Exit the program.

**Usage:**
```
ox> exit
```

or

```
ox> quit
```

## Keyboard Shortcuts

- **Tab** - Auto-complete commands
- **Ctrl+C** - Cancel current input (doesn't exit)
- **Ctrl+D** - Exit the program
- **Up/Down arrows** - Navigate command history

## Command-Line Options

### Version

Show the installed version:

```bash
ox --version
```

### Help

Show command-line help:

```bash
ox --help
```

**Output:**
```
Usage: ox [OPTIONS] FILE

  Interactive training log analyzer.

  FILE: Path to training log file

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.
```

## Examples

### Analyze Your Training Log

```bash
$ ox ~/training/2024.ox
Loading /home/user/training/2024.ox...
✓ Loaded 156 sessions

Type 'help' for commands, 'exit' to quit

ox> stats
```

### Check Exercise Progression

```bash
ox> history deadlift
```

This shows your deadlift history, making it easy to see if you're progressing over time.

### Multiple Logs

Want to analyze different time periods? Just run ox with different files:

```bash
# Analyze Q1
ox training-q1-2024.ox

# Analyze Q2
ox training-q2-2024.ox
```

## Tips

### Use Consistent Naming

The CLI is case-sensitive and matches exercise names exactly:

```
squat           ✓ matches
Squat           ✗ different
squat-barbell   ✗ different
```

Use consistent naming in your log for best results.

### Tab Completion

Press Tab to complete commands:

```
ox> sta[Tab]
ox> stats
```

### Quick Analysis Workflow

1. Open your training log in your text editor
2. Add today's workout
3. Save the file
4. Run `ox training.ox` in a terminal
5. Use `history` to check progress
6. Keep training!

## Troubleshooting

### File Not Found

```
Error: Invalid value for 'FILE': Path 'training.ox' does not exist.
```

**Solution:** Make sure the file path is correct:
```bash
# Use absolute path
ox /home/user/training.ox

# Or relative path
cd ~/training
ox training.ox
```

### Parse Errors

If the CLI fails to load your file, check for syntax errors:

- Dates must be `YYYY-MM-DD` format
- Exercise names can't have spaces
- Sessions must have `@session` and `@end` tags

See the [syntax documentation](index.md) for details.

### No History Found

```
No history found for 'sqat'
```

**Solution:** Check your spelling! Exercise names must match exactly. Use `stats` to see all exercise names in your log.

## Future Commands

Commands planned for future releases:

- `compare EXERCISE1 EXERCISE2` - Compare two exercises
- `weekly` - Show weekly summary
- `volume` - Show total volume over time
- `export` - Export data to CSV/JSON
- `graph EXERCISE` - Show ASCII graph of progression

Have ideas for new commands? [Open an issue](https://github.com/konnerhorton/ox/issues)!

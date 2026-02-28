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
✓ Loaded 45 completed, 2 planned sessions

Type 'help' for commands, 'exit' to quit

ox>
```

If the file has parse errors, a warning is shown:

```
Warning: 2 parse error(s). Run 'lint' for details.
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

Completed sessions: 45
Planned sessions: 2
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

### `report`

List available reports or run one. Reports query the SQLite database and return tabular results.

**Usage:**
```
ox> report                          # list available reports
ox> report REPORT_NAME [OPTIONS]    # run a report
```

**Example — list reports:**
```
ox> report

Available Reports:
  volume - Volume over time for a movement
    Usage: report volume -m/--movement <movement> [-b/--bin <bin>]
  matrix - Session count per movement per time period
    Usage: report matrix [-b/--bin <bin>]
  e1rm - Estimated 1RM progression for a movement
    Usage: report e1rm -m/--movement <movement> [-f/--formula <formula>]
```

**Example — run `volume` report:**
```
ox> report volume -m squat
ox> report volume --movement deadlift --bin monthly
```

**Example — run `matrix` report:**
```
ox> report matrix
ox> report matrix --bin monthly
```

**Example — run `e1rm` report:**
```
ox> report e1rm -m deadlift
ox> report e1rm --movement squat --formula epley
```

For details on each report, see [Reports & Plugins](plugins.md).

### `generate`

List available generators or run one. Generators produce `.ox` formatted text for planning sessions.

**Usage:**
```
ox> generate                          # list available generators
ox> generate GENERATOR_NAME [OPTIONS] # run a generator
```

Generator output can be pasted directly into your training log.

For details on generators and how to install them, see [Reports & Plugins](plugins.md).

### `query`

Run a raw SQL query against your training data.

**Usage:**
```
ox> query SELECT ...
```

**Examples:**
```
ox> query SELECT * FROM sessions LIMIT 10
ox> query SELECT movement_name, COUNT(*) as sessions FROM movements GROUP BY movement_name ORDER BY sessions DESC
ox> query SELECT date, weight_magnitude, reps FROM training WHERE movement_name = 'squat' ORDER BY date
```

Use `tables` to see what tables and views are available.

### `tables`

Show available tables and views in the SQLite database.

**Usage:**
```
ox> tables
```

**Output:**
```
  movements (table)
  sessions (table)
  training (table)
```

### `reload`

Reload the log file from disk without restarting. Use this after editing your training log.

**Usage:**
```
ox> reload
```

**Output:**
```
Reloading training.ox...
✓ Loaded 46 completed, 2 planned sessions
```

### `lint`

Show parse errors in the log file.

**Usage:**
```
ox> lint
```

**Output (no errors):**
```
No parse errors found.
```

**Output (with errors):**
```
Line 42, col 0: Syntax error
Line 87, col 12: Missing weight
```

Lint errors are also summarized on startup and after `reload`.

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
✓ Loaded 156 completed, 4 planned sessions

Type 'help' for commands, 'exit' to quit

ox> stats
```

### Check Exercise Progression

```bash
ox> history deadlift
```

### Query the Database Directly

```bash
ox> query SELECT strftime('%Y-%m', date) as month, SUM(reps * weight_magnitude) as volume FROM training WHERE movement_name = 'squat' GROUP BY month
```

### Multiple Logs

Want to analyze different time periods? Run ox with different files:

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
5. Use `reload` if you want to keep the session open and re-parse
6. Use `history` to check progress
7. Keep training!

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

If the CLI warns about parse errors on load, run `lint` to see details:

```
ox> lint
Line 42, col 0: Syntax error
```

- Dates must be `YYYY-MM-DD` format
- Exercise names can't have spaces
- Sessions must have `@session` and `@end` tags

See the [syntax documentation](index.md) for details.

### No History Found

```
No history found for 'sqat'
```

**Solution:** Check your spelling. Exercise names must match exactly. Use `stats` to see all exercise names in your log.

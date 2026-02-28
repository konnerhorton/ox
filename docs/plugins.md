---
icon: material/puzzle-edit
---

# Reports & Plugins

Ox has a plugin system for extending analysis and training plan generation. Plugins come in two types:

- **Reports** — query the SQLite database and return tabular results
- **Generators** — accept parameters and return `.ox` formatted text for planning

## Built-in Reports

These reports are included with ox and available immediately.

### `volume`

Volume over time for a single movement.

**CLI usage:**
```
ox> report volume -m MOVEMENT [-b BIN]
```

**Parameters:**
- `-m` / `--movement` *(required)* — exercise name to filter by
- `-b` / `--bin` *(default: `weekly`)* — time bin: `daily`, `weekly`, `weekly-num`, or `monthly`

**Examples:**
```
ox> report volume -m squat
ox> report volume --movement deadlift --bin monthly
```

**Output columns:** `period`, `total_volume`, `total_reps`, `avg_weight_per_rep`

### `matrix`

Session count per movement per time period. Rows are time periods; columns are movement names sorted by frequency.

**CLI usage:**
```
ox> report matrix [-b BIN]
```

**Parameters:**
- `-b` / `--bin` *(default: `weekly`)* — time bin: `daily`, `weekly`, `weekly-num`, or `monthly`

**Examples:**
```
ox> report matrix
ox> report matrix --bin monthly
```

**Output columns:** `period`, then one column per movement name

### `e1rm`

Estimated one-rep max (1RM) progression for a movement over time.

Only considers sets where the movement note contains `^rm` — this is the convention for marking max-effort sets.

**CLI usage:**
```
ox> report e1rm -m MOVEMENT [-f FORMULA]
```

**Parameters:**
- `-m` / `--movement` *(required)* — exercise name
- `-f` / `--formula` *(default: `brzycki`)* — formula to use: `brzycki` or `epley`

**Examples:**
```
ox> report e1rm -m deadlift
ox> report e1rm --movement squat --formula epley
```

**Output columns:** `date`, `estimated_1rm`, `weight`, `reps`, `unit`

**Marking max-effort sets in your log:**

Add `^rm` anywhere in the movement note:

```
deadlift: 315lb 1x3 "^rm top set"
squat: 225lb 5x1 "^rm — new training max"
```

## Example Generator

An example generator plugin for Wendler 5/3/1 cycles is included in `examples/plugins/wendler531.py`. It is not installed by default — see [Installing Plugins](#installing-plugins) below.

### `wendler531`

Generates a 4-week Wendler 5/3/1 cycle as `.ox` planned sessions.

**CLI usage (after installing):**
```
ox> generate wendler531 -m MOVEMENT -t TRAINING_MAX [-u UNIT] [-d START_DATE]
```

**Parameters:**
- `-m` / `--movement` *(required)* — movement name (e.g., `squat`)
- `-t` / `--training_max` *(required)* — training max weight (numeric)
- `-u` / `--unit` *(default: `lbs`)* — weight unit: `lbs` or `kg`
- `-d` / `--start_date` *(default: today)* — start date as `YYYY-MM-DD`

**Example:**
```
ox> generate wendler531 -m squat -t 315
ox> generate wendler531 -m bench-press -t 200 -u lbs -d 2026-03-01
```

**Output:** Valid `.ox` text with `!` (planned) sessions that you can paste into your log:

```
# Wendler 5/3/1 — squat (TM: 315lbs)

@session
2026-03-01 ! 5s Week
squat: 205lbs 1x5
squat: 235lbs 1x5
squat: 270lbs 1x5
@end

@session
2026-03-08 ! 3s Week
...
```

## Installing Plugins

### Personal scripts (`~/.ox/plugins/`)

Place any `.py` file in `~/.ox/plugins/`. It will be loaded automatically on startup.

To install the bundled Wendler 5/3/1 example:

```bash
mkdir -p ~/.ox/plugins
cp /path/to/ox/examples/plugins/wendler531.py ~/.ox/plugins/
```

### Installable packages (entry points)

Plugins can also be distributed as Python packages that register via the `ox.plugins` entry point group. In your `pyproject.toml`:

```toml
[project.entry-points."ox.plugins"]
my_plugin = "my_package.my_module"
```

The referenced module must export a `register()` function (see below).

## Writing a Plugin

A plugin is a Python module that exports a `register()` function returning a list of plugin descriptors.

### Report plugin

```python
import sqlite3

def my_report(conn: sqlite3.Connection, movement: str) -> tuple[list[str], list[tuple]]:
    rows = conn.execute(
        "SELECT date, SUM(reps) FROM training WHERE movement_name = ? GROUP BY date",
        (movement,),
    ).fetchall()
    return ["date", "total_reps"], rows


def register():
    return [
        {
            "type": "report",
            "name": "my-report",
            "fn": my_report,
            "description": "Total reps per day for a movement",
            "params": [
                {"name": "movement", "type": str, "required": True, "short": "m"},
            ],
        }
    ]
```

### Generator plugin

```python
def my_generator(movement: str, sets: int = 5) -> str:
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    lines = ["@session", f"{today} ! Generated Session"]
    for _ in range(sets):
        lines.append(f"{movement}: BW 1x10")
    lines.append("@end")
    return "\n".join(lines)


def register():
    return [
        {
            "type": "generator",
            "name": "my-generator",
            "fn": my_generator,
            "description": "Generate a bodyweight session",
            "params": [
                {"name": "movement", "type": str, "required": True, "short": "m"},
                {"name": "sets", "type": int, "required": False, "default": 5, "short": "s"},
            ],
        }
    ]
```

### Plugin descriptor fields

| Field | Required | Description |
|---|---|---|
| `type` | yes | `"report"` or `"generator"` |
| `name` | yes | Name used in the CLI (`report NAME` or `generate NAME`) |
| `fn` | yes | Callable that implements the plugin |
| `description` | yes | Short description shown in listings |
| `params` | yes | List of parameter descriptors (see below) |
| `needs_db` | no | If `True`, generator receives `conn` as first arg |

### Parameter descriptor fields

| Field | Required | Description |
|---|---|---|
| `name` | yes | Parameter name (used as `--name` flag) |
| `type` | yes | Python type to cast the value to (e.g., `str`, `int`) |
| `required` | yes | Whether the parameter is required |
| `default` | no | Default value if not provided |
| `short` | no | Single-character short flag (e.g., `"m"` → `-m`) |

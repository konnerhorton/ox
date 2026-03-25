---
icon: material/puzzle-edit
---

# Reports & Plugins

Two plugin types: **reports** (query DB, return tables) and **generators** (produce `.ox` text).

## Built-in Reports

### `volume`

Volume over time for a movement.

```
ox> report volume -m squat
ox> report volume -m deadlift --bin monthly --unit kg
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | exercise name |
| `-b/--bin` | `weekly` | `daily`, `weekly`, `weekly-num`, `monthly` |
| `-u/--unit` | `lb` | any mass unit |

### `matrix`

Session count per movement per time period.

```
ox> report matrix
ox> report matrix --bin monthly
```

| Param | Default | Options |
|---|---|---|
| `-b/--bin` | `weekly` | `daily`, `weekly`, `weekly-num`, `monthly` |

### `e1rm`

Estimated 1RM progression. Only uses sets with `^rm` in the note.

```
ox> report e1rm -m deadlift
ox> report e1rm -m squat --formula epley --output plot
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | exercise name |
| `-f/--formula` | `brzycki` | `brzycki`, `epley` |
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot` |

Mark max-effort sets in your log with `^rm`:

```
deadlift: 315lb 1x3 "^rm top set"
```

### `weighin`

Body weight tracking with statistics and trend analysis.

```
ox> report weighin
ox> report weighin --output plot --window 14
ox> report weighin --output stats
```

| Param | Default | Options |
|---|---|---|
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot`, `stats` |
| `-w/--window` | `7` | rolling average window (days) |

Supports multiple scales — `stats` output shows per-scale breakdowns.

## Built-in Generator

### `wendler531`

Generates a 4-week Wendler 5/3/1 cycle as planned sessions.

```
ox> generate wendler531 -m squat:315,bench:225
ox> generate wendler531 -m deadlift:405 --unit kg --start-date 2026-03-01
```

| Param | Default | Options |
|---|---|---|
| `-m/--movements` | *required* | `name:max` pairs, comma-separated |
| `-u/--unit` | `lb` | `lb`, `kg` |
| `-d/--start-date` | today | `YYYY-MM-DD` |
| `-r/--rm` | `true` | `true`, `false` — tag sets with `^rm` |

## Installing Plugins

### Personal scripts

Place `.py` files in `~/.ox/plugins/` — loaded automatically.

### Entry points

Distribute as a Python package with an `ox.plugins` entry point:

```toml
[project.entry-points."ox.plugins"]
my_plugin = "my_package.my_module"
```

## Writing a Plugin

Export a `register()` function returning a list of descriptors.

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
    return [{
        "type": "report",
        "name": "my-report",
        "fn": my_report,
        "description": "Total reps per day",
        "params": [
            {"name": "movement", "type": str, "required": True, "short": "m"},
        ],
    }]
```

### Generator plugin

```python
def my_generator(movement: str, sets: int = 5) -> str:
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    lines = ["@session", f"{today} ! Generated Session"]
    lines += [f"{movement}: BW 1x10" for _ in range(sets)]
    lines.append("@end")
    return "\n".join(lines)

def register():
    return [{
        "type": "generator",
        "name": "my-generator",
        "fn": my_generator,
        "description": "Bodyweight session generator",
        "params": [
            {"name": "movement", "type": str, "required": True, "short": "m"},
            {"name": "sets", "type": int, "required": False, "default": 5, "short": "s"},
        ],
    }]
```

### Descriptor fields

**Plugin:**

| Field | Required | Description |
|---|---|---|
| `type` | yes | `"report"` or `"generator"` |
| `name` | yes | CLI name |
| `fn` | yes | Callable |
| `description` | yes | Short description |
| `params` | yes | Parameter descriptors |
| `needs_db` | no | If `True`, generator receives `conn` as first arg |

**Parameter:**

| Field | Required | Description |
|---|---|---|
| `name` | yes | `--name` flag |
| `type` | yes | Python type (`str`, `int`, etc.) |
| `required` | yes | Whether required |
| `default` | no | Default value |
| `short` | no | Single-char short flag |

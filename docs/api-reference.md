---
icon: material/api
---

# API Reference

## Basic Usage

```python
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

for session in log.sessions:
    print(f"{session.date}: {session.name}")
    for movement in session.movements:
        print(f"  {movement.name}: {movement.total_reps} reps")
```

## Data Structures

All are frozen dataclasses with `slots=True`.

### TrainingLog

| Attribute | Type |
|---|---|
| `sessions` | `tuple[TrainingSession, ...]` |
| `notes` | `tuple[Note, ...]` |
| `weigh_ins` | `tuple[WeighIn, ...]` |
| `queries` | `tuple[StoredQuery, ...]` |
| `movement_definitions` | `tuple[MovementDefinition, ...]` |
| `diagnostics` | `tuple[Diagnostic, ...]` |

**Properties:** `completed_sessions`, `planned_sessions`

**Methods:** `movements(name=None)`, `movement_history(name)`, `most_recent_session(name)`

### TrainingSession

| Attribute | Type |
|---|---|
| `date` | `datetime.date` |
| `name` | `str \| None` |
| `flag` | `str` (`"*"`, `"!"`, `"W"`) |
| `movements` | `tuple[Movement, ...]` |
| `notes` | `tuple[Note, ...]` |

### Movement

| Attribute | Type |
|---|---|
| `name` | `str` |
| `sets` | `list[TrainingSet]` |
| `note` | `str \| None` |

**Properties:** `total_reps`, `top_set_weight`

**Methods:** `total_volume()`, `to_ox(compact_reps=False)`

### TrainingSet

| Attribute | Type |
|---|---|
| `reps` | `int` |
| `weight` | `Quantity \| None` |

**Properties:** `volume` (`reps × weight`, or `None` for BW)

### MovementDefinition

| Attribute | Type |
|---|---|
| `name` | `str` |
| `equipment` | `str \| None` |
| `tags` | `tuple[str, ...]` |
| `note` | `str \| None` |
| `url` | `str \| None` |

Parsed from `@movement` blocks. Used by the LSP for name completion; queryable directly off the log.

### WeighIn

| Attribute | Type |
|---|---|
| `date` | `datetime.date` |
| `weight` | `Quantity` |
| `time_of_day` | `str \| None` |
| `scale` | `str \| None` |

### Note

| Attribute | Type |
|---|---|
| `text` | `str` |
| `date` | `datetime.date \| None` |

### StoredQuery

| Attribute | Type |
|---|---|
| `name` | `str` |
| `sql` | `str` |
| `date` | `datetime.date` |

### Diagnostic

| Attribute | Type |
|---|---|
| `line` | `int` |
| `col` | `int` |
| `end_line` | `int` |
| `end_col` | `int` |
| `message` | `str` |
| `severity` | `str` (`"error"` or `"warning"`) |

## Working with Units

ox uses [pint](https://pint.readthedocs.io/) for weights:

```python
weight = movement.sets[0].weight

weight.to('kg')          # convert
weight.magnitude         # numeric value
weight.units             # unit object

from ox.units import ureg
if weight > 100 * ureg.pound:
    print("Heavy!")
```

## Database Layer

Load into SQLite for complex queries:

```python
from ox.db import create_db

conn = create_db(log)
rows = conn.execute("""
    SELECT movement_name, SUM(reps * weight_magnitude) AS volume
    FROM training
    WHERE movement_name = 'squat'
    GROUP BY movement_name
""").fetchall()
conn.close()
```

**Tables:** `sessions`, `movements`, `sets`, `notes`, `session_notes`, `weigh_ins`, `queries`

**Views:** `training` (denormalized join of sessions/movements/sets)

## Round-trip Serialization

```python
session.to_ox()     # serialize session to .ox format
movement.to_ox()    # serialize movement
note.to_ox()        # serialize note
```

## Plugin API

Plugins receive a `PluginContext` and return one of three result types. All are frozen dataclasses in `ox.plugins`.

### PluginContext

| Attribute | Type |
|---|---|
| `db` | `sqlite3.Connection` |
| `log` | `TrainingLog` |

### TableResult

| Attribute | Type |
|---|---|
| `columns` | `list[str]` |
| `rows` | `list[tuple]` |

### TextResult

| Attribute | Type |
|---|---|
| `text` | `str` |

### PlotResult

| Attribute | Type |
|---|---|
| `lines` | `list[str]` |

See [Plugins](plugins.md) for a walkthrough of writing a plugin and registering it via `register()`.

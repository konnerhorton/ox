---
icon: material/api
---

# API Reference

Use ox as a Python library to parse and analyze your training logs.

## Basic Usage

```python
from pathlib import Path
from ox.cli import parse_file

# Parse a training log file
log = parse_file(Path("training.ox"))

# Access all sessions
for session in log.sessions:
    print(f"{session.date}: {session.name}")
    for movement in session.movements:
        print(f"  {movement.name}: {movement.total_reps} reps")
```

## Data Structures

### TrainingLog

A collection of training sessions with query methods.

**Attributes:**
- `sessions`: `tuple[TrainingSession, ...]` - All sessions in the log
- `notes`: `tuple[Note, ...]` - Top-level notes not attached to a session
- `diagnostics`: `tuple[Diagnostic, ...]` - Parse errors and warnings

**Properties:**
- `completed_sessions`: sessions with flag `"*"`
- `planned_sessions`: sessions with flag `"!"`

**Methods:**
- `movements(name=None)` - Iterate over `(date, Movement)` pairs, optionally filtered by name
- `movement_history(name)` - Sorted list of `(date, Movement)` for a given exercise
- `most_recent_session(name)` - Most recent `(date, Movement)` for a given exercise

**Example:**
```python
print(len(log.completed_sessions))   # 45
print(len(log.planned_sessions))     # 2
print(len(log.notes))                # top-level notes

for date, movement in log.movements("squat"):
    print(f"{date}: {movement.total_reps} reps")
```

### TrainingSession

Represents a single workout session.

**Attributes:**
- `date`: `datetime.date` - The date of the session
- `name`: `str | None` - Session name (e.g., "Upper Body"), `None` for single-line entries
- `flag`: `str` - Session flag (`"*"`, `"!"`, or `"W"`)
- `movements`: `tuple[Movement, ...]` - Exercises in this session
- `notes`: `tuple[Note, ...]` - Notes attached to this session

**Example:**
```python
session = log.sessions[0]
print(session.date)            # 2024-01-15
print(session.name)            # "Upper Body"
print(session.flag)            # "*"
print(len(session.movements))  # 3
print(session.notes)           # ()
```

### Movement

Represents a single exercise/movement within a session.

**Attributes:**
- `name`: `str` - Exercise name (e.g., `"squat"`, `"bench-press"`)
- `sets`: `list[TrainingSet]` - List of sets performed
- `note`: `str | None` - Movement-specific note

**Properties:**
- `total_reps`: `int` - Total reps across all sets
- `top_set_weight`: `Quantity | None` - Heaviest weight used across all sets

**Methods:**
- `total_volume()` - Total volume (`reps × weight`) across all sets, or `None` for bodyweight movements
- `to_ox(compact_reps=False)` - Serialize back to `.ox` format

**Example:**
```python
movement = session.movements[0]
print(movement.name)             # "squat"
print(movement.total_reps)       # 25
print(movement.top_set_weight)   # 185 pound
print(movement.total_volume())   # 4625 pound
print(movement.note)             # "felt heavy"
```

### TrainingSet

Represents a single set of an exercise.

**Attributes:**
- `reps`: `int` - Number of repetitions
- `weight`: `Quantity | None` - Weight used (`None` means bodyweight)

**Properties:**
- `volume`: `Quantity | None` - `reps × weight`, or `None` for bodyweight sets

**Example:**
```python
training_set = movement.sets[0]
print(training_set.reps)               # 5
print(training_set.weight)             # 185 pound
print(training_set.weight.to('kg'))    # 83.91 kilogram
print(training_set.volume)             # 925 pound
```

### Note

Represents a note entry — either top-level (standalone) or attached to a session.

**Attributes:**
- `text`: `str` - The note text
- `date`: `datetime.date | None` - Set for standalone `note_entry` lines; `None` for in-session notes

**Example:**
```python
# Top-level notes from the log
for note in log.notes:
    print(f"{note.date}: {note.text}")

# Session-level notes
for note in session.notes:
    print(note.text)
```

### Diagnostic

Represents a parse error or warning found in the log file.

**Attributes:**
- `line`: `int` - 1-based line number
- `col`: `int` - 0-based column
- `end_line`: `int` - 1-based end line
- `end_col`: `int` - 0-based end column
- `message`: `str` - Description of the error
- `severity`: `str` - `"error"` or `"warning"`

**Example:**
```python
for diag in log.diagnostics:
    print(f"Line {diag.line}, col {diag.col}: {diag.message}")
```

## Common Tasks

### Filter by Exercise

Get all instances of a specific exercise:

```python
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

for date, movement in log.movements("squat"):
    print(f"{date}: {len(movement.sets)} sets, {movement.total_reps} reps")
```

### Track Progress Over Time

```python
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

squat_history = log.movement_history("squat")

for date, movement in squat_history:
    top = movement.top_set_weight
    print(f"{date}: top set {top}")
```

### Calculate Volume

```python
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

for session in log.completed_sessions:
    volumes = [
        m.total_volume()
        for m in session.movements
        if m.total_volume() is not None
    ]
    if volumes:
        total = sum(v.to('kg').magnitude for v in volumes)
        print(f"{session.date}: {total:.1f} kg total volume")
```

### Working with Units

ox uses [pint](https://pint.readthedocs.io/) for unit handling:

```python
movement = log.sessions[0].movements[0]
weight = movement.sets[0].weight

# Convert units
print(weight.to('kg'))      # Convert to kilograms
print(weight.to('pound'))   # Convert to pounds

# Get numeric value
print(weight.magnitude)     # Just the number
print(weight.units)         # Just the unit

# Compare weights
from ox.units import ureg
if weight > 100 * ureg.pound:
    print("Heavy!")
```

### Filter by Date Range

```python
from datetime import date
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

start_date = date(2024, 1, 1)
end_date = date(2024, 1, 31)

january_sessions = [
    s for s in log.sessions
    if start_date <= s.date <= end_date
]

print(f"Sessions in January: {len(january_sessions)}")
```

### Check for Parse Errors

```python
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

if log.diagnostics:
    for d in log.diagnostics:
        print(f"Line {d.line}: {d.message} ({d.severity})")
else:
    print("No parse errors.")
```

### Serialize Back to .ox Format

Data structures support round-trip serialization:

```python
from pathlib import Path
from ox.cli import parse_file

log = parse_file(Path("training.ox"))

# Serialize a session back to .ox format
session = log.sessions[0]
print(session.to_ox())

# Serialize a movement
movement = session.movements[0]
print(movement.to_ox())
```

### Export to Dictionary

```python
from pathlib import Path
from ox.cli import parse_file
import json

log = parse_file(Path("training.ox"))

data = []
for session in log.sessions:
    session_data = {
        "date": session.date.isoformat(),
        "name": session.name,
        "flag": session.flag,
        "movements": [
            {
                "name": m.name,
                "note": m.note,
                "sets": [
                    {"reps": s.reps, "weight": str(s.weight)}
                    for s in m.sets
                ],
            }
            for m in session.movements
        ],
    }
    data.append(session_data)

with open("training_data.json", "w") as f:
    json.dump(data, f, indent=2)
```

## Using the Database Layer

For more complex queries, load your log into an in-memory SQLite database:

```python
from pathlib import Path
from ox.cli import parse_file
from ox.db import create_db

log = parse_file(Path("training.ox"))
conn = create_db(log)

# Query total volume per week for a movement
rows = conn.execute("""
    SELECT
        date(date, '-' || strftime('%w', date) || ' days') AS week,
        SUM(reps * weight_magnitude) AS volume
    FROM training
    WHERE movement_name = 'squat'
    GROUP BY week
    ORDER BY week
""").fetchall()

for week, volume in rows:
    print(f"{week}: {volume:.1f}")

conn.close()
```

See [Reports & Plugins](plugins.md) for built-in reports that use this layer.

## API Documentation

For complete source-level documentation, see:

- `src/ox/data.py` - Core data structures (`TrainingLog`, `TrainingSession`, `Movement`, `TrainingSet`, `Note`, `Diagnostic`)
- `src/ox/parse.py` - Tree-sitter node processing
- `src/ox/cli.py` - `parse_file()` entry point
- `src/ox/db.py` - SQLite schema and `create_db()`
- `src/ox/units.py` - Pint unit registry (`ureg`)

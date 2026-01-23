---
icon: material/api
---

# API Reference

Use ox as a Python library to parse and analyze your training logs.

## Basic Usage

```python
from ox import parse

# Parse a training log file
log = parse("training.ox")

# Access all sessions
for session in log.sessions:
    print(f"{session.date}: {session.name}")
    for movement in session.movements:
        print(f"  {movement.name}: {movement.sets}")
```

## Data Structures

### TrainingSession

Represents a single workout session.

**Attributes:**
- `date`: `datetime.date` - The date of the session
- `name`: `str | None` - Session name (e.g., "Upper Body")
- `flag`: `str` - Session flag ("*", "!", or "W")
- `movements`: `tuple[Movement, ...]` - Exercises in this session
- `note`: `str | None` - Session-level notes

**Example:**
```python
session = log.sessions[0]
print(session.date)        # 2024-01-15
print(session.name)        # "Upper Body"
print(session.flag)        # "*"
print(len(session.movements))  # 3
```

### Movement

Represents a single exercise/movement.

**Attributes:**
- `name`: `str` - Exercise name (e.g., "squat", "bench-press")
- `sets`: `list[TrainingSet]` - List of sets performed
- `note`: `str | None` - Movement-specific notes

**Example:**
```python
movement = session.movements[0]
print(movement.name)       # "squat"
print(len(movement.sets))  # 5
print(movement.note)       # "felt heavy"
```

### TrainingSet

Represents a single set of an exercise.

**Attributes:**
- `reps`: `int` - Number of repetitions
- `weight`: `Quantity` - Weight used (using pint units)

**Example:**
```python
training_set = movement.sets[0]
print(training_set.reps)          # 5
print(training_set.weight)        # 135 <Unit('pound')>
print(training_set.weight.to('kg'))  # 61.23 kilogram
```

## Common Tasks

### Filter by Exercise

Get all instances of a specific exercise:

```python
from ox import parse

log = parse("training.ox")

# Find all squat sessions
for session in log.sessions:
    for movement in session.movements:
        if movement.name == "squat":
            print(f"{session.date}: {len(movement.sets)} sets")
```

### Track Progress Over Time

```python
from ox import parse

log = parse("training.ox")

# Track squat progress
squat_history = []
for session in log.sessions:
    for movement in session.movements:
        if movement.name == "squat":
            max_weight = max(s.weight for s in movement.sets)
            squat_history.append((session.date, max_weight))

# Sort by date
squat_history.sort()

# Print progression
for date, weight in squat_history:
    print(f"{date}: {weight}")
```

### Calculate Volume

```python
from ox import parse

log = parse("training.ox")

# Calculate total volume for a session
for session in log.sessions:
    total_volume = 0
    for movement in session.movements:
        for training_set in movement.sets:
            # Volume = reps × weight
            volume = training_set.reps * training_set.weight.to('kg').magnitude
            total_volume += volume

    print(f"{session.date}: {total_volume:.1f} kg total volume")
```

### Working with Units

ox uses [pint](https://pint.readthedocs.io/) for unit handling:

```python
from ox import parse

log = parse("training.ox")

movement = log.sessions[0].movements[0]
weight = movement.sets[0].weight

# Convert units
print(weight.to('kg'))      # Convert to kilograms
print(weight.to('lbs'))     # Convert to pounds

# Get numeric value
print(weight.magnitude)     # Just the number
print(weight.units)         # Just the unit

# Compare weights
if weight > 100 * ureg.pounds:
    print("Heavy!")
```

### Filter by Date Range

```python
from datetime import date
from ox import parse

log = parse("training.ox")

start_date = date(2024, 1, 1)
end_date = date(2024, 1, 31)

# Get sessions in date range
january_sessions = [
    s for s in log.sessions
    if start_date <= s.date <= end_date
]

print(f"Sessions in January: {len(january_sessions)}")
```

### Export to Dictionary

```python
from ox import parse
import json

log = parse("training.ox")

# Convert to dict for JSON export (example structure)
data = []
for session in log.sessions:
    session_data = {
        "date": session.date.isoformat(),
        "name": session.name,
        "movements": []
    }
    for movement in session.movements:
        movement_data = {
            "name": movement.name,
            "sets": [
                {
                    "reps": s.reps,
                    "weight": str(s.weight)
                }
                for s in movement.sets
            ]
        }
        session_data["movements"].append(movement_data)
    data.append(session_data)

# Save to JSON
with open("training_data.json", "w") as f:
    json.dump(data, f, indent=2)
```

## Advanced Usage

### Custom Analysis

Build your own analytics:

```python
from ox import parse
from collections import defaultdict

log = parse("training.ox")

# Track frequency of each exercise
exercise_count = defaultdict(int)
for session in log.sessions:
    for movement in session.movements:
        exercise_count[movement.name] += 1

# Sort by frequency
sorted_exercises = sorted(
    exercise_count.items(),
    key=lambda x: x[1],
    reverse=True
)

print("Most frequent exercises:")
for exercise, count in sorted_exercises[:5]:
    print(f"{exercise}: {count} times")
```

### Weekly Summaries

```python
from ox import parse
from datetime import timedelta

log = parse("training.ox")

# Group by week
weekly_sessions = defaultdict(list)
for session in log.sessions:
    week_start = session.date - timedelta(days=session.date.weekday())
    weekly_sessions[week_start].append(session)

# Print weekly summaries
for week_start, sessions in sorted(weekly_sessions.items()):
    print(f"\nWeek of {week_start}:")
    print(f"  Sessions: {len(sessions)}")

    # Count total sets
    total_sets = sum(
        len(m.sets)
        for s in sessions
        for m in s.movements
    )
    print(f"  Total sets: {total_sets}")
```

## API Documentation

For complete API documentation, see the source code in `src/ox/`:

- `data.py` - Core data structures
- `parse.py` - Parser functions
- `units.py` - Unit registry configuration

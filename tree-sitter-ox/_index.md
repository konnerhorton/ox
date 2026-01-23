---
icon: lucide/rocket
---

# Ox

Ox is a plain text format for tracking training. Write your workouts in a simple text file, parse them into structured data, and analyze your progress over time.

Named after Milo of Croton, the ancient Greek wrestler who allegedly carried a calf daily as it grew into an ox, building his strength progressively.

Inspired by plain-text accounting systems like [Beancount](https://github.com/beancount/beancount).

## Documentation

- **[Getting Started](getting-started.md)** - Your first training log
- **[CLI Reference](cli-reference.md)** - Command-line interface guide
- **[API Reference](api-reference.md)** - Python library usage

## Quick Start

Example log:

Create a training log file (e.g., `training.ox`):

```
2025-11-14 * pullups: 24kg 5/5/5

@session
2025-11-14 * Upper EMOM
kb-tgu: 32kg 1x4 "easy"
kb-oh-press: 32kg 4x4
note: felt tired today
@end

2025-11-14 W gym: 155lbs "morning"
```

## Structure

**Entry**: A record in your log, either single-line or multiline.

**Item**: Data within the Entry, can be an excercise, note, or measurement.
Items must have associated details.

**Details**: Specific details about the Item like reps, sets, notes, weights, or times.

## Syntax

### Comments

Use `#` for standalone comments (ignored by parser):

```
# Week 1 - Deload
2025-11-14 * pullups: 20kg 5/5/5

# This is a note for myself
2025-11-15 * run: 5km
```

Comments are not stored as data. Use `note:` items if you want to preserve notes for analysis.

### Single-line entries

Useful for single Items (like a single-excercise session or a weigh-in) or when you don't have a reaosn to group Items.

```
2025-11-14 * pullups: 24kg 5/5/5
2025-11-14 * run: 5km 25min
2025-11-14 W gym: 155lbs
```

**Format:**

```ebnf
single_line_entry = date, " ", flag, " ", item, ": ", details ;

date = digit, digit, digit, digit, "-", digit, digit, "-", digit, digit ;
flag = "*" | "!" | "W" ;
item = identifier ;
details = detail, { " ", detail } ;
```

### Multi-line entries (sessions)

Use tagged blocks for workouts with multiple exercises:

```
@session
2025-11-14 * Upper Day
pullups: 24kg 5/5/5
kb-oh-press: 32kg 4x4
kb-row: 32kg 4x4
note: felt strong today
@end
```

**Format:**

```ebnf
multiline_entry = "@session", newline,
                  date, " ", flag, " ", name, newline,
                  { item, ": ", details, newline },
                  "@end" ;

name = text_until_newline ;
```

The session name (`Upper Day`) can be arbitrary or refer to a predefined template (future feature).

### Exercise definitions

It can be useful to define excercises for reference, the syntax below allows this.
All fields shown are options, and you can add arbitaray ones as needed.

```
@exercise kb-oh-press
equipment: kettlebell
pattern: press
url: https://example.com/kb-press-tutorial
note: keep elbow tight, don't flare
@end
```

**Fields:**
- `equipment`: Type of equipment (kettlebell, barbell, bodyweight, etc.)
- `pattern`: Movement pattern (press, squat, hinge, pull, etc.)
- `url`: Link to tutorial or form reference
- `note`: Form cues or other notes

### Flags

- `*` - Completed
- `!` - Planned
- `W` - Weigh-in

### Item Naming Conventions

The only rule is that they use no spaces, but we also recommend making them descriptive:

`{weight-type}-{descriptor}-{movement}`

`kb-oh-press` == Kettlebell Overhead Press  
`bb-back-squat` == Barbell Back Squat

### Details

Use Details to describe the Item, these can be used in any order:

**Weights:**

```
24kg          single weight
24kg+32kg     combined weights (two kettlebells, one in each hand)
24kg/32kg     progressive weights (to mactch different sets)
155lbs        bodyweight or other measurement
BW            bodyweight (inferred if not explicit)
```

**Reps:**

```
5/3/1         sets of reps
335           3 sets of 5 reps
```

**Time:**

```
25min
90sec
2hr
```

**Distance:**

```
5km
3mi
100m
50ft
```

**Notes:**

Notes can either be part of an Item's details (with quotes):

```
2025-11-14 * pullups: 24kg 5/5/5 "felt strong"
```

Or it's own line (Item) and does not require quotes:

```
note: felt really strong today, hit a PR
```

**Example combinations:**

```
2025-11-14 * pullups: 24kg 5/5/5 "easy"
2025-11-14 * run: 5km 25min "new route"
2025-11-14 * plank: 90sec
```

## Examples

```
# sinle-line entry
2025-11-14 W bodyweight: 155lbs

# completed session
@session
2025-11-14 * Strength Day
bb-squat: 135lbs 5/5/5
bb-press: 95lbs 5/5/5
bb-deadlift: 225lbs 5/5/5
@end

# planned session
@session
2025-11-15 ! Upper Day
pullups: 28kg 5/5/5
kb-oh-press: 32kg 4x4
@end

# single-line entry
2025-11-14 * stretching: 10min
```

## Data Structures

The parser converts entries into Python dataclasses for analysis:

```python
from ox import parse

log = parse("training.ox")

# Get all pullup sessions
for date, movement in log.movements("pullups"):
    print(f"{date}: {movement.total_reps} reps @ {movement.top_set_weight}")
```

See the [API Reference](api-reference.md) for complete details.

## Learn More

- **[Getting Started Guide](getting-started.md)** - Step-by-step tutorial
- **[CLI Commands](cli-reference.md)** - Analyze your logs from the terminal
- **[API Documentation](api-reference.md)** - Use ox as a Python library

## Roadmap

Future features planned:

- **Templates**: Define reusable session templates
- **Programs**: Track mesocycles and progression schemes
- **Visualization**: Built-in progress charts and graphs
- **Export**: Convert logs to CSV, JSON, or other formats

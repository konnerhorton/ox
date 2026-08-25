---
icon: material/rocket-launch
---

# Getting Started

## Installation

```bash
pip install ox
```

## Your First Log

Create `training.ox`:

```
2024-01-15 T squat: 135lb 5x5
```

Run it:

```bash
ox training.ox
ox> query SELECT * FROM training LIMIT 10
```

## Syntax

### Single-line entries

```
2024-01-15 T squat: 135lb 5x5
2024-01-15 T run: 5km PT25M
2024-01-15 W 185lb T06:30 "home"
2024-01-15 note "deload week"
```

### Session blocks

A session groups movements done in one sitting. Only `date:` is required, and it must be the first
line; everything else may follow in any order.

```
@session
date: 2024-01-16
name: Upper Body
bench-press: 135lb 5x5
overhead-press: 95lb 3x8
pullup: BW 4x10
note: "felt strong today"
@end
```

Drop the name for a session you do not want to name — a few things done in the same window, grouped
so you write the date once:

```
@session
date: 2024-01-16
pullups: BW 3x10
pushups: BW 3x15
jump-rope: PT10M
@end
```

### Session fields

| Field | Meaning |
|---|---|
| `date:` | Required, and must be the first line |
| `name:` | Optional; omit for an ad hoc session |
| `completed:` | `true` (default) or `false` for planned work |
| `format:` | Free text naming the session's shape, e.g. `5/3/1 wave` |
| `srpe:` | Session RPE — see below |
| `note:` | Freeform note attached to the session |

Planning is expressed only by `completed: false`. A single-line entry always records training that
happened, so plans that never happen are simply never written:

```
@session
date: 2024-01-20
name: Upper Day
completed: false
bench-press: 185lb 5x5
@end
```

### Session RPE

Rate the whole session from 1 to 10 and record how long it ran. The `srpe` plugin turns these into
training load (AU = rating x minutes), with ACWR, monotony, and strain reports:

```
@session
date: 2024-01-16
name: Upper Body
srpe: 6 PT50M "hard but clean"
bench-press: 135lb 5x5
@end
```

### Entry types

- `T` — a training entry
- `W` — weigh-in
- `note` — freeform note
- `query` — stored SQL query

### Weights

```
135lb             pounds
24kg              kilograms
BW                bodyweight
24kg+32kg         combined (two bells)
135/155/175lb progressive (per-set)
```

Any [pint](https://pint.readthedocs.io/)-compatible mass unit works (`g`, `oz`, `stone`, `grain`, …); `lb` and `kg` are just the common cases.

### Reps

```
5x3               5 sets of 3 reps
5/3/1             3 sets with different reps
10/8/6/4/2        pyramid
```

### Duration and distance

Work measured by time or ground covered rather than reps:

```
PT45S             45 seconds (ISO 8601)
PT1H30M15S        an hour, thirty minutes, fifteen seconds
PT30S/PT25S/PT20S per-set durations
400m              metres
3mi               miles
100m/200m/400m    per-set distances
100/200/400m      same, with the unit implied from the last value
```

Any pint-compatible length unit works (`m`, `km`, `ft`, `yd`, `mi`, `nmi`, …).

Weight, duration, and distance are independent — a set may carry all three:

```
plank: BW PT45S 3x1           3 sets, 45-second hold each
weighted-plank: 45lb PT30S 3x1
run: 5km PT25M                one set, 5km in 25 minutes
farmer-carry: 32kg 40m 4x1    4 carries of 40m with a 32kg bell
sprint: 100m/200m/400m        3 sets, one per distance
```

A field written once applies to every set; written as a `/`-list it maps one value per set. The rep
scheme decides how many sets there are — `5x1` means five sets of a single rep. With no rep scheme the
count comes from the longest `/`-list, or one set if there is none, so `run: PT30M` is a single set.

### Migrating an older log

Logs written before 0.6 used `*` / `!` flags, a positional session header, and `srpe: "5; PT45M"`.
Convert one with:

```bash
python scripts/migrate_ox.py training.ox --in-place
```

The script refuses to guess: planned single-line entries and fractional sRPE ratings stop it with a
message naming the line, so you can decide what those should become.

### Movement names

No spaces — hyphens are common but any non-space format works:

```
squat             kb-swing          bb-deadlift
bench-press       kb-oh-press       bb-back-squat
```

### Movement definitions

Declare a movement once with `@movement` to give it equipment, tags, a description, and a reference URL. Definitions are stored on the parsed log (`TrainingLog.movement_definitions`) and feed LSP name completion.

```
@movement squat
equipment: barbell
tags: squat, lower
note: back squat
url: https://example.com/squat-form
@end
```

### Notes inside sessions

Inside a `@session` block, a `note:` line attaches to the session (not to any one movement) and lands in the `session_notes` table:

```
@session
date: 2025-01-16
name: Upper Body
bench-press: 135lb 5x5
note: "felt strong today"
@end
```

### Stored queries

Save a SQL query with a name so it can be recalled later:

```
2025-01-10 query "recent-squats" "SELECT * FROM training WHERE movement_name='squat' ORDER BY date DESC LIMIT 10"
```

### Loading plugins

Plugins extend ox with custom analysis or generation. Reference a Python file from your log with `@plugin` (path is relative to the `.ox` file):

```
@plugin "plugins/my_plugin.py"
```

See [Plugins](plugins.md) for the built-ins and for writing your own.

### Includes

Split logs across files:

```
@include "2022.ox"
@include "2023.ox"
```

## Example

```
# Week 1

@session
date: 2024-01-15
name: Lower Body
srpe: 7 PT55M
squat: 135lb 5x5
deadlift: 185lb 3x5
@end

2024-01-16 T run: 5km PT28M "felt good"

@session
date: 2024-01-17
name: Upper Body
bench-press: 135lb 5x5
overhead-press: 95lb 3x8
pullup: BW 4x10
@end

2024-01-17 W 185lb T06:30 "home"
```

## Next Steps

- [CLI Reference](cli-reference.md) — commands and usage
- [Reports & Plugins](plugins.md) — built-in analysis and extending ox
- [API Reference](api-reference.md) — Python library
- [Editor Support](editor-support.md) — syntax highlighting and LSP
- [example.ox](https://github.com/konnerhorton/ox/blob/main/examples/example.ox) — full reference log
- [advanced.ox](https://github.com/konnerhorton/ox/blob/main/examples/advanced.ox) — 8 weeks of training with sRPE tracking

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
2024-01-15 * squat: 135lb 5x5
```

Run it:

```bash
ox training.ox
ox> query SELECT * FROM training LIMIT 10
```

## Syntax

### Single-line entries

```
2024-01-15 * squat: 135lb 5x5
2024-01-15 * run: 5km PT25M
2024-01-15 W 185lb T06:30 "home"
2024-01-15 note "deload week"
```

### Session blocks

```
@session
2024-01-16 * Upper Body
bench-press: 135lb 5x5
overhead-press: 95lb 3x8
pullup: BW 4x10
note: "felt strong today"
@end
```

### Entry types

- `*` — completed
- `!` — planned
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
2025-01-16 * Upper Body
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
2024-01-15 * Lower Body
squat: 135lb 5x5
deadlift: 185lb 3x5
@end

2024-01-16 * run: 5km PT28M "felt good"

@session
2024-01-17 * Upper Body
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

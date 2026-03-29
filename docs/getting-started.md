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
135lb/155lb/175lb progressive (per-set)
```

### Reps

```
5x5               5 sets of 5 reps
5/3/1             3 sets with different reps
10/8/6/4/2        pyramid
```

### Exercise names

No spaces — hyphens are common but any non-space format works:

```
squat             kb-swing          bb-deadlift
bench-press       kb-oh-press       bb-back-squat
```

### Includes

Split logs across files:

```
@include "upper.ox"
@include "lower.ox"
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
- [example.ox](https://github.com/konnerhorton/ox/blob/main/example/example.ox) — full reference log

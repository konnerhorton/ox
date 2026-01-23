---
icon: material/rocket-launch
---

# Getting Started

This guide will help you start tracking your training with ox.

## Installation

Install via pip:

```bash
pip install ox
```

## Your First Training Log

Create a file called `training.ox` and add your first workout:

```
2024-01-15 * squat: 135lbs 5x5
```

That's it! You've logged your first exercise.

## Adding More Detail

### Single-line entries

Log quick workouts or single exercises:

```
2024-01-15 * squat: 135lbs 5x5  
2024-01-15 * bench-press: 135lbs 5x5  
2024-01-15 * run: 5km 25min  
```

### Multi-exercise sessions

Group related exercises together:

```title="title"
@session
2024-01-16 * Upper Body
bench-press: 135lbs 5x5
overhead-press: 95lbs 3x8
pullup: BW 4x10
note: felt strong today
@end
```

## Understanding the Syntax

### Date Format
Always use `YYYY-MM-DD` format:
```
2024-01-15    ✓ correct
01/15/2024    ✗ wrong
15-01-2024    ✗ wrong
```

### Flags
- `*` = Completed (what you actually did)
- `!` = Planned (what you intend to do)
- `W` = Weigh-in (body weight measurement)

### Exercise Names
Use descriptive names with no spaces:
```
squat           ✓
bench-press     ✓
kb-swing        ✓ (kettlebell swing)
bb-deadlift     ✓ (barbell deadlift)
bench press     ✗ (has space)
```

### Weight Formats
```
135lbs          pounds
24kg            kilograms
BW              bodyweight
24kg+32kg       combined weights (two bells)
135lbs/155lbs/175lbs    progressive weights
```

### Rep Schemes
```
5x5             5 sets of 5 reps
5/5/5           3 sets of 5 reps
10/8/6/4/2      descending reps (pyramid)
```

## Complete Example

Here's a week of training:

```
# Week 1 - Starting Strength

@session
2024-01-15 * Lower Body
squat: 135lbs 5x5
deadlift: 185lbs 3x5
box-jump: BW 3x5
@end

2024-01-16 * run: 5km 28min "felt good"

@session
2024-01-17 * Upper Body
bench-press: 135lbs 5x5
overhead-press: 95lbs 3x8
pullup: BW 4x10
@end

@session
2024-01-18 * KB Workout
kb-swing: 32kg 5x15
kb-snatch: 24kg 5x5 "each arm"
kb-clean-and-press: 24kg 5x3 "each arm"
@end

@session
2024-01-19 * Lower Body
squat: 140lbs 5x5 "felt heavier than Monday"
deadlift: 190lbs 3x5
box-jump: BW 3x5
@end

2024-01-20 * rest-day: "active recovery walk"
```

## Next Steps

- Check out the [full syntax documentation](index.md) for all features
- See [example.ox](https://github.com/konnerhorton/ox/blob/master/example/example.ox) for a complete training log
- Learn how to [analyze your logs with the API](api-reference.md)
- Explore [CLI commands](cli-reference.md) for working with logs

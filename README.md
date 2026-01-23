# Ox

`ox` is a plain text format for tracking training. Write your training sessions in a text file, parse them into structured data, and analyze progress over time.

Named after [Milo of Croton](https://en.wikipedia.org/wiki/Milo_of_Croton), the ancient Greek Olympic wrestler who, in the off-season, carried a newborn calf daily so that by the time the Olympics came around he was carrying a 4-year-old ox.

Inspired by plain-text accounting systems like [Beancount](https://github.com/beancount/beancount).

## Overview

Physical training is most effective when starting small, working consitently, and practicing over decades.
Over that time, both the individual and available software will change.
The old method (paper), provides infinite flexibility, but analyse and progress tracking is hard. The new methods (a plethera of apps) are less flexible and do not give user cfull ontrol of their data.
Plaintext provides the data longevity and access, so I just need a syntax that provides the flexibility and ease of input as paper along with the analytics of software. Here is my implementation.

Currently, you can:

- Define excercises (this essentially just adds metadata right now, in the future I'd like to incorporate it into the analysis).
- Record both completed and planned training sessions (though planned training sessions are all but ignored in the parsing)
- Training sessions consist of a movement (squat) with details that can include weights, reps, time, distance, and notes.
  - Time and distance would be for things like running, but flexbility is key, so use it however you like!
- Perform some simple analysis via a CLI that shows progression for a given movement over time, or broad stats on all your recorded movements.
- record a bodyweight measurement

In the furture, I would like to:

- Make it easier to write plugins to perform specific analyses.
  - Right now you can do this through the python API, so you can write a script for yourself.
  - It'd also be nice to calculate RM values given a weight / rep set and track it over time (useful for programs like [Wendler's 5/3/1](https://www.jimwendler.com/collections/books-programs))
- Make the `tree-sitter` parser more robust by ensuring it can handle any valid units the user wants to use.
  - `tree-sitter` provides the tree, then the python library processes the data. `pint` is used for units, so I'd like `tree-sitter` to accept any valid `pint` units for a given dimension. For example, right now you can only use `lbs` and `kg` for weights (ie mass, if you want to get technical), it should accept all iterations of those that `pint` accepts, as well as `ton` (if you're ambitiious).
- Build out the vscode extension that not only includes syntax highlights but has a full LSP (with suggestions) and snippets.
- Provide the abililty to plan and track different cycles (micro/meso/macro) for a given movement or session.

## Documentation

Full documentation available at [https://konnerhorton.github.io/ox](https://konnerhorton.github.io/ox)

- **[Getting Started](getting-started.md)** - Your first training log
- **[CLI Reference](cli-reference.md)** - Command-line interface guide
- **[API Reference](api-reference.md)** - Python library usage
- **[Editor Support](editor-support.md)** - Support for editors

## Installation

```bash
pip install ox
```

Or install from source:

```bash
git clone https://github.com/konnerhorton/ox.git
cd ox
pip install -e .
```

## Quick Start

Create a training log file (e.g., `training.ox`):

```
2025-11-14 * pullups: 24kg 5/5/5

@session
2024-01-23 * Upper Volume
bench-press: 135lbs 5x10
overhead-press: 85lbs 4x10
pullup: BW 5x8
@end

2024-01-23 W bodyweight: 155lbs "morning"
```

Parse and analyze your log:

```python
from ox import parse

# Parse your training log
log = parse("training.ox")

# Analyze your progress
for date, movement in log.movements("pullups"):
    print(f"{date}: {movement.total_reps} reps @ {movement.top_set_weight}")
```

## Features

- **Simple syntax** - Plain text format that's easy to write and read
- **Flexible logging** - Single-line entries or multi-exercise sessions
- **Progress tracking** - Parse logs into structured data for analysis
- **Unit support** - Mix kg, lbs, bodyweight seamlessly
- **Notes and comments** - Track how you felt, form cues, and more

## Syntax Overview

**Entry**: A record in your log, either single-line or multiline.

**Item**: Data within the Entry, can be an excercise, note, or measurement.
Items must have associated details.

**Details**: Specific details about the Item like reps, sets, notes, weights, or times.

### Single-line entries

Useful for single Items (like a single-excercise session or a weigh-in) or when you don't have a reason to group Items.

```
2025-11-14 * pullups: 24kg 5/5/5
2025-11-14 * run: 5km 25min
2025-11-14 W bodyweight: 155lbs
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

### Details

**Weights:**

```
24kg          single weight
24kg+32kg     combined weights (two kettlebells)
24kg/32kg     progressive weights (different sets)
155lbs        pounds
BW            bodyweight
```

**Reps:**

```
5/3/1         sets with different reps
3x5           3 sets of 5 reps
```

**Time:**

```
25min         time
```

**Distance:**

```
5km           distance
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

### Item Naming Conventions

The only rule is that they use no spaces, but we also recommend making them descriptive:

`{weight-type}-{descriptor}-{movement}`

`kb-oh-press` == Kettlebell Overhead Press  
`bb-back-squat` == Barbell Back Squat

### Comments

Use `#` for standalone comments (ignored by parser):

```
# Week 1 - Deload
2025-11-14 * pullups: 20kg 5/5/5

# This is a note for myself
2025-11-15 * run: 5km
```

Comments are not stored as data. Use `note:` items if you want to preserve notes for analysis.

## Examples

See [example/example.ox](example/example.ox) for a complete training log example spanning multiple weeks with various exercises and rep schemes.

## Editor Support

A VSCode extension with syntax highlighting is available in `editors/vscode`. To install, symlink it to your VSCode extensions folder:

```bash
ln -s /path/to/ox/editors/vscode ~/.vscode/extensions/ox
```

Then reload VSCode. See the [editor documentation](https://konnerhorton.github.io/ox/editor-support) for more details.

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

## Development

```bash
# Clone the repository
git clone https://github.com/konnerhorton/ox.git
cd ox

# Install in development mode
pip install -e .

# Run tests
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Inspiration

This project draws inspiration from:

- [Beancount](https://github.com/beancount/beancount) - Plain text accounting
- [Ledger](https://www.ledger-cli.org/) - Command line accounting tool
- Plain text workflows and future-proof data formats

# Ox

Plain text training log format and toolchain. Record training in `.ox` files, parse into structured data, analyze progress over time.

Inspired by [Beancount](https://github.com/beancount/beancount) (plain text accounting, but for training). Named after [Milo of Croton](https://en.wikipedia.org/wiki/Milo_of_Croton).

## Quick Start

Create `training.ox`:

```
2025-01-14 T pullups: 24kg 5/5/5

@session
date: 2025-01-15
name: Upper Volume
bench-press: 135lb 5x10
overhead-press: 85lb 4x10
pullup: BW 5x8
@end

2025-01-15 W 185lb T06:30 "home"
```

Run the CLI:

```bash
ox training.ox
```

## Documentation

Full docs at [konnerhorton.github.io/ox](https://konnerhorton.github.io/ox):

- [Getting Started](https://konnerhorton.github.io/ox/getting-started/) — first training log
- [CLI Reference](https://konnerhorton.github.io/ox/cli-reference/) — commands and usage
- [Reports & Plugins](https://konnerhorton.github.io/ox/plugins/) — built-in reports, plugin system
- [API Reference](https://konnerhorton.github.io/ox/api-reference/) — Python library
- [Editor Support](https://konnerhorton.github.io/ox/editor-support/) — VSCode extension, LSP, tree-sitter grammar

## Syntax Overview

```
# Single-line entry
2025-01-14 T squat: 135lb 5x5 "felt good"

# Timed and measured work
2025-01-14 T plank: BW PT45S 3x1
2025-01-14 T run: 5km PT25M

# Session block — only `date:` is required, and it must come first
@session
date: 2025-01-15
name: Lower Body
srpe: 6 PT50M
squat: 135lb 5x5
deadlift: 185lb 3x5
note: "easy day"
@end

# Ad hoc session — no name, and planned work with `completed: false`
@session
date: 2025-01-16
pullups: BW 3x10
pushups: BW 3x15
@end

# Weigh-in
2025-01-15 W 185lb T06:30 "home"

# Note
2025-01-15 note "deload week"

# Include another file
@include "other.ox"

# Movement definition
@movement squat
equipment: barbell
tags: squat, lower
note: back squat
@end

# Load a plugin
@plugin "plugins/my_plugin.py"
```

**Markers:** `T` training entry, `W` weigh-in

**Session fields:** `date:` (required, first), `name:`, `completed:`, `format:`, `srpe:`, `note:`

**Session RPE:** `srpe: 6 PT50M "note"` — a rating and how long the session ran

**Weights:** `24kg`, `135lb`, `BW`, `24kg+32kg` (combined), `24/32/48kg` (progressive, with implied units)

**Reps:** `5x5` (sets x reps), `5/3/1` (per-set)

**Duration:** ISO 8601 (`PT30M`, `PT1H30M15S`), progressive `PT30S/PT25S/PT20S`

**Distance:** `5km`, `3mi`, `400m`, progressive `100m/200m/400m` (or `100/200/400m`)

Weight, duration, and distance are independent per-set fields, so a set can carry all of them.
Given once a field applies to every set; given as a `/`-list it maps one value per set. The rep
scheme sets the count (`5x1` is five sets of one rep); with none, `run: PT30M` is a single set.

**Movement names:** no spaces (`kb-oh-press`, `bb-back-squat`)

Planning is expressed only by a session's `completed: false` — a single-line entry always records
training that happened. Logs in the pre-0.6 flag syntax convert with `scripts/migrate_ox.py`.

## Installation

```bash
pip install ox
```

From source:

```bash
git clone https://github.com/konnerhorton/ox.git
cd ox
pip install -e .
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check src/ tests/
```

## License

MIT — see [LICENSE](LICENSE).

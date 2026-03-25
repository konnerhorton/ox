# Ox

Plain text training log format and toolchain. Write workouts in `.ox` files, parse into structured data, analyze progress over time.

Inspired by [Beancount](https://github.com/beancount/beancount) (plain text accounting, but for training). Named after [Milo of Croton](https://en.wikipedia.org/wiki/Milo_of_Croton).

## Quick Start

Create `training.ox`:

```
2025-01-14 * pullups: 24kg 5/5/5

@session
2025-01-15 * Upper Volume
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
- [Editor Support](https://konnerhorton.github.io/ox/editor-support/) — VSCode, Neovim, Helix

## Syntax Overview

```
# Single-line entry
2025-01-14 * squat: 135lb 5x5 "felt good"

# Session block
@session
2025-01-15 * Lower Body
squat: 135lb 5x5
deadlift: 185lb 3x5
note: easy day
@end

# Weigh-in
2025-01-15 W 185lb T06:30 "home"

# Note
2025-01-15 note "deload week"

# Include another file
@include "other.ox"
```

**Flags:** `*` completed, `!` planned, `W` weigh-in

**Weights:** `24kg`, `135lb`, `BW`, `24kg+32kg` (combined), `24kg/32kg/48kg` (progressive)

**Reps:** `5x5` (sets x reps), `5/3/1` (per-set)

**Duration:** ISO 8601 (`PT30M`, `PT1H30M15S`)

**Distance:** `5km`, `3mi`, `400m`

**Exercise names:** no spaces, hyphenated lowercase (`kb-oh-press`, `bb-back-squat`)

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

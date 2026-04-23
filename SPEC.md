# Ox — Product Spec

## What is ox?

A plain text training log format and toolchain.
Write workouts in a `.ox` text file, parse them into structured data, analyze progress over time.
Inspired by [Beancount](https://github.com/beancount/beancount) — plain text accounting, but for training.
Designed for tracking progress over years and decades, not just weeks and months.

## Who is it for?

People who train consistently over years and want to own their data.
Developers and power users comfortable with text files and CLIs.

## Core Principles

- **Plain text is the source of truth.** The `.ox` file is the canonical record. Everything else is derived.
- **No cloud, no accounts, no lock-in.** Your data is a text file on your filesystem.
- **Paper-like flexibility with software analytics.** As easy to write as a notebook, but parseable for real analysis.
- **Long-lived data.** A log written today should be readable in 20 years. Text outlasts apps.

## Current State

### What works today

- **Tree-sitter grammar** (`tree-sitter-ox/grammar.js`) — parses `.ox` files into syntax trees; supports many mass units (kg, lb, oz, stone, grain, etc.), ISO 8601 durations, and distance units
- **Python parser** (`src/ox/parse.py`) — tree-sitter nodes → dataclasses
- **Data model** (`src/ox/data.py`) — `TrainingSet`, `Movement`, `TrainingSession`, `TrainingLog`, `Note`, `WeighIn`, `StoredQuery`, `Diagnostic`
- **SQLite query layer** (`src/ox/db.py`) — in-memory DB with `sessions`, `movements`, `sets`, `notes`, `session_notes`, `weigh_ins`, `queries` tables and `training` view
- **Plugin system** (`src/ox/plugins.py`) — built-in plugins plus user plugins loaded via `@plugin` directives in `.ox` files
- **Built-in reports** (`src/ox/reports.py`) — `volume` (volume over time) and `matrix` (session count per movement)
- **Built-in plugins** — `e1rm` (estimated 1RM via Brzycki/Epley), `weighin` (weight tracking with stats/plot/rolling average), `wendler531` (5/3/1 cycle generator)
- **CLI** (`src/ox/cli.py`) — interactive REPL with `report`, `generate`, `query`, `tables`, `lint`, `reload` commands and tab completion
- **LSP** (`src/ox/lsp.py`) — diagnostics (syntax errors + include validation), movement name completion, comment folding ranges
- **Weigh-in tracking** — full pipeline: parse → `WeighIn` dataclass → DB → builtin report with table/plot/stats output
- **Notes** — standalone and session-level notes, parse → `Note` dataclass → DB, `to_ox()` round-trip
- **Stored queries** — named SQL queries embedded in `.ox` files, accessible via CLI `query` command
- **Include directives** — `@include "path.ox"` with recursive resolution and cycle detection
- **Lint** (`src/ox/lint.py`) — parse error collection for CLI and LSP
- **VSCode extension** — syntax highlighting
- **MkDocs documentation site** (`docs/`)
- **Round-trip serialization** — `to_ox()` methods write data back to `.ox` format
- **Unit handling** — weights tracked as `pint.Quantity`

### What's incomplete

- Planned sessions (`!` flag) — parsed but ignored in analysis
- Template blocks (`@template`) — grammar exists, no processing
- Progressive implied weights (e.g. `160/185/210lbs`) — known parsing bug
- CLI movement autocompletion (tab-complete movement names, not just commands)

## Direction

### Richer analysis

- Cycle tracking — micro/meso/macro periodization
- Movement definitions feeding into analysis (e.g. grouping by movement tag)
- `pint.Quantity` for time/distance — enables derived units like pace and speed

### Better editor experience

- LSP hover info (movement definitions, recent history for a movement)
- LSP completions for session templates
- Snippets for common entry patterns

## Non-Goals

- **Not a workout planner or coach.** Ox records and analyzes. It doesn't prescribe.
- **Not a web app or mobile app.** CLI tool and text format.
- **Not a social platform.** No sharing, leaderboards, or community features.
- **No proprietary format extensions.** The `.ox` format stays simple enough to read with no tooling.

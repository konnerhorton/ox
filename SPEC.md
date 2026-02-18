# Ox — Product Spec

## What is ox?

A plain text training log format and toolchain.
Write workouts in a `.ox` text file, parse them into structured data, analyze progress over time.
Inspired by [Beancount](https://github.com/beancount/beancount) — plain text accounting, but for training.
A big guiding principle is that one should plan their training over the course of years and decades, not weeks and months.
So, you should be able to track progress over that time frame.

## Who is it for?

People who train consistently over years and want to own their data.
Developers and power users comfortable with text files and CLIs.

## Core Principles

- **Plain text is the source of truth.** The `.ox` file is the canonical record. Everything else is derived from it.
- **No cloud, no accounts, no lock-in.** Your data is a text file on your filesystem.
- **Paper-like flexibility with software analytics.** The format should be as easy to write as scribbling in a notebook, but parseable for real analysis.
- **Long-lived data.** A log written today should be readable in 20 years. Text outlasts apps.

## Current State

### What works today

- **Tree-sitter grammar** (`tree-sitter-ox/grammar.js`) parses `.ox` files into syntax trees
- **Python parser** (`src/ox/parse.py`) converts tree-sitter nodes into dataclasses
- **Data model** (`src/ox/data.py`) — `TrainingSet`, `Movement`, `TrainingSession`, `TrainingLog`
- **SQLite query layer** (`src/ox/db.py`) — in-memory DB with `sessions`, `movements`, `sets` tables and `training` view; arbitrary SQL via CLI
- **Plugin system** (`src/ox/plugins.py`) — discovery from `~/.ox/plugins/`, entry points, and builtins; report and generator types
- **Reports** (`src/ox/reports.py`) — `volume` (volume over time) and `matrix` (session count per movement) with parameterized args; `get_all_reports()` merges builtin and plugin reports
- **Builtin e1rm plugin** — estimated 1RM via Brzycki/Epley formulas, filters on `^rm` note convention
- **Builtin wendler531 plugin** — Wendler 5/3/1 cycle generator
- **CLI** (`src/ox/cli.py`) — interactive REPL with `stats`, `history`, `report`, `generate`, `query`, `tables`, `reload` commands and tab completion
- **LSP** (`src/ox/lsp.py`) — basic diagnostics (syntax errors) for editor integration
- **VSCode extension** — syntax highlighting
- **MkDocs documentation site** (`docs/`)
- **Round-trip serialization** — `to_ox()` methods write data back to `.ox` format
- **Unit handling** — weights tracked as `pint.Quantity` (kg, lbs)

### What's incomplete

- Weigh-in processing (`W` flag) — parsed by tree-sitter but not processed into data structures
- Planned sessions (`!` flag) — parsed but mostly ignored in analysis
- Exercise definitions (`@exercise` blocks) — parsed by tree-sitter but not used in analysis
- Template blocks (`@template`) — grammar exists, no processing
- Progressive implied weights (e.g. `160/185/210lbs`) — known parsing bug
- LSP only does diagnostics — no completions, hover, or go-to-definition
- Tree-sitter grammar only accepts `kg` and `lbs` — should accept any valid pint mass unit
- `pint.Quantity` should be used for time as well
- CLI exercise autocompletion (tab-complete exercise names from the log, not just commands)

## Direction

### Richer analysis

- Cycle tracking — micro/meso/macro periodization
- Exercise definitions feeding into analysis (e.g. grouping by movement pattern)
- Generator plugins (e.g. Wendler 5/3/1 cycle generation from a training max)

### CLI

- Exercise autocompletion (tab-complete exercise names from the log, not just commands)

### Better editor experience

- LSP completions (exercise names, session templates)
- Hover info (exercise definitions, recent history for a movement)
- Snippets for common entry patterns
- Broader unit support in the grammar (any valid pint mass unit)

## Non-Goals

- **Not a workout planner or coach.** Ox records and analyzes what you did. It doesn't tell you what to do.
- **Not a web app or mobile app.** It's a CLI tool and text format. Edit your `.ox` file however you want.
- **Not a social platform.** No sharing, leaderboards, or community features.
- **No proprietary format extensions.** The `.ox` format should stay simple enough to read with no tooling at all.

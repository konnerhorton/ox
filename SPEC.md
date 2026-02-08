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
- **CLI** (`src/ox/cli.py`) — interactive REPL with `stats` and `history` commands
- **LSP** (`src/ox/lsp.py`) — basic diagnostics (syntax errors) for editor integration
- **VSCode extension** — syntax highlighting
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
- for the CLI:
  - after loading, options the user has should be listed, with a comprehensive help menu available upon request
  - options will include: list excercises (sorted by most frequently found in the log), stats and history as is, volume progression

## Direction

### SQLite query layer

The current analysis is hardcoded in Python methods on `TrainingLog` (`stats`, `movement_history`, etc.). This limits what users can ask of their data.

**Plan:** After parsing `.ox` into dataclasses, load into an in-memory SQLite database. This gives:

- Users can write arbitrary SQL queries against their training data
- A `query` CLI command (e.g. `ox query "SELECT ..."`)
- A foundation for plugins — any analysis is just a SQL query
- No new dependencies (sqlite3 is in the stdlib)

The `.ox` file remains the source of truth. SQLite is a derived, ephemeral view — re-created from the parsed file each session. No caching, no sync issues.

**Schema direction:**

```
sessions(id, date, flag, name)
movements(id, session_id, name, note)
sets(id, movement_id, reps, weight_magnitude, weight_unit)
```

### Richer analysis

- Cycle tracking — micro/meso/macro periodization
- Exercise definitions feeding into analysis (e.g. grouping by movement pattern)
- Track total volume of a given excercise over time (for example, total volume of kb-swings on a weekly basis this year)

Create a plugin framework that allows users to write their own, some included ones might be:

- Estimated 1RM calculations from weight/rep data (useful for percentage-based programs like 5/3/1)
- Generate specific plans from a known progression (like the 4-week cycle in the Wendler 5/3/1 given a training max)

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

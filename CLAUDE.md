# Ox

Plain text training log parser and analyzer.
Uses a custom tree-sitter grammar to parse `.ox` log files into structured data for querying and analysis.

## Usage Notes
- `SPEC.md` is your guide for the goals, non-goals, and roadmap for this repo.
- If you edit `tree-sitter-ox/grammar.js`, regenerate and reinstall:
  ```bash
  cd tree-sitter-ox && tree-sitter generate && cd ..
  uv sync --reinstall-package tree-sitter-ox
  ```
  uv keys built wheels by version number, so it will not rebuild the C extension on its own — the package version never changes. `uv cache clean tree-sitter-ox && uv sync` is **not** sufficient: `uv sync` audits, sees the version already installed, and skips the rebuild. `--reinstall-package` is what forces it.
- Symptom of a stale C extension: a large, scattered wave of "Syntax error" diagnostic failures across `test_parse`/`test_db`/`test_integration` while `git status` is clean and `grammar.js` visibly contains the rule being rejected. Reinstall before investigating further.

## Commands

```bash
uv run pytest                  # run all tests
uv run pytest tests/test_parse.py  # run a specific test file
uv run ruff check src/ tests/  # lint
uv run ruff format src/ tests/ # format
```

## Project Structure

```
src/ox/
  parse.py      - Tree-sitter node → data structures (the core parser)
  data.py       - Dataclasses: TrainingSet, Movement, TrainingSession, TrainingLog, Note, WeighIn, StoredQuery, Diagnostic
  db.py         - In-memory SQLite layer: create_db(log) → Connection
  plugins.py    - Plugin discovery, registry, PluginContext, result types (TableResult, TextResult, PlotResult)
  sql_utils.py  - SQL helper utilities for plugins (parse_plugin_args, plugin_usage, _weight_sql_expr, _time_bin_expr)
  units.py      - Pint unit registry (shared instance)
  cli.py        - Click CLI with interactive REPL (run, query, tables, lint, reload)
  lsp.py        - LSP server: diagnostics, movement completion, comment folding
  lint.py       - Parse error collection for CLI lint command and LSP
  builtins/
    volume.py      - Volume over time plugin
    e1rm.py        - Estimated 1RM plugin (Brzycki/Epley)
    weighin.py     - Weigh-in stats/plot plugin (rolling average, trend, multi-scale)
    srpe.py        - Session RPE training load plugin (ACWR, monotony, strain)
    wendler531.py  - Wendler 5/3/1 cycle generator plugin
tests/
  conftest.py        - Shared fixtures (simple_log_*, weight_edge_cases, log_with_query_*, log_with_weigh_ins_*, weigh_in_multi_scale_*, simple_db, example_db)
  test_parse.py      - Weight/rep parsing
  test_data.py       - Data structures
  test_db.py         - SQLite schema, loading, views, queries
  test_reports.py    - SQL utils, volume plugin, arg parsing, plugin registry
  test_plugins.py    - Plugin registration, loading, builtins
  test_integration.py - End-to-end parsing
  test_weighin.py    - Weigh-in plugin (rolling avg, trend, table/plot/stats)
  test_notes.py      - Note parsing, session notes, DB population
  test_srpe.py       - sRPE plugin (training load, ACWR, monotony, strain)
  test_lint.py       - Diagnostic collection
tree-sitter-ox/
  grammar.js  - Tree-sitter grammar definition for .ox format
editors/
  vscode/     - VSCode extension for .ox syntax highlighting
examples/
  plugins/            - Example plugin scripts (wendler531.py)
  plugin_template.py  - Template for writing user plugins
docs/         - MkDocs documentation source
examples/
  example.ox   - Reference training log with all supported formats
  advanced.ox  - sRPE tracking example with 8 weeks of training data
```

## .ox File Format

```
# Comments start with #

# Single-line entry: date T movement: weight distance duration reps "note"
2025-01-10 T pullups: BW 5x10
2025-01-10 T plank: BW PT45S 3x1
2025-01-10 T run: 5km PT25M
2025-01-10 T farmer-carry: 32kg 40m 4x1

# Session block. Only `date:` is required, and it must come first.
@session
date: 2025-01-11
name: Upper Day
bench-press: 135lb 5x5
kb-oh-press: 24kg 5/5/5
@end

# Ad hoc session: no name needed
@session
date: 2025-01-10
pullups: BW 3x10
pushups: BW 3x15
@end

# Planned session, and session RPE: srpe: <rating> <duration> ["note"]
@session
date: 2025-01-15
name: Upper Day
completed: false
format: 5/3/1 wave
srpe: 5 PT45M "felt strong"
bench-press: 185lb 5x5
@end

# Weigh-in: date W weight [time] [scale]
2025-01-10 W 185lb T06:30 "home"

# Note: date note "text"
2025-01-10 note "deload week"

# Stored query: date query "name" "SQL"
2025-01-10 query "recent" "SELECT * FROM training LIMIT 10"

# Include another file
@include "other.ox"

# Movement definition
@movement squat
equipment: barbell
tags: squat, lower
note: back squat
@end

# Template block
@template "my-template"
squat: 185lb 5x5
bench-press: 135lb 5x5
@end

# Load a plugin
@plugin "my_plugin.py"

# Markers: T = training entry, W = weigh-in
# Session fields: date: (required, first), name:, completed:, format:, srpe:, note:
# completed: defaults to true; false marks a planned session
# Weight units: kg, lb, g, oz, stone, grain, and more (any pint-compatible mass unit)
# Weight formats: 24kg, BW, 24kg+32kg (combined), 24kg/32kg/48kg (progressive), 160/185/210lb (implied unit)
# Rep formats: 5x5 (sets x reps), 5/5/5 (per-set reps)
# Duration: ISO 8601 (PT30M, PT1H30M15S), progressive PT30S/PT25S/PT20S
# Distance: numeric + unit (m, km, ft, mi, etc.), progressive 100m/200m/400m or 100/200/400m
```

Weight, duration, and distance are independent per-set fields — a set may carry all of them at once.
Given once, a field broadcasts across every set; given as a `/`-list, it maps one value per set.
Set count comes from the rep scheme (`5x1` is five sets of one rep). With no rep scheme, the count is
the length of the longest `/`-list, defaulting to one set — so `run: PT30M` is a single 30-minute set.

Planning is expressed only by a session block's `completed: false`; a single-line entry always records
training that happened. Logs written in the pre-0.6 flag syntax (`*`, `!`, positional session headers,
`srpe: "5; PT45M"`) are converted by `scripts/migrate_ox.py`.

## Conventions

- Python 3.12, dependencies managed with uv
- Frozen dataclasses with `slots=True` for data structures
- `pint.Quantity` for all weight values (never raw numbers)
- Movement names are hyphenated lowercase (e.g. `kb-oh-press`, `bench-press`)
- `to_ox()` methods serialize back to .ox format (round-trip support)
- Tree-sitter nodes are processed in `parse.py`; data structures live in `data.py` — keep this separation
- All analysis features are plugins (builtins or user-defined). Plugins receive `PluginContext(db, log)` and return `TableResult`, `TextResult`, or `PlotResult`
- CLI commands: `plugins` to list available plugins, `query` for raw SQL. Plugins are invoked by name directly (e.g. `volume -m squat`)


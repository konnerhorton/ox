# Ox

Plain text training log parser and analyzer.
Uses a custom tree-sitter grammar to parse `.ox` log files into structured data for querying and analysis.

## Usage Notes
- `SPEC.md` is your guide for the goals, non-goals, and roadmap for this repo.
- If you edit `tree-sitter-ox/grammar.js` run `cd tree-sitter-ox && tree-sitter generate && cd ..` then reinstall with `uv cache clean tree-sitter-ox && uv sync`. The cache clean is required because uv caches built wheels by version number and won't rebuild the C extension otherwise.

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
  parse.py    - Tree-sitter node → data structures (the core parser)
  data.py     - Dataclasses: TrainingSet, Movement, TrainingSession, TrainingLog, Note, WeighIn, StoredQuery, Diagnostic
  db.py       - In-memory SQLite layer: create_db(log) → Connection
  reports.py  - Reports: volume, matrix; get_all_reports() merges builtin + plugin reports
  plugins.py  - Plugin discovery and registry (report + generator types)
  units.py    - Pint unit registry (shared instance)
  cli.py      - Click CLI with interactive REPL (stats, history, report, generate, query, tables, lint, reload)
  lsp.py      - LSP server: diagnostics, movement completion, comment folding
  lint.py     - Parse error collection for CLI lint command and LSP
  builtins/
    e1rm.py        - Estimated 1RM report (Brzycki/Epley)
    weighin.py     - Weigh-in stats/plot report (rolling average, trend, multi-scale)
    wendler531.py  - Wendler 5/3/1 cycle generator
tests/
  conftest.py        - Shared fixtures (simple_log_*, weight_edge_cases, log_with_query_*, log_with_weigh_ins_*, weigh_in_multi_scale_*, simple_db, example_db)
  test_parse.py      - Weight/rep parsing
  test_data.py       - Data structures
  test_db.py         - SQLite schema, loading, views, queries
  test_reports.py    - Reports, arg parsing, registry
  test_plugins.py    - Plugin registration, loading, builtins
  test_integration.py - End-to-end parsing
  test_weighin.py    - Weigh-in report (rolling avg, trend, table/plot/stats)
  test_notes.py      - Note parsing, session notes, DB population
  test_lint.py       - Diagnostic collection
tree-sitter-ox/
  grammar.js  - Tree-sitter grammar definition for .ox format
editors/
  vscode/     - VSCode extension for .ox syntax highlighting
examples/
  plugins/    - Example plugin scripts (wendler531.py)
docs/         - MkDocs documentation source
example/
  example.ox  - Reference training log with all supported formats
```

## .ox File Format

```
# Comments start with #

# Single-line entry: date flag exercise: weight reps "note"
2025-01-10 * pullups: BW 5x10

# Session block
@session
2025-01-11 * Upper Day
bench-press: 135lb 5x5
kb-oh-press: 24kg 5/5/5
@end

# Weigh-in: date W weight [time] [scale]
2025-01-10 W 185lb T06:30 "home"

# Note: date note "text"
2025-01-10 note "deload week"

# Stored query: date query "name" "SQL"
2025-01-10 query "recent" "SELECT * FROM training LIMIT 10"

# Include another file
@include "other.ox"

# Flags: * = completed, ! = planned, W = weigh-in
# Weight units: kg, lb, g, oz, stone, grain, and more (any pint-compatible mass unit)
# Weight formats: 24kg, BW, 24kg+32kg (combined), 24kg/32kg/48kg (progressive)
# Rep formats: 5x5 (sets x reps), 5/5/5 (per-set reps)
# Duration: ISO 8601 (PT30M, PT1H30M15S)
# Distance: numeric + unit (m, km, ft, mi, etc.)
```

## Conventions

- Python 3.12, dependencies managed with uv
- Frozen dataclasses with `slots=True` for data structures
- `pint.Quantity` for all weight values (never raw numbers)
- Exercise names are hyphenated lowercase (e.g. `kb-oh-press`, `bench-press`)
- `to_ox()` methods serialize back to .ox format (round-trip support)
- Tree-sitter nodes are processed in `parse.py`; data structures live in `data.py` — keep this separation

## Known Issues
- Progressive weights for the same movement require explicit units, this is a known bug and applicable tests are skipped.

# Ox

Plain text training log parser and analyzer.
Uses a custom tree-sitter grammar to parse `.ox` log files into structured data for querying and analysis.


## Usage Notes
- `SPEC.md` is your guide for the goals, non-goals, and roadmap for this repo.
- if you edit `tree-sitter/grammar.js` run `tree-sitter generate` then reinstall the package before doing any additional work.

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
  parse.py   - Tree-sitter node → data structures (the core parser)
  data.py    - Dataclasses: TrainingSet, Movement, TrainingSession, TrainingLog
  db.py      - In-memory SQLite layer: create_db(log) → Connection
  reports.py - Standard reports: volume_over_time, session_matrix, REPORTS registry
  units.py   - Pint unit registry (shared instance)
  cli.py     - Click CLI with interactive REPL (ox command)
  lsp.py     - LSP server for .ox files (ox-lsp command)
tests/
  conftest.py        - Shared fixtures (simple_log_content, weight_edge_cases, simple_db)
  test_parse.py      - Unit tests for weight/rep parsing
  test_data.py       - Unit tests for data structures
  test_db.py         - Tests for SQLite schema, loading, views, queries
  test_reports.py    - Tests for reports, arg parsing, registry
  test_integration.py - End-to-end parsing tests
tree-sitter-ox/
  grammar.js  - Tree-sitter grammar definition for .ox format
example/
  example.ox  - Reference training log with all supported formats
```

## .ox File Format

```
# Comments start with #

# Single-line entry: date flag exercise: weight reps "note"
2025-01-10 * pullups: BW 5x10

# Session block: multiple exercises in one session
@session
2025-01-11 * Upper Day
bench-press: 135lbs 5x5
kb-oh-press: 24kg 5/5/5
@end

# Flags: * = completed, ! = planned, W = weigh-in
# Weight formats: 24kg, 135lbs, BW (bodyweight), 24kg+32kg (combined), 24kg/32kg/48kg (progressive)
# Rep formats: 5x5 (sets x reps), 5/5/5 (per-set reps)
```

## Conventions

- Python 3.12, dependencies managed with uv
- Frozen dataclasses with `slots=True` for data structures
- `pint.Quantity` for all weight values (never raw numbers)
- Exercise names are hyphenated lowercase (e.g. `kb-oh-press`, `bench-press`)
- `to_ox()` methods serialize back to .ox format (round-trip support)
- Tree-sitter nodes are processed in `parse.py`; data structures live in `data.py` — keep this separation

## Known Issues
- Progressive weights for the same movement require explicit units, this is known bug and applicable tests are skipped.

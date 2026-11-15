# Tests

## Running

```bash
uv run pytest                                  # everything
uv run pytest tests/test_parse.py              # one file
uv run pytest tests/test_data.py -k bodyweight # matching tests
```

`uv run` builds the compiled grammar (`ox._grammar`) if `tree-sitter-ox/src/parser.c` changed. A wave of
unexpected "Syntax error" failures usually means a stale build: `uv sync --reinstall-package ox-train`.

## Layout

One test file per module or plugin (`test_parse.py`, `test_db.py`, `test_srpe.py`, …). A few that aren't
obvious from the name:

- `conftest.py`: shared fixtures, including small logs (`simple_log_*`, `log_with_*`), weight edge cases and
  ready-built databases (`simple_db`, and `example_db` from `examples/example.ox`).
- `test_reports.py`: SQL helpers, argument parsing, the plugin registry and the `volume` plugin.
- `test_add.py` drives `add` with a scripted prompt function; `test_cli_add.py` runs it end to end through
  prompt_toolkit pipe input, paced because completion is asynchronous.
- `smoke.py` isn't collected by pytest. It checks an installed wheel and is run by cibuildwheel and the
  release workflow.

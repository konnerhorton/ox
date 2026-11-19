# Ox

Plain text training log parser and analyzer.
Uses a custom tree-sitter grammar to parse `.ox` log files into structured data for querying and analysis.
Status and what's next: `STATUS.md`.

## Usage Notes
- `SPEC.md` is your guide for the goals, non-goals, and roadmap for this repo.
- Work follows the spec-driven-development process: each unit of work (feature, fix, decision) gets a
  branch and a `docs/work/<branch>.md` holding its intent, spec and plan. Files for merged units are history.
- `docs/work/TODO.md` is the backlog, referenced as "TODO #n".
- If you edit `tree-sitter-ox/grammar.js`, regenerate the parser:
  ```bash
  cd tree-sitter-ox && tree-sitter generate && cd ..
  ```
  The grammar is compiled into ox-train itself as `ox._grammar` (root `setup.py`). `[tool.uv] cache-keys`
  in `pyproject.toml` lists `parser.c`, so the next `uv sync` or `uv run` rebuilds the extension.
- Symptom of a stale C extension: a large, scattered wave of "Syntax error" diagnostic failures across `test_parse`/`test_db`/`test_integration` while `git status` is clean and `grammar.js` visibly contains the rule being rejected. Force a rebuild with `uv sync --reinstall-package ox-train` before investigating further.
- Releasing the VSCode extension (`editors/vscode`): bump `version` in `package.json`, add a `CHANGELOG.md`
  entry, then `npm install && npx -p node@22 -p @vscode/vsce -c "vsce package"` (system Node is 18, an apt
  package — don't replace it; `vsce` needs ≥20). Upload the `.vsix` at
  https://marketplace.visualstudio.com/manage via the extension's ⋯ → Update. No PAT: Azure DevOps rejects
  the personal Microsoft account ("does not exist in tenant 'Microsoft Services'").
- The VSCode extension deliberately ships no color theme: a theme replaces the user's wholesale and
  leaves other languages uncolored. Pick grammar scopes by checking how the built-in theme JSON
  (`/usr/share/code/resources/app/extensions/theme-defaults/themes/`) resolves them, not from
  memory. VS Code's defaults are now Dark 2026 / Light 2026, and `keyword.operator` is uncolored
  in all of them.
- The micro plugin (`editors/micro`) likewise ships no colorscheme. Its `syntax/ox.yaml` uses only groups that
  micro's built-in colorschemes define, checked against the `color-link` lines in the binary
  (`strings /usr/bin/micro | grep '^color-link'`). RE2 takes the first matching alternative, not the longest,
  so put longer alternatives (progressive weights) first.
- The REPL reads nothing from piped stdin ("Input is not a terminal"). To run a plugin from a script, call
  `ox.cli.load_log(path)` and then `PLUGINS[name]["fn"](ctx, **parse_plugin_args(params, args))`; `@plugin`
  plugins in the file are loaded by then.

## Commands

```bash
uv run pytest                  # run all tests
uv run pytest tests/test_parse.py  # run a specific test file
uv run ruff check src/ tests/  # lint
uv run ruff format src/ tests/ # format
```

## Project Structure

Where the layout isn't obvious from the file names:

```
src/ox/
  parse.py      - Tree-sitter node → data structures (the core parser)
  sql_utils.py  - Helpers for plugins: parse_plugin_args, plugin_usage, weight_sql_expr, time_bin_expr
  plot.py       - Thin facade over plotext (scatter, multi_line, bar); returns PlotResult lines
  completion.py - REPL tab completion, including add's line and name completers
  grammar.py    - LANGUAGE: the compiled grammar (C extension ox._grammar, built from _grammar.c by setup.py)
tests/
  conftest.py      - Shared fixtures (simple_log_*, log_with_*, weigh_in_multi_scale_*, simple_db, example_db)
  test_reports.py  - SQL utils, volume plugin, arg parsing, plugin registry
  test_cli_add.py  - add end to end through prompt_toolkit pipe input (paced: completion is async)
  smoke.py         - Installed-package smoke test (run by cibuildwheel and the release workflow, not pytest)
examples/
  example.ox       - Reference log: entries, sessions, movement definitions
  advanced.ox      - 8 weeks of sRPE-tracked training
  plugin_template.py, plugins/ - Starting points for user plugins
```

## .ox File Format

Every form, with examples: `docs/getting-started.md` (`@template` is only in the grammar). The notation:

```
# Comments start with #
2025-01-10 T pullups: BW 5x10            # single-line entry: date T movement: weight distance duration reps "note"
@session ... @end                         # session block; date: is required and comes first
2025-01-10 W 185lb T06:30 "home"         # weigh-in: date W weight [time] [scale]
2025-01-10 note "deload week"            # note
2025-01-10 query "name" "SQL"            # stored query
@include "other.ox"   @plugin "my_plugin.py"
@plugin "volume" "{'a': [1]}"   @plugin "my_plugin.py" "{...}"   # config: Python literal, may span lines
@movement squat ... @end   @template "name" ... @end

# Session fields: date: (required, first), name:, completed:, format:, srpe: <rating> <duration> ["note"], note:
# completed: defaults to true; false marks a planned session
# Weight: 24kg, BW, 24kg+32kg (combined), 24kg/32kg/48kg (progressive), 160/185/210lb (implied unit);
#   any pint-compatible mass unit
# Reps: 5x5 (sets x reps), 5/5/5 (per-set reps)
# Duration: ISO 8601 (PT30M, PT1H30M15S), progressive PT30S/PT25S/PT20S
# Distance: numeric + unit (m, km, ft, mi, etc.), progressive 100m/200m/400m or 100/200/400m
```

Weight, duration, and distance are independent per-set fields — a set may carry all of them at once.
Each applies to every rep in the set, so totals multiply by reps (`3x6 50yd` is 900yd, `3x5 PT30S` is 7m30s).
Given once, a field broadcasts across every set; given as a `/`-list, it maps one value per set.
Set count comes from the rep scheme (`5x1` is five sets of one rep). With no rep scheme, the count is
the length of the longest `/`-list, defaulting to one set — so `run: PT30M` is a single 30-minute set.

Planning is expressed only by a session block's `completed: false`; a single-line entry always records
training that happened.

## Conventions

- Python 3.12, dependencies managed with uv
- Frozen dataclasses with `slots=True` for data structures
- `pint.Quantity` for all weight values (never raw numbers)
- Movement names are hyphenated lowercase (e.g. `kb-oh-press`, `bench-press`)
- `to_ox()` methods serialize back to .ox format (round-trip support)
- Tree-sitter nodes are processed in `parse.py`; data structures live in `data.py` — keep this separation
- All analysis features are plugins (builtins or user-defined). Plugins receive `PluginContext(db, log)` and return `TableResult`, `TextResult`, or `PlotResult`
- Plugin param `name`s are Python identifiers; the CLI flag is the name with `_` → `-` (`start_date` → `--start-date`, the only accepted spelling)
- A plugin param named `movement` or `movements` gets movement-name completion in the REPL (`ox.completion`)
- CLI commands: `plugins` to list available plugins, `query` for raw SQL. Plugins are invoked by name directly (e.g. `volume -m squat`)


# hyphen-flags: multi-word plugin flags use hyphens

Resolves TODO #4.

## Intent

### Goal
A plugin parameter named `start_date` is passed on the command line as `--start-date`, and only
that way. Usage strings and error messages show the hyphenated form.

### Why
- `docs/plugins.md` documents `wendler531 --start-date 2026-03-01`, but `parse_plugin_args`
  (`src/ox/sql_utils.py`) matches the long flag against the param name exactly, so only
  `--start_date` works and the documented command fails with "Unknown flag".
- Hyphens are the usual style on the command line (GNU long options, Click, argparse all map
  `--start-date` to `start_date`), and ox's own vocabulary is already hyphenated (movement names,
  time bins like `weekly-num`).
- Fixing it in the parser fixes every multi-word param at once: `wendler531`'s `start_date` and
  `e1rm`'s `y_step` / `x_scale`, plus any user plugin's.

### Constraints
- A param's `name` stays a Python identifier, since it's the keyword argument the plugin function
  receives. Only the flag is derived from it: `name.replace("_", "-")`.
- Short flags (`-d`) are unchanged.

### Out of scope
- Renaming params or changing the param-spec format.
- Any other change to the argument syntax (`--flag=value`, boolean flags, etc.).

### SPEC sections touched
- None. Recorded as a convention in `CLAUDE.md` (plugin authoring), and `CHANGELOG.md` gets an
  entry because `--start_date`, `--y_step` and `--x_scale` stop working.

### Decisions (intent review, 2026-11-04)
1. **Hyphens only.** The underscore form (`--start_date`) is rejected from now on, so each flag has
   one spelling.
2. **"Did you mean" hint.** When an unknown long flag contains `_` and its hyphenated form is a real flag, the
   error says so: `Unknown flag: --start_date (did you mean --start-date?)`. That covers anyone
   who learned the old spelling, without accepting it.

## Plan

One build commit, with close-out included.

1. **`hyphen-flags: spell multi-word plugin flags with hyphens` (Sonnet)**
   - `src/ox/sql_utils.py`: add `_flag_name(param) -> str` returning `param["name"].replace("_", "-")`.
     Use it in `parse_plugin_args` for the long-flag match, the "Missing required flag(s)" message
     and the "did you mean" hint (decision 2), and in `plugin_usage` for both the flag and its
     placeholder (`[-d/--start-date <start-date>]`). Update the `parse_plugin_args` docstring to
     state the rule.
   - `tests/test_reports.py`, in the `parse_plugin_args` / `plugin_usage` tests, with a param spec
     containing `start_date`:
     - `--start-date 2026-03-01` parses to `{"start_date": "2026-03-01"}`;
     - `--start_date 2026-03-01` raises `ValueError` matching `did you mean --start-date`;
     - a missing required `start_date` names `--start-date`;
     - `plugin_usage` renders `--start-date <start-date>`;
     - an unknown flag with no hyphenated match keeps the plain `Unknown flag: --foo` message.
   - `tests/test_wendler531.py` and any e1rm tests: switch any `--start_date` / `--y_step` /
     `--x_scale` uses to the hyphenated form (`grep -rn -- "--[a-z]*_" tests/`).
   - Docs: `docs/plugins.md` already shows `--start-date`; check the e1rm section and the
     "writing plugins" section, and add one sentence there that a param named `start_date` becomes
     `--start-date`. Same sentence in `examples/plugin_template.py`'s param comment if it has one.
   - Close-out: delete TODO #4 from `docs/work/TODO.md`; add a `CLAUDE.md` Conventions line
     ("Plugin param `name`s are Python identifiers; the CLI flag is the name with `_` → `-`");
     add a line to the unreleased section of `CHANGELOG.md` (create it if no other unit has).
   - `uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest`.

# v0.5.0

First release after v0.2.0. This is a large jump — the reports system has been replaced by a proper plugin architecture, parsing has grown in several directions, and the CLI, LSP, and docs have all been reworked. The notes below group changes by theme rather than by commit.

## Breaking changes

- **`@exercise` blocks are now `@movement` blocks.** The block type, the parsed dataclass (`MovementDefinition`), and the tree-sitter grammar all use the new name. Update any `.ox` logs that use the old directive.
- **The `run` REPL command has been removed.** Use `plugins` to list available plugins, and invoke a plugin directly by name (e.g. `volume -m squat`). Avoid naming a custom plugin the same as a built-in command (`query`, `tables`, `reload`, `lint`, `plugins`, `help`, `exit`, `quit`) — built-ins win the name lookup.
- **Reports have been replaced by plugins.** The previous `report` / `generate` CLI commands are gone. The `stats` and `history` plugins were removed; other analyses moved to the new plugin system.
- **Unit normalization.** `lbs` has been unified to `lb`. The grammar now accepts any pint-compatible mass unit (`g`, `oz`, `stone`, `grain`, `kg`, `lb`, …).
- **Time tokens are ISO 8601.** Durations are written `PT30M`, `PT1H30M15S`, etc.

## New plugins

Four built-in plugins ship with this release:

- **`e1rm`** — Estimated 1RM progression from sets tagged with `^rm`, with Brzycki and Epley formulas and table/plot output.
- **`weighin`** — Body-weight tracking with rolling average, trend, multi-scale breakdown, and plot.
- **`srpe`** — Session RPE training load, AU totals per time bin, and ACWR / monotony / strain output modes.
- **`wendler531`** — Generates a 4-week Wendler 5/3/1 cycle as planned sessions (`!` flag), with optional `^rm` tagging and configurable start date and unit.

The existing `volume` plugin remains.

## Plugin system

- Plugins are first-class. A plugin exports `register()` and its functions receive `PluginContext(db, log)`, returning `TableResult`, `TextResult`, or `PlotResult`.
- Load user plugins from your log with `@plugin "path/to/plugin.py"`. Paths resolve relative to the `.ox` file.
- User plugins loaded via `@plugin` override built-ins with the same name.
- On startup, the CLI prints the list of user plugins that were loaded.
- The REPL lists plugins via `plugins` and invokes them by name.

## Parser and language features

- **Movement definitions** — `@movement name … @end` blocks with `equipment`, `tags`, `note`, and `url` fields. Parsed into `MovementDefinition` and exposed on `TrainingLog.movement_definitions`.
- **Notes are first-class objects** — both single-line `note "…"` entries and in-session `note:` lines flow through `Note` / session notes and into the database.
- **Stored queries** — `2025-01-10 query "name" "SELECT …"` lines are parsed and surfaced via the `query` command by name.
- **Weigh-ins** — `date W weight [time] [scale]` lines parse into `WeighIn` dataclasses and populate a `weigh_ins` table.
- **Implied units in progressive weights** — `160/185/210lb` now parses correctly; each segment inherits the nearest following unit.
- **`BW` inside progressions** — `BW/24kg/32kg` and similar forms work without lint errors.
- **Parse diagnostics / linter** — parse errors are collected on load and surfaced via the `lint` command and through the LSP.
- **SQLite `REGEXP`** — available in `query` expressions.
- **Short flags** on plugin parameters (e.g. `-m`, `-b`).

## CLI

- `plugins` — new command to list available plugins.
- Plugins are invoked directly by name. Running a plugin with no args prints its usage.
- `reload` — re-parse the current log from disk without leaving the REPL. Reprints parse diagnostics and re-announces loaded user plugins.
- `tables -h` — show column details alongside the table/view list.
- `query name` — recall a stored query by name, or run inline SQL with `query SELECT …`.
- `--version` reads from `pyproject.toml` so there is a single source of truth.

## Plots

All built-in plots now route through a small `plot` facade over `plotext`, giving consistent axes, markers, and legends across `e1rm`, `weighin`, and `srpe`. The earlier hand-rolled ASCII plots are gone.

## Editor support

- **VSCode** — syntax highlighting updated to cover `@movement`, `@session`, `@template`, `@plugin`, `@include`, `note` entries, `query` entries, and the `equipment`/`tags`/`note`/`url` fields inside movement definitions. Comment folding is fixed.
- **LSP** — movement-name autocomplete is populated from `@movement` blocks in the parsed log; diagnostics surface parse errors and invalid `@include` paths; comment folding is supported.

## Documentation

- `docs/getting-started.md` covers movement definitions, session-level notes, stored queries, and `@plugin` loading.
- `docs/plugins.md` documents every built-in plugin, loading rules, the plugin API, and reserved names.
- `docs/api-reference.md` now lists every dataclass (including `MovementDefinition`), the full `TrainingLog` surface, and the plugin result types.
- `docs/cli-reference.md` reflects the current command set.
- `docs/editor-support.md` clarifies that VSCode is the only shipped extension; Neovim and Helix users can wire up the grammar and `ox-lsp` directly.

## Fixes

- `e1rm` only considers completed sessions.
- Progressive weights with `BW` no longer trigger lint errors.
- Weekly time bins default to Sunday dates.
- Single-line sessions now use the movement name as the session name.

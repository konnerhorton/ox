# plugin-config: configure a plugin from the log with `@plugin "<name>" "<config>"`

## Intent

### Goal
A log can configure any plugin, builtin or user, with `@plugin "<name>" "<config>"`, or on the line that loads a user
plugin's file, `@plugin "<file>.py" "<config>"`. The config is a Python literal that may span lines. The plugin reads its parsed config from the log it is given, and lint and the LSP report a
config that can't be read while you edit:

```
@plugin "plugins/mix.py" "{
  'categories': ['strength', 'conditioning', 'skill'],
}"
@plugin "summary" "{'panels': ['sessions -n 5', 'mix --since 8w']}"
```

### Why
- `repl-summary` (decision 13) needs it first, and so does `mix`: each grouping a plugin uses (categories, skill
  groups) is a list of tags or name patterns in that plugin's config, because the tooling assumes no tag or naming
  convention (`repl-summary` decision 14). Evidence: tagging the 117 movements in the author's log showed that one
  person's conventions (base-equipment-variant names, one category tag, family tags only where names can't group)
  don't belong in ox.
- Today a plugin has no settings at all: everything is a command-line argument typed each time.
- Config in the log, not beside it: the log is the source of truth (SPEC "Core Principles"), the settings travel with
  it, and lint and the LSP can check them while you edit. Beancount configures its plugins the same way
  (`plugin "module" "config"`).

### Constraints
- **The smallest grammar change that works.** `@plugin` gains an optional second string. No new directive or block.
- **A first argument ending in `.py` loads a file,** as today, relative to the `.ox` file that holds it; any other
  first argument names a plugin being configured (`repl-summary` decision 1, amended by decision 6 here).
- **The config is a Python literal read with `ast.literal_eval`** (`repl-summary` decision 2): multi-line, inner strings
  in single quotes, so lists and dicts work. What its keys mean is the plugin's own business; ox only parses it.
- **`PluginContext` stays `(db, log)`.** The config reaches the plugin through the log, so user plugins get no second
  channel and the plugin signature doesn't change.
- **No new dependencies.**
- **Existing logs keep working.** `@plugin "x.py"` behaves exactly as now.

### Out of scope
- Any plugin that reads a config. `summary`, `mix` and the skill-maintenance groups are their own units; this one ships
  the mechanism and its docs, tested with a fixture plugin.
- Checking a config's keys or types against what the plugin expects (a schema a plugin declares). Each plugin validates
  its own; a declared schema can come later if several plugins want lint to check them.
- A user-level config file (e.g. `~/.config/ox/`), and config passed on the command line.
- `@include` and every other directive: unchanged.

### SPEC sections touched
- "Core Principles": none changed; follows "Plain text is the source of truth".
- "Non-Goals", "No proprietary format extensions": the config is a Python literal inside an ordinary quoted string,
  readable with no tooling; this stays within it.
- New cross-cutting decision for `SPEC.md`: plugins are configured from the log with `@plugin "<name>" "<config>"`; the
  config is a Python literal that ox parses and the plugin interprets. Later plugins configure the same way.
- Other files: `tree-sitter-ox/grammar.js`, `parse.py`, `data.py` (`TrainingLog`), `plugins.py`, `lint.py`/LSP,
  `editors/vscode` TextMate grammar, `editors/micro/syntax/ox.yaml`, `docs/plugins.md`, `docs/getting-started.md`,
  `CLAUDE.md` (format notation), `CHANGELOG.md`.

### Decisions (intent review, 2026-11-19)
1. **The config gets its own multi-line string token:** `"`, then anything but `"`, then `"`, newlines allowed.
   `quoted_string` and `file_path` stay single-line. A config can't contain `"`; inner strings use `'`. Cost accepted:
   an unclosed quote swallows the rest of the file as one parse error at the directive. VSCode's TextMate grammar and
   micro's `syntax/ox.yaml` get whatever rules highlight it correctly across lines.
2. **A plugin reads its config with `log.plugin_config(name)`,** which returns the parsed value, or `None` when the log
   doesn't configure that name. Configs in `@include`d files count, as their `@plugin` loads already do. Parsed once
   at load, so a plugin never sees the raw string.
3. **The same plugin configured twice: the first directive wins** (in load order, includes in place). Lint flags a
   name configured twice. A plugin configured on its file's line and again by name is also configured twice; lint
   can't see that (decision 5), so the REPL warns at load.
4. **A config that doesn't parse is a lint and LSP error at the directive.** Loading the log logs a warning and treats
   that plugin as unconfigured, so the REPL still starts.
5. **Lint and the LSP check configured names only against the builtins,** since they don't execute user plugin files,
   and stay silent on other names. The REPL warns at load, once user plugins are registered:
   `config for unknown plugin 'x'`.
6. **A config after a `.py` path configures the plugin that file registers** (decision 8), so a user plugin is loaded
   and configured in one line. Amends `repl-summary` decision 1, which kept loading and configuring on separate lines
   because a file could register several plugins. Builtins have no file, so they are configured by name. The one
   misused form left is a name with no config (`@plugin "mix"` does nothing), a lint error.
7. **Files keep their `.py`; names are bare,** so each line says whether it loads a file. Considered: bare words
   everywhere, appending `.py` to find a file for any name that isn't a builtin. Rejected: a name couldn't tell
   "configure the builtin" from "load the file that overrides it" without checking the disk, so adding a file would
   change what an existing line means, and every existing `@plugin "x.py"` would break.
8. **One file, one plugin.** Every plugin file in the repo already registers exactly one (the builtins,
   `examples/plugin_template.py`, `examples/plugins/wendler531.py`), and the rule makes a config after a `.py` path
   unambiguous. `register()` may return a single descriptor dict (documented) or a one-item list (existing files keep
   loading). A list of more than one is a load warning naming the file, and nothing from it loads, rather than
   silently dropping the rest. Builtins follow the same rule. Not decided here: requiring the plugin's name to match
   its file name, which would let lint know user plugin names without running them (decisions 3 and 5); with one
   plugin per file it can be added later without breaking anything.

## Spec

### Changes
- **`tree-sitter-ox/grammar.js`:** `plugin_directive` becomes `"@plugin"`, `field("target", $.file_path)`,
  `optional(field("config", $.plugin_config))`, `optional("\n")`. New token `plugin_config: /"[^"]*"/`, newlines
  allowed (D1). The field is renamed `path` → `target` because a name isn't a path. Regenerate the parser.
- **`src/ox/data.py`:** new frozen `PluginDirective(target: str, config: str | None, file: Path, line: int)`; `config`
  is the raw text between the quotes, `file` the absolute path of the `.ox` file holding it, `line` 1-based; property
  `loads_file` is `target.endswith(".py")`. `TrainingLog.plugin_paths` is replaced by
  `plugin_directives: tuple[PluginDirective, ...]` (load order), with `plugin_paths` kept as a property returning the
  targets of file directives. New field `plugin_configs: dict[str, object]` (empty by default) and method
  `plugin_config(name) -> object | None`.
- **`src/ox/parse.py`:** `process_plugin_directive(node, file)` returns a `PluginDirective`.
- **`src/ox/cli.py`:** `_parse_single_file` and `_load_recursive` carry directives instead of path strings.
  `load_log` sets the configs with `dataclasses.replace(log, plugin_configs=load_plugins(log))` before building the
  `PluginContext`. `print_load_summary` prints each entry of `LOAD_WARNINGS` as a yellow line.
- **`src/ox/plugins.py`:**
  - `read_plugin_config(text) -> object`: `ast.literal_eval`, raising `ValueError` with a one-line reason for any
    failure (syntax error, or a non-literal such as a name or call). Used by loading and by lint.
  - `load_plugins(log=None) -> dict[str, object]`: loads builtins, then each file directive resolved against its own
    `directive.file`, then returns the configs (rules below). The `base_path` parameter goes.
  - `_register_descriptors` accepts a dict or a list; a list longer than one is refused (D8).
  - New module-level `LOAD_WARNINGS: list[str]`, cleared by `load_plugins`, beside `PLUGINS` and `USER_PLUGINS`.
- **`src/ox/lint.py`:** `collect_diagnostics` adds plugin checks (below). The LSP gets them through
  `collect_diagnostics` with no change of its own.
- **`editors/vscode/syntaxes/ox.tmLanguage.json`:** the plugin directive becomes a `begin`/`end` rule: begins at
  `@plugin`, the target and an optional opening config quote; the config to its closing `"` is
  `string.quoted.double.ox`, across lines. The single-line form keeps its current scopes. Bump `version` in
  `package.json` with a `CHANGELOG.md` entry; uploading the `.vsix` is by hand after merge.
- **`editors/micro/syntax/ox.yaml`:** a region from a config's opening quote to its closing one, `constant.string`,
  so lines inside a multi-line config stay one color.
- **`docs/plugins.md`:** "Loading" gains the config forms; new "Configuring a plugin" section (both forms, the literal
  rules, first one wins, how a plugin reads `ctx.log.plugin_config(name)`); "Writing a Plugin" shows `register()`
  returning one dict and states one file, one plugin.
- **`docs/getting-started.md`** "Loading plugins", **`CLAUDE.md`** format notation: the config forms.
- **`SPEC.md`** (changed in this commit): new section "Plugins" with the cross-cutting decisions: every analysis
  feature is a plugin; one file registers one plugin; a plugin is configured from the log, by name or on its file's
  line; the config is a Python literal that ox parses and the plugin interprets; the first config wins.
- **`CHANGELOG.md`** Unreleased: configuring plugins; the include path fix; one plugin per file (a file registering
  several no longer loads).

### Decisions
1. **Config resolution, in `load_plugins`.** Walk `plugin_directives` in load order. A file directive with a config
   configures the plugin its file registered; if the file failed to load, no extra warning (its load failure already
   says so). A name directive with a config configures that name. A name directive without one is ignored at load
   (lint reports it). Each config is read with `read_plugin_config`; one that fails adds
   `<file>:<line>: config for '<name>' doesn't parse: <reason>` to `LOAD_WARNINGS` and leaves that plugin
   unconfigured (D4). A name already configured adds `<file>:<line>: '<name>' is already configured at <file>:<line>;
   this config is ignored` (D3). After all directives, a configured name not in `PLUGINS` adds
   `<file>:<line>: config for unknown plugin '<name>'` (D5). A `None` config is indistinguishable from none.
2. **Load order is the existing one:** a file's own directives in order, then each `@include`d file's, in include
   order. Decision 3 said "includes in place"; keeping the existing order avoids also changing which user plugin
   overrides which.
3. **Plugin paths in included files resolve against the file that holds them,** as `docs/plugins.md` already says.
   Today they resolve against the root log (`plugins.py`, `_load_from_log_directives`). Fixed here because directives
   now carry their file.
4. **One file, one plugin** (D8): `register()` returning a dict or a one-item list registers it; a list of more than
   one adds `<path> registers <n> plugins; a file may register one. Not loaded.` to `LOAD_WARNINGS` and registers
   nothing. An empty list registers nothing, as now.
5. **Lint checks, per file** (lint and the LSP see one file at a time):
   - A config that `read_plugin_config` rejects: error `Plugin config doesn't parse: <reason>`, spanning the config.
   - A name directive with no config: error `@plugin "<name>" does nothing: add a config, or a .py path to load a
     file`, spanning the target.
   - A name configured a second time in the same file: warning `'<name>' is already configured on line <n>; this
     config is ignored`, spanning the target. Across files, and file-plus-name, only the REPL warns.
   - No unknown-name check. D5 limits lint to builtin names, but any other name may be a user plugin, so in practice
     lint reports none; the REPL's load warning covers it.
6. **Unclosed config quote.** The token runs to the next `"` in the file, so the config ends in the wrong place and
   fails to parse (an error at the directive), with syntax errors after it. No special hint: the config error points
   at the cause.
7. **Not in scope:** `to_ox()` for directives (none exists today), an LSP check that a `.py` path exists, completion
   after `@plugin`.

### Acceptance criteria
1. **Grammar:** `@plugin "mix"` + a config on one line, and a config spanning four lines with single-quoted strings,
   `[`, `{`, `#` and blank lines inside, each parse with no error into `plugin_directive` with `target` and `config`
   fields. `@plugin "plugins/x.py"` still parses, with no `config`. Entries after a multi-line config parse normally.
2. **Directive data:** parsing a log gives `PluginDirective`s with the raw config, the absolute file and the 1-based
   line; `plugin_paths` returns only the `.py` targets.
3. **Reading a config:** with a fixture plugin file and `@plugin "fixture.py" "{'a': [1, 2]}"`,
   `ctx.log.plugin_config("fixture")` returns `{'a': [1, 2]}`; with the config given by name instead, the same; an
   unconfigured plugin returns `None`. A builtin configured by name (`@plugin "volume" "{'x': 1}"`) returns its value.
4. **Includes:** a config in an included file is read; a `.py` path in `sub/inc.ox` loads `sub/plugins/x.py` (D3).
5. **First wins:** two name configs for one plugin, in one file and across an include, and a file config followed by a
   name config: the first value is returned and `LOAD_WARNINGS` has one entry per ignored config naming both lines.
6. **Unparsable config:** `"{'a': [}"` and `"open('x')"` leave the plugin unconfigured, add one warning each, and the
   REPL still starts; `query` works.
7. **Unknown name:** `@plugin "nope" "{}"` adds `config for unknown plugin 'nope'`; no lint diagnostic.
8. **One file, one plugin:** a file returning one dict loads; a one-item list loads; a two-item list adds the warning
   and registers neither. Every builtin's `register()` returns exactly one descriptor.
9. **Load summary:** `print_load_summary` prints each `LOAD_WARNINGS` entry in yellow after the counts.
10. **Lint:** the three checks of decision 5 report the stated severity, message and span, through `lint` and through
    the LSP's `get_diagnostics`; a valid config, and a config after a `.py` path, report nothing.
11. **Highlighting (checked by eye):** in VS Code and micro, a four-line config is string-colored on every line,
    `@plugin` and the target keep their colors, and the line after the closing quote is colored normally. A
    single-line `@plugin "x.py"` looks as before.
12. **No regressions:** existing `@plugin "x.py"` logs load the same plugins; full test suite and ruff pass.

## Plan

Six build commits in two sessions: steps 1–3 on Sonnet (plumbing and highlighting, where the spec fixes the shapes
and tests decide), then steps 4–6 on Opus (config resolution, lint messages, docs and close-out). Each commit passes
`uv run pytest` and `uv run ruff check src/ tests/`.

### 1. `plugin-config: parse @plugin configs into PluginDirective` (Sonnet)
- `tree-sitter-ox/grammar.js`: `plugin_directive` gets `field("target", $.file_path)` and
  `optional(field("config", $.plugin_config))`; new token `plugin_config: ($) => /"[^"]*"/`. Regenerate the parser,
  then `uv sync --reinstall-package ox-train`. Risk: if the lexer confuses `plugin_config` with `quoted_string` or
  `file_path`'s `"`, give `plugin_config` a `token(prec(...))`; nothing else may start with `"` after a target.
- `tree-sitter-ox/test/corpus/plugin_directive.txt` (new): the forms of AC 1 (no config; one-line config; four-line
  config with `'`, `[`, `{`, `#` and a blank line; an entry after it).
- `src/ox/data.py`: `PluginDirective` (frozen, slots) with `loads_file`; `TrainingLog.plugin_directives` replaces the
  `plugin_paths` field, which becomes a property.
- `src/ox/parse.py`: `process_plugin_directive(node, file)` returns a `PluginDirective` (raw config without its
  quotes, `line = start_point[0] + 1`).
- `src/ox/cli.py`: `_parse_single_file`/`_load_recursive`/`parse_file` carry directives. `load_plugins` is unchanged
  in this commit and still reads `plugin_paths` against the root log, so behavior is the same.
- `tests/test_plugins.py`: `_make_log` builds `PluginDirective`s.
- Tests: `tree-sitter test` and `tests/test_parse.py` (`TestPluginDirective`: fields, absolute file, 1-based line,
  `plugin_paths` only `.py` targets, an entry after a multi-line config is parsed) prove AC 1, 2; the existing suite,
  AC 12 so far.

### 2. `plugin-config: one plugin per file` (Sonnet)
- `src/ox/plugins.py`: `LOAD_WARNINGS: list[str]`, cleared by `load_plugins`. `_register_descriptors` takes a dict or
  a list; a list of more than one appends `<path> registers <n> plugins; a file may register one. Not loaded.` and
  registers nothing (spec decision 4). Builtins keep their one-item lists.
- `tests/test_plugins.py`: `test_multiple_descriptors_in_one_call` becomes the refusal test; add dict and one-item
  list cases, an empty list, and a test that every builtin's `register()` yields exactly one descriptor (AC 8).

### 3. `plugin-config: highlight multi-line configs in VS Code and micro` (Sonnet)
- `editors/vscode/syntaxes/ox.tmLanguage.json`: `plugin-directive` becomes `patterns` of a `begin`/`end` rule
  (`^(@plugin)\s+("[^"]+")\s+(")` … `"`, body `string.quoted.double.ox`) before the existing single-line `match`.
- `editors/micro/syntax/ox.yaml`: a `constant.string` region starting at a config's opening quote after
  `@plugin "<target>"` and ending at `"`; check that `@plugin` keeps `preproc` and the target stays a string.
- `editors/vscode/package.json` version 0.2.0 → 0.3.0; `editors/vscode/CHANGELOG.md` entry.
- Tests: none automated. AC 11 is checked by eye at the end of this session, in VS Code (extension host via F5, or the
  packaged `.vsix`) and in micro (copy `syntax/ox.yaml` into `~/.config/micro/syntax/`), with a file holding a
  single-line `@plugin "x.py"`, a one-line config and a four-line config followed by an entry. The user confirms.

### 4. `plugin-config: resolve plugin configs when the log loads` (Opus)
- `src/ox/plugins.py`: `read_plugin_config(text)` (`ast.literal_eval`; `SyntaxError`/`ValueError`/`TypeError` →
  `ValueError` with one-line reason). `load_plugins(log=None) -> dict[str, object]`: builtins, then each file
  directive resolved against `directive.file.parent` (spec decision 3), recording which name each file registered;
  then the config walk of spec decision 1, then the unknown-name pass. `_load_from_log_directives` and `base_path` go.
- `src/ox/data.py`: `TrainingLog.plugin_configs: dict[str, object]` (default empty) and `plugin_config(name)`.
- `src/ox/cli.py`: `load_log` does `log = replace(log, plugin_configs=load_plugins(log))` before the context;
  `print_load_summary` prints each `LOAD_WARNINGS` entry in yellow after the counts, `markup=False` for the text.
- `tests/test_plugins.py`: callers of `load_plugins(log, base)` move to logs on disk loaded through `load_log`, with
  a fixture plugin file written to `tmp_path`.
- Tests, in a new `TestPluginConfig` class through `load_log`: AC 3 (file config, name config, unconfigured `None`,
  builtin `volume`), AC 4 (config in an include; `sub/inc.ox` loading `sub/plugins/x.py`), AC 5 (three duplicate
  cases, one warning each naming both lines), AC 6 (both bad configs; `ctx.db` answers a query), AC 7, AC 9 (`print_load_summary`
  output through `capsys`, as in `tests/test_cli.py`).

### 5. `plugin-config: lint plugin directives` (Opus)
- `src/ox/lint.py`: `_plugin_diagnostics(root, lines)` called from `collect_diagnostics`, skipping directives with
  errors: the three checks of spec decision 5, with their severities and messages. The config span runs from its
  start to its end point, converted to characters per row (it can span lines, so `_char_span` doesn't fit); the
  target span covers the quoted target.
- Tests: `tests/test_lint.py` for each check's severity, message and span, and silence on a valid config and on a
  config after a `.py` path; `tests/test_lsp.py` for one of each through `get_diagnostics` (AC 10). An unclosed config
  quote (spec decision 6) yields the parse error at the directive.

### 6. `plugin-config: document plugin configs, close out` (Opus)
- `docs/plugins.md`, `docs/getting-started.md`, `CLAUDE.md` format notation, as in the spec;
  `examples/plugin_template.py` and `examples/plugins/wendler531.py` return one dict.
- Check `SPEC.md` "Plugins" against what was built.
- Close-out: `CHANGELOG.md` Unreleased (configuring plugins, the include path fix, one plugin per file);
  `STATUS.md` (clear "In progress", move plugin-config to Done, set Next from `repl-summary` decision 13);
  `docs/work/TODO.md` for anything deferred with a trigger (plugin name matching its file name, D8; a declared config
  schema). AC 12: full suite and ruff. Then merge with `--no-ff` (approval), and upload the `.vsix` by hand.

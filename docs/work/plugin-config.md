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

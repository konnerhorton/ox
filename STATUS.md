# Status

**Next:** shared time windows (`--since 8w`), the next unit `repl-summary` depends on (its decision 13).

Last checkpoint: 1, after micro-syntax, 2026-11-15, `e9d430c`.

## In progress

None.

## Open

- **Planned sessions** (`completed: false`): parsed and queryable, but no analysis treats them specially.
- **Session formats** (`format:`): a first vocabulary, checked by `formats`, lives in `ox.formats`; the grammar,
  LSP and `lint` don't know it yet, and the parsed fields aren't in SQL.
- **Template blocks** (`@template`): the grammar parses them, nothing processes them, and `format:` has no
  link to them (TODO #6).
- **`repl-summary`** (branch; intent rewritten, spec predates the rewrite): a summary of `rich` panels when
  the REPL starts. Parked until its prerequisite units are merged (decision 13: time windows, `movements`, `mix`,
  `srpe` load output, `progress`; `plugin-config` is done). The author's log is migrated to tagged `@movement`
  definitions, which those units were waiting on.

## Done

- **Format and parser:** tree-sitter grammar compiled into ox as `ox._grammar`; sessions, single-line
  entries, weigh-ins, notes, stored queries, `@include`, `@movement`, `@plugin`; weight, duration and
  distance as per-set fields; first-class `srpe:`; `to_ox()` round-trip.
- **Data and analysis:** in-memory SQLite layer; plugin system with builtins `volume`, `e1rm`, `weighin`,
  `srpe`, `wendler531`, `formats` (checks `format:` against its vocabulary); plots through `ox.plot`.
- **Plugin config:** `@plugin "<name>" "<config>"` (or a config after a `.py` path), a Python literal read by
  `ctx.log.plugin_config(name)`; one plugin per file; lint, LSP and highlighting.
- **CLI:** REPL with `add`, `plugins`, `query`, `tables`, `lint`, `reload`, plugins by name, and
  context-aware tab completion.
- **Editors:** LSP (diagnostics, completion, folding); VSCode extension on the Marketplace
  (`konnerhorton.ox-training-log`); micro plugin, installed by hand.
- **Distribution:** on PyPI as `ox-train` (v0.6.1); a `v*` tag releases through
  `.github/workflows/release.yml`. MkDocs site at konnerhorton.github.io/ox.

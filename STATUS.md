# Status

**Next:** `plugin-config`, the first unit `repl-summary` depends on (its decision 13): config for a plugin
through `@plugin "<name>" "<config>"`.

Last checkpoint: 1, after micro-syntax, 2026-11-15, `e9d430c`.

## In progress

- `plugin-config` (branch): intent, spec and plan committed in `docs/work/plugin-config.md`. Next: build steps
  1–3 in a new Sonnet session, then 4–6 on Opus.

## Open

- **Planned sessions** (`completed: false`): parsed and queryable, but no analysis treats them specially.
- **Session formats** (`format:`): a first vocabulary, checked by `formats`, lives in `ox.formats`; the grammar,
  LSP and `lint` don't know it yet, and the parsed fields aren't in SQL.
- **Template blocks** (`@template`): the grammar parses them, nothing processes them, and `format:` has no
  link to them (TODO #6).
- **`repl-summary`** (branch; intent rewritten, spec predates the rewrite): a summary of `rich` panels when
  the REPL starts. Parked until its prerequisite units are merged (decision 13: `plugin-config`, time windows,
  `movements`, `mix`, `srpe` load output, `progress`). The author's log is migrated to tagged `@movement`
  definitions, which those units were waiting on.

## Done

- **Format and parser:** tree-sitter grammar compiled into ox as `ox._grammar`; sessions, single-line
  entries, weigh-ins, notes, stored queries, `@include`, `@movement`, `@plugin`; weight, duration and
  distance as per-set fields; first-class `srpe:`; `to_ox()` round-trip.
- **Data and analysis:** in-memory SQLite layer; plugin system with builtins `volume`, `e1rm`, `weighin`,
  `srpe`, `wendler531`, `formats` (checks `format:` against its vocabulary); plots through `ox.plot`.
- **CLI:** REPL with `add`, `plugins`, `query`, `tables`, `lint`, `reload`, plugins by name, and
  context-aware tab completion.
- **Editors:** LSP (diagnostics, completion, folding); VSCode extension on the Marketplace
  (`konnerhorton.ox-training-log`); micro plugin, installed by hand.
- **Distribution:** on PyPI as `ox-train` (v0.6.1); a `v*` tag releases through
  `.github/workflows/release.yml`. MkDocs site at konnerhorton.github.io/ox.

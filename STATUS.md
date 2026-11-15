# Status

**Next:** `format-vocabulary`, a vocabulary for the session `format:` field, parsed by a builtin plugin. Its
intent is on main (`docs/work/format-vocabulary.md`) with no branch yet; it waits on TODO #6's undecided
`intervals` argument style.

Last checkpoint: none yet.

## Open

- **Planned sessions** (`completed: false`): parsed and queryable, but no analysis treats them specially.
- **Template blocks** (`@template`): the grammar parses them, nothing processes them, and `format:` has no
  link to them (TODO #6).
- **`repl-summary`** (branch, intent and spec committed): a summary of `rich` panels when the REPL starts.
  Parked. Its intent predates `repl-add` and says `add` follows it, so it needs a rebase and a rewritten
  intent before it resumes; TODO #16 and #17 come first.

## Done

- **Format and parser:** tree-sitter grammar compiled into ox as `ox._grammar`; sessions, single-line
  entries, weigh-ins, notes, stored queries, `@include`, `@movement`, `@plugin`; weight, duration and
  distance as per-set fields; first-class `srpe:`; `to_ox()` round-trip.
- **Data and analysis:** in-memory SQLite layer; plugin system with builtins `volume`, `e1rm`, `weighin`,
  `srpe`, `wendler531`; plots through `ox.plot`.
- **CLI:** REPL with `add`, `plugins`, `query`, `tables`, `lint`, `reload`, plugins by name, and
  context-aware tab completion.
- **Editors:** LSP (diagnostics, completion, folding); VSCode extension on the Marketplace
  (`konnerhorton.ox-training-log`); micro plugin, installed by hand.
- **Distribution:** on PyPI as `ox-train` (v0.6.1); a `v*` tag releases through
  `.github/workflows/release.yml`. MkDocs site at konnerhorton.github.io/ox.

# TODO

Items to fix, research or decide. Refer to them as "TODO #n"; numbers are never reused or
renumbered. When an item is resolved, move any decision into `SPEC.md` (or the unit's
`docs/work/<id>.md`) and delete it here.

- [ ] **#6 Map `format:` values to a more descriptive data structure.** A short `format:` value (e.g.
  `"pavel-sprints"`) can't hold a full protocol on its own. Pavel sprints are 6 × (8s work / 22s
  rest) per set with 2 min between sets, and a `set-rest` argument on `intervals` was rejected as
  verbose and confusing. Instead, a format name could refer to a definition written once elsewhere,
  in the same way as the existing ideas: `@template` blocks (SPEC "What's incomplete": "grammar
  exists, no processing; `format:` is a free-text stub with no linkage to them") and
  `docs/future.md` "Protocol metadata" ("defined once for the named session"). Also undecided: how
  `intervals` writes its work and rest arguments. The log uses `"intervals work-PT1M rest-PT1M"` for
  now, but it isn't settled. Related unit: `docs/work/format-vocabulary.md`.

- [ ] **#8 Publish the VSCode extension to Open VSX** (for VSCodium/Cursor users). It is on the VS Code
  Marketplace as `konnerhorton.ox-training-log`. Sign in to https://open-vsx.org with GitHub, sign
  the publisher agreement, create an access token, then from `editors/vscode` (system Node is 18;
  `ovsx` needs ≥20):
  ```bash
  npx -p node@22 -p ovsx -c "ovsx create-namespace konnerhorton -p <token>"   # first time only
  npx -p node@22 -p ovsx -c "ovsx publish ox-training-log-<version>.vsix -p <token>"
  ```
  Then add Open VSX back to the install section of `docs/editor-support.md`.

- [ ] **#11 Syntax highlighting for nano.** Ship `editors/nano/ox.nanorc` with install steps in
  `docs/editor-support.md`. It's regex-based, so it approximates the tree-sitter grammar the way the
  TextMate grammar and the micro plugin's `syntax/ox.yaml` do, and it's another copy to keep in step
  with `grammar.js`.

- [ ] **#12 Snippets in the VSCode extension.** Already on the SPEC roadmap ("Snippets for common
  entry patterns"). Add `contributes.snippets` with session block, single-line entry, weigh-in,
  note, `@movement`, `@template`, `@include` and stored query, using `$CURRENT_YEAR-$CURRENT_MONTH-$CURRENT_DATE`
  for dates. Ships as a version bump of the extension. Do this after LSP completions (SPEC roadmap)
  so the snippets cover what completions don't.

- [ ] **#13 Install the micro plugin through ox.** A wheel can't run code at install time, so ship
  `editors/micro` as package data plus a command that copies it to `$MICRO_CONFIG_HOME/plug/ox/`
  (default `~/.config/micro/plug/ox/`). Open CLI choice for `SPEC.md`: `ox --install-micro`, a
  separate `ox-editor install micro` script, or turning `ox` into a command group. Decide whether the
  plugin's version then follows ox's.

- [ ] **#14 Lint on save in the micro plugin.** Run `ox` lint from an `onSave` callback and show
  diagnostics with `buffer.NewMessage`, the way micro's built-in `linter` plugin works.

- [ ] **#15 List the micro plugin in micro's plugin channel** so `micro -plugin install ox` works.
  Needs a download URL per release and `Versions` in `editors/micro/repo.json`.

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

- [ ] **#10 `add` command in the REPL.** Append a session to the log from the interactive prompt:
  date defaults to today, movement names complete from the loaded log, and the file is only ever
  appended to (never rewritten). This is the REPL's first write path. Open questions: which file
  receives the append when the log uses `@include` (the root file passed to `ox`, or a configurable
  target); validating the new block by parsing it before writing, then reloading. Prefill works at
  two levels: a movement's line gets its last recorded weight/reps, and a session name already used
  prefills every movement from that session's most recent instance. Its UI depends on the REPL
  overhaul (dashboard-style REPL), so settle that first.

- [ ] **#11 Syntax highlighting for nano and micro.** Ship `editors/nano/ox.nanorc` and
  `editors/micro/ox.yaml` with install steps in `docs/editor-support.md`. Both are regex-based, so
  they approximate the tree-sitter grammar the way the TextMate grammar does, and each is another
  copy to keep in step with `grammar.js`.

- [ ] **#12 Snippets in the VSCode extension.** Already on the SPEC roadmap ("Snippets for common
  entry patterns"). Add `contributes.snippets` with session block, single-line entry, weigh-in,
  note, `@movement`, `@template`, `@include` and stored query, using `$CURRENT_YEAR-$CURRENT_MONTH-$CURRENT_DATE`
  for dates. Ships as a version bump of the extension. Do this after LSP completions (SPEC roadmap)
  so the snippets cover what completions don't.

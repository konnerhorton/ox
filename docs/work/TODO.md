# TODO

Items to fix, research or decide. Refer to them as "TODO #n"; numbers are never reused or
renumbered. When an item is resolved, move any decision into `SPEC.md` (or the unit's
`docs/work/<id>.md`) and delete it here.

- [ ] **#1 Ship the migration script with the package.** `scripts/migrate_ox.py` isn't packaged, but
  the CHANGELOG and every lint hint (`MIGRATE` in `src/ox/lint.py`) point users to it. Anyone who
  installed ox without cloning the repo won't have it. Either add an `ox migrate` subcommand (and
  update the `MIGRATE` hint text) or link to the script's URL in the CHANGELOG.

- [ ] **#2 Guard `TrainingSession` against an sRPE rating without a duration.** A session built in code
  (e.g. by a plugin like wendler531) with `srpe_rating` set and `srpe_duration=None` crashes in
  `to_ox()` at `format_iso_duration(None)`. The parser can't produce this, since the grammar
  requires a duration. Add a `__post_init__` check in `src/ox/data.py` so that `srpe_rating`,
  `srpe_duration` and `srpe_note` are only accepted together, with the rating present.

- [ ] **#3 Publish the VSCode extension** (`editors/vscode`, ID `konnerhorton.ox-training-log`).
  Current `vsce` needs Node ≥20, but the system Node is 18 (Ubuntu apt package — don't replace it,
  other apt packages depend on it). Run `vsce` under a throwaway Node 22 via `npx` instead.
  1. Create the `konnerhorton` publisher at https://marketplace.visualstudio.com/manage, then an
     Azure DevOps Personal Access Token with scope *Marketplace → Manage* (All accessible organizations).
  2. Optional: sign in to https://open-vsx.org with GitHub, create the `konnerhorton` namespace, and
     generate an access token (for VSCodium/Cursor users).
  3. Package and smoke-test:
     ```bash
     cd editors/vscode
     npm install   # node_modules ships in the VSIX (vscode-languageclient)
     npx -p node@22 -p @vscode/vsce -c "vsce package"
     code --install-extension ox-training-log-0.1.0.vsix
     ```
  4. Publish (paste the PAT when prompted by `login`):
     ```bash
     npx -p node@22 -p @vscode/vsce -c "vsce login konnerhorton && vsce publish"
     npx -p node@22 -p ovsx -c "ovsx create-namespace konnerhorton -p <open-vsx-token>"   # first time only
     npx -p node@22 -p ovsx -c "ovsx publish ox-training-log-0.1.0.vsix -p <open-vsx-token>"
     ```
  5. Deploy the docs site only after publishing: `docs/editor-support.md` already tells users to
     install from the Marketplace/Open VSX.
  6. For later releases: bump `version` in `editors/vscode/package.json`, add a `CHANGELOG.md`
     entry, and repeat steps 3–4. Don't commit the `.vsix` (it is excluded from packaging, not from git).

- [ ] **#4 Fix the `wendler531` start-date flag in the docs.** `docs/plugins.md` shows
  `--start-date 2026-03-01`, but `parse_plugin_args` (`src/ox/sql_utils.py`) matches long flags
  against the param name exactly, so the working flag is `--start_date` and `--start-date` fails with
  "Unknown flag". Either fix the docs or have `parse_plugin_args` accept hyphens for underscores
  (which would fix it for every plugin's multi-word params).

- [ ] **#5 Publish ox to PyPI as `ox-train`.** The name `ox` is taken on PyPI; `ox-train` was free as
  of 2026-10-24. Rename the distribution in `pyproject.toml` (`name = "ox-train"`) while keeping the
  `ox` import package and the `ox` / `ox-lsp` commands. The C extension `tree-sitter-ox` is a local
  path dependency, so it must be published too or vendored into the wheel. Then switch the install
  instructions in `README.md`, `docs/getting-started.md` and `docs/editor-support.md` from
  `git+https://...` to `ox-train`. Roadmap: SPEC "Direction → Distribution".

- [ ] **#6 Map `format:` values to a more descriptive data structure.** A short `format:` value (e.g.
  `"pavel-sprints"`) can't hold a full protocol on its own. Pavel sprints are 6 × (8s work / 22s
  rest) per set with 2 min between sets, and a `set-rest` argument on `intervals` was rejected as
  verbose and confusing. Instead, a format name could refer to a definition written once elsewhere,
  in the same way as the existing ideas: `@template` blocks (SPEC "What's incomplete": "grammar
  exists, no processing; `format:` is a free-text stub with no linkage to them") and
  `docs/future.md` "Protocol metadata" ("defined once for the named session"). Also undecided: how
  `intervals` writes its work and rest arguments. The log uses `"intervals work-PT1M rest-PT1M"` for
  now, but it isn't settled. Related unit: `docs/work/format-vocabulary.md`.

- [ ] **#7 Define that weight and distance apply to each rep.** In `pavel-sprints: 3x6 50yd`, each of
  the 18 sprints is ~50yd, so the total is 900yd, not 150yd. Likewise `pullup: 24kg 3x5` means 24kg
  on every one of the 15 reps. Today SPEC "What works today" only says these are "independent
  per-set fields", and the `sets` table stores one `distance_magnitude` per set row next to `reps`,
  so the meaning isn't written down anywhere. Document "applies to each rep" (SPEC,
  `docs/getting-started.md` "Duration and distance") and make any derived totals (volume, total
  distance, pace) multiply by reps. Open question: does duration follow the same rule? Existing
  usage says no: `plank: BW PT45S 3x1` and `run-interval: 3x1 PT1M` time the whole set, and with a
  single rep per set both readings agree. `3x5 PT30S`, though, could mean 30s per rep or 30s per set.

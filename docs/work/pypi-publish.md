# pypi-publish: publish ox to PyPI as `ox-train`

## Intent

### Goal
`uv tool install ox-train` (or `pip install ox-train`) installs the `ox` and `ox-lsp` commands on
Linux, macOS and Windows without a C compiler. Releases are built and uploaded by GitHub Actions
when a version tag is pushed.

### Why
- Today the only install path is `uv tool install git+https://github.com/konnerhorton/ox`, which
  needs a compiler to build the grammar's C extension. SPEC "Direction → Distribution" lists PyPI.
- The name `ox` is taken on PyPI. `ox-train` and `tree-sitter-ox` were both free as of 2026-10-26.
- The `tree-sitter-ox` dependency is a local path (`[tool.uv.sources]` in `pyproject.toml`), which
  PyPI can't resolve, so the package can't be published as it stands.

### Constraints
- The distribution is renamed to `ox-train`. The import package stays `ox`, and the commands stay
  `ox` and `ox-lsp`.
- `parse.py` depends on the grammar's exact node types, so the grammar and the parser must always
  ship as a matched pair.
- The grammar workflow in `CLAUDE.md` (edit `grammar.js`, `tree-sitter generate`, reinstall) has to
  keep working for local development.
- CI stays green on PRs (`.github/workflows/ci.yml`: lint, format check, pytest).

### Out of scope
- The VSCode extension's install docs beyond the `ox-lsp` install command (`docs/editor-support.md`
  otherwise stays as is). Open VSX is TODO #8.
- Publishing the grammar separately for other tools to reuse. It can be split out later if someone
  needs it.
- conda-forge, Homebrew and other channels.

### SPEC sections touched
- "What works today": drop the **Migration** line, and note that ox installs from PyPI.
- "Direction → Distribution": remove the PyPI item (done).
- Docs: `README.md`, `docs/getting-started.md` (install, plus the "Migrating an older log"
  section), `docs/editor-support.md` (install), `CHANGELOG.md`, and `CLAUDE.md` (grammar reinstall
  steps if the build changes, migrate mentions, project structure).
- `docs/work/TODO.md`: delete #5 and #1, and add an item to drop the old-syntax lint hints.

### Decisions (intent review, 2026-10-26)
1. **Vendor the grammar into the `ox-train` wheel.** `ox-train`'s own build compiles
   `tree-sitter-ox/src/parser.c` into an extension module inside `ox`, and the `tree-sitter-ox`
   dependency is dropped. That means one package, one version and one release, and the grammar and
   parser can't drift apart. Rejected: publishing `tree-sitter-ox` as a second package (two
   releases, version pinning, and a grammar version that has never been bumped). Cost: the wheel
   becomes platform-specific instead of pure Python.
2. **Release through GitHub Actions with PyPI trusted publishing.** Pushing a `v*` tag builds wheels
   with `cibuildwheel` (Linux, macOS and Windows) plus an sdist, then uploads through OIDC, so
   there's no API token to store. A TestPyPI upload runs first as a dry run. Rejected: a manual
   `uv build && uv publish` (Linux wheel only, plus a stored token).
3. **Drop the migration script (also closes TODO #1).** The only pre-0.6 log was the author's, and
   it has already been converted. Remove `scripts/migrate_ox.py`, `tests/test_migrate.py` and its
   fixtures, plus the pointers to it in `lint.py`, the README, the getting-started guide, SPEC and
   CLAUDE.md. Past `CHANGELOG.md` entries stay as history. This goes in its own commit, separate
   from the packaging change.
4. **Keep the old-syntax lint hints for now, minus the pointer to the script.** The hints for the
   `*`/`!` flags, the positional session header and `srpe: "5; PT45M"` still explain the new
   syntax. Only the "migrate_ox.py converts…" suffix (`MIGRATE` in `src/ox/lint.py`) goes. A new
   TODO item tracks dropping the hints soon.
5. **The first PyPI release is `0.6.1`.**

6. **Wheels for Linux, macOS and Windows.** abi3 (cp312+) wheels for Linux x86_64/aarch64, macOS
   arm64/x86_64 and Windows x86_64, plus an sdist. `requires-python` stays `>=3.12`.
7. **Build the extension straight from `tree-sitter-ox/src/`** through a root `setup.py`, with no
   copy of the C sources. `tree-sitter-ox/` stays the grammar's development home.
8. **The grammar's Python import moves into `ox`.** Today `cli.py`, `lsp.py`, `test_parse.py` and
   `test_lint.py` each call `Language(tree_sitter_ox.language())`, where `tree_sitter_ox` is the
   top-level module the `tree-sitter-ox` dist installs. The C extension becomes `ox._grammar`, and
   one helper in `ox` returns the `Language` for all four call sites. Rejected: shipping a
   top-level `tree_sitter_ox` module inside `ox-train`, which would clash with any other
   `tree-sitter-ox` package.

### Setup outside the repo
- PyPI and TestPyPI pending publishers: set up by the author on 2026-10-26 (project `ox-train`,
  owner `konnerhorton`, repo `ox`, workflow `release.yml`, environments `pypi` and `testpypi`).

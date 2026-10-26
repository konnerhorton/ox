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

## Spec

### Changes

**Packaging (`pyproject.toml`, new root `setup.py`, `MANIFEST.in`)**
- `name = "ox-train"`, `version = "0.6.1"`. Drop the `tree-sitter-ox` dependency and its
  `[tool.uv.sources]` entry. Keep `tree-sitter>=0.25.2`, since the generated parser is ABI 15.
- The root `setup.py` declares one extension, `ox._grammar`, built from
  `tree-sitter-ox/src/parser.c` and `src/ox/_grammar.c`, with `include_dirs=["tree-sitter-ox/src"]`.
  It uses the limited API (`Py_LIMITED_API=0x030C0000`), so the wheel is tagged `cp312-abi3`. The
  compiler flags are the ones `tree-sitter-ox/setup.py` uses today.
- `MANIFEST.in` puts the C sources and headers into the sdist (`tree-sitter-ox/src/parser.c`,
  `tree-sitter-ox/src/tree_sitter/*.h` and `src/ox/_grammar.c`), so an sdist install can compile
  without the rest of `tree-sitter-ox/`.
- `[tool.cibuildwheel]`: `build = "cp312-*"`, skip musllinux and PyPy, and a `test-command` that
  runs the smoke test (AC 2) against each built wheel.

**Grammar import (`src/ox/_grammar.c`, `src/ox/grammar.py`)**
- `_grammar.c` is the current `bindings/python/tree_sitter_ox/binding.c`, with the module renamed to
  `_grammar` (`PyInit__grammar`).
- `ox.grammar` exposes `LANGUAGE: tree_sitter.Language`, built once at import.
- `cli.py`, `lsp.py`, `tests/test_parse.py` and `tests/test_lint.py` use `ox.grammar.LANGUAGE`
  instead of `Language(tree_sitter_ox.language())`.
- `cli.py`'s `--version` reads `importlib.metadata.version("ox-train")`. It reads `"ox"` today,
  which would raise `PackageNotFoundError` after the rename.

**`tree-sitter-ox/`**
- Remove its Python packaging, which nothing installs any more: `pyproject.toml`, `setup.py`,
  `uv.lock` and `bindings/python/`. `grammar.js`, `src/`, `test/corpus/` and the other language
  bindings stay. `tree-sitter generate` doesn't touch `bindings/`, so the grammar dev loop is
  unchanged up to the reinstall step.

**Dropping the migration script**
- Delete `scripts/migrate_ox.py`, `tests/test_migrate.py` and its fixtures
  (`tests/fixtures/migrate_old.ox`, `migrate_new.ox`).
- `src/ox/lint.py`: delete `MIGRATE` and its three uses. The hint text otherwise stays.
- `tests/test_lint.py::test_migration_hints_name_the_script` becomes a test that the old-syntax
  hints still fire and no longer mention a script.
- Remove the pointers in `README.md`, `docs/getting-started.md` ("Migrating an older log" section),
  `SPEC.md` ("Migration" line) and `CLAUDE.md`. Past `CHANGELOG.md` entries stay.

**Release workflow (`.github/workflows/release.yml`)**
- Triggers: a `v*` tag push, and `workflow_dispatch`, which builds without publishing.
- `build_wheels`: `pypa/cibuildwheel` on `ubuntu-latest` (x86_64), `ubuntu-24.04-arm` (aarch64),
  `macos-13` (x86_64), `macos-14` (arm64) and `windows-latest` (AMD64). Each wheel is tested in
  place by `test-command`.
- `build_sdist`: `uv build --sdist`. Then it installs the sdist in a fresh venv and runs the smoke
  test, which proves the sdist compiles.
- `check_version`: on a tag push, fails unless the tag equals `v` + the `pyproject.toml` version.
- `publish_testpypi` (environment `testpypi`) and then `publish_pypi` (environment `pypi`, needs
  `publish_testpypi`) use `pypa/gh-action-pypi-publish` with `id-token: write`. Neither runs on
  `workflow_dispatch`.

**CI (`ci.yml`)**: unchanged. `uv sync` now compiles the extension on the runner, which has a
compiler.

**Docs and bookkeeping**
- Install commands become `uv tool install ox-train` in `README.md`, `docs/getting-started.md` and
  `docs/editor-support.md`, with `pip install ox-train` as the alternative. README's "From source"
  section stays.
- `CLAUDE.md`: the grammar reinstall command becomes `uv sync --reinstall-package ox-train`, and the
  explanation of why is updated. Add `grammar.py` to the project structure, and remove the migrate
  sentence.
- `CHANGELOG.md`: a `v0.6.1` entry covering the PyPI name, the vendored grammar, and the removed
  migration script.
- `SPEC.md`: "What works today" says ox installs from PyPI as `ox-train`, and the "Migration" line
  goes. "Direction → Distribution" drops the PyPI item.
- `docs/work/TODO.md`: delete #1 and #5. Add #9: drop the old-syntax lint hints (`_old_entry`,
  `_old_header`, `_old_srpe` in `src/ox/lint.py`) once no pre-0.6 log is in use.

### Decisions
1. **Expose a `Language` object, not a capsule function.** `ox.grammar.LANGUAGE` replaces the four
   `Language(tree_sitter_ox.language())` calls. Callers only ever wrap the capsule, so building the
   `Language` once removes repeated code. The private `ox._grammar.language()` still returns the
   capsule.
2. **No PR-time wheel build.** A cross-platform build on every PR is slow and catches little that
   the `workflow_dispatch` dry run before tagging doesn't. PR CI already compiles the extension on
   Linux.
3. **The real upload waits for TestPyPI to succeed.** A broken upload to PyPI can't be reused under
   the same version, while TestPyPI is disposable.
4. **musllinux (Alpine) and PyPy get no wheels.** They can install from the sdist. Add them if
   someone asks.

### Acceptance criteria
1. **Distribution name and contents:** `uv build` produces `ox_train-0.6.1.tar.gz` and
   `ox_train-0.6.1-cp312-abi3-<platform>.whl`. The wheel's `METADATA` has `Name: ox-train` and no
   `Requires-Dist: tree-sitter-ox`. The wheel contains `ox/_grammar.abi3.so` (or `.pyd`) and no
   top-level `tree_sitter_ox`.
2. **Smoke test:** in a fresh venv with only the built wheel installed, `ox --version` prints
   `0.6.1`, `ox-lsp --help` exits 0, and
   `python -c "from ox.cli import parse_file; ..."` on `examples/example.ox` returns a log with
   sessions and no error diagnostics.
3. **The sdist compiles:** the AC 2 smoke test passes in a fresh venv with only
   `ox_train-0.6.1.tar.gz` installed.
4. **One grammar import:** `grep -rn tree_sitter_ox src tests` finds nothing.
5. **The grammar dev loop still works:** after a whitespace-only edit to `grammar.js`,
   `tree-sitter generate` and then `uv sync --reinstall-package ox-train` rebuild the extension, and
   the test suite passes.
6. **Migration removed:** `scripts/migrate_ox.py` and `tests/test_migrate.py` are gone. The three
   old-syntax inputs (`*` flag, positional header, `srpe: "5; PT45M"`) still get hints, and none of
   them contain `migrate`. `grep -rn migrate_ox` outside `CHANGELOG.md` and `docs/work/` finds
   nothing.
7. **Dry run:** a `workflow_dispatch` run of `release.yml` builds and tests all five wheels and the
   sdist, and publishes nothing.
8. **Version guard:** a tag that doesn't match the `pyproject.toml` version fails `check_version`
   before anything is uploaded. Checked by reading the step's script and running its shell logic
   locally with a mismatched tag. No bad tag gets pushed.
9. **Release:** pushing `v0.6.1` uploads to TestPyPI and then PyPI. Afterwards,
   `uv tool install ox-train` on this machine (from PyPI, with no repo checkout) passes the AC 2
   smoke test.
10. **Repo green:** `uv run pytest`, `ruff check` and `ruff format --check` pass on every commit, and
    PR CI passes.
11. **Docs:** `README.md`, `docs/getting-started.md` and `docs/editor-support.md` install with
    `ox-train` and contain no `git+https`. CHANGELOG, SPEC, CLAUDE.md and TODO are updated as listed
    above.

## Plan

Five build commits, then the release. Every commit passes `uv run pytest`, `ruff check` and
`ruff format --check`.

### 1. `pypi-publish: drop the migration script`
- Delete `scripts/migrate_ox.py`, `tests/test_migrate.py` and `tests/fixtures/migrate_{old,new}.ox`.
- `src/ox/lint.py`: delete `MIGRATE` and its three uses.
- `tests/test_lint.py`: `test_migration_hints_name_the_script` becomes
  `test_old_syntax_hints_name_no_script`.
- Remove the pointers in `README.md`, `docs/getting-started.md`, `SPEC.md` and `CLAUDE.md`.
- Tests: AC 6.

### 2. `pypi-publish: rename the distribution to ox-train`
- `pyproject.toml`: `name = "ox-train"`, `version = "0.6.1"`. `src/ox/cli.py`: `--version` reads
  `ox-train`. Refresh `uv.lock`.

### 3. `pypi-publish: vendor the grammar as ox._grammar`
- New `src/ox/_grammar.c` (binding renamed), `src/ox/grammar.py` (`LANGUAGE`), root `setup.py`
  (abi3 extension built from `tree-sitter-ox/src/parser.c`) and `MANIFEST.in`.
- `pyproject.toml`: drop the `tree-sitter-ox` dependency and source. Add uv `cache-keys` and
  `[tool.cibuildwheel]`.
- `cli.py`, `lsp.py`, `test_parse.py` and `test_lint.py` use `ox.grammar.LANGUAGE`.
- Delete the Python packaging in `tree-sitter-ox/`. `CLAUDE.md`: new reinstall command, and
  `grammar.py` added to the project structure.
- Tests: AC 1–5 (local `uv build`, smoke tests from the wheel and the sdist in fresh venvs, grep,
  grammar dev loop).

### 4. `pypi-publish: add release workflow`
- `.github/workflows/release.yml`: `check_version`, `build_wheels` (5 runners, cibuildwheel),
  `build_sdist` (with a smoke test), `publish_testpypi`, `publish_pypi`. Publishing runs on `v*`
  tags only.
- Tests: AC 8 locally, and a local Linux cibuildwheel build.

### 5. `pypi-publish: switch install docs to ox-train and close out`
- Install docs (`README.md`, `docs/getting-started.md`, `docs/editor-support.md`), `CHANGELOG.md`
  v0.6.1, `SPEC.md`, and `docs/work/TODO.md` (delete #1 and #5, add #9).
- Tests: AC 11.

### Release (each step needs the author's approval)
1. Push, open a PR, CI green (AC 10). 2. Merge `--no-ff` and push. 3. Dry run with
`gh workflow run release.yml --ref main` (AC 7). `workflow_dispatch` needs the file on the default
branch, so this runs after the merge. 4. Tag `v0.6.1` and push. 5. `uv tool install ox-train` and
the smoke test (AC 9).

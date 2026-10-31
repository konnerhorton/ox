# vscode-standard-scopes: highlight `.ox` with any theme, drop Ox Dark

## Intent

### Goal
The VSCode extension stops shipping the Ox Dark color theme. `.ox` files get distinct,
readable highlighting from whatever theme the user already has, because the grammar's scope
names fall into the standard TextMate categories that common themes color. Every token the
grammar emits gets a color in VS Code's default themes. That includes the `T`/`W` markers,
`completed:` booleans, sRPE ratings and `@plugin`.

### Why
- **Selecting Ox Dark breaks every other language.** VS Code color themes replace each other and
  don't layer. `themes/ox-dark.json` has rules only for `*.ox` scopes plus a generic `comment`,
  so with Ox Dark active, Python, JSON, Markdown and every other language render as plain
  `#d4d4d4` text with green comments.
- **Users shouldn't need a theme to get good highlighting.** A syntax extension should look right
  in the theme the user already chose.
- **The theme has gaps today.** It targets `keyword.operator.flag.ox`, but the grammar emits
  `keyword.operator.marker.ox`, so `T`/`W` are never colored. `constant.language.boolean.ox`,
  `constant.numeric.rating.ox` and `keyword.control.plugin.ox` have no rule at all.
- **Many value kinds share one color.** Date, weight, reps, time, distance and rating all sit
  under `constant.numeric.*`, so a generic theme gives them one color. Ox Dark was the only
  thing telling them apart.

### Constraints
- Grammar changes are limited to scope names. Match patterns (what gets tokenized) stay as
  they are.
- Every scope keeps its `.ox` suffix, so a user can still target Ox tokens precisely with
  `editor.tokenColorCustomizations`.
- Use only scope categories that VS Code's built-in themes actually color. The mapping is
  checked against the theme source files, not chosen from memory.

### Out of scope
- Semantic tokens from `ox-lsp`.
- Shipping colors through `configurationDefaults` or any other default setting (option 3 in
  the discussion).
- A complete replacement theme based on vendored Dark+ (option 2).
- An automated grammar test harness (e.g. `vscode-tmgrammar-test`).
- Uploading the release to the Marketplace. That stays the manual step in `CLAUDE.md`. This
  unit prepares the version bump and changelog.
- Changes to the tree-sitter grammar.
- Open VSX publishing (TODO #8).

### SPEC sections touched
- None. SPEC lists the extension as "syntax highlighting, and diagnostics and completions via
  `ox-lsp`", which still holds. Updated alongside: `editors/vscode/package.json`, `README.md`,
  `CHANGELOG.md`, the grammar, `docs/editor-support.md` (if it describes colors), and the deletion
  of `themes/ox-dark.json`.

### Decisions (intent review, 2026-10-31)
1. **The scope mapping is decided in the spec step,** after reading VS Code's
   `dark_vs.json`/`dark_plus.json`/`light_vs.json`/`light_plus.json` (and Dark/Light Modern) to
   see which categories get distinct colors. Example of the problem to check: Dark+ seems to
   leave `keyword.operator` at the default foreground, so the markers may need a different
   category than they have now.
2. **Target themes for "distinct and readable":** Dark Modern and Light Modern (the defaults),
   plus a spot check in one popular third-party theme (One Dark Pro?).
3. **Verification is manual.** Open `examples/example.ox` in each target theme and use
   *Developer: Inspect Editor Tokens and Scopes* on each token kind. Screenshots go in the PR.
4. **Version bump to 0.2.0** (minor), because removing a contributed theme is user-visible.
   Users who had Ox Dark selected fall back to a default theme on update. The changelog says so
   and suggests a `tokenColorCustomizations` snippet for anyone who wants the old palette.
5. **The README keeps that snippet** as the opt-in way to get Ox Dark's `.ox` colors on top of
   any dark theme.
6. **The `Themes` category is removed** from `package.json`, and `galleryBanner` stays.

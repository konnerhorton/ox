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

## Spec

The rules live here. The grammar, `package.json`, the extension README and CHANGELOG, and
`docs/editor-support.md` carry the result.

### Changes
- **`editors/vscode/syntaxes/ox.tmLanguage.json`:** rename scopes per the mapping below. No match
  pattern changes.
- **`editors/vscode/themes/ox-dark.json`:** deleted, and the `themes/` directory with it.
- **`editors/vscode/package.json`:** remove `contributes.themes` and the `"Themes"` category, and
  bump `version` to `0.2.0`. `galleryBanner` stays (intent decision 6).
- **`editors/vscode/README.md`:** replace the "Ox Dark color theme" bullet with "works with any
  color theme", and add an opt-in `editor.tokenColorCustomizations` snippet that reproduces Ox
  Dark's `.ox` colors using the new scope names (intent decision 5).
- **`editors/vscode/CHANGELOG.md`:** a `0.2.0` entry. The theme is removed, users who had it
  selected fall back to a default theme, see the README snippet for the old palette, scopes were
  renamed, and the `T`/`W` markers and session names are now colored.
- **`docs/editor-support.md`, Features:** one line saying highlighting uses your current color
  theme.

### Scope mapping

| Token | Old scope | New scope |
|---|---|---|
| `T` / `W` marker | `keyword.operator.marker.ox` | `keyword.other.marker.ox` |
| Date | `constant.numeric.date.ox` | `entity.name.type.date.ox` |
| Session `name:` value | `entity.name.section.ox` | `markup.heading.session.ox` |
| Field keys (`date:`, `srpe:`, `equipment:` …) | `support.type.property-name.ox` | `entity.other.attribute-name.ox` |
| Rep scheme | `constant.numeric.reps.ox` | `variable.other.constant.reps.ox` |
| Comment, block/include/plugin keywords, `note`/`query`, movement name, boolean, strings, weight, time, distance, rating | — | unchanged |

Resolved foreground for each new scope, read from the theme JSON files (VS Code 1.143.1
`theme-defaults`, One Dark Pro from `Binaryify/OneDark-Pro` master). "b" means bold.

| Scope | Dark 2026 | Dark Modern | Light Modern | Light 2026 | One Dark Pro |
|---|---|---|---|---|---|
| `keyword.other.marker` / `note` / `query` | `#ff7b72` | `#569cd6` | `#0000ff` | `#cf222e` | `#c678dd` |
| `entity.name.type.date` | `#4EC9B0` | `#4EC9B0` | `#267f99` | `#267f99` | `#e5c07b` |
| `entity.name.function` (movement) | `#d2a8ff` | `#DCDCAA` | `#795E26` | `#8250df` | `#61afef` |
| `constant.numeric.*` (weight, time, distance, rating) | `#b5cea8` | `#b5cea8` | `#098658` | `#098658` | `#d19a66` |
| `variable.other.constant.reps` | `#79c0ff` | `#4FC1FF` | `#0070C1` | `#0550ae` | `#e5c07b` |
| `string.*` | `#a5d6ff` | `#ce9178` | `#a31515` | `#0a3069` | `#98c379` |
| `markup.heading.session` | `#79c0ff` b | `#569cd6` b | `#800000` b | `#0550ae` b | `#e06c75` |
| `entity.other.attribute-name` | `#9cdcfe` | `#9cdcfe` | `#e50000` | `#e50000` | `#d19a66` |
| `keyword.control.*` | `#C586C0` | `#C586C0` | `#AF00DB` | `#AF00DB` | `#c678dd` |
| `constant.language.boolean` | `#569cd6` | `#569cd6` | `#0000ff` | `#0000ff` | `#d19a66` |

### Decisions
1. **Target themes are Dark 2026 and Light 2026 as well as Dark/Light Modern.** This corrects
   intent decision 2: VS Code 1.143's built-in defaults are `COLOR_THEME_DARK = "Dark 2026"` and
   `COLOR_THEME_LIGHT = "Light 2026"` (from `workbench.desktop.main.js`). Modern is still widely
   used, so all four are targets. One Dark Pro stays the third-party spot check.
2. **Markers become `keyword.other.marker`,** the same category as `note` and `query`. All four
   words say what kind of entry the line is, and `keyword.operator` gets only the default
   foreground in every built-in theme (it's `#d4d4d4` in `dark_vs.json`), which is why `T`/`W`
   showed up plain.
3. **The date becomes `entity.name.type.date`.** It's the identifier at the head of every entry,
   and moving it out of `constant.numeric` separates it from the numbers on the same line.
4. **Reps become `variable.other.constant.reps`.** Of the categories tried, it's the only one that
   contrasts with dates, markers, numbers and strings in all four built-ins. Candidates rejected:
   - `constant.language`: same color as the marker in Dark Modern.
   - `constant.character`: same color as the marker in Dark 2026.
   - `string.other`: same color as quoted strings.
5. **Weight, time, distance and rating stay `constant.numeric`, and share one color.** No
   standard category gives time and distance a fourth distinct color in all four built-ins
   without borrowing a scope with an unrelated meaning. `constant.character.escape` and
   `string.regexp` would work in the built-ins but render unpredictably elsewhere. The unit
   suffix (`kg`, `PT…`, `m`) already tells them apart. The README snippet restores Ox Dark's
   separate colors for anyone who wants them.
6. **Session name becomes `markup.heading.session`.** `entity.name.section` gets no color in
   Dark Modern or Light Modern. A heading is what a session name is, and the built-ins render it
   bold.
7. **Field keys become `entity.other.attribute-name`.** Same color as before in the built-ins,
   and One Dark Pro colors it, whereas it leaves `support.type.property-name` at the default
   foreground (`#abb2bf`).
8. **Known overlap in One Dark Pro:** date and reps are both `#e5c07b`. It's accepted because
   the two never sit next to each other and they look different (`2025-01-10` vs `5x5`), and
   avoiding it would cost contrast in a built-in theme.

### Acceptance criteria
1. `editors/vscode/themes/` doesn't exist, and `package.json` has no `contributes.themes` and no
   `"Themes"` category.
2. The grammar contains none of the old scope names in the mapping table. It contains each new
   scope name.
3. The grammar's match patterns are byte-identical to `main` apart from the scope names. The
   only diff lines are `"name": "…"` lines.
4. In each of Dark 2026, Dark Modern, Light Modern and Light 2026, *Developer: Inspect Editor
   Tokens and Scopes* shows a non-default foreground for every token kind in the mapping table,
   including `T`, `W`, `completed:` values, the sRPE rating, `@plugin` and the session name.
   Checked on a scratch `.ox` file holding one of each token kind, because no example file has
   all of them (`example.ox` lacks `srpe:`, `completed:` and `@plugin`). The scratch file isn't
   committed.
5. In those four themes, on a single-line entry, the date, marker, movement name, weight, rep
   scheme and quoted note each have a different foreground.
6. With a Python and a JSON file open after the change, they're highlighted by the active theme
   (the original bug). This holds trivially once no Ox theme can be selected, and is checked
   anyway.
7. `package.json` `version` is `0.2.0`, the CHANGELOG has a `0.2.0` entry covering the removal
   and the fallback, and `vsce package` succeeds.
8. The README snippet, pasted into user settings, gives `.ox` tokens Ox Dark's former colors
   (spot check: date `#4EC9B0` bold, reps `#CE9178`, distance `#D4A5FF`).

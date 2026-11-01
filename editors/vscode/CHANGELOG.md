# Changelog

## 0.2.0

- **Removed the Ox Dark theme.** A VS Code color theme replaces the active one, so selecting
  Ox Dark left every other language without highlighting. `.ox` files now use your own theme.
  If you had Ox Dark selected, VS Code falls back to a default theme. The README has a
  `tokenColorCustomizations` snippet that restores Ox Dark's `.ox` colors on top of any theme.
- Renamed scopes to standard TextMate categories, so default themes color dates, markers, movement
  names, numbers, rep schemes and notes distinctly:
  - `keyword.operator.marker.ox` → `keyword.other.marker.ox`
  - `constant.numeric.date.ox` → `entity.name.type.date.ox`
  - `entity.name.section.ox` → `markup.heading.session.ox`
  - `support.type.property-name.ox` → `entity.other.attribute-name.ox`
  - `constant.numeric.reps.ox` → `variable.other.constant.reps.ox`
- Fixed: the `T`/`W` entry markers and session names were uncolored in most themes.

## 0.1.0

First Marketplace release.

- Syntax highlighting for `.ox` files and the Ox Dark theme
- `ox-lsp` integration: diagnostics, movement completions, comment folding
- Finds `ox-lsp` through the `ox.lsp.path` setting, a project `.venv` (Windows included), or `PATH`
- Shows a notice with install instructions when `ox-lsp` is missing
- **Ox: Restart Language Server** command

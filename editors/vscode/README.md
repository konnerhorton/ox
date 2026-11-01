# Ox for VS Code

Language support for [Ox](https://github.com/konnerhorton/ox) plain-text training logs (`.ox` files).

## Features

- **Syntax highlighting** for dates, entry markers (`T`, `W`), session blocks and fields, weights,
  reps, durations, distances, notes, stored queries, and directives (`@include`, `@plugin`, …)
- **Diagnostics**: syntax errors (with hints for common mistakes) and invalid `@include` paths,
  as you type
- **Completions**: movement names from the `@movement` blocks in your log
- **Folding** for comment sections, `#` comment toggling, and auto-closing quotes
- **Works with any color theme**: highlighting uses standard TextMate scopes, so your current theme
  colors `.ox` files

```
@session
date: 2025-01-11
name: Upper Day
srpe: 7 PT50M "felt strong"
bench-press: 135lb 5x5
kb-oh-press: 24kg 5/5/5
@end

2025-01-12 T run: 5km PT25M
2025-01-12 W 185lb T06:30 "home"
```

## Custom colors

Highlighting follows your color theme. Weights, durations, distances and sRPE ratings share the
theme's number color, and the unit suffix tells them apart. If you want separate colors, or
the palette of the old Ox Dark theme (removed in 0.2.0), add this to your user `settings.json`.
It's tuned for dark themes. To apply it to one theme only, nest it under that theme's name,
e.g. `"[Dark Modern]": { "textMateRules": [...] }`.

```jsonc
"editor.tokenColorCustomizations": {
  "textMateRules": [
    { "scope": "comment.line.number-sign.ox", "settings": { "foreground": "#6A9955", "fontStyle": "italic" } },
    { "scope": ["keyword.control.block.ox", "keyword.control.include.ox", "keyword.control.plugin.ox", "keyword.other.query.ox"],
      "settings": { "foreground": "#C586C0", "fontStyle": "bold" } },
    { "scope": ["keyword.other.marker.ox", "keyword.other.note.ox"], "settings": { "foreground": "#D4878F", "fontStyle": "bold" } },
    { "scope": "entity.name.type.date.ox", "settings": { "foreground": "#4EC9B0", "fontStyle": "bold" } },
    { "scope": "markup.heading.session.ox", "settings": { "foreground": "#DCDCAA", "fontStyle": "" } },
    { "scope": "entity.name.function.ox", "settings": { "foreground": "#9CDCFE" } },
    { "scope": "entity.other.attribute-name.ox", "settings": { "foreground": "#569CD6" } },
    { "scope": "constant.numeric.weight.ox", "settings": { "foreground": "#B5CEA8" } },
    { "scope": "variable.other.constant.reps.ox", "settings": { "foreground": "#CE9178" } },
    { "scope": "constant.numeric.time.ox", "settings": { "foreground": "#DCDCAA" } },
    { "scope": "constant.numeric.distance.ox", "settings": { "foreground": "#D4A5FF" } },
    { "scope": "string.quoted.double.ox", "settings": { "foreground": "#E8B87A", "fontStyle": "italic" } },
    { "scope": "string.unquoted.ox", "settings": { "foreground": "#D4D4D4" } }
  ]
}
```

## Requirements

You get syntax highlighting with no setup. Diagnostics and completions come from the `ox-lsp`
language server, which ships with the `ox` Python package:

```bash
uv tool install git+https://github.com/konnerhorton/ox
```

The extension looks for `ox-lsp` in this order:

1. The `ox.lsp.path` setting, if set
2. A `.venv` in the workspace or the open file's directory (or up to five parent directories)
3. Your `PATH`

If it can't find `ox-lsp`, you'll see a one-time notice, and syntax highlighting keeps working.

## Settings

| Setting       | Default | Description                                                            |
| ------------- | ------- | ---------------------------------------------------------------------- |
| `ox.lsp.path` | `""`    | Path to the `ox-lsp` executable. Leave it empty to discover it automatically. |

## Commands

- **Ox: Restart Language Server**

## More

See the [Ox documentation](https://konnerhorton.github.io/ox/) for the full file format and CLI.

# Ox for VS Code

Language support for [Ox](https://github.com/konnerhorton/ox) plain-text training logs (`.ox` files).

## Features

- **Syntax highlighting** for dates, entry markers (`T`, `W`), session blocks and fields, weights,
  reps, durations, distances, notes, stored queries, and directives (`@include`, `@plugin`, …)
- **Diagnostics**: syntax errors (with hints for common mistakes) and invalid `@include` paths,
  as you type
- **Completions**: movement names from the `@movement` blocks in your log
- **Folding** for comment sections, `#` comment toggling, and auto-closing quotes
- **Ox Dark** color theme tuned for `.ox` files

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

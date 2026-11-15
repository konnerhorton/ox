---
icon: material/puzzle
---

# Editor Support

## VSCode Extension

Syntax highlighting, diagnostics, and completions for `.ox` files. Source lives in `editors/vscode`.

### Install

Install **Ox** (`konnerhorton.ox-training-log`) from the VS Code Marketplace, or search for "Ox"
in the Extensions view.

To run it from a source checkout instead:

```bash
cd /path/to/ox/editors/vscode && npm install
ln -s "$PWD" ~/.vscode/extensions/ox
```

Then reload VSCode (`Ctrl+Shift+P` → "Developer: Reload Window").

Highlighting needs no setup. Diagnostics and completions need `ox-lsp` (see [below](#language-server-lsp)).
The extension looks for it in this order:

1. The `ox.lsp.path` setting
2. A `.venv` in the workspace or the open file's directory (or up to five parent directories)
3. Your `PATH`

If it can't find `ox-lsp`, it shows a one-time notice. Run **Ox: Restart Language Server** after
installing `ox-lsp` or changing the setting.

### Features

- Syntax highlighting for dates, markers (`T`, `W`), session fields (`date:`, `name:`,
  `completed:`, `format:`, `srpe:`), weights, reps, durations, distances, strings, and comments
- Highlighting uses your current color theme, and the extension's README has an opt-in snippet for
  custom `.ox` colors
- Block directives (`@session`, `@movement`, `@template`, `@end`) and top-level directives (`@include`, `@plugin`)
- `note` and `query` entry highlighting; `equipment`/`tags`/`note`/`url` fields inside `@movement` blocks
- Comment toggling (`#`)
- Comment section folding
- Auto-closing quotes

## micro Plugin

Syntax highlighting for `.ox` files in the [micro](https://micro-editor.github.io) editor. Source lives in
`editors/micro`.

### Install

Copy the plugin from a clone of the ox repository into micro's plugin folder:

```bash
mkdir -p ~/.config/micro/plug
cp -r /path/to/ox/editors/micro ~/.config/micro/plug/ox
```

If you set `$MICRO_CONFIG_HOME`, use `$MICRO_CONFIG_HOME/plug/ox` in place of `~/.config/micro/plug/ox`. To work on
the plugin itself, symlink it instead (`ln -s /path/to/ox/editors/micro ~/.config/micro/plug/ox`) so edits take
effect the next time micro starts.

Restart micro. `micro -plugin list` should show `ox`, and an `.ox` file opens with `ft:ox` in the status line.
Installing the plugin through `ox` is planned.

### Features

- Highlighting for comments, block keywords and directives, dates, the `T`/`W`/`note`/`query` markers, movement
  names, session and `@movement` fields, weights, reps, durations, distances, `completed:` values, sRPE ratings and
  quoted strings
- Colors come from your micro colorscheme. The plugin ships none
- `> help ox` lists which colorscheme group each kind of token uses

## Language Server (LSP)

`ox-lsp` provides real-time editor integration via stdio. It is installed with ox:

```bash
uv tool install ox-train
```

### Features

- **Diagnostics** — syntax errors (with a hint for common mistakes, the same as `lint`) and invalid `@include` paths
- **Completions** — movement name autocomplete, populated from `@movement` blocks in the parsed log
- **Folding** — collapse comment sections

### Editor Configuration

**VSCode**: the Ox extension above starts `ox-lsp` for you.

**Other editors**: point any LSP client at the `ox-lsp` command (stdio, no arguments) for `.ox` files.

## Tree-sitter Grammar

Available in `tree-sitter-ox/` for editors with tree-sitter support. The VSCode extension and the micro plugin are the editor integrations shipped today; Neovim and Helix users can wire
up the grammar and `ox-lsp` themselves.

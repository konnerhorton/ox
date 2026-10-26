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
- Block directives (`@session`, `@movement`, `@template`, `@end`) and top-level directives (`@include`, `@plugin`)
- `note` and `query` entry highlighting; `equipment`/`tags`/`note`/`url` fields inside `@movement` blocks
- Comment toggling (`#`)
- Comment section folding
- Auto-closing quotes

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

Available in `tree-sitter-ox/` for editors with tree-sitter support. The VSCode extension is the only editor integration shipped today; Neovim and Helix users can wire up the grammar and `ox-lsp` themselves.

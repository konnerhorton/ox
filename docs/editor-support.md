---
icon: material/puzzle
---

# Editor Support

## VSCode Extension

Syntax highlighting for `.ox` files. Located in `editors/vscode`.

### Install

```bash
ln -s /path/to/ox/editors/vscode ~/.vscode/extensions/ox
```

Reload VSCode (`Ctrl+Shift+P` → "Developer: Reload Window").

### Features

- Syntax highlighting for dates, flags (`*`, `!`, `W`), weights, reps, strings, and comments
- Block directives (`@session`, `@movement`, `@template`, `@end`) and top-level directives (`@include`, `@plugin`)
- `note` and `query` entry highlighting; `equipment`/`tags`/`note`/`url` fields inside `@movement` blocks
- Comment toggling (`#`)
- Comment section folding
- Auto-closing quotes

## Language Server (LSP)

`ox-lsp` provides real-time editor integration via stdio.

### Features

- **Diagnostics** — syntax errors and invalid `@include` paths
- **Completions** — movement name autocomplete, populated from `@movement` blocks in the parsed log
- **Folding** — collapse comment sections

### Editor Configuration

**VSCode** — use a generic LSP client extension pointing to `ox-lsp`.

## Tree-sitter Grammar

Available in `tree-sitter-ox/` for editors with tree-sitter support. The VSCode extension is the only editor integration shipped today; Neovim and Helix users can wire up the grammar and `ox-lsp` themselves.

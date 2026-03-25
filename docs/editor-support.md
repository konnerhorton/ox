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

- Syntax highlighting (dates, flags, weights, reps, comments, strings)
- Comment toggling (`#`)
- Comment section folding
- Auto-closing quotes

## Language Server (LSP)

`ox-lsp` provides real-time editor integration via stdio.

### Features

- **Diagnostics** — syntax errors and invalid `@include` paths
- **Completions** — movement name autocomplete
- **Folding** — collapse comment sections

### Editor Configuration

**VSCode** — use a generic LSP client extension pointing to `ox-lsp`.

## Tree-sitter Grammar

Available in `tree-sitter-ox/` for editors with tree-sitter support.

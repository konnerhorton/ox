# Editor Support

## VSCode

A VSCode extension providing syntax highlighting for `.ox` files is included in the repository at `editors/vscode`.

### Installation

VSCode extensions must be installed globally. Symlink the extension to your VSCode extensions folder:

```bash
ln -s /path/to/ox/editors/vscode ~/.vscode/extensions/ox
```

Then reload VSCode (`Ctrl+Shift+P` → "Developer: Reload Window").

### Features

- Syntax highlighting for all Ox constructs:
  - Dates, flags, and session names
  - Exercise names and metadata keys
  - Weights, rep schemes, time, and distance values
  - Quoted strings and comments
- Language configuration with:
  - Comment toggling (`#`)
  - Auto-closing quotes
  - Code folding for `@session`, `@exercise`, and `@template` blocks

### Development Mode

If you're developing the extension, you can run it in debug mode instead of symlinking. Create `editors/vscode/.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Extension",
      "type": "extensionHost",
      "request": "launch",
      "args": ["--extensionDevelopmentPath=${workspaceFolder}"]
    }
  ]
}
```

Open `editors/vscode` as a workspace and press F5 to launch a new VSCode window with the extension loaded.

## Other Editors

A tree-sitter grammar is available in `tree-sitter-ox` which can be used to add Ox support to any editor with tree-sitter integration (Neovim, Helix, Emacs, etc.).

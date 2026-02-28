---
icon: material/puzzle
---

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
  - Code folding for `@session` and `@exercise` blocks

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

## Language Server (LSP)

Ox ships with a Language Server Protocol implementation (`ox-lsp`) that provides real-time diagnostics in any LSP-compatible editor.

### What it provides

- **Diagnostics** — syntax errors are underlined as you type, on save, and on open

### Starting the server

The `ox-lsp` command is installed alongside `ox`:

```bash
ox-lsp
```

The server communicates over stdio and is typically launched automatically by your editor's LSP client.

### VSCode

Add the following to your VSCode `settings.json` to enable the language server alongside the syntax-highlighting extension:

```json
{
  "languageServerExample.trace.server": "verbose"
}
```

Or configure it via a generic LSP client extension (e.g., `vscode-languageclient`) pointing to `ox-lsp`.

### Neovim (with nvim-lspconfig)

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

if not configs.ox_lsp then
  configs.ox_lsp = {
    default_config = {
      cmd = { 'ox-lsp' },
      filetypes = { 'ox' },
      root_dir = function(fname)
        return lspconfig.util.find_git_ancestor(fname) or vim.fn.getcwd()
      end,
      settings = {},
    },
  }
end

lspconfig.ox_lsp.setup {}
```

### Helix

Add to your `languages.toml`:

```toml
[[language]]
name = "ox"
file-types = ["ox"]
language-servers = ["ox-lsp"]

[language-server.ox-lsp]
command = "ox-lsp"
```

## Other Editors

A tree-sitter grammar is available in `tree-sitter-ox` which can be used to add Ox support to any editor with tree-sitter integration (Neovim, Helix, Emacs, etc.).

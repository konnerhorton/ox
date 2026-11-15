# micro-syntax: a micro editor plugin, starting with syntax highlighting

## Intent

### Goal
Start a Lua plugin for the micro editor at `editors/micro/`, the micro counterpart of `editors/vscode`. This first unit
adds only syntax highlighting. The plugin registers `syntax/ox.yaml` for `.ox` files, and that file colors the same
token kinds as the TextMate grammar: comments, block keywords and directives (`@session`, `@end`, `@movement`,
`@template`, `@include`, `@plugin`), dates, the `T`/`W`/`note`/`query` markers, movement names, session and metadata
keys, weights, rep schemes, durations, distances, `completed:` booleans, sRPE ratings and quoted strings.
`docs/editor-support.md` gets a micro section that explains how to install the plugin by hand.

### Why
- micro is a common terminal editor, and it opens `.ox` files as plain text today. This is TODO #11, the micro half.
- **A plugin rather than a bare syntax file:** a plugin can grow later without users changing how they install it.
  It can add lint diagnostics on save (`onSave` plus `buffer.NewMessage`, the way micro's built-in `linter` plugin
  works), commands, and a help page. A plugin can also be installed by ox itself later on.
- A plugin doesn't change how highlighting works. micro plugins can't tokenize text, so the colors still come from
  the YAML regex rules, which the plugin registers with `config.AddRuntimeFile("ox", config.RTSyntax, ...)`.
- Syntax comes first because every later feature of the plugin ships inside this skeleton.

### Constraints
- **micro's regex engine is limited.** micro uses Go's RE2: there's no lookahead or lookbehind, and there are no
  capture groups, so each rule colors its whole match. Later rules override earlier ones. Tokens that depend on
  context, such as a movement name as opposed to the `date:` key, or `T` only when it follows a date, are
  approximated through rule order and `^` anchors, the same way the TextMate grammar approximates `grammar.js`.
- Use only color groups that micro's built-in colorschemes actually color, checked against the colorscheme source
  files rather than chosen from memory. This is the same rule the VS Code grammar follows (`vscode-standard-scopes`).
- Ship no colorscheme. A micro colorscheme replaces the user's for every filetype, the same problem that made
  VS Code drop Ox Dark.
- Target micro 2.0.x, using the plugin API of the 2.0.13 build installed here.
- `ox.yaml` becomes one more copy to keep in step with `grammar.js`, next to `ox.tmLanguage.json`.

### Out of scope
These are later units. The deferred items go to `docs/work/TODO.md` at close-out.
- **Installing through ox.** A wheel can't run code at install time, so this needs the plugin shipped as package
  data plus a command that copies it to `$MICRO_CONFIG_HOME/plug/ox/`. Which command is still open:
  `ox --install-micro`, a separate `ox-editor install micro` script, or turning `ox` into a command group. This is
  a CLI decision for `SPEC.md`.
- **Lint diagnostics on save**, and any other plugin commands.
- **Listing in micro's plugin channel** (`micro -plugin install ox`).
- nano. TODO #11 keeps nano, reworded at close-out.
- LSP in micro. That needs a third-party plugin, and the docs' "point any LSP client at `ox-lsp`" line covers it.
- An automated highlighting test in CI.
- Changes to `grammar.js` or the TextMate grammar.

### SPEC sections touched
- Current State → What works today: add the micro plugin next to the VSCode extension.
- Direction → Better editor experience (context only).

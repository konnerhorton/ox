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

## Spec

There's no long-lived topic doc for this, so the rules live here. `editors/micro/` and `docs/editor-support.md` carry
the result.

### Changes
- **`editors/micro/ox.lua`:** sets `VERSION = "0.1.0"`. Its `preinit()` registers `syntax/ox.yaml` as an
  `RTSyntax` file and `help/ox.md` as an `RTHelp` file, both under the plugin name `ox` (decision 1).
- **`editors/micro/syntax/ox.yaml`:** the rules below. It sets `filetype: ox` and detects `\.ox$` by filename.
- **`editors/micro/help/ox.md`:** a short page for `> help ox`. It says what the plugin does, which colors mean
  what, and links to the docs site.
- **`editors/micro/repo.json`:** `Name`, `Description`, `Website` and `Tags`, with no `Versions` (decision 6).
- **`docs/editor-support.md`:** a "micro" section after the VSCode one. It covers what you get, how to install by
  hand (copy `editors/micro` from a clone to `~/.config/micro/plug/ox`, or symlink it when developing, with
  `$MICRO_CONFIG_HOME` in place of `~/.config/micro` when that's set), that colors follow your colorscheme, and
  that installing through ox is planned. The closing "Tree-sitter Grammar" sentence that calls VSCode "the only
  editor integration shipped today" is updated.

### Color groups

A micro rule colors its whole match, and later rules override earlier ones. RE2 has no lookaround and no captures,
so context comes from `^` anchors and rule order. The rules appear below in file order.

| # | Token | Regex (YAML escaping omitted) | Group |
|---|---|---|---|
| 1 | Block item name | `^\s*[^\s#@:][^\s:]*:` | `special` |
| 2 | Single-line item name | `^\d{4}-\d{2}-\d{2}\s+T\s+[^\s:]+:` | `special` |
| 3 | `@movement` name | `^\s*@movement\s+[^\s:]+` | `special` |
| 4 | Entry marker `T` `W` `note` `query` | `^\d{4}-\d{2}-\d{2}\s+(T\|W\|note\|query)\b` | `statement` |
| 5 | Date | `\b\d{4}-\d{2}-\d{2}\b` | `type` |
| 6 | Block keyword, directive | `^\s*@(session\|movement\|template\|end\|include\|plugin)\b` | `preproc` |
| 7 | Rep scheme | `\b\d+x\d+\b`, `\b\d+(/\d+)+\b` | `identifier` |
| 8 | Weight, single, combined, progressive, `BW` | the `grammar.js` `weight` alternatives, wrapped in `\b` | `constant.number` |
| 9 | Distance, single, progressive | the `grammar.js` `distance` alternatives, wrapped in `\b` | `constant.number` |
| 10 | Duration, single, progressive | the `grammar.js` `duration` regex, after `\b` | `constant.number` |
| 11 | sRPE rating | `^\s*srpe:\s*\d+\b` | `constant.number` |
| 12 | `completed:` value | `^\s*completed:\s*(true\|false)\b` | `constant.bool` |
| 13 | Session `name:` value | `^\s*name:.*$` | `type` |
| 14 | Free-text value (`format:`, `equipment:`, `tags:`, `tag:`, `url:`, `note:`) | `^\s*(format\|equipment\|tags?\|url\|note):.*$` | `default` |
| 15 | Field key | `^\s*(date\|name\|completed\|format\|srpe\|note\|equipment\|tags?\|url):` | `statement` |
| 16 | Quoted string | `"[^"]*"` | `constant.string` |
| 17 | Comment | `^\s*#.*$` | `comment` |

How the order resolves the context-dependent cases:
- `2025-01-10 T pullups: BW 5x10`: rule 2 colors through `pullups:`. Rules 4 and 5 then recolor the date and `T`.
- `date: 2025-01-11`, `srpe: 5 PT45M`, `completed: false`: rule 1 makes the key `special`, and rule 15 takes it
  back to `statement`. The date, rating, duration or boolean keeps its value color.
- `format: 5/3/1 wave`, `note: back squat 5x5` (in `@movement`): rules 7–10 color numbers inside free text, then
  rule 14 resets the line and rule 15 recolors the key. `name: 5x5 Day` works the same through rule 13.
- `160/185/210lb`, `100/200/400m`: rule 7 claims `160/185/210` as reps, and rules 8 and 9 then recolor the whole
  token.
- `2025-01-10 W 185lb T06:30 "home"`: rule 1 can't match, because a date followed by a space isn't `name:`.
  `T06:30` stays plain, the same as in the TextMate grammar.
- `2025-01-10 note "deload: week"`: the colon inside the string can't start an item, since rule 1 needs no
  whitespace before the colon. Rule 16 colors the string.
- A colon ends item names, so the `:` gets the name's color. The TextMate grammar leaves it plain. This is accepted.

### Resolved colors

Colorschemes are read from the `color-link` lines embedded in the micro 2.0.13 binary (`strings /usr/bin/micro`).
All 25 built-in colorschemes define `comment`, `constant`, `identifier`, `preproc`, `special`, `statement` and
`type`. `constant.string` is defined in 21 of them, `constant.bool` in 6 and `constant.number` in 5. Where a
dotted group is missing, micro falls back to `constant`. 🟡 The `default` colorscheme is assumed to be the block
with a monokai palette on `#282828`, since the blocks in the binary aren't labelled. AC 3 confirms it on screen:

| Group | Tokens | Color |
|---|---|---|
| `comment` | comments | `#75715E` grey |
| `preproc` | `@session` `@end` `@movement` `@template` `@include` `@plugin` | `#CB4B16` orange |
| `statement` | markers, field keys | `#F92672` pink |
| `type` | dates, session names | `#66D9EF` cyan |
| `identifier` | rep schemes | `#66D9EF` cyan |
| `special` | movement names | `#A6E22E` green |
| `constant.number` → `constant` | weights, distances, durations, ratings | `#AE81FF` purple |
| `constant.bool` → `constant` | `true` / `false` | `#AE81FF` purple |
| `constant.string` | quoted strings | `#E6DB74` yellow |

### Decisions
1. 🟡 **Register in `preinit()`, not `init()`.** micro calls `init()` after buffers exist, so `micro log.ox` would
   open before the syntax file is registered. The built-in `literate` plugin works around this with
   `config.Reload()` and `buf:UpdateRules()`. Registering in `preinit()` should avoid the problem altogether. If
   the build shows otherwise, the fallback is `init()` plus `config.Reload()`. AC 1 decides.
2. **Markers and field keys share `statement`.** Both are the fixed words that give a line its structure, and in
   the default colorscheme `statement` is the strongest color. `keyword`-like categories are what VS Code uses for
   the markers too.
3. **Movement names are `special`.** Green in the default colorscheme, which is where monokai puts function names,
   matching VS Code's `entity.name.function`.
4. **Rep schemes are `identifier`,** the one remaining group that's distinct from `constant`. Weights and reps
   sit next to each other in almost every line, so they need different colors. In the default colorscheme
   `identifier` matches `type`, so reps and dates are both cyan. They never sit next to each other (dates open a
   line, reps sit among the values), so this is accepted.
5. 🟡 **Free-text values are reset to `default`,** so numbers inside `format:` or a movement's `note:` don't look like
   set data. Without block context, this applies to these keys anywhere, which is harmless, since none of them
   is a movement name in practice. It assumes micro accepts `default` as a rule group, as it does in colorschemes.
   If it doesn't, rule 14 is dropped and free text keeps the number colors.
6. **`repo.json` without `Versions`.** micro's docs ask for a `repo.json` in every plugin, but `Versions` needs a
   download URL, which only exists once the plugin is in a channel. That's out of scope.
7. **The plugin is versioned on its own,** starting at `0.1.0` like the VSCode extension. Whether it follows the
   ox version once ox installs it is a question for that unit.
8. **There's no committed highlight test,** per the intent. Verification is manual, through tmux (see below). The
   case file lives in the scratchpad, and the plan step says how to recreate it.

### Acceptance criteria
Checked with `editors/micro` copied to `$MICRO_CONFIG_HOME/plug/ox` under a temporary `MICRO_CONFIG_HOME`, so the
user's own micro config is untouched. micro runs in a detached tmux pane, `tmux capture-pane -e -p` captures the
screen, and the ANSI color codes are compared per token.

1. `micro examples/example.ox` shows filetype `ox` in the status line and highlights on the first frame, with no
   restart. So does a new, empty `new.ox` once a line is typed.
2. micro starts with no plugin error, and `micro -plugin list` lists `ox 0.1.0`.
3. In the `default` colorscheme, every token in the case file renders in the color its group has in the table
   above. The case file covers every row of the color group table and every example in "How the order resolves",
   plus every line of `examples/example.ox`.
4. Every group the syntax file uses is in the color group table, and each is either defined in all 25 built-in
   colorschemes or falls back to `constant`, which is.
5. `> help ox` opens the plugin's help page.
6. A `.py` file still opens with filetype `python`. The plugin claims only `.ox`.
7. The install steps in `docs/editor-support.md`, followed exactly against the temporary config, produce the
   result in AC 1.
8. Nothing outside `editors/micro/`, `docs/editor-support.md` and this work file changes, and `uv run pytest` and
   `uv run ruff check src/ tests/` still pass.

### Close-out (for the record, done in the last build commit)
- `SPEC.md` "What works today": a micro plugin bullet next to the VSCode extension.
- `CLAUDE.md`: next to the VSCode no-theme note, add that the micro plugin ships no colorscheme, and that its
  groups are checked against the `color-link` lines in the micro binary.
- `docs/work/TODO.md`: reword #11 to cover nano only. Add items for installing through ox (with the three command
  options), lint on save, and listing in micro's plugin channel.
- `CHANGELOG.md` Unreleased: the micro plugin.

## Plan

Two build commits, both on Opus, so the build fits in one session. Step 1 is regex work judged against the screen.
Step 2 is short, and it carries the close-out, which needs Opus anyway.

### Verification harness (scratchpad, not committed)
A fresh session has to recreate this, since the scratchpad doesn't carry over.
- `MICRO_CONFIG_HOME=$SCRATCH/mcfg`. Copy `editors/micro` to `$SCRATCH/mcfg/plug/ox` (use `cp -r`, not a symlink, so
  AC 7 tests what the docs say). Never touch `~/.config/micro`.
- `cases.ox` in the scratchpad holds one line for each row of the spec's color group table and each example in "How
  the order resolves", inside the right blocks: a single-line `T` entry, a weigh-in with `T06:30` and a scale, a
  `note` with a colon in its string, a `query`, and a session with `date:`, `name: 5x5 Day`, `completed: false`,
  `format: 5/3/1 wave`, `srpe: 5 PT45M "note"`, `note:`, plus items with `BW`, `24kg+32kg`, `160/185/210lb`,
  `BW/25lb`, `5x5`, `5/5/5`, `PT30S/PT25S`, `100/200/400m` and `5km`. Also `@movement squat` with `equipment:`,
  `tags:` and a `note:` containing `5x5`, a `@template`, `@include`, `@plugin`, and top-level and indented comments.
- `check.py` (run with `python3 -I`) starts micro in a detached tmux pane:
  `tmux new-session -d -x 160 -y 60 -e MICRO_CONFIG_HOME=... -e COLORTERM=truecolor "micro <file>"`. It waits until
  the status line shows the filetype, then runs `tmux capture-pane -e -p` and parses the SGR codes into a color per
  character. For each case it prints each token with its foreground and the expected group's color from the spec's
  resolved colors table, and flags mismatches. If tmux reduces the colors to 256 (`38;5;n`), compare against the
  nearest xterm-256 color of each hex instead.
- Kill the tmux session after each capture.

### Step 1: `micro-syntax: add the micro plugin with syntax highlighting` (Opus)
Files: `editors/micro/ox.lua`, `editors/micro/syntax/ox.yaml`, `editors/micro/help/ox.md`,
`editors/micro/repo.json`.
- `ox.lua`: `VERSION = "0.1.0"`. `preinit()` calls `config.AddRuntimeFile("ox", config.RTSyntax,
  "syntax/ox.yaml")` and `config.AddRuntimeFile("ox", config.RTHelp, "help/ox.md")`.
- `ox.yaml`: rules 1–17 in order, with the weight, distance and duration regexes copied from `grammar.js` (there's
  a comment above each saying so, to keep them in step).
- Resolve the 🟡 decisions as the harness shows them. Decision 1: if `preinit()` fails AC 1, switch to `init()`
  plus `config.Reload()`. Decision 5: if `default` isn't accepted as a group, drop rule 14. Colorscheme identity:
  if the screen doesn't match the resolved colors table, correct the table. Record any change in `## Spec` in this
  same commit.
- Proves:
  - AC 1: `micro examples/example.ox` and a new `new.ox`, with the status line captured.
  - AC 2: `micro -plugin list` and a clean first frame, with no error in the info bar.
  - AC 3: `check.py` on `cases.ox` and `examples/example.ox`, with no mismatches.
  - AC 4: grep the `- group:` keys in `ox.yaml` against the spec table.
  - AC 5: send `Ctrl-e`, `help ox`, `Enter` through `tmux send-keys`, then capture.
  - AC 6: open a scratch `.py` file and capture the status line.
- After the harness passes, look at one full capture of `examples/example.ox` yourself, as a human-facing check.

### Step 2: `micro-syntax: document the micro plugin and close out` (Opus)
Files: `docs/editor-support.md`, `SPEC.md`, `CLAUDE.md`, `docs/work/TODO.md`, `CHANGELOG.md`.
- `docs/editor-support.md`: the micro section and the updated Tree-sitter sentence, per `## Spec` → Changes.
- Close-out, as `## Spec` → Close-out lists:
  - the micro bullet in `SPEC.md` "What works today";
  - the colorscheme note in `CLAUDE.md` next to the VSCode one;
  - TODO #11 reworded to nano only;
  - new TODO items for installing through ox (the options: `ox --install-micro`, an `ox-editor install micro`
    script, `ox` as a command group), lint on save, and the micro plugin channel;
  - a `CHANGELOG.md` Unreleased entry.
- Proves:
  - AC 7: wipe `$SCRATCH/mcfg`, follow the doc's install steps exactly, and rerun the AC 1 capture.
  - AC 8: `git diff --stat main` lists only the expected paths, and `uv run pytest` and
    `uv run ruff check src/ tests/` pass.

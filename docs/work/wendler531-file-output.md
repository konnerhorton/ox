# wendler531-file-output: append a generated cycle to a file

## Intent

### Goal
`wendler531` takes an optional `-f/--file <path>` argument. When it's given, the generated cycle is
appended to that file as valid `.ox` text, so a planned cycle goes straight into a log without
copy-paste.

### Why
- Today the output only goes to the console, so getting a cycle into a log means copy-pasting it
  from the terminal.
- SPEC "Core Principles": plain text is the source of truth. The plugin already emits round-trippable
  `.ox` (`completed: false` sessions); this closes the gap to the file.

### Constraints
- The output must stay valid `.ox` that parses back to the same sessions (round-trip convention,
  CLAUDE.md).
- Never overwrite or truncate an existing file. Append only.
- Without `-f`, behavior is unchanged.
- Args go through the existing `parse_plugin_args` param spec; the plugin infrastructure doesn't change.

### Out of scope
- Generic output redirection for every plugin (e.g. `volume ... > out.txt`). Table and plot output
  isn't `.ox`, so appending makes less sense there. A separate CLI-level unit if ever wanted.
- Reloading the REPL after appending to the open log. The user runs `reload`.
- Checking for duplicates (e.g. the same cycle appended twice).
- The `--start-date` docs bug (TODO #4).

### SPEC sections touched
- None. `docs/plugins.md` (wendler531 param table) and `CHANGELOG.md` get updated.

### Decisions (intent review, 2026-10-24)
1. **Relative paths resolve against the current working directory; `~` is expanded.** `PluginContext`
   doesn't carry the log's path, and resolving against it would mean changing the plugin API, which
   is out of proportion here. An absolute path goes anywhere. Python doesn't expand `~` on its own,
   so `-f ~/log.ox` would otherwise create a directory literally named `~`.
2. **The cycle is still shown on the console, followed by an "Appended" line.** You can see what was
   written without opening the file.
3. **Blank-line separation.** If the file is non-empty, a blank line separates the existing content
   from the new block, adding a trailing newline first if the file doesn't end in one.
4. **Missing file → created. Missing parent directory → error** (`ValueError`, shown in red by the
   CLI), with no directories created.

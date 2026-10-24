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

## Spec

The rules live here; `docs/plugins.md` gets the user-facing description.

### Changes
- **`src/ox/builtins/wendler531.py`:** a new `file` param (`-f`, default `None`) on `wendler531()` and
  in `register()`; the append logic in a small helper, `_append_to_file(path, text)`.
- **`docs/plugins.md`, wendler531 section:** a `-f/--file` row in the param table and one example.
- **`CHANGELOG.md`, v0.6.0 (untagged):** a one-line entry.

### Decisions
1. **The appended text is exactly the cycle text** that's displayed without `-f` (four sessions, each
   rendered by `TrainingSession.to_ox()`, separated by blank lines, ending in a newline). No header
   comment and no generation timestamp, so the file gets the same `.ox` the console shows.
2. **Separator rule (intent decision 3, made exact).** Existing bytes are never modified, so
   separation is only ever *added*:
   - empty or new file → nothing is prepended;
   - file ends in `\n\n` → nothing is prepended;
   - file ends in a single `\n` → `\n` is prepended;
   - file ends without a newline → `\n\n` is prepended.
   A file that already ends in several blank lines keeps them; trimming them would mean rewriting
   existing content.
3. **Path handling:** `Path(file).expanduser()`, resolved against the current working directory.
   The "Appended" line shows the **resolved absolute path**, so a cwd-relative path is never
   ambiguous about where the cycle went.
4. **Return value:** `TextResult(cycle_text + "\nAppended 4 sessions to <absolute path>\n")`.
   The count comes from the generated sessions, not a literal 4.
5. **Errors are `ValueError`,** the exception the CLI's `run_plugin` catches and shows in red:
   - parent directory missing → `ValueError("Directory does not exist: <parent>")`;
   - path is a directory → `ValueError("Not a file: <path>")`;
   - any other `OSError` on open or write (permissions, etc.) → re-raised as
     `ValueError(f"Could not write to <path>: <reason>")`.
6. **Nothing is written unless the whole cycle generates.** The cycle text is built first; the file
   is opened only afterwards, so a bad `-m` value or date leaves the file untouched.
7. **Encoding:** UTF-8 for reading the tail and appending. The tail check reads only the last two
   bytes.

### Acceptance criteria
1. **No `-f`, no change:** `wendler531(ctx, movements="squat:300", start_date="2026-01-05")` returns
   the same text as before this change, and no file is created.
2. **New file:** with `file=<tmp>/new.ox` (not existing), the file is created and its contents equal
   the cycle text exactly.
3. **Existing content preserved:** appending to a file containing
   `2026-01-01 T pullups: BW 5x10\n` leaves that line byte-for-byte at the start, followed by `\n`,
   then the cycle text.
4. **Separator cases:** for existing contents `""`, `"x\n\n"`, `"x\n"` and `"x"`, the bytes inserted
   before the cycle text are `""`, `""`, `"\n"` and `"\n\n"` respectively.
5. **Round-trip:** `parse_file` on the file from AC 3 yields the original session plus four sessions
   dated 2026-01-05, -12, -19 and -26, all `completed == False`, with no diagnostics.
6. **Appends twice:** running the same command twice leaves eight planned sessions in the file
   (no dedupe, per Out of scope).
7. **Result text:** the returned text is the cycle text followed by
   `\nAppended 4 sessions to <absolute path>\n`, and the path shown is absolute even when `file` is
   relative (tested with `monkeypatch.chdir(tmp_path)` and `file="log.ox"`).
8. **`~` expansion:** with `HOME` monkeypatched to `tmp_path`, `file="~/log.ox"` writes
   `tmp_path/log.ox`.
9. **Missing parent directory:** `file=<tmp>/nope/log.ox` raises `ValueError` mentioning
   `Directory does not exist`, and `<tmp>/nope` is not created.
10. **Path is a directory:** `file=<tmp>` raises `ValueError` mentioning `Not a file`.
11. **No partial write:** `movements="squat"` (no training max) with `file=<existing file>` raises
    `ValueError` and leaves the file byte-for-byte unchanged.
12. **CLI flags:** `parse_plugin_args` with `-f log.ox` and with `--file log.ox` both give
    `{"file": "log.ox", ...}`; `register()` lists the param with `short: "f"` and default `None`.
13. **Docs:** `docs/plugins.md` lists `-f/--file`, and `uv run mkdocs build` is clean.

# drop-old-syntax-hints: remove the pre-0.6 syntax lint hints

Resolves TODO #9.

## Intent

### Goal
Lint stops carrying special-case hints for the pre-0.6 syntax: `*`/`!` entry flags, positional
session headers (`2025-01-12 * Lower` after `@session`) and `srpe: "5; PT45M"`.

### Why
- The hints existed to support migrating old logs. The migration script was removed in v0.6.1 and
  the only pre-0.6 log has been converted, so they no longer serve anyone (user decision,
  2026-11-04).
- Each is a regex and a rule that every line runs through; dropping them shrinks `lint.py` and its
  tests.

### Constraints
- Old syntax must still be *rejected*. It just gets the general diagnostic instead of a
  migration-specific one. Checked by running lint without the three rules:

  | Input | Diagnostic after removal |
  |---|---|
  | `2025-01-10 * pullups: BW 5x10` | `Syntax error` (line 1) |
  | `@session` / `2025-01-12 * Lower` / … | "A session block must start with a `date:` line" (line 1), plus `Syntax error` on the following lines |
  | `srpe: "5; PT45M"` in a session | the existing "sRPE line is `srpe: <whole-number rating> <duration> ["note"]`…" hint |

  🟡 Proposed: the generic `Syntax error` for `*`/`!` entries is acceptable. No new hint for them.

### Out of scope
- Other lint rules, and the parser's handling of malformed `srpe:` lines (`get_srpe` keeps its
  `has_error` check, which applies to any malformed line, not just the old one).

### SPEC sections touched
- None. `CHANGELOG.md` gets an entry.

## Plan

One build commit, with close-out included.

1. **`drop-old-syntax-hints: remove pre-0.6 lint hints` (Sonnet)**
   - `src/ox/lint.py`: delete `OLD_ENTRY`, `OLD_HEADER`, `OLD_SRPE`, the functions `_old_entry`,
     `_old_header`, `_old_srpe`, and their entries in `LINE_RULES`. In `_session_without_date`,
     drop the `or OLD_HEADER.match(first)` clause, so an old header gets the missing-`date:` hint.
   - `src/ox/parse.py:62`: reword the comment so it doesn't cite the pre-0.6 form as its example
     (e.g. "A malformed line still recovers a rating and duration").
   - `tests/test_lint.py`: remove the `"Old sRPE"` case from the `test_hint` parameters (line 91),
     `test_old_session_header_hint` and `test_old_syntax_hints_name_no_script`. Add one test pinning
     the fallbacks in the table above: each old form still produces an error-severity diagnostic,
     and the old header and old sRPE forms get the messages listed.
   - Found during build: `src/ox/lint.py`'s module docstring cited "the pre-0.6 syntax" as an
     example hint, and `tests/test_parse.py::test_old_quoted_form_is_a_syntax_error` asserted the
     "Old sRPE syntax" message. The docstring now cites a malformed `srpe:` line; the test is
     renamed `test_quoted_form_is_a_syntax_error` and asserts the sRPE-line hint.
   - `grep -rn "Old entry\|Old session header\|Old sRPE\|pre-0.6" src/ tests/ docs/` should only
     find `CHANGELOG.md` history.
   - Close-out: delete TODO #9 from `docs/work/TODO.md`; add a line to the unreleased section of
     `CHANGELOG.md` (create it if `srpe-guard` hasn't merged first).
   - `uv run ruff check src/ tests/ && uv run ruff format src/ tests/ && uv run pytest`.

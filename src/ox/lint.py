"""Lint utilities for ox training log files.

Tree-sitter reports where parsing failed, not why. `collect_diagnostics` turns
each ERROR node into a diagnostic, and where a line inside the error matches a
known mistake (curly quotes, the pre-0.6 syntax, `135lbs`, `25min`, ...) it
reports that mistake instead of a bare "Syntax error".

Error recovery often wraps a whole session block in one ERROR node, so hints
are checked against every line the node covers. Every hint pattern matches
only text the grammar rejects, so a valid line swept into a large ERROR node
never picks up a hint.
"""

import re
from typing import Callable, Optional

from ox.data import Diagnostic

DATE = r"\d{4}-\d{2}-\d{2}"
MIGRATE = "scripts/migrate_ox.py converts pre-0.6 logs"

BLOCK_START = re.compile(r"\s*@(session|movement|template)\b")
BLOCK_END = re.compile(r"\s*@end\b")

OLD_ENTRY = re.compile(rf"\s*{DATE}\s+([*!])\s+[^\s:]+\s*:")
OLD_HEADER = re.compile(rf"\s*{DATE}\s+([*!])\s+\S")
MISSING_T = re.compile(rf"\s*{DATE}\s+([a-z][\w-]*)\s*:")
OLD_SRPE = re.compile(r'\s*(srpe:\s*".*)')
SRPE_FRACTION = re.compile(r"\s*srpe:\s*(\d+\.\d+)")
SRPE_ANY = re.compile(r"\s*(srpe:.*?)\s*$")
VALID_SRPE = re.compile(r'\s*srpe:\s*\d+\s+PT\S+(\s+"[^"\n]*")?\s*$')
COMPLETED = re.compile(r"\s*completed:\s*(.*?)\s*$")
DATE_LINE = re.compile(r"\s*date:\s*(.*?)\s*$")
PLURAL_UNIT = re.compile(r"(?<=\d)(lbs|kgs)\b")
LOOSE_DURATION = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s?"
    r"(hours|hour|hrs|hr|h|minutes|minute|mins|min|seconds|second|secs|sec|s)\b"
)
CURLY = re.compile(r"[“”]")

ISO_UNIT = {"h": "H", "m": "M", "s": "S"}

Span = tuple[int, int]


def _mask_quoted(line: str) -> str:
    """Blank out the contents of closed "..." strings, keeping columns intact."""
    return re.sub(r'"[^"]*"', lambda m: '"' + " " * (len(m[0]) - 2) + '"', line)


def _group_span(match: re.Match, group: int = 1) -> Span:
    return match.start(group), match.end(group)


# Each rule takes one line and returns (span, message) if the line has that
# mistake. Rules run in order and the first match wins.


def _curly_quotes(line: str):
    # Curly quotes inside a closed straight-quoted note are fine. They're a
    # mistake when they stand in for the straight quotes, which leaves a
    # straight quote unpaired or puts the curly quote outside any note.
    if not CURLY.search(line):
        return None
    if line.count('"') % 2 == 0 and not CURLY.search(_mask_quoted(line)):
        return None
    found = [m.start() for m in CURLY.finditer(line)]
    return (found[0], found[-1] + 1), 'Curly quote: use a straight double quote (")'


def _old_entry(line: str):
    if m := OLD_ENTRY.match(line):
        return _group_span(m), (
            f"Old entry syntax: replace `{m[1]}` with `T`; planned work goes in a "
            f"session block with `completed: false`. {MIGRATE}"
        )
    return None


def _old_header(line: str):
    if m := OLD_HEADER.match(line):
        return _group_span(m), (
            "Old session header: write `date:` and `name:` lines after "
            f"`@session`, and `completed: false` for planned work. {MIGRATE}"
        )
    return None


def _missing_t(line: str):
    if m := MISSING_T.match(line):
        return _group_span(m), (
            "Single-line entry needs `T` after the date, "
            f"e.g. `2025-01-10 T {m[1]}: ...`"
        )
    return None


def _old_srpe(line: str):
    if m := OLD_SRPE.match(line):
        return _group_span(m), (
            f'Old sRPE syntax: write `srpe: 5 PT45M ["note"]`. {MIGRATE}'
        )
    return None


def _srpe_fraction(line: str):
    if m := SRPE_FRACTION.match(line):
        return _group_span(m), "sRPE rating must be a whole number"
    return None


def _srpe_malformed(line: str):
    if (m := SRPE_ANY.match(line)) and not VALID_SRPE.match(line):
        return _group_span(m), (
            'sRPE line is `srpe: <whole-number rating> <duration> ["note"]`, '
            "e.g. `srpe: 5 PT45M`"
        )
    return None


def _completed_value(line: str):
    if (m := COMPLETED.match(line)) and m[1] not in ("true", "false"):
        return _value_span(line, m), "`completed:` takes `true` or `false`"
    return None


def _date_value(line: str):
    if (m := DATE_LINE.match(line)) and not re.fullmatch(DATE, m[1]):
        return _value_span(line, m), "`date:` takes a date in YYYY-MM-DD form"
    return None


def _value_span(line: str, m: re.Match) -> Span:
    """The value's span, or the whole line when the value is empty."""
    if m.start(1) == m.end(1):
        return len(line) - len(line.lstrip()), len(line)
    return _group_span(m)


def _unclosed_quote(line: str):
    if line.count('"') % 2 == 1:
        return (line.rfind('"'), len(line)), 'Unclosed quote: add a closing `"`'
    return None


def _plural_unit(line: str):
    if m := PLURAL_UNIT.search(_mask_quoted(line)):
        unit = m[1]
        return _group_span(m), f"Unknown unit `{unit}`: use `{unit[:-1]}`"
    return None


def _loose_duration(line: str):
    if not (m := LOOSE_DURATION.search(_mask_quoted(line))):
        return None
    amount, unit = m[1], m[2]
    example = "`PT30M`, `PT45S`, or `PT1H30M`"
    if amount.isdigit():
        example = f"`PT{amount}{ISO_UNIT[unit[0]]}`"
    return (m.start(), m.end()), f"Durations use ISO 8601: write {example}"


LINE_RULES: tuple[Callable[[str], Optional[tuple[Span, str]]], ...] = (
    _curly_quotes,
    _old_entry,
    _old_header,
    _missing_t,
    _old_srpe,
    _srpe_fraction,
    _srpe_malformed,
    _completed_value,
    _date_value,
    _unclosed_quote,
    _plural_unit,
    _loose_duration,
)


# Block rules look past the line itself, so they take every line of the file.


def _first_content_line(lines: list[str], row: int) -> Optional[str]:
    """The next line after `row` that isn't blank or a comment."""
    for line in lines[row + 1 :]:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return line
    return None


def _session_without_date(lines: list[str], row: int):
    if lines[row].strip() != "@session":
        return None
    first = _first_content_line(lines, row)
    if first is None or DATE_LINE.match(first) or OLD_HEADER.match(first):
        return None
    return _line_span(lines[row]), "A session block must start with a `date:` line"


def _block_without_end(lines: list[str], row: int):
    if not (m := BLOCK_START.match(lines[row])):
        return None
    for line in lines[row + 1 :]:
        if BLOCK_END.match(line):
            return None
        if BLOCK_START.match(line):
            break
    return _line_span(lines[row]), f"`@{m[1]}` block is missing `@end`"


def _line_span(line: str) -> Span:
    return len(line) - len(line.lstrip()), len(line.rstrip())


BLOCK_RULES = (_session_without_date, _block_without_end)


def _hint_for(lines: list[str], row: int) -> Optional[tuple[Span, str]]:
    """The first hint that applies to `row`, if any."""
    line = lines[row]
    for rule in LINE_RULES:
        if hint := rule(line):
            return hint
    for rule in BLOCK_RULES:
        if hint := rule(lines, row):
            return hint
    return None


def _rows(node) -> range:
    """Rows a node covers, not counting a trailing row it only touches at col 0."""
    start, end = node.start_point[0], node.end_point[0]
    if end > start and node.end_point[1] == 0:
        end -= 1
    return range(start, end + 1)


def _enclosing_block_row(lines: list[str], row: int) -> Optional[int]:
    """The row of the nearest block opener at or above `row`."""
    for r in range(min(row, len(lines) - 1), -1, -1):
        if BLOCK_START.match(lines[r]):
            return r
    return None


def collect_diagnostics(tree) -> tuple[Diagnostic, ...]:
    """Walk a tree-sitter tree and collect ERROR/MISSING nodes as Diagnostics.

    Lines with a recognized mistake get one targeted diagnostic each (columns
    in characters); other errors fall back to "Syntax error" / "Missing X".
    """
    lines = tree.root_node.text.decode("utf-8").split("\n")
    errors, missing = [], []

    def visit(node):
        if node.type == "ERROR":
            errors.append(node)
            return  # don't recurse into ERROR subtrees
        if node.is_missing:
            missing.append(node)
            return
        for child in node.children:
            visit(child)

    visit(tree.root_node)

    hints: dict[int, tuple[Span, str]] = {}
    unexplained = []
    for node in errors:
        found = False
        for row in _rows(node):
            if row < len(lines) and (hint := _hint_for(lines, row)):
                hints[row] = hint
                found = True
        if not found:
            unexplained.append(node)

    generic = []
    for node in missing:
        row = node.start_point[0]
        if node.type == "@end":
            opener = _enclosing_block_row(lines, row)
            if opener is not None and (hint := _block_without_end(lines, opener)):
                hints[opener] = hint
                continue
        generic.append((node, f"Missing {node.type}"))
    generic.extend((node, "Syntax error") for node in unexplained)

    diagnostics = [
        Diagnostic(
            line=row + 1,
            col=start,
            end_line=row + 1,
            end_col=end,
            message=message,
            severity="error",
        )
        for row, ((start, end), message) in hints.items()
    ]
    diagnostics.extend(
        Diagnostic(
            line=node.start_point[0] + 1,
            col=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_col=node.end_point[1],
            message=message,
            severity="error",
        )
        for node, message in generic
        if node.start_point[0] not in hints
    )
    return tuple(sorted(diagnostics, key=lambda d: (d.line, d.col)))

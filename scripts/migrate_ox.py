#!/usr/bin/env python3
"""Convert .ox files from the old flag syntax to the new session syntax.

Three transformations:

- Single-line entries swap the `*` completion flag for the `T` type marker.
- Session block headers become `date:` / `name:` / `completed:` lines.
- The `srpe: "5; PT45M"` movement hack becomes a real `srpe: 5 PT45M` line.

Everything else — weigh-ins, notes, queries, `@movement`, `@template`,
`@include`, `@plugin`, comments, blank lines — passes through untouched.

The script refuses to guess. Anything it cannot convert faithfully raises
MigrationError naming the line, so the file is fixed by hand rather than
silently mangled.

Usage:
    python scripts/migrate_ox.py log.ox              # write to stdout
    python scripts/migrate_ox.py log.ox --in-place   # rewrite the file
"""

import argparse
import re
import sys
from pathlib import Path

DATE = r"\d{4}-\d{2}-\d{2}"

# A single-line entry: date, flag, then "movement: details".
SINGLELINE = re.compile(rf"^(?P<date>{DATE}) (?P<flag>[*!]) (?P<rest>[^\s:]+:.*)$")

# The positional session header, the line right after "@session".
SESSION_HEADER = re.compile(rf"^(?P<date>{DATE}) (?P<flag>[*!]) (?P<name>.+)$")

# The old sRPE movement hack, with either separator seen in the wild.
OLD_SRPE = re.compile(
    r'^(?P<indent>\s*)srpe:\s*"\s*(?P<rating>[\d.]+)\s*[;,]\s*(?P<duration>PT\S+?)\s*"\s*$',
    re.IGNORECASE,
)

# The same data buried in a movement's note. Hoisting it turns the entry into
# an unnamed session block, so only the unambiguous shape is converted: the
# sRPE must be a trailing, comma-separated suffix of the note.
EMBEDDED_SRPE = re.compile(r"\bsrpe:\s*[\d.]+\s*[;,]\s*PT\S*", re.IGNORECASE)
HOISTABLE_NOTE = re.compile(
    r'^(?P<before>.*?)"(?:(?P<note>[^"]*?)\s*,\s*)?'
    r"srpe:\s*(?P<rating>[\d.]+)\s*[;,]\s*(?P<duration>PT\S+?)\s*\"$",
    re.IGNORECASE,
)


class MigrationError(Exception):
    """A line the script will not convert on its own."""


def _fail(line_no: int, line: str, reason: str) -> None:
    raise MigrationError(f"line {line_no}: {reason}\n    {line.strip()}")


def _convert_srpe(match: re.Match, line_no: int, line: str) -> str:
    rating = match["rating"]
    if not rating.isdigit():
        _fail(
            line_no,
            line,
            f"sRPE rating {rating!r} is not a whole number and the new syntax "
            "takes an integer; pick a rating by hand",
        )
    return f"{match['indent']}srpe: {rating} {match['duration']}"


def _hoist_srpe(single: re.Match, line_no: int, line: str) -> list[str]:
    """Rewrite a single-line entry whose note carries an sRPE as a session block.

    `2025-01-08 * run: PT30M "easy pace, srpe: 3; PT30M"` becomes an unnamed
    session holding the movement and a real `srpe:` line. The note keeps only
    the text before the sRPE suffix.
    """
    note = HOISTABLE_NOTE.match(single["rest"])
    if not note:
        _fail(
            line_no,
            line,
            "sRPE is in a note but not as a trailing `, srpe: N; PT...` suffix; "
            "move it to an `srpe:` line inside a session block by hand",
        )
    if not note["rating"].isdigit():
        _fail(
            line_no,
            line,
            f"sRPE rating {note['rating']!r} is not a whole number and the new "
            "syntax takes an integer; pick a rating by hand",
        )

    movement = note["before"].rstrip()
    if note["note"]:
        movement += f' "{note["note"]}"'
    return [
        "@session",
        f"date: {single['date']}",
        movement,
        f"srpe: {note['rating']} {note['duration']}",
        "@end",
    ]


def migrate_text(text: str) -> str:
    """Convert one .ox document from the old syntax to the new one.

    Raises:
        MigrationError: On a planned single-line entry, a session block whose
            header is missing, or an sRPE value that cannot be represented.
    """
    out: list[str] = []
    expect_header = False

    for line_no, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()

        if stripped == "@session":
            expect_header = True
            out.append(line)
            continue

        if expect_header:
            expect_header = False
            match = SESSION_HEADER.match(stripped)
            if not match:
                _fail(line_no, line, "@session is not followed by a date header")
            out.append(f"date: {match['date']}")
            out.append(f"name: {match['name'].strip()}")
            if match["flag"] == "!":
                out.append("completed: false")
            continue

        srpe = OLD_SRPE.match(line)
        if srpe:
            out.append(_convert_srpe(srpe, line_no, line))
            continue

        single = SINGLELINE.match(stripped)
        if single:
            if single["flag"] == "!":
                _fail(
                    line_no,
                    line,
                    "planned single-line entries have no new-syntax equivalent; "
                    "write it as a session block with `completed: false`",
                )
            if EMBEDDED_SRPE.search(stripped):
                out.extend(_hoist_srpe(single, line_no, line))
            else:
                out.append(f"{single['date']} T {single['rest']}")
            continue

        if EMBEDDED_SRPE.search(line):
            _fail(
                line_no,
                line,
                "sRPE is buried in a note this script cannot hoist; move it to "
                "an `srpe:` line inside a session block by hand",
            )

        out.append(line)

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="+", type=Path, help=".ox files to convert")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="rewrite each file instead of writing to stdout",
    )
    args = parser.parse_args(argv)

    failures = 0
    for path in args.files:
        try:
            converted = migrate_text(path.read_text())
        except MigrationError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failures += 1
            continue
        if args.in_place:
            path.write_text(converted)
            print(f"{path}: converted", file=sys.stderr)
        else:
            sys.stdout.write(converted)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

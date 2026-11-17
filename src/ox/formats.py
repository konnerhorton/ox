"""The session `format:` vocabulary.

A session's `format:` value describes its timing structure as one quoted string,
a name plus fixed arguments: `"emom PT2M"`, `"intervals PT4M:PT3M"`,
`"superset 2-3-2"`. This module holds the rules and parses a value against them.
It has no plugin or output code, so the same rules can back `lint` or the grammar
later.

A value that doesn't parse is never an error: `parse_format` returns it with a
`problem` message, and the log keeps it as written.
"""

import re
from dataclasses import dataclass
from datetime import timedelta

from ox.duration import parse_iso_duration


@dataclass(frozen=True, slots=True)
class FormatRule:
    """One entry in the format vocabulary.

    Attributes:
        name: The format name, e.g. "emom"
        usage: How it is written, e.g. "emom [interval]"
        description: What it means, in plain English
    """

    name: str
    usage: str
    description: str


VOCABULARY: tuple[FormatRule, ...] = (
    FormatRule(
        "emom",
        "emom [interval]",
        "one set starts every interval (default PT1M), e.g. emom PT2M",
    ),
    FormatRule(
        "alt-emom",
        "alt-emom [interval]",
        "like emom, rotating through the movements, one per interval",
    ),
    FormatRule(
        "intervals",
        "intervals <work>:<rest>",
        "fixed work and rest durations, e.g. intervals PT4M:PT3M",
    ),
    FormatRule(
        "superset",
        "superset <n>-<n>-…",
        "movements grouped in the order listed, e.g. superset 2-3-2",
    ),
    FormatRule(
        "pavel-sprints",
        "pavel-sprints",
        "6 sprints of 8s work / 22s rest per set, 2 min walk between sets",
    ),
    FormatRule("ladder", "ladder", "reps climb by one each round"),
    FormatRule("circuit", "circuit", "one set of each movement in turn, repeated"),
)

_RULES = {rule.name: rule for rule in VOCABULARY}
_DEFAULT_INTERVAL = "PT1M"
_GROUPS = re.compile(r"[1-9]\d*(?:-[1-9]\d*)*$")


@dataclass(frozen=True, slots=True)
class ParsedFormat:
    """A `format:` value parsed against the vocabulary.

    Attributes:
        value: The value as written, quotes included
        name: The format name, or None if the value didn't get that far
        interval: Time between set starts (emom, alt-emom)
        rotating: True for alt-emom
        work: Work duration (intervals)
        rest: Rest duration (intervals)
        groups: Movement group sizes in order (superset)
        meaning: Plain-English reading of the value; "" when there is a problem
        problem: Why the value doesn't fit the vocabulary, or None
    """

    value: str
    name: str | None = None
    interval: timedelta | None = None
    rotating: bool = False
    work: timedelta | None = None
    rest: timedelta | None = None
    groups: tuple[int, ...] | None = None
    meaning: str = ""
    problem: str | None = None


def _duration(text: str) -> timedelta | None:
    """A single positive ISO 8601 duration, or None if `text` isn't one."""
    if "/" in text:
        return None
    try:
        td = parse_iso_duration(text)
    except ValueError:
        return None
    return td if td > timedelta(0) else None


def parse_format(value: str) -> ParsedFormat:
    """Parse a session `format:` value against the vocabulary.

    Args:
        value: The value as written after `format:`, e.g. '"emom PT2M"'

    Returns:
        A ParsedFormat. If the value doesn't fit the vocabulary, `problem` says
        why ("not quoted", "empty", 'unknown format "<name>"' or
        'expected "<usage>"') and `meaning` is "".
    """
    text = value.strip()
    if len(text) < 2 or not (text.startswith('"') and text.endswith('"')):
        return ParsedFormat(value, problem="not quoted")
    words = text[1:-1].split()
    if not words:
        return ParsedFormat(value, problem="empty")

    name, args = words[0], words[1:]
    rule = _RULES.get(name)
    if rule is None:
        return ParsedFormat(value, name=name, problem=f'unknown format "{name}"')
    bad = ParsedFormat(value, name=name, problem=f'expected "{rule.usage}"')

    if name in ("emom", "alt-emom"):
        if len(args) > 1:
            return bad
        written = args[0] if args else _DEFAULT_INTERVAL
        interval = _duration(written)
        if interval is None:
            return bad
        rotating = name == "alt-emom"
        meaning = f"one set every {written}"
        if rotating:
            meaning += ", rotating through movements"
        return ParsedFormat(
            value, name=name, interval=interval, rotating=rotating, meaning=meaning
        )

    if name == "intervals":
        if len(args) != 1 or args[0].count(":") != 1:
            return bad
        work_text, rest_text = args[0].split(":")
        work, rest = _duration(work_text), _duration(rest_text)
        if work is None or rest is None:
            return bad
        return ParsedFormat(
            value,
            name=name,
            work=work,
            rest=rest,
            meaning=f"{work_text} work, {rest_text} rest",
        )

    if name == "superset":
        if len(args) != 1 or not _GROUPS.match(args[0]):
            return bad
        groups = tuple(int(n) for n in args[0].split("-"))
        return ParsedFormat(
            value,
            name=name,
            groups=groups,
            meaning="movements grouped " + ", ".join(str(n) for n in groups),
        )

    # Named protocols take no arguments.
    if args:
        return bad
    return ParsedFormat(value, name=name, meaning=rule.description)


def check_movement_count(parsed: ParsedFormat, count: int) -> bool:
    """Check a parsed format against a session's movement count.

    Only a superset can disagree: its group sizes must add up to the number of
    movement lines in the session.

    Args:
        parsed: The session's parsed format
        count: The number of movement lines in the session

    Returns:
        False if `parsed` is a superset whose groups don't add up to `count`,
        otherwise True
    """
    return parsed.groups is None or sum(parsed.groups) == count

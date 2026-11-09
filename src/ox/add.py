"""The REPL's `add` command: append one session to the log.

The pure pieces (prefill lookups, line checks, building and appending the
text) are separate from `run_add`, which drives the prompts through an
injected `ask` function so tests can script the answers.
"""

import re
from datetime import date
from pathlib import Path

from tree_sitter import Parser

from ox.data import Movement, TrainingLog, TrainingSession
from ox.grammar import LANGUAGE
from ox.lint import collect_diagnostics
from ox.parse import process_node

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

MOVEMENT_EXAMPLE = "Expected a movement line, e.g. `squat: 185lb 5x5`"


def _parse(text: str) -> tuple[list[str], list[TrainingSession]]:
    """Diagnostic messages and sessions from parsing `text` as a log."""
    tree = Parser(LANGUAGE).parse(text.encode("utf-8"))
    messages = [d.message for d in collect_diagnostics(tree)]
    sessions = [
        result
        for child in tree.root_node.children
        if isinstance(result := process_node(child), TrainingSession)
    ]
    return messages, sessions


def _block(day: date, lines: list[str]) -> str:
    return "\n".join(["@session", f"date: {day.isoformat()}", *lines, "@end"]) + "\n"


def last_session(log: TrainingLog, name: str) -> TrainingSession | None:
    """The completed session named exactly `name` with the latest date.

    On a tie, the one later in the log wins.
    """
    best = None
    for session in log.sessions:
        if session.completed and session.name == name:
            if best is None or session.date >= best.date:
                best = session
    return best


def last_movements(log: TrainingLog) -> dict[str, Movement]:
    """Each movement's instance in the latest completed session.

    On a tie, the one later in the log wins.
    """
    best: dict[str, tuple[date, Movement]] = {}
    for session in log.sessions:
        if not session.completed:
            continue
        for movement in session.movements:
            seen = best.get(movement.name)
            if seen is None or session.date >= seen[0]:
                best[movement.name] = (session.date, movement)
    return {name: movement for name, (_, movement) in best.items()}


def prefill_text(movement: Movement) -> str:
    """The movement as an `.ox` line, without its note."""
    return Movement(movement.name, movement.sets, None).to_ox()


def parse_date(text: str, today: date) -> date:
    """The date typed at the `date` prompt; empty means `today`.

    Raises:
        ValueError: If `text` isn't a real calendar date in YYYY-MM-DD form.
    """
    text = text.strip()
    if not text:
        return today
    if not ISO_DATE.fullmatch(text):
        raise ValueError("Date must be YYYY-MM-DD, e.g. 2025-01-10")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Not a calendar date: {text}") from None


def check_line(text: str, day: date) -> str | None:
    """The problem with a movement line, or None if it parses as one."""
    messages, sessions = _parse(_block(day, [text.strip()]))
    if messages:
        return messages[0]
    session = sessions[0] if len(sessions) == 1 else None
    if (
        session is None
        or len(session.movements) != 1
        or session.name is not None
        or session.format is not None
        or session.srpe_rating is not None
        or session.notes
        or not session.completed
    ):
        return MOVEMENT_EXAMPLE
    return None


def check_srpe(text: str, day: date) -> str | None:
    """The problem with an sRPE value (`<rating> <duration> ["note"]`), or None."""
    messages, _ = _parse(_block(day, [f"srpe: {text.strip()}"]))
    return messages[0] if messages else None


def check_note(text: str) -> str | None:
    """The problem with a session note, or None."""
    if '"' in text:
        return "A note can't contain `\"`"
    return None


def build_session(
    day: date,
    name: str,
    format: str,
    lines: list[str],
    srpe: str,
    note: str,
) -> TrainingSession | None:
    """The session the answers describe, or None if there's nothing to add.

    Built by parsing a block of the answers, so movement lines become
    `Movement`s through the same code that reads the log. Empty strings mean
    the field was left out.
    """
    if not (lines or srpe.strip() or note.strip()):
        return None
    body = []
    if name.strip():
        body.append(f"name: {name.strip()}")
    if format.strip():
        body.append(f"format: {format.strip()}")
    if srpe.strip():
        body.append(f"srpe: {srpe.strip()}")
    if note.strip():
        body.append(f'note: "{note.strip()}"')
    body.extend(line.strip() for line in lines)
    messages, sessions = _parse(_block(day, body))
    if messages or len(sessions) != 1:
        raise ValueError(messages[0] if messages else "Couldn't build the session")
    return sessions[0]


def verify(text: str, session: TrainingSession) -> str | None:
    """The problem if `text` doesn't parse back to exactly `session`, or None."""
    messages, sessions = _parse(text + "\n")
    if messages:
        return messages[0]
    if sessions != [session]:
        return "The text doesn't parse back to the session"
    return None


def append_session(path: Path, text: str) -> None:
    """Append `text` to `path` after a blank line, leaving the rest untouched."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        last = b""
        if size:
            f.seek(-1, 2)
            last = f.read(1)
    prefix = b""
    if size:
        if last != b"\n":
            prefix += b"\n"
        prefix += b"\n"
    with open(path, "ab") as f:
        f.write(prefix + text.encode("utf-8") + b"\n")

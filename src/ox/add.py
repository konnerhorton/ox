"""The REPL's `add` command: append one session to the log.

The pure pieces (prefill lookups, line checks, building and appending the
text) are separate from `run_add`, which drives the prompts through an
injected `ask` function so tests can script the answers.
"""

import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

from prompt_toolkit.completion import Completer
from tree_sitter import Parser

from ox.completion import (
    MovementLineCompleter,
    SessionNameCompleter,
    _movement_index,
)
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


Ask = Callable[..., str]

MOVEMENT_PROMPT = "- "


def _ask_checked(
    ask: Ask,
    echo: Callable[[str], None],
    label: str,
    check: Callable[[str], str | None],
    default: str = "",
    completer: Completer | None = None,
) -> str:
    """Ask until the answer is empty or passes `check`; a rejected answer
    comes back as the next default so it can be fixed rather than retyped."""
    while True:
        text = ask(label, default=default, completer=completer).strip()
        if not text:
            return ""
        if (problem := check(text)) is None:
            return text
        echo(problem)
        default = text


def run_add(
    log: TrainingLog,
    path: Path,
    ask: Ask,
    today: date,
    echo: Callable[[str], None],
) -> TrainingSession | None:
    """Prompt for a session, preview it and append it to `path` on confirmation.

    `ask(label, default="", completer=None)` is the only input. Returns the
    session written, or None if nothing was (nothing to add, declined, or
    cancelled with Ctrl+C / Ctrl+D). Doesn't reload the log.
    """
    try:
        return _run_add(log, path, ask, today, echo)
    except (KeyboardInterrupt, EOFError):
        echo("Cancelled.")
        return None


def _run_add(log, path, ask, today, echo):
    default = today.isoformat()
    while True:
        text = ask("date: ", default=default)
        try:
            day = parse_date(text, today)
            break
        except ValueError as e:
            echo(str(e))
            default = text

    name = ask("name: ", completer=SessionNameCompleter(log)).strip()
    previous = last_session(log, name) if name else None

    def check(text):
        return check_line(text, day)

    fmt = ""
    lines = []
    if previous is not None:
        fmt = ask("format: ", default=previous.format or "").strip()
    echo("Movements: Tab completes a name with its last sets; an empty line ends.")
    if previous is not None:
        for movement in previous.movements:
            line = _ask_checked(
                ask, echo, MOVEMENT_PROMPT, check, default=prefill_text(movement)
            )
            if line:
                lines.append(line)

    prefills = {n: prefill_text(m) for n, m in last_movements(log).items()}
    completer = MovementLineCompleter(_movement_index(log), prefills)
    while line := _ask_checked(ask, echo, MOVEMENT_PROMPT, check, completer=completer):
        lines.append(line)

    srpe = _ask_checked(ask, echo, "srpe: ", lambda t: check_srpe(t, day))
    note = _ask_checked(ask, echo, "note: ", check_note)

    try:
        session = build_session(day, name, fmt, lines, srpe, note)
    except ValueError as e:
        echo(f"Not written: {e}")
        return None
    if session is None:
        echo("Nothing to add.")
        return None

    text = session.to_ox()
    if (problem := verify(text, session)) is not None:
        echo(f"Not written: {problem}")
        return None

    echo("")
    echo(text)
    echo("")
    while True:
        answer = ask(f"Append to {path}? [Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            append_session(path, text)
            return session
        if answer in ("n", "no"):
            echo("Not written.")
            return None

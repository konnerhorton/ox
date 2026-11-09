"""Context-aware tab completion for the REPL.

The first word completes commands and plugin names; words after a plugin name
complete that plugin's long flags; the value after a movement flag completes
movement names from the log; the word after `query` completes stored queries.
"""

from collections.abc import Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from ox.data import TrainingLog
from ox.sql_utils import _flag_name

# A plugin param with one of these names takes movement names as its value.
MOVEMENT_PARAMS = ("movement", "movements")


def _movement_index(log: TrainingLog) -> list[tuple[str, str]]:
    """Movement names in the log with a note, most recently trained first.

    The note is the ISO date of the latest completed session, `planned` if the
    name appears only in planned sessions, or `defined` if only in `@movement`.
    Trained names come first by date descending; the rest follow by name.
    """
    last_done: dict[str, str] = {}
    planned: set[str] = set()
    for session in log.sessions:
        for movement in session.movements:
            if session.completed:
                iso = session.date.isoformat()
                if iso > last_done.get(movement.name, ""):
                    last_done[movement.name] = iso
            else:
                planned.add(movement.name)
    defined = {d.name for d in log.movement_definitions}

    trained = sorted(last_done.items(), key=lambda kv: kv[0])
    trained.sort(key=lambda kv: kv[1], reverse=True)
    rest = sorted((planned | defined) - last_done.keys())
    return trained + [(n, "planned" if n in planned else "defined") for n in rest]


def movement_names(log: TrainingLog) -> list[str]:
    """Movement names in the log, most recently trained first."""
    return [name for name, _ in _movement_index(log)]


def _flag_note(param: dict) -> str:
    if param.get("required"):
        return "required"
    default = param.get("default")
    return "optional" if default is None else f"default: {default}"


def _param_flags(param: dict) -> set[str]:
    flags = {f"--{_flag_name(param)}"}
    if param.get("short"):
        flags.add(f"-{param['short']}")
    return flags


class ReplCompleter(Completer):
    """prompt_toolkit completer for the `ox>` prompt."""

    def __init__(
        self,
        commands: Iterable[str],
        plugins: dict[str, dict],
        movements: list[tuple[str, str]],
        queries: Iterable[str],
    ):
        self.commands = list(commands)
        self.plugins = plugins
        self.movements = movements
        self.queries = list(queries)

    def get_completions(self, document: Document, complete_event: CompleteEvent):
        text = document.text_before_cursor
        words = text.split()
        if not words or text[-1].isspace():
            words.append("")
        word = words[-1]

        if len(words) == 1:
            yield from _match([(c, "") for c in self.commands], word)
            return

        head = words[0].lower()
        if head == "query":
            if len(words) == 2:
                yield from _match([(q, "") for q in self.queries], word)
            return

        entry = self.plugins.get(head)
        if entry is None:
            return
        params = entry["params"]

        prev = words[-2]
        if any(
            p["name"] in MOVEMENT_PARAMS and prev in _param_flags(p) for p in params
        ):
            seg = word.rsplit(",", 1)[-1]
            if ":" not in seg:
                yield from _match(self.movements, seg)
            return

        if word.startswith("-"):
            used = set(words[1:-1])
            options = [
                (f"--{_flag_name(p)}", _flag_note(p))
                for p in params
                if not (_param_flags(p) & used)
            ]
            yield from _match(options, word)


def _match(options: list[tuple[str, str]], prefix: str):
    low = prefix.lower()
    for text, note in options:
        if text.lower().startswith(low):
            yield Completion(text, start_position=-len(prefix), display_meta=note)

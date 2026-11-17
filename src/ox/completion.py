"""Context-aware tab completion for the REPL.

The first word completes commands and plugin names; words after a plugin name
complete that plugin's long flags; the value after a movement flag completes
movement names from the log; the word after `query` completes stored queries.
"""

from collections.abc import Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from ox.data import MovementIndexEntry, TrainingLog
from ox.sql_utils import flag_name

# A plugin param with one of these names takes movement names as its value.
MOVEMENT_PARAMS = ("movement", "movements")


def _movement_note(entry: MovementIndexEntry) -> str:
    """Completion note for a movement: its last trained date, or its status."""
    if entry.status == "trained":
        return entry.last.isoformat()
    return entry.status


def _flag_note(param: dict) -> str:
    if param.get("required"):
        return "required"
    default = param.get("default")
    return "optional" if default is None else f"default: {default}"


def _param_flags(param: dict) -> set[str]:
    flags = {f"--{flag_name(param)}"}
    if param.get("short"):
        flags.add(f"-{param['short']}")
    return flags


class ReplCompleter(Completer):
    """prompt_toolkit completer for the `ox>` prompt."""

    def __init__(
        self,
        commands: Iterable[str],
        plugins: dict[str, dict],
        movements: list[MovementIndexEntry],
        queries: Iterable[str],
    ):
        self.commands = list(commands)
        self.plugins = plugins
        self.movements = [(e.name, _movement_note(e)) for e in movements]
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
                (f"--{flag_name(p)}", _flag_note(p))
                for p in params
                if not (_param_flags(p) & used)
            ]
            yield from _match(options, word)


class MovementLineCompleter(Completer):
    """Completer for a movement line at the `add` prompt.

    Before any `:`, offers movement names (in `TrainingLog.movement_index`
    order, noted by `_movement_note`). Accepting one replaces the whole line with that movement's
    prefill text, or `name: ` if it has none.
    """

    def __init__(self, movements: list[MovementIndexEntry], prefills: dict[str, str]):
        self.movements = [(e.name, _movement_note(e)) for e in movements]
        self.prefills = prefills

    def get_completions(self, document: Document, complete_event: CompleteEvent):
        text = document.text_before_cursor
        if ":" in text:
            return
        low = text.strip().lower()
        for name, note in self.movements:
            if name.lower().startswith(low):
                yield Completion(
                    self.prefills.get(name, f"{name}: "),
                    start_position=-len(text),
                    display=name,
                    display_meta=note,
                )


def _session_name_index(log: TrainingLog) -> list[tuple[str, str]]:
    """Session names: completed ones latest first (noted with the date), then
    names used only in planned sessions, alphabetically (noted `planned`)."""
    last_done: dict[str, str] = {}
    planned: set[str] = set()
    for session in log.sessions:
        if session.name is None:
            continue
        if session.completed:
            iso = session.date.isoformat()
            if iso > last_done.get(session.name, ""):
                last_done[session.name] = iso
        else:
            planned.add(session.name)
    done = sorted(last_done.items(), key=lambda kv: kv[0])
    done.sort(key=lambda kv: kv[1], reverse=True)
    return done + [(n, "planned") for n in sorted(planned - last_done.keys())]


class SessionNameCompleter(Completer):
    """Completer for the `name` prompt of `add`: the whole line is the name."""

    def __init__(self, log: TrainingLog):
        self.names = _session_name_index(log)

    def get_completions(self, document: Document, complete_event: CompleteEvent):
        yield from _match(self.names, document.text_before_cursor)


def _match(options: list[tuple[str, str]], prefix: str):
    low = prefix.lower()
    for text, note in options:
        if text.lower().startswith(low):
            yield Completion(text, start_position=-len(prefix), display_meta=note)

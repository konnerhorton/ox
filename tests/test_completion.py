"""Tests for REPL tab completion (ox.completion)."""

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from ox.cli import REPL_COMMANDS, build_completer, parse_file
from ox.add import last_movements, prefill_text
from ox.completion import (
    MovementLineCompleter,
    ReplCompleter,
    SessionNameCompleter,
    _movement_index,
    movement_names,
)
from ox.plugins import PLUGINS, load_plugins

FIXTURE = """\
2025-01-01 T squat: 225lb 5x5
2025-01-03 T bench-press: 135lb 5x5
2025-01-08 T squat: 235lb 5x5

@session
date: 2025-02-01
completed: false
deadlift: 315lb 1x5
squat: 245lb 5x5
@end

@movement front-squat
equipment: barbell
@end

2025-01-08 query "recent" "SELECT * FROM training LIMIT 10"
"""

COMMANDS = REPL_COMMANDS


@pytest.fixture
def log_path(tmp_path):
    path = tmp_path / "log.ox"
    path.write_text(FIXTURE)
    return path


@pytest.fixture
def log(log_path):
    return parse_file(log_path)


@pytest.fixture
def completer(log):
    load_plugins()
    return ReplCompleter(
        COMMANDS + list(PLUGINS),
        dict(PLUGINS),
        _movement_index(log),
        [q.name for q in log.queries],
    )


def complete(c, text):
    return [
        (comp.text, comp.display_meta_text)
        for comp in c.get_completions(Document(text), CompleteEvent())
    ]


def texts(c, text):
    return [t for t, _ in complete(c, text)]


# AC 1
def test_movement_names_order(log):
    assert movement_names(log) == ["squat", "bench-press", "deadlift", "front-squat"]


# AC 2
def test_first_word(completer):
    assert texts(completer, "vo") == ["volume"]
    assert set(texts(completer, "")) == set(COMMANDS) | set(PLUGINS)


# AC 3
def test_flags(completer):
    assert texts(completer, "volume --") == ["--movement", "--bin", "--unit"]
    assert texts(completer, "volume -m squat --") == ["--bin", "--unit"]
    notes = dict(complete(completer, "volume --"))
    assert notes["--bin"] == "default: weekly"
    assert notes["--movement"] == "required"


def test_flags_skip_long_form_used(completer):
    assert texts(completer, "volume --bin daily -") == ["--movement", "--unit"]


def test_flag_note_optional(completer):
    notes = dict(complete(completer, "wendler531 --"))
    assert notes["--start-date"] == "optional"


# AC 4
def test_movement_value(completer):
    assert complete(completer, "volume -m ") == [
        ("squat", "2025-01-08"),
        ("bench-press", "2025-01-03"),
        ("deadlift", "planned"),
        ("front-squat", "defined"),
    ]
    assert texts(completer, "e1rm --movement s") == ["squat"]


# AC 5
def test_movement_list(completer):
    assert texts(completer, "wendler531 -m squat:315,de") == ["deadlift"]
    assert texts(completer, "wendler531 -m squat:3") == []


def test_movement_list_start_position(completer):
    [comp] = completer.get_completions(
        Document("wendler531 -m squat:315,de"), CompleteEvent()
    )
    assert comp.start_position == -2


# AC 6
def test_queries(completer):
    assert texts(completer, "query r") == ["recent"]
    assert texts(completer, "query SELECT * FROM r") == []


# AC 7
@pytest.mark.parametrize("text", ["volume -m squat --bin w", "tables ", "bogus -m "])
def test_nothing_elsewhere(completer, text):
    assert texts(completer, text) == []


# AC 8
def test_user_plugin(log):
    plugins = {
        "mine": {
            "fn": lambda ctx, movement: None,
            "description": "user plugin",
            "params": [
                {"name": "movement", "type": str, "required": True, "short": "x"}
            ],
        }
    }
    c = ReplCompleter(["mine"], plugins, _movement_index(log), [])
    assert texts(c, "mine -x b") == ["bench-press"]
    assert texts(c, "mine --movement f") == ["front-squat"]


# AC 9
def test_case_insensitive(completer):
    assert texts(completer, "volume -m SQ") == ["squat"]


# AC 10
def test_reload_picks_up_new_movement(log_path):
    load_plugins()
    assert texts(build_completer(parse_file(log_path)), "volume -m kb") == []
    with log_path.open("a") as f:
        f.write("2025-01-09 T kb-swing: 24kg 5x10\n")
    assert texts(build_completer(parse_file(log_path)), "volume -m kb") == ["kb-swing"]


# AC 11
def test_build_completer_offers_repl_commands(log):
    load_plugins()
    offered = set(texts(build_completer(log), ""))
    assert set(REPL_COMMANDS) <= offered
    assert set(PLUGINS) <= offered


# repl-add: movement-line and session-name completion (repl-add spec D4, D6)
ADD_ROOT = """\
@session
date: 2025-01-01
name: Upper Day
bench-press: 135lb 5x5 "easy"
pullups: BW 3x8
@end

@include "jan.ox"

@session
date: 2025-01-08
name: Upper Day
bench-press: 140lb 5x5
pullups: BW 3x10
@end

@session
date: 2025-02-01
name: Lower Day
completed: false
squat: 200lb 5x5
deadlift: 225lb 1x5
@end
"""


@pytest.fixture
def add_log(tmp_path):
    (tmp_path / "jan.ox").write_text("2025-01-03 T squat: 185lb 5x5\n")
    path = tmp_path / "add.ox"
    path.write_text(ADD_ROOT)
    return parse_file(path)


@pytest.fixture
def line_completer(add_log):
    prefills = {n: prefill_text(m) for n, m in last_movements(add_log).items()}
    return MovementLineCompleter(_movement_index(add_log), prefills)


def completions(c, text):
    return list(c.get_completions(Document(text), CompleteEvent()))


# repl-add AC 2
def test_movement_line_prefill(line_completer):
    [sq] = completions(line_completer, "sq")
    assert sq.text == "squat: 185lb 5x5"
    assert sq.start_position == -2
    assert sq.display_text == "squat"
    assert sq.display_meta_text == "2025-01-03"
    assert texts(line_completer, "bench") == ["bench-press: 140lb 5x5"]
    assert texts(line_completer, "dead") == ["deadlift: "]


def test_movement_line_after_colon(line_completer):
    assert texts(line_completer, "squat:") == []
    assert texts(line_completer, "squat: 185") == []


def test_movement_line_empty_offers_all(line_completer):
    assert [c.display_text for c in completions(line_completer, "")] == [
        "bench-press",
        "pullups",
        "squat",
        "deadlift",
    ]


# repl-add AC 3
def test_session_name_completion(add_log):
    c = SessionNameCompleter(add_log)
    assert complete(c, "U") == [("Upper Day", "2025-01-08")]
    assert complete(c, "") == [("Upper Day", "2025-01-08"), ("Lower Day", "planned")]
    assert complete(c, "upper d") == [("Upper Day", "2025-01-08")]

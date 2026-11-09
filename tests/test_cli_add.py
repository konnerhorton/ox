"""End-to-end tests for `add` in the REPL, driven through prompt_toolkit pipe input."""

import re
import threading
import time
from datetime import date

import pytest
from click.testing import CliRunner
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from ox.cli import cli

ROOT = """\
@session
date: 2025-01-08
name: Upper Day
bench-press: 140lb 5x5
@end

@include "jan.ox"
"""

JAN = "2025-01-03 T squat: 185lb 5x5\n"

PAUSE = 0.05

TAB, ENTER, CTRL_C, CTRL_D, CLEAR = "\t", "\r", "\x03", "\x04", "\x15"


@pytest.fixture
def log_path(tmp_path):
    (tmp_path / "jan.ox").write_text(JAN)
    path = tmp_path / "log.ox"
    path.write_text(ROOT)
    return path


def drive(path, keys: list[str]) -> str:
    """Run the REPL on `path`, sending each item of `keys` as typed input.

    Items go in with a short pause between them, and a Tab is sent on its
    own: completion runs as a background task, so a Tab or Enter arriving
    before it settles acts on the uncompleted text.
    """
    chunks = [part for key in keys for part in re.split(r"(\t)", key) if part]

    def feed(pipe):
        for chunk in chunks:
            time.sleep(PAUSE)
            pipe.send_text(chunk)

    with create_pipe_input() as pipe:
        feeder = threading.Thread(target=feed, args=(pipe,), daemon=True)
        feeder.start()
        with create_app_session(input=pipe, output=DummyOutput()):
            result = CliRunner().invoke(cli, [str(path)])
        feeder.join()
    assert result.exception is None, result.output
    return result.output


def line(text=""):
    return text + ENTER


# repl-add AC 2 end to end: Tab on `sq` writes the prefill line
def test_add_tab_prefill(log_path):
    out = drive(
        log_path,
        [
            "add" + ENTER,
            line(),  # date: keep today
            line(),  # name
            "sq" + TAB + ENTER,  # movement line
            line(),  # end movements
            line(),  # srpe
            line(),  # note
            line("y"),
            "exit" + ENTER,
        ],
    )
    today = date.today().isoformat()
    assert log_path.read_text() == ROOT + f"\n{today} T squat: 185lb 5x5\n"
    assert f"Added {today} session to" in out
    assert (log_path.parent / "jan.ox").read_text() == JAN


# repl-add AC 11: cancel inside add, then the REPL keeps going
@pytest.mark.parametrize("key", [CTRL_C, CTRL_D])
@pytest.mark.parametrize("prompts_before", [0, 2, 4, 6])
def test_add_cancel(log_path, key, prompts_before):
    answers = [line(), line(), line("squat: 1lb 1x1"), line(), line("5 PT1H"), line()]
    before = log_path.read_bytes()
    out = drive(
        log_path,
        [
            "add" + ENTER,
            *answers[:prompts_before],
            key,
            "tables" + ENTER,
            "exit" + ENTER,
        ],
    )
    assert "Cancelled." in out
    assert "training" in out  # `tables` ran after the cancel
    assert "Goodbye!" in out
    assert log_path.read_bytes() == before


# repl-add AC 12: after add, queries and completion see the new session
def test_add_reloads(log_path):
    out = drive(
        log_path,
        [
            "add" + ENTER,
            CLEAR + line("2025-03-01"),
            line(),
            line("curl: 30lb 3x10"),
            line(),
            line(),
            line(),
            line(),
            "query SELECT date, movement_name FROM training WHERE date = '2025-03-01'"
            + ENTER,
            "volume -m cu" + TAB,
            ENTER,
            "exit" + ENTER,
        ],
    )
    assert "Added 2025-03-01 session" in out
    query_out, volume_out = out.split("Added 2025-03-01 session")[1].split("row(s)")[:2]
    assert query_out.count("curl") == 3  # one row per set
    # `cu<Tab>` completed to `curl` (a first-time movement): the plugin found
    # its 900 lb of volume, where an uncompleted `cu` would give "No results."
    assert "900" in volume_out
    assert "No results" not in volume_out


# repl-add AC 14
def test_add_usage(log_path):
    before = log_path.read_bytes()
    out = drive(log_path, ["add foo" + ENTER, "exit" + ENTER])
    assert "Usage: add" in out
    assert "date:" not in out
    assert log_path.read_bytes() == before

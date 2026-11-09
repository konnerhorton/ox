"""Tests for the REPL's `add` command (ox.add)."""

from datetime import date

import pytest

from ox.add import (
    append_session,
    build_session,
    check_line,
    check_note,
    check_srpe,
    last_movements,
    last_session,
    parse_date,
    prefill_text,
    verify,
)
from ox.cli import parse_file

ROOT = """\
@session
date: 2025-01-01
name: Upper Day
format: 5/3/1 wave
bench-press: 135lb 5x5 "easy"
pullups: BW 3x8
@end

@include "jan.ox"

@session
date: 2025-01-08
name: Upper Day
format: 5/3/1 wave
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

JAN = "2025-01-03 T squat: 185lb 5x5\n"

NOTED_BENCH = """\
2025-01-01 T bench-press: 130lb 5x5
2025-01-05 T bench-press: 135lb 5x5 "easy"
"""

DAY = date(2025, 3, 1)


@pytest.fixture
def log_path(tmp_path):
    (tmp_path / "jan.ox").write_text(JAN)
    path = tmp_path / "log.ox"
    path.write_text(ROOT)
    return path


@pytest.fixture
def log(log_path):
    return parse_file(log_path)


# AC 1: the named session's last instance
def test_last_session(log):
    session = last_session(log, "Upper Day")
    assert session.date == date(2025, 1, 8)
    assert session.format == "5/3/1 wave"
    assert [prefill_text(m) for m in session.movements] == [
        "bench-press: 140lb 5x5",
        "pullups: BW 3x10",
    ]


def test_last_session_planned_or_unknown(log):
    assert last_session(log, "Lower Day") is None
    assert last_session(log, "upper day") is None
    assert last_session(log, "Nope") is None


def test_last_session_tie_takes_later_in_log(tmp_path):
    path = tmp_path / "log.ox"
    path.write_text(
        "@session\ndate: 2025-01-01\nname: A\nsquat: 100lb 1x1\n@end\n"
        "@session\ndate: 2025-01-01\nname: A\nsquat: 110lb 1x1\n@end\n"
    )
    session = last_session(parse_file(path), "A")
    assert prefill_text(session.movements[0]) == "squat: 110lb 1x1"


# AC 2: a movement's last instance, note dropped
def test_last_movements(log):
    prefills = {n: prefill_text(m) for n, m in last_movements(log).items()}
    assert prefills == {
        "bench-press": "bench-press: 140lb 5x5",
        "pullups": "pullups: BW 3x10",
        "squat": "squat: 185lb 5x5",
    }


def test_prefill_drops_note(tmp_path):
    path = tmp_path / "log.ox"
    path.write_text(NOTED_BENCH)
    movement = last_movements(parse_file(path))["bench-press"]
    assert movement.note == "easy"
    assert prefill_text(movement) == "bench-press: 135lb 5x5"


# AC 6: nothing to add
def test_build_session_nothing():
    assert build_session(DAY, "", "", [], "", "") is None
    assert build_session(DAY, "Upper Day", "5/3/1", [], "  ", "") is None


# AC 7: line validation
def test_check_line():
    assert check_line("squat: 185lb 5x5", DAY) is None
    assert check_line("squat: 185lbs 5x5", DAY) == "Unknown unit `lbs`: use `lb`"
    assert check_line("squat 185", DAY) is not None


def test_check_line_rejects_session_fields():
    for line in ["name: Upper", "format: x", "srpe: 5 PT1H", 'note: "x"']:
        assert check_line(line, DAY) is not None


def test_check_srpe():
    assert check_srpe('7 PT1H "felt strong"', DAY) is None
    assert check_srpe("5.5 PT1H", DAY) == "sRPE rating must be a whole number"
    assert check_srpe("11 PT1H", DAY) == "sRPE rating must be between 1 and 10"


def test_check_note():
    assert check_note("deload") is None
    assert check_note('say "hi"') is not None


def test_parse_date():
    assert parse_date("2025-03-01", DAY) == date(2025, 3, 1)
    with pytest.raises(ValueError, match="2025-02-30"):
        parse_date("2025-02-30", DAY)
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_date("20250301", DAY)


# AC 8
def test_parse_date_default():
    assert parse_date("", DAY) == DAY
    assert parse_date("  ", DAY) == DAY


# AC 9: append only
@pytest.mark.parametrize(
    "original, expected_prefix",
    [
        (b"2025-01-01 T squat: 1lb 1x1", b"2025-01-01 T squat: 1lb 1x1\n\n"),
        (b"2025-01-01 T squat: 1lb 1x1\n", b"2025-01-01 T squat: 1lb 1x1\n\n"),
        (b"", b""),
    ],
)
def test_append_session(tmp_path, original, expected_prefix):
    path = tmp_path / "log.ox"
    path.write_bytes(original)
    append_session(path, "2025-03-01 T squat: 190lb 5x5")
    assert path.read_bytes() == expected_prefix + b"2025-03-01 T squat: 190lb 5x5\n"


def test_append_leaves_included_file(log_path):
    jan = log_path.parent / "jan.ox"
    before = jan.read_bytes()
    append_session(log_path, "2025-03-01 T squat: 190lb 5x5")
    assert jan.read_bytes() == before
    assert log_path.read_bytes() == ROOT.encode() + b"\n2025-03-01 T squat: 190lb 5x5\n"


# AC 4-6 texts and AC 13: round trip
AC5_TEXT = """\
@session
date: 2025-03-02
name: Upper Day
format: 5/3/1 wave
srpe: 7 PT1H "felt strong"
note: "deload"
bench-press: 140lb 5x5
dips: BW 3x10
@end"""


@pytest.mark.parametrize(
    "args, text",
    [
        (
            (date(2025, 3, 1), "", "", ["squat: 190lb 5x5"], "", ""),
            "2025-03-01 T squat: 190lb 5x5",
        ),
        (
            (
                date(2025, 3, 2),
                "Upper Day",
                "5/3/1 wave",
                ["bench-press: 140lb 5x5", "dips: BW 3x10"],
                '7 PT1H "felt strong"',
                "deload",
            ),
            AC5_TEXT,
        ),
        (
            (date(2025, 3, 3), "", "", [], "6 PT1H30M", ""),
            "@session\ndate: 2025-03-03\nsrpe: 6 PT1H30M\n@end",
        ),
    ],
)
def test_build_and_verify(args, text):
    session = build_session(*args)
    assert session.to_ox() == text
    assert verify(session.to_ox(), session) is None


def test_verify_catches_mismatch():
    session = build_session(DAY, "", "", ["squat: 190lb 5x5"], "", "")
    assert verify("2025-03-01 T squat: 195lb 5x5", session) is not None
    assert verify("2025-03-01 T squat: 190lbs 5x5", session) is not None

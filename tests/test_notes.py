"""Tests for Note as a first-class directive."""

from datetime import date

import pytest

from ox.cli import parse_file
from ox.data import Note, TrainingSession, TrainingSet, Movement
from ox.db import create_db


# ---------------------------------------------------------------------------
# Note dataclass
# ---------------------------------------------------------------------------


def test_note_to_ox_standalone():
    note = Note(text="rest day", date=date(2025, 1, 10))
    assert note.to_ox() == '2025-01-10 note "rest day"'


def test_note_to_ox_no_date():
    note = Note(text="in-session note")
    # date is None — calling to_ox() would raise; just confirm the attribute
    assert note.date is None
    assert note.text == "in-session note"


# ---------------------------------------------------------------------------
# TrainingSession.to_ox() with notes
# ---------------------------------------------------------------------------


def test_training_session_to_ox_with_notes():
    session = TrainingSession(
        date=date(2025, 1, 11),
        flag="*",
        name="Upper Day",
        movements=(
            Movement(
                name="bench-press", sets=[TrainingSet(reps=5, weight=None)], note=None
            ),
        ),
        notes=(Note(text="Cycle 1 Week 1"),),
    )
    result = session.to_ox()
    lines = result.splitlines()
    assert lines[0] == "@session"
    assert lines[1] == "2025-01-11 * Upper Day"
    assert lines[2] == 'note: "Cycle 1 Week 1"'
    assert lines[3].startswith("bench-press:")
    assert lines[4] == "@end"


def test_training_session_to_ox_no_notes():
    session = TrainingSession(
        date=date(2025, 1, 11),
        flag="*",
        name="Upper Day",
        movements=(
            Movement(
                name="bench-press", sets=[TrainingSet(reps=5, weight=None)], note=None
            ),
        ),
    )
    result = session.to_ox()
    assert "note:" not in result


# ---------------------------------------------------------------------------
# parse_file — session notes
# ---------------------------------------------------------------------------


@pytest.fixture
def log_with_session_notes(tmp_path):
    content = """\
@session
2025-01-11 * Upper Day
note: "Cycle 1 Week 1"
bench-press: 135lb 5x5
@end
"""
    f = tmp_path / "test.ox"
    f.write_text(content)
    return parse_file(f)


def test_parse_session_note_extracted(log_with_session_notes):
    session = log_with_session_notes.sessions[0]
    assert len(session.notes) == 1
    assert session.notes[0].text == "Cycle 1 Week 1"
    assert session.notes[0].date is None


def test_parse_session_note_not_in_movements(log_with_session_notes):
    session = log_with_session_notes.sessions[0]
    assert len(session.movements) == 1
    assert session.movements[0].name == "bench-press"


# ---------------------------------------------------------------------------
# parse_file — standalone note_entry
# ---------------------------------------------------------------------------


@pytest.fixture
def log_with_standalone_note(tmp_path):
    content = """\
2025-01-10 note "rest day"
2025-01-11 * pullups: BW 5x10
"""
    f = tmp_path / "test.ox"
    f.write_text(content)
    return parse_file(f)


def test_parse_standalone_note_in_log_notes(log_with_standalone_note):
    assert len(log_with_standalone_note.notes) == 1
    note = log_with_standalone_note.notes[0]
    assert note.text == "rest day"
    assert note.date == date(2025, 1, 10)


def test_parse_standalone_note_not_session(log_with_standalone_note):
    # Only the singleline_entry should become a session
    assert len(log_with_standalone_note.sessions) == 1


# ---------------------------------------------------------------------------
# parse_file — no notes → empty collections
# ---------------------------------------------------------------------------


@pytest.fixture
def log_without_notes(tmp_path):
    content = """\
2025-01-11 * pullups: BW 5x10
"""
    f = tmp_path / "test.ox"
    f.write_text(content)
    return parse_file(f)


def test_no_notes_log_notes_empty(log_without_notes):
    assert log_without_notes.notes == ()


def test_no_notes_session_notes_empty(log_without_notes):
    assert log_without_notes.sessions[0].notes == ()


# ---------------------------------------------------------------------------
# DB: session_notes and notes tables
# ---------------------------------------------------------------------------


@pytest.fixture
def db_with_notes(tmp_path):
    content = """\
2025-01-10 note "rest day"

@session
2025-01-11 * Upper Day
note: "Cycle 1 Week 1"
bench-press: 135lb 5x5
@end
"""
    f = tmp_path / "test.ox"
    f.write_text(content)
    log = parse_file(f)
    conn = create_db(log)
    yield conn
    conn.close()


def test_db_notes_table_populated(db_with_notes):
    rows = db_with_notes.execute("SELECT date, text FROM notes").fetchall()
    assert len(rows) == 1
    assert rows[0] == ("2025-01-10", "rest day")


def test_db_session_notes_table_populated(db_with_notes):
    rows = db_with_notes.execute("SELECT text FROM session_notes").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Cycle 1 Week 1"


def test_db_session_notes_fk(db_with_notes):
    rows = db_with_notes.execute(
        "SELECT sn.text FROM session_notes sn JOIN sessions s ON sn.session_id = s.id"
    ).fetchall()
    assert rows[0][0] == "Cycle 1 Week 1"

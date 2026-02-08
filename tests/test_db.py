"""Tests for the in-memory SQLite database layer."""

import sqlite3

import pytest

from ox.data import TrainingLog
from ox.db import create_db, _decompose_weight
from ox.units import ureg


class TestSchema:
    """Verify the database schema is created correctly."""

    def test_sessions_table_exists(self, simple_db):
        rows = simple_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchall()
        assert len(rows) == 1

    def test_movements_table_exists(self, simple_db):
        rows = simple_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='movements'"
        ).fetchall()
        assert len(rows) == 1

    def test_sets_table_exists(self, simple_db):
        rows = simple_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sets'"
        ).fetchall()
        assert len(rows) == 1

    def test_training_view_exists(self, simple_db):
        rows = simple_db.execute(
            "SELECT name FROM sqlite_master WHERE type='view' AND name='training'"
        ).fetchall()
        assert len(rows) == 1

    def test_foreign_keys_enforced(self, simple_db):
        with pytest.raises(sqlite3.IntegrityError):
            simple_db.execute(
                "INSERT INTO movements (session_id, name) VALUES (9999, 'fake')"
            )


class TestDecomposeWeight:
    """Verify _decompose_weight splits Quantity objects correctly."""

    def test_kg(self):
        mag, unit = _decompose_weight(24.0 * ureg.kilogram)
        assert mag == 24.0
        assert unit == "kilogram"

    def test_lbs(self):
        mag, unit = _decompose_weight(135.0 * ureg.pounds)
        assert mag == 135.0
        assert unit == "pound"

    def test_bodyweight_none(self):
        mag, unit = _decompose_weight(None)
        assert mag is None
        assert unit is None


class TestDataLoading:
    """Verify data is loaded correctly from TrainingLog.

    The simple_log_content fixture has:
    - 1 single-line entry: 2025-01-10 * pullups: BW 5x10 (5 sets, no weight)
    - 1 completed session: 2025-01-11 * Upper Day
        - bench-press: 135lbs 5x5 (5 sets)
        - kb-oh-press: 24kg 5/5/5 (3 sets)
    - 1 planned session: 2025-01-12 ! Lower Day
        - squat: 185lbs 3x5 (3 sets)
    """

    def test_session_count(self, simple_db):
        count = simple_db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        assert count == 3

    def test_movement_count(self, simple_db):
        count = simple_db.execute("SELECT COUNT(*) FROM movements").fetchone()[0]
        assert count == 4

    def test_set_count(self, simple_db):
        count = simple_db.execute("SELECT COUNT(*) FROM sets").fetchone()[0]
        assert count == 16

    def test_session_dates(self, simple_db):
        dates = [
            r[0] for r in simple_db.execute("SELECT date FROM sessions ORDER BY date").fetchall()
        ]
        assert dates == ["2025-01-10", "2025-01-11", "2025-01-12"]

    def test_session_flags(self, simple_db):
        flags = [
            r[0]
            for r in simple_db.execute("SELECT flag FROM sessions ORDER BY date").fetchall()
        ]
        assert flags == ["*", "*", "!"]

    def test_movement_names(self, simple_db):
        names = sorted(
            r[0] for r in simple_db.execute("SELECT name FROM movements").fetchall()
        )
        assert names == ["bench-press", "kb-oh-press", "pullups", "squat"]

    def test_session_name_nullable(self, simple_db):
        """Single-line entries have no session name."""
        row = simple_db.execute(
            "SELECT name FROM sessions WHERE date = '2025-01-10'"
        ).fetchone()
        assert row[0] is None

    def test_session_name_present(self, simple_db):
        row = simple_db.execute(
            "SELECT name FROM sessions WHERE date = '2025-01-11'"
        ).fetchone()
        assert row[0] == "Upper Day"


class TestWeightInDatabase:
    """Verify weight magnitude and unit are stored correctly."""

    def test_weighted_set_has_magnitude(self, simple_db):
        row = simple_db.execute(
            """SELECT weight_magnitude, weight_unit FROM training
               WHERE movement_name = 'bench-press' LIMIT 1"""
        ).fetchone()
        assert row[0] == 135.0
        assert row[1] == "pound"

    def test_kg_weight(self, simple_db):
        row = simple_db.execute(
            """SELECT weight_magnitude, weight_unit FROM training
               WHERE movement_name = 'kb-oh-press' LIMIT 1"""
        ).fetchone()
        assert row[0] == 24.0
        assert row[1] == "kilogram"

    def test_bodyweight_is_null(self, simple_db):
        row = simple_db.execute(
            """SELECT weight_magnitude, weight_unit FROM training
               WHERE movement_name = 'pullups' LIMIT 1"""
        ).fetchone()
        assert row[0] is None
        assert row[1] is None


class TestTrainingView:
    """Test the convenience 'training' view."""

    def test_view_returns_all_sets(self, simple_db):
        count = simple_db.execute("SELECT COUNT(*) FROM training").fetchone()[0]
        assert count == 16

    def test_view_has_expected_columns(self, simple_db):
        cursor = simple_db.execute("SELECT * FROM training LIMIT 1")
        columns = [desc[0] for desc in cursor.description]
        assert columns == [
            "session_id",
            "date",
            "flag",
            "session_name",
            "movement_id",
            "movement_name",
            "movement_note",
            "set_id",
            "reps",
            "weight_magnitude",
            "weight_unit",
        ]

    def test_filter_by_movement_name(self, simple_db):
        rows = simple_db.execute(
            "SELECT * FROM training WHERE movement_name = 'bench-press'"
        ).fetchall()
        assert len(rows) == 5

    def test_filter_by_date(self, simple_db):
        rows = simple_db.execute(
            "SELECT * FROM training WHERE date = '2025-01-11'"
        ).fetchall()
        # Upper Day: bench-press 5 sets + kb-oh-press 3 sets = 8
        assert len(rows) == 8


class TestEdgeCases:
    """Test edge cases in data loading."""

    def test_empty_log(self):
        log = TrainingLog(sessions=())
        conn = create_db(log)
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        assert count == 0
        conn.close()

    def test_movement_with_note(self, example_db):
        """Notes from the .ox file are stored in the movements table."""
        rows = example_db.execute(
            "SELECT note FROM movements WHERE note IS NOT NULL LIMIT 1"
        ).fetchall()
        assert len(rows) >= 1
        assert isinstance(rows[0][0], str)


class TestUserQueries:
    """Test realistic SQL queries a user would write."""

    def test_count_sessions_per_exercise(self, simple_db):
        rows = simple_db.execute(
            """SELECT movement_name, COUNT(DISTINCT session_id) as sessions
               FROM training
               GROUP BY movement_name
               ORDER BY sessions DESC"""
        ).fetchall()
        # Each movement appears in exactly one session
        assert all(r[1] == 1 for r in rows)
        assert len(rows) == 4

    def test_max_weight_per_exercise(self, simple_db):
        rows = simple_db.execute(
            """SELECT movement_name, MAX(weight_magnitude) as max_weight, weight_unit
               FROM training
               WHERE weight_magnitude IS NOT NULL
               GROUP BY movement_name"""
        ).fetchall()
        results = {r[0]: (r[1], r[2]) for r in rows}
        assert results["bench-press"] == (135.0, "pound")
        assert results["kb-oh-press"] == (24.0, "kilogram")
        assert results["squat"] == (185.0, "pound")

    def test_total_reps_per_exercise(self, simple_db):
        rows = simple_db.execute(
            """SELECT movement_name, SUM(reps) as total_reps
               FROM training
               GROUP BY movement_name
               ORDER BY total_reps DESC"""
        ).fetchall()
        results = {r[0]: r[1] for r in rows}
        assert results["pullups"] == 50  # 5x10
        assert results["bench-press"] == 25  # 5x5
        assert results["kb-oh-press"] == 15  # 5/5/5
        assert results["squat"] == 15  # 3x5

    def test_volume_query(self, simple_db):
        """Total volume = SUM(reps * weight_magnitude) per exercise."""
        rows = simple_db.execute(
            """SELECT movement_name, SUM(reps * weight_magnitude) as volume
               FROM training
               WHERE weight_magnitude IS NOT NULL
               GROUP BY movement_name"""
        ).fetchall()
        results = {r[0]: r[1] for r in rows}
        assert results["bench-press"] == 135.0 * 25  # 135 * 5reps * 5sets
        assert results["kb-oh-press"] == 24.0 * 15  # 24 * (5+5+5)

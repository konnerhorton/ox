"""In-memory SQLite database for training log queries."""

import sqlite3
from typing import Optional

from pint import Quantity

from ox.data import TrainingLog

SCHEMA = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    flag TEXT NOT NULL,
    name TEXT
);

CREATE TABLE movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    note TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_id INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    weight_magnitude REAL,
    weight_unit TEXT,
    FOREIGN KEY (movement_id) REFERENCES movements(id)
);

CREATE VIEW training AS
SELECT
    s.id AS session_id,
    s.date,
    s.flag,
    s.name AS session_name,
    m.id AS movement_id,
    m.name AS movement_name,
    m.note AS movement_note,
    t.id AS set_id,
    t.reps,
    t.weight_magnitude,
    t.weight_unit
FROM sessions s
JOIN movements m ON m.session_id = s.id
JOIN sets t ON t.movement_id = m.id;
"""


def _decompose_weight(weight: Optional[Quantity]) -> tuple[Optional[float], Optional[str]]:
    """Split a pint Quantity into (magnitude, unit_string) for SQLite storage.

    Returns (None, None) for bodyweight (weight is None).
    """
    if weight is None:
        return None, None
    return float(weight.magnitude), str(weight.units)


def create_db(log: TrainingLog) -> sqlite3.Connection:
    """Load a TrainingLog into an in-memory SQLite database.

    Args:
        log: Parsed training log

    Returns:
        sqlite3.Connection to the in-memory database
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    for session in log.sessions:
        cursor = conn.execute(
            "INSERT INTO sessions (date, flag, name) VALUES (?, ?, ?)",
            (session.date.isoformat(), session.flag, session.name),
        )
        session_id = cursor.lastrowid

        for movement in session.movements:
            cursor = conn.execute(
                "INSERT INTO movements (session_id, name, note) VALUES (?, ?, ?)",
                (session_id, movement.name, movement.note),
            )
            movement_id = cursor.lastrowid

            for training_set in movement.sets:
                mag, unit = _decompose_weight(training_set.weight)
                conn.execute(
                    "INSERT INTO sets (movement_id, reps, weight_magnitude, weight_unit) VALUES (?, ?, ?, ?)",
                    (movement_id, training_set.reps, mag, unit),
                )

    conn.commit()
    return conn

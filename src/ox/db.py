"""In-memory SQLite database for training log queries."""

import re
import sqlite3
from typing import Optional

from pint import Quantity

from ox.data import TrainingLog

SCHEMA = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 1,
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
    duration_seconds REAL,
    distance_magnitude REAL,
    distance_unit TEXT,
    FOREIGN KEY (movement_id) REFERENCES movements(id)
);

CREATE TABLE session_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    text       TEXT NOT NULL
);

CREATE TABLE notes (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE queries (
    id   INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    sql  TEXT NOT NULL
);

CREATE TABLE movement_definitions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL UNIQUE,
    equipment TEXT,
    note      TEXT,
    url       TEXT
);

CREATE TABLE movement_tags (
    movement_definition_id INTEGER NOT NULL REFERENCES movement_definitions(id),
    tag                    TEXT NOT NULL,
    PRIMARY KEY (movement_definition_id, tag)
);

CREATE TABLE weigh_ins (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT NOT NULL,
    weight_magnitude REAL NOT NULL,
    weight_unit      TEXT NOT NULL,
    time_of_day      TEXT,
    scale            TEXT
);

CREATE VIEW training AS
SELECT
    s.id AS session_id,
    s.date,
    s.completed,
    s.name AS session_name,
    m.id AS movement_id,
    m.name AS movement_name,
    m.note AS movement_note,
    t.id AS set_id,
    t.reps,
    t.weight_magnitude,
    t.weight_unit,
    t.duration_seconds,
    t.distance_magnitude,
    t.distance_unit
FROM sessions s
JOIN movements m ON m.session_id = s.id
JOIN sets t ON t.movement_id = m.id;
"""


def _decompose_quantity(
    quantity: Optional[Quantity],
) -> tuple[Optional[float], Optional[str]]:
    """Split a pint Quantity into (magnitude, unit_string) for SQLite storage.

    Used for both weights and distances. Returns (None, None) when absent —
    for weight that means bodyweight.
    """
    if quantity is None:
        return None, None
    return float(quantity.magnitude), str(quantity.units)


def create_db(log: TrainingLog) -> sqlite3.Connection:
    """Load a TrainingLog into an in-memory SQLite database.

    Args:
        log: Parsed training log

    Returns:
        sqlite3.Connection to the in-memory database
    """
    conn = sqlite3.connect(":memory:")
    conn.create_function("regexp", 2, lambda pat, val: bool(re.search(pat, val or "")))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    for session in log.sessions:
        cursor = conn.execute(
            "INSERT INTO sessions (date, completed, name) VALUES (?, ?, ?)",
            (session.date.isoformat(), int(session.completed), session.name),
        )
        session_id = cursor.lastrowid

        for movement in session.movements:
            cursor = conn.execute(
                "INSERT INTO movements (session_id, name, note) VALUES (?, ?, ?)",
                (session_id, movement.name, movement.note),
            )
            movement_id = cursor.lastrowid

            for training_set in movement.sets:
                mag, unit = _decompose_quantity(training_set.weight)
                dist_mag, dist_unit = _decompose_quantity(training_set.distance)
                duration = training_set.duration
                conn.execute(
                    "INSERT INTO sets (movement_id, reps, weight_magnitude, weight_unit,"
                    " duration_seconds, distance_magnitude, distance_unit)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        movement_id,
                        training_set.reps,
                        mag,
                        unit,
                        # `is not None`: a zero timedelta is falsy but real
                        duration.total_seconds() if duration is not None else None,
                        dist_mag,
                        dist_unit,
                    ),
                )

        for note in session.notes:
            conn.execute(
                "INSERT INTO session_notes (session_id, text) VALUES (?, ?)",
                (session_id, note.text),
            )

    for note in log.notes:
        conn.execute(
            "INSERT INTO notes (date, text) VALUES (?, ?)",
            (note.date.isoformat(), note.text),
        )

    for q in log.queries:
        conn.execute(
            "INSERT INTO queries (date, name, sql) VALUES (?, ?, ?)",
            (q.date.isoformat(), q.name, q.sql),
        )

    for mdef in log.movement_definitions:
        cursor = conn.execute(
            "INSERT INTO movement_definitions (name, equipment, note, url) VALUES (?, ?, ?, ?)",
            (mdef.name, mdef.equipment, mdef.note, mdef.url),
        )
        mdef_id = cursor.lastrowid
        for tag in mdef.tags:
            conn.execute(
                "INSERT INTO movement_tags (movement_definition_id, tag) VALUES (?, ?)",
                (mdef_id, tag),
            )

    for w in log.weigh_ins:
        mag, unit = _decompose_quantity(w.weight)
        conn.execute(
            "INSERT INTO weigh_ins (date, weight_magnitude, weight_unit, time_of_day, scale) VALUES (?, ?, ?, ?, ?)",
            (
                w.date.isoformat(),
                mag,
                unit,
                w.time_of_day.strftime("%H:%M") if w.time_of_day else None,
                w.scale,
            ),
        )

    conn.commit()
    return conn

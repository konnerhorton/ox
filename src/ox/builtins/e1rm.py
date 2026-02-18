"""Estimated 1RM report plugin for ox.

Tracks estimated one-rep max over time for a given movement.
Only considers sets tagged with "^rm" in the movement note
(convention for marking max-effort sets).

Usage:
    report e1rm -m deadlift
    report e1rm -m squat -f epley

Example .ox line:
    deadlift: 315lbs 1x3 "^rm top set felt good"
"""


def _brzycki(weight, reps):
    """Brzycki formula: weight * 36 / (37 - reps)."""
    if reps >= 37:
        return weight
    return weight * 36 / (37 - reps)


def _epley(weight, reps):
    """Epley formula: weight * (1 + reps / 30)."""
    return weight * (1 + reps / 30)


FORMULAS = {
    "brzycki": _brzycki,
    "epley": _epley,
}


def estimated_1rm(conn, movement, formula="brzycki"):
    """Estimated 1RM progression for a movement.

    Finds sets where the movement note contains "^rm", takes the
    heaviest set per movement line, and calculates estimated 1RM.

    Args:
        conn: SQLite connection
        movement: Movement name to filter by
        formula: 1RM formula to use ("brzycki" or "epley")

    Returns:
        (columns, rows) tuple
    """
    if formula not in FORMULAS:
        raise ValueError(
            f"Unknown formula '{formula}'. Choose from: {', '.join(FORMULAS)}"
        )

    calc = FORMULAS[formula]

    # Find the heaviest set per movement_id where note contains ^rm
    rows = conn.execute(
        """
        SELECT
            t.date,
            t.weight_magnitude,
            t.reps,
            t.weight_unit
        FROM training t
        WHERE t.movement_name = ?
          AND t.movement_note LIKE '%^rm%'
          AND t.weight_magnitude IS NOT NULL
        ORDER BY t.date, t.weight_magnitude DESC
        """,
        (movement,),
    ).fetchall()

    if not rows:
        return (
            ["date", "estimated_1rm", "weight", "reps", "unit"],
            [],
        )

    # Group by date, take the heaviest set per date
    seen_dates = {}
    for date, weight, reps, unit in rows:
        if date not in seen_dates or weight > seen_dates[date][0]:
            seen_dates[date] = (weight, reps, unit)

    result = []
    for date in sorted(seen_dates):
        weight, reps, unit = seen_dates[date]
        e1rm = round(calc(weight, reps), 1)
        result.append((date, e1rm, weight, reps, unit))

    columns = ["date", "estimated_1rm", "weight", "reps", "unit"]
    return columns, result


def register():
    return [
        {
            "type": "report",
            "name": "e1rm",
            "fn": estimated_1rm,
            "description": "Estimated 1RM progression for a movement",
            "params": [
                {"name": "movement", "type": str, "required": True, "short": "m"},
                {
                    "name": "formula",
                    "type": str,
                    "default": "brzycki",
                    "required": False,
                    "short": "f",
                },
            ],
        }
    ]

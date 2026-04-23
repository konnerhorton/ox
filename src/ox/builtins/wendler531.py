"""Wendler 5/3/1 cycle generator plugin for ox.

Generates a 4-week training cycle based on Jim Wendler's 5/3/1 program.
Outputs valid .ox text with planned (!) flag.

Usage:
    wendler531 -m squat:315
    wendler531 -m squat:315,bench-press:200
    wendler531 -m squat:315 -u kg
    wendler531 -m squat:315,deadlift:405 -d 2026-03-01
"""

from datetime import datetime, timedelta

from ox.data import Movement, TrainingSession, TrainingSet
from ox.plugins import PluginContext, TextResult
from ox.units import Q_

# Percentages of training max for each week.
# Each week is a list of (percentage, minimum_reps) tuples.
WEEK_SCHEMES = {
    1: [(0.65, 5), (0.75, 5), (0.85, 5)],
    2: [(0.70, 3), (0.80, 3), (0.90, 3)],
    3: [(0.75, 5), (0.85, 3), (0.95, 1)],
    4: [(0.40, 5), (0.50, 5), (0.60, 5)],
}


def _round_weight(weight, unit):
    """Round weight to nearest 5 lbs or 2.5 kg."""
    increment = 2.5 if unit == "kg" else 5
    return round(weight / increment) * increment


def _parse_movements(movements_str):
    """Parse comma-separated name:training_max pairs.

    Args:
        movements_str: e.g. "squat:315" or "squat:315,deadlift:405"

    Returns:
        List of (name, training_max_float) tuples.
    """
    result = []
    for pair in movements_str.split(","):
        pair = pair.strip()
        if ":" not in pair:
            raise ValueError(
                f"Invalid movement format '{pair}'. Expected name:training_max"
            )
        name, tm_str = pair.rsplit(":", 1)
        result.append((name.strip(), float(tm_str.strip())))
    return result


def _pint_unit(unit):
    """Map short unit strings to pint-compatible unit strings."""
    return {"lb": "pound", "lbs": "pound", "kg": "kilogram"}.get(unit, unit)


def wendler531(ctx: PluginContext, movements, unit="lb", start_date=None, rm="true"):
    """Generate a 4-week Wendler 5/3/1 cycle."""
    parsed = _parse_movements(movements)
    pint_unit = _pint_unit(unit)
    tag_rm = rm.lower() == "true"

    if start_date:
        date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        date = datetime.now().date()

    sessions = []
    for week_num in range(1, 5):
        session_date = date + timedelta(weeks=week_num - 1)
        scheme = WEEK_SCHEMES[week_num]

        week_movements = []
        for name, training_max in parsed:
            sets = []
            for pct, reps in scheme:
                weight = _round_weight(training_max * pct, unit)
                sets.append(TrainingSet(reps=reps, weight=Q_(weight, pint_unit)))
            note = f"training max == {training_max:g}"
            if tag_rm and week_num <= 3:
                note = f"^rm {note}"
            week_movements.append(Movement(name=name, sets=sets, note=note))

        sessions.append(
            TrainingSession(
                date=session_date,
                flag="!",
                name=f"531-week-{week_num}",
                movements=tuple(week_movements),
            )
        )

    return TextResult("\n\n".join(s.to_ox() for s in sessions) + "\n")


def register():
    return [
        {
            "name": "wendler531",
            "fn": wendler531,
            "description": "Generate a Wendler 5/3/1 cycle",
            "params": [
                {
                    "name": "movements",
                    "type": str,
                    "required": True,
                    "short": "m",
                },
                {
                    "name": "unit",
                    "type": str,
                    "default": "lb",
                    "required": False,
                    "short": "u",
                },
                {
                    "name": "start_date",
                    "type": str,
                    "default": None,
                    "required": False,
                    "short": "d",
                },
                {
                    "name": "rm",
                    "type": str,
                    "default": "true",
                    "required": False,
                    "short": "r",
                },
            ],
        }
    ]

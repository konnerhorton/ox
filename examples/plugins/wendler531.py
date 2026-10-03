"""Wendler 5/3/1 cycle generator plugin for ox.

Generates a 4-week training cycle based on Jim Wendler's 5/3/1 program.
Outputs valid .ox text with `completed: false` sessions.

This is a minimal, single-movement example of a generator plugin. ox ships a
fuller `wendler531` builtin; loading this file with `@plugin` replaces it.

Usage:
    wendler531 -m squat -t 315
    wendler531 -m squat -t 140 -u kg
    wendler531 -m bench-press -t 200 -d 2026-03-01
"""

from datetime import datetime, timedelta

from ox.data import Movement, TrainingSession, TrainingSet
from ox.plugins import PluginContext, TextResult
from ox.units import Q_

# Percentages of training max for each week
# (percentage, reps) tuples for the 3 main sets
WEEKS = {
    "5s": [(0.65, 5), (0.75, 5), (0.85, 5)],
    "3s": [(0.70, 3), (0.80, 3), (0.90, 3)],
    "5/3/1": [(0.75, 5), (0.85, 3), (0.95, 1)],
    "Deload": [(0.40, 5), (0.50, 5), (0.60, 5)],
}

WEEK_ORDER = ["5s", "3s", "5/3/1", "Deload"]


def _round_weight(weight, unit):
    """Round weight to nearest 5 lb or 2.5 kg."""
    increment = 2.5 if unit == "kg" else 5
    return round(weight / increment) * increment


def wendler531(ctx: PluginContext, movement, training_max, unit="lb", start_date=None):
    """Generate a 4-week Wendler 5/3/1 cycle.

    Args:
        movement: Movement name (e.g., "squat")
        training_max: Training max weight (number as string)
        unit: Weight unit ("lb" or "kg")
        start_date: Start date as YYYY-MM-DD string (defaults to today)

    Returns:
        TextResult holding valid .ox text
    """
    tm = float(training_max)

    if start_date:
        date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        date = datetime.now().date()

    sessions = []
    for week_name in WEEK_ORDER:
        sets = [
            TrainingSet(reps=reps, weight=Q_(_round_weight(tm * pct, unit), unit))
            for pct, reps in WEEKS[week_name]
        ]
        sessions.append(
            TrainingSession(
                date=date,
                completed=False,
                name=f"{week_name} Week",
                movements=(Movement(name=movement, sets=sets, note=None),),
            )
        )
        date += timedelta(weeks=1)

    header = f"# Wendler 5/3/1 — {movement} (TM: {tm:g}{unit})"
    body = "\n\n".join(s.to_ox() for s in sessions)
    return TextResult(f"{header}\n\n{body}\n")


def register():
    return [
        {
            "name": "wendler531",
            "fn": wendler531,
            "description": "Generate a Wendler 5/3/1 cycle for one movement",
            "params": [
                {"name": "movement", "type": str, "required": True, "short": "m"},
                {"name": "training_max", "type": str, "required": True, "short": "t"},
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
            ],
        }
    ]

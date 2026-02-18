"""Wendler 5/3/1 cycle generator plugin for ox.

Generates a 4-week training cycle based on Jim Wendler's 5/3/1 program.
Outputs valid .ox text with planned (!) flag.

Usage:
    generate wendler531 -m squat -t 315
    generate wendler531 -m squat -t 315 -u kg
    generate wendler531 -m bench-press -t 200 -d 2026-03-01
"""

from datetime import datetime, timedelta

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
    """Round weight to nearest 5 lbs or 2.5 kg."""
    increment = 2.5 if unit == "kg" else 5
    return round(weight / increment) * increment


def _format_weight(weight, unit):
    """Format weight with unit, using int if whole number."""
    if weight == int(weight):
        return f"{int(weight)}{unit}"
    return f"{weight}{unit}"


def wendler531(movement, training_max, unit="lbs", start_date=None):
    """Generate a 4-week Wendler 5/3/1 cycle.

    Args:
        movement: Movement name (e.g., "squat")
        training_max: Training max weight (number as string)
        unit: Weight unit ("lbs" or "kg")
        start_date: Start date as YYYY-MM-DD string (defaults to today)

    Returns:
        Valid .ox formatted text
    """
    tm = float(training_max)

    if start_date:
        date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        date = datetime.now().date()

    lines = [f"# Wendler 5/3/1 — {movement} (TM: {_format_weight(tm, unit)})"]
    lines.append("")

    for week_name in WEEK_ORDER:
        sets = WEEKS[week_name]
        date_str = date.strftime("%Y-%m-%d")

        lines.append("@session")
        lines.append(f"{date_str} ! {week_name} Week")

        for pct, reps in sets:
            weight = _round_weight(tm * pct, unit)
            w_str = _format_weight(weight, unit)
            lines.append(f"{movement}: {w_str} 1x{reps}")

        lines.append("@end")
        lines.append("")

        date += timedelta(weeks=1)

    return "\n".join(lines).rstrip() + "\n"


def register():
    return [
        {
            "type": "generator",
            "name": "wendler531",
            "fn": wendler531,
            "description": "Generate a Wendler 5/3/1 cycle",
            "params": [
                {"name": "movement", "type": str, "required": True, "short": "m"},
                {"name": "training_max", "type": str, "required": True, "short": "t"},
                {
                    "name": "unit",
                    "type": str,
                    "default": "lbs",
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

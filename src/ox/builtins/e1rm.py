"""Estimated 1RM report plugin for ox.

Tracks estimated one-rep max over time for a given movement.
Only considers sets tagged with "^rm" in the movement note
(convention for marking max-effort sets).

Usage:
    e1rm -m deadlift
    e1rm -m squat -f epley
    e1rm -m deadlift -o plot

Example .ox line:
    deadlift: 315lbs 1x3 "^rm top set felt good"
"""

from ox import plot
from ox.plugins import PlotResult, PluginContext, TableResult
from ox.units import Q_


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


def estimated_1rm(
    ctx: PluginContext,
    movement,
    formula="brzycki",
    unit="lb",
    output="table",
    width=None,
    height=None,
    y_step=None,
    x_scale=None,
):
    """Estimated 1RM progression for a movement.

    Finds sets where the movement note contains "^rm", takes the
    heaviest set per movement line, and calculates estimated 1RM.
    """
    if formula not in FORMULAS:
        raise ValueError(
            f"Unknown formula '{formula}'. Choose from: {', '.join(FORMULAS)}"
        )
    if output not in ("table", "plot"):
        raise ValueError("output must be 'table' or 'plot'")

    calc = FORMULAS[formula]

    rows = ctx.db.execute(
        """
        SELECT
            t.date,
            t.weight_magnitude,
            t.reps,
            t.weight_unit
        FROM training t
        WHERE t.movement_name = ?
          AND t.flag IS '*'
          AND t.movement_note LIKE '%^rm%'
          AND t.weight_magnitude IS NOT NULL
        ORDER BY t.date, t.weight_magnitude DESC
        """,
        (movement,),
    ).fetchall()

    if not rows:
        if output == "plot":
            return PlotResult([])
        return TableResult(
            ["date", f"estimated_1rm ({unit})", f"weight ({unit})", "reps"], []
        )

    seen_dates = {}
    for date, raw_weight, reps, raw_unit in rows:
        if date not in seen_dates or raw_weight > seen_dates[date][0]:
            seen_dates[date] = (raw_weight, reps, raw_unit)

    result = []
    for date in sorted(seen_dates):
        raw_weight, reps, raw_unit = seen_dates[date]
        converted = round(float(Q_(raw_weight, raw_unit).to(unit).magnitude), 1)
        e1rm = round(calc(converted, reps), 1)
        result.append((date, e1rm, converted, reps))

    if output == "plot":
        dates = [row[0] for row in result]
        values = [row[1] for row in result]
        kwargs = {"y_label": f"e1rm ({unit})"}
        if width is not None:
            kwargs["width"] = int(width)
        if height is not None:
            kwargs["height"] = int(height)
        if y_step is not None:
            kwargs["y_step"] = float(y_step)
        if x_scale is not None:
            if x_scale not in ("week", "month", "quarter", "year"):
                raise ValueError("x_scale must be one of: week, month, quarter, year")
            kwargs["x_scale"] = x_scale
        return PlotResult(plot.scatter(dates, values, **kwargs))

    columns = ["date", f"estimated_1rm ({unit})", f"weight ({unit})", "reps"]
    return TableResult(columns, result)


def register():
    return [
        {
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
                {
                    "name": "unit",
                    "type": str,
                    "default": "lb",
                    "required": False,
                    "short": "u",
                },
                {
                    "name": "output",
                    "type": str,
                    "default": "table",
                    "required": False,
                    "short": "o",
                },
                {
                    "name": "width",
                    "type": int,
                    "default": None,
                    "required": False,
                    "short": "W",
                },
                {
                    "name": "height",
                    "type": int,
                    "default": None,
                    "required": False,
                    "short": "H",
                },
                {
                    "name": "y_step",
                    "type": float,
                    "default": None,
                    "required": False,
                    "short": "y",
                },
                {
                    "name": "x_scale",
                    "type": str,
                    "default": None,
                    "required": False,
                    "short": "x",
                },
            ],
        }
    ]

"""Estimated 1RM report plugin for ox.

Tracks estimated one-rep max over time for a given movement.
Only considers sets tagged with "^rm" in the movement note
(convention for marking max-effort sets).

Usage:
    run e1rm -m deadlift
    run e1rm -m squat -f epley
    run e1rm -m deadlift -o plot

Example .ox line:
    deadlift: 315lbs 1x3 "^rm top set felt good"
"""

from datetime import date as _date

from ox.plugins import PlotResult, PluginContext, TableResult
from ox.units import Q_

_PLOT_WIDTH = 60
_PLOT_HEIGHT = 15


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


def _render_plot(data, unit):
    """Render data as a transparent ASCII line plot.

    Args:
        data: List of (date, e1rm, weight, reps) tuples sorted by date
        unit: Weight unit string for the Y axis label

    Returns:
        List of strings, one per plot row
    """
    dates = [row[0] for row in data]
    values = [row[1] for row in data]

    min_v = min(values)
    max_v = max(values)
    v_range = max_v - min_v or 1.0

    width = _PLOT_WIDTH
    height = _PLOT_HEIGHT

    grid = [[" "] * width for _ in range(height)]

    parsed = [_date.fromisoformat(d) for d in dates]
    day_offsets = [(d - parsed[0]).days for d in parsed]
    total_days = day_offsets[-1] or 1

    def to_y(v):
        return int((max_v - v) / v_range * (height - 1) + 0.5)

    def to_x(i):
        if total_days == 0:
            return width // 2
        return int(day_offsets[i] / total_days * (width - 1))

    coords = [(to_x(i), to_y(v)) for i, v in enumerate(values)]

    for x, y in coords:
        if 0 <= y < height and 0 <= x < width:
            grid[y][x] = "●"

    tick_interval = max(1, height // 4)
    lines = []
    for row_idx in range(height):
        v = max_v - v_range * row_idx / (height - 1) if height > 1 else max_v
        if row_idx % tick_interval == 0 or row_idx == height - 1:
            label = f"{v:6.1f} │"
        else:
            label = "       │"
        lines.append(label + "".join(grid[row_idx]))

    lines.append("       └" + "─" * width)

    n = len(dates)
    num_labels = min(5, n)
    if num_labels > 1:
        label_indices = [int(i * (n - 1) / (num_labels - 1)) for i in range(num_labels)]
    else:
        label_indices = [0]

    x_label_chars = [" "] * (8 + width)
    for idx in label_indices:
        x = 8 + to_x(idx)
        label = dates[idx][-5:] if len(dates[idx]) >= 5 else dates[idx]
        start = x - len(label) // 2
        for j, ch in enumerate(label):
            pos = start + j
            if 0 <= pos < len(x_label_chars):
                x_label_chars[pos] = ch

    lines.append("".join(x_label_chars))
    return lines


def estimated_1rm(
    ctx: PluginContext, movement, formula="brzycki", unit="lb", output="table"
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
        return PlotResult(_render_plot(result, unit))

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
            ],
        }
    ]

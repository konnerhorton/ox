"""Weigh-in statistics and plot report for ox.

Tracks body weight over time, with support for multiple scales.

Usage:
    report weighin
    report weighin -o plot
    report weighin -o stats
    report weighin -u kg
    report weighin -o plot -w 14

Example .ox lines:
    2025-01-10 W 185lb
    2025-01-10 W 83.9kg T07:30 "morning"
    2025-01-11 W 185.2lb "home scale"
"""

from collections import defaultdict
from datetime import date as _date, timedelta as _timedelta

from ox.units import Q_

_PLOT_WIDTH = 60
_PLOT_HEIGHT = 15
_MARKERS = ["●", "○", "▲", "△", "■", "□"]
_AVG_MARKER = "·"


def _rolling_avg(data, window_days):
    """Compute rolling average for each data point.

    For each point at date D, averages all measurements in the window
    [D - (window_days - 1), D]. Only actual measurements are included;
    days with no measurement are ignored.

    Args:
        data: List of (date_str, weight, scale) sorted by date
        window_days: Number of calendar days in the trailing window

    Returns:
        List of (date_str, avg_weight) aligned with input data
    """
    result = []
    for date_str, _weight, _scale in data:
        d = _date.fromisoformat(date_str)
        cutoff = d - _timedelta(days=window_days - 1)
        window_weights = [
            w for ds, w, _ in data if cutoff <= _date.fromisoformat(ds) <= d
        ]
        result.append((date_str, sum(window_weights) / len(window_weights)))
    return result


def _linear_trend(pairs):
    """Least-squares slope in units per day.

    Args:
        pairs: List of (date_str, weight) sorted by date

    Returns:
        Slope in units/day, or None if fewer than 2 points or zero x-variance
    """
    if len(pairs) < 2:
        return None
    dates = [_date.fromisoformat(d) for d, _ in pairs]
    weights = [w for _, w in pairs]
    x = [(d - dates[0]).days for d in dates]
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(weights) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, weights))
    den = sum((xi - mean_x) ** 2 for xi in x)
    if den == 0:
        return None
    return num / den


def _render_plot(data, avg_data, scale_markers, unit, window_days):
    """Render weigh-in data as ASCII plot.

    Raw data points use per-scale markers; rolling average uses _AVG_MARKER.
    Data points render on top of average markers when they share a cell.

    Args:
        data: List of (date_str, weight, scale) sorted by date
        avg_data: List of (date_str, avg_weight) aligned with data
        scale_markers: Dict mapping scale -> marker char
        unit: Unit string for y-axis label
        window_days: Window size for legend

    Returns:
        List of strings, one per plot row (including x-axis and legend)
    """
    all_weights = [w for _, w, _ in data] + [w for _, w in avg_data]
    min_v = min(all_weights)
    max_v = max(all_weights)
    v_range = max_v - min_v or 1.0

    width = _PLOT_WIDTH
    height = _PLOT_HEIGHT
    grid = [[" "] * width for _ in range(height)]

    dates = [d for d, _, _ in data]
    parsed = [_date.fromisoformat(d) for d in dates]
    first_day = parsed[0]
    total_days = (parsed[-1] - first_day).days or 1

    def to_y(v):
        return int((max_v - v) / v_range * (height - 1) + 0.5)

    def to_x(date_str):
        offset = (_date.fromisoformat(date_str) - first_day).days
        return int(offset / total_days * (width - 1))

    # Draw rolling average first so data points render on top
    for date_str, avg_w in avg_data:
        x, y = to_x(date_str), to_y(avg_w)
        if 0 <= y < height and 0 <= x < width and grid[y][x] == " ":
            grid[y][x] = _AVG_MARKER

    for date_str, weight, scale in data:
        x, y = to_x(date_str), to_y(weight)
        if 0 <= y < height and 0 <= x < width:
            grid[y][x] = scale_markers[scale]

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
    label_indices = (
        [int(i * (n - 1) / (num_labels - 1)) for i in range(num_labels)]
        if num_labels > 1
        else [0]
    )
    x_label_chars = [" "] * (8 + width)
    for idx in label_indices:
        x = 8 + to_x(dates[idx])
        label = dates[idx][-5:]
        start = x - len(label) // 2
        for j, ch in enumerate(label):
            pos = start + j
            if 0 <= pos < len(x_label_chars):
                x_label_chars[pos] = ch
    lines.append("".join(x_label_chars))

    lines.append("")
    for scale, marker in scale_markers.items():
        display = scale if scale is not None else "(no scale)"
        lines.append(f"  {marker}  {display}")
    lines.append(f"  {_AVG_MARKER}  {window_days}-day rolling avg")

    return lines


def weigh_in_report(conn, unit="lb", output="table", window=7):
    """Weigh-in statistics over time.

    Args:
        conn: SQLite connection
        unit: Weight unit for output values (default "lb")
        output: Output format ("table", "plot", or "stats")
        window: Rolling average window in calendar days (default 7)

    Returns:
        (columns, rows) tuple
    """
    if output not in ("table", "plot", "stats"):
        raise ValueError("output must be 'table', 'plot', or 'stats'")

    rows = conn.execute(
        """
        SELECT date, weight_magnitude, weight_unit, scale
        FROM weigh_ins
        ORDER BY date, time_of_day
        """
    ).fetchall()

    if not rows:
        if output == "plot":
            return ["plot"], [("No weigh-in data found.",)]
        if output == "stats":
            return [
                "scale",
                "count",
                f"current ({unit})",
                f"min ({unit})",
                f"max ({unit})",
                f"avg ({unit})",
                f"trend ({unit}/wk)",
            ], []
        return ["date", f"weight ({unit})", "scale"], []

    data = []
    for date_str, mag, raw_unit, scale in rows:
        converted = round(float(Q_(mag, raw_unit).to(unit).magnitude), 2)
        data.append((date_str, converted, scale))

    if output == "table":
        return (
            ["date", f"weight ({unit})", "scale"],
            [(d, w, s or "") for d, w, s in data],
        )

    if output == "plot":
        if len(data) < 2:
            return (["plot"], [("Not enough data to plot.",)])
        scales = list(dict.fromkeys(s for _, _, s in data))
        scale_markers = {s: _MARKERS[i % len(_MARKERS)] for i, s in enumerate(scales)}
        avg_data = _rolling_avg(data, window)
        plot_lines = _render_plot(data, avg_data, scale_markers, unit, window)
        return (["plot"], [(line,) for line in plot_lines])

    # stats
    by_scale = defaultdict(list)
    for date_str, weight, scale in data:
        by_scale[scale].append((date_str, weight))

    all_pairs = [(d, w) for d, w, _ in data]

    def make_row(label, pairs):
        weights = [w for _, w in pairs]
        n = len(weights)
        trend = _linear_trend(pairs)
        return (
            label,
            n,
            weights[-1],
            round(min(weights), 2),
            round(max(weights), 2),
            round(sum(weights) / n, 2),
            round(trend * 7, 3) if trend is not None else None,
        )

    stats_rows = []
    for scale in sorted(by_scale.keys(), key=lambda s: s or ""):
        label = scale if scale is not None else "(no scale)"
        stats_rows.append(make_row(label, by_scale[scale]))
    if len(by_scale) > 1:
        stats_rows.append(make_row("(all)", all_pairs))

    columns = [
        "scale",
        "count",
        f"current ({unit})",
        f"min ({unit})",
        f"max ({unit})",
        f"avg ({unit})",
        f"trend ({unit}/wk)",
    ]
    return columns, stats_rows


def register():
    return [
        {
            "type": "report",
            "name": "weighin",
            "fn": weigh_in_report,
            "description": "Weigh-in statistics over time",
            "params": [
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
                    "name": "window",
                    "type": int,
                    "default": 7,
                    "required": False,
                    "short": "w",
                },
            ],
        }
    ]

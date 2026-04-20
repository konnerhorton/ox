"""Weigh-in statistics and plot report for ox.

Tracks body weight over time, with support for multiple scales.

Usage:
    run weighin
    run weighin -o plot
    run weighin -o stats
    run weighin -u kg
    run weighin -o plot -w 14

Example .ox lines:
    2025-01-10 W 185lb
    2025-01-10 W 83.9kg T07:30 "morning"
    2025-01-11 W 185.2lb "home scale"
"""

from collections import defaultdict
from datetime import date as _date, timedelta as _timedelta

from ox import plot
from ox.plugins import PlotResult, PluginContext, TableResult
from ox.units import Q_


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


def weigh_in_report(ctx: PluginContext, unit="lb", output="table", window=0):
    """Weigh-in statistics over time."""
    if output not in ("table", "plot", "stats"):
        raise ValueError("output must be 'table', 'plot', or 'stats'")

    rows = ctx.db.execute(
        """
        SELECT date, weight_magnitude, weight_unit, scale
        FROM weigh_ins
        ORDER BY date, time_of_day
        """
    ).fetchall()

    if not rows:
        if output == "plot":
            return PlotResult(["No weigh-in data found."])
        if output == "stats":
            return TableResult(
                [
                    "scale",
                    "count",
                    f"current ({unit})",
                    f"min ({unit})",
                    f"max ({unit})",
                    f"avg ({unit})",
                    f"trend ({unit}/wk)",
                ],
                [],
            )
        return TableResult(["date", f"weight ({unit})", "scale"], [])

    data = []
    for date_str, mag, raw_unit, scale in rows:
        converted = round(float(Q_(mag, raw_unit).to(unit).magnitude), 2)
        data.append((date_str, converted, scale))

    if output == "table":
        return TableResult(
            ["date", f"weight ({unit})", "scale"],
            [(d, w, s or "") for d, w, s in data],
        )

    if output == "plot":
        if len(data) < 2:
            return PlotResult(["Not enough data to plot."])
        scales = list(dict.fromkeys(s for _, _, s in data))
        series: list[plot.Series] = []
        for s in scales:
            scale_data = [(d, w) for d, w, sc in data if sc == s]
            series.append(
                plot.Series(
                    label=s if s is not None else "(no scale)",
                    dates=[d for d, _ in scale_data],
                    values=[w for _, w in scale_data],
                    style="scatter",
                )
            )
        if window > 0:
            avg_data = _rolling_avg(data, window)
            series.append(
                plot.Series(
                    label=f"{window}-day rolling avg",
                    dates=[d for d, _ in avg_data],
                    values=[v for _, v in avg_data],
                    style="line",
                )
            )
        return PlotResult(plot.multi_series(series, y_label=f"weight ({unit})"))

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
    return TableResult(columns, stats_rows)


def register():
    return [
        {
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
                    "default": 0,
                    "required": False,
                    "short": "w",
                },
            ],
        }
    ]

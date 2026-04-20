"""Session Rate of Perceived Exertion (sRPE) plugin for ox.

Computes training load in arbitrary units (AU) from sRPE entries.
AU = rating × duration_minutes.

sRPE data is extracted from:
- Session metadata movements: `srpe: "4; PT30M"` (parsed as a movement named "srpe")
- Single-line entry notes: `"srpe: 4; PT50M"` (embedded in the movement note)

Usage:
    run srpe
    run srpe -b monthly
    run srpe -o plot
    run srpe -o acwr
    run srpe -o monotony
    run srpe -o strain
"""

import math
import re
from collections import defaultdict
from datetime import date as _date, timedelta as _timedelta

from ox import plot
from ox.plugins import PlotResult, PluginContext, TableResult

_SRPE_PATTERN = re.compile(
    r"srpe:\s*(\d+(?:\.\d+)?)\s*[;,]\s*(PT[\dHMShms]+)", re.IGNORECASE
)


def _parse_iso_duration_minutes(duration_str: str) -> float:
    """Parse an ISO 8601 duration string into total minutes.

    Supports PT#H#M#S format (e.g., PT30M, PT1H30M, PT1H, PT90S).
    """
    m = re.match(
        r"PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$",
        duration_str,
        re.IGNORECASE,
    )
    if not m:
        raise ValueError(f"Invalid ISO 8601 duration: {duration_str}")
    hours = float(m.group(1) or 0)
    minutes = float(m.group(2) or 0)
    seconds = float(m.group(3) or 0)
    return hours * 60 + minutes + seconds / 60


def _parse_srpe(text: str) -> tuple[float, float, float] | None:
    """Parse an sRPE string and return (rating, duration_minutes, AU).

    Returns None if the string doesn't contain a valid sRPE entry.
    """
    m = _SRPE_PATTERN.search(text)
    if not m:
        return None
    rating = float(m.group(1))
    duration_min = _parse_iso_duration_minutes(m.group(2))
    return rating, duration_min, rating * duration_min


def _extract_srpe_data(ctx: PluginContext) -> list[tuple[str, float, float, float]]:
    """Extract all sRPE entries from the database.

    Returns list of (date, rating, duration_minutes, AU).
    """
    results = []

    # Case 1: srpe as a movement name in a session (srpe: "4; PT30M")
    # The note field contains the value like "4; PT30M"
    rows = ctx.db.execute(
        """
        SELECT s.date, m.note
        FROM movements m
        JOIN sessions s ON m.session_id = s.id
        WHERE LOWER(m.name) = 'srpe' AND m.note IS NOT NULL
        ORDER BY s.date
        """
    ).fetchall()

    for date_str, note in rows:
        parsed = _parse_srpe(f"srpe: {note}")
        if parsed:
            results.append((date_str, *parsed))

    # Case 2: srpe embedded in a movement note (e.g., "srpe: 4; PT50M")
    rows = ctx.db.execute(
        """
        SELECT s.date, m.note
        FROM movements m
        JOIN sessions s ON m.session_id = s.id
        WHERE LOWER(m.name) != 'srpe'
          AND m.note IS NOT NULL
          AND LOWER(m.note) LIKE '%srpe:%'
        ORDER BY s.date
        """
    ).fetchall()

    for date_str, note in rows:
        parsed = _parse_srpe(note)
        if parsed:
            results.append((date_str, *parsed))

    results.sort(key=lambda r: r[0])
    return results


def _daily_au(data: list[tuple[str, float, float, float]]) -> dict[_date, float]:
    """Aggregate sRPE data into total AU per calendar day."""
    daily: dict[_date, float] = defaultdict(float)
    for date_str, _rating, _dur, au in data:
        daily[_date.fromisoformat(date_str)] += au
    return dict(daily)


def _weekly_daily_buckets(
    daily: dict[_date, float],
) -> dict[_date, list[float]]:
    """Bucket daily AU into ISO weeks (Mon-Sun), filling missing days with 0.

    Returns {monday_date: [au_per_day, ...]} spanning first to last observed day.
    """
    if not daily:
        return {}
    all_dates = sorted(daily.keys())
    first, last = all_dates[0], all_dates[-1]
    weeks: dict[_date, list[float]] = defaultdict(list)
    d = first
    while d <= last:
        monday = d - _timedelta(days=d.weekday())
        weeks[monday].append(daily.get(d, 0.0))
        d += _timedelta(days=1)
    return weeks


def _acwr_report(
    data: list[tuple[str, float, float, float]],
    acute_days: int = 7,
    chronic_days: int = 28,
) -> TableResult:
    """Acute:Chronic Workload Ratio rolling report.

    For each day that has sRPE data, compute:
    - acute  = sum of AU in the last *acute_days* days
    - chronic = average weekly AU over the last *chronic_days* days
    - ACWR   = acute / chronic
    """
    daily = _daily_au(data)
    if not daily:
        return TableResult(["date", "acute_AU", "chronic_AU", "ACWR", "zone"], [])

    all_dates = sorted(daily.keys())
    first, last = all_dates[0], all_dates[-1]

    # Build a complete date range so rest days count as 0
    date_range = []
    d = first
    while d <= last:
        date_range.append(d)
        d += _timedelta(days=1)

    full_daily = {d: daily.get(d, 0.0) for d in date_range}
    dates_list = sorted(full_daily.keys())

    rows = []
    for i, d in enumerate(dates_list):
        # Only report rows for dates that actually have training data
        if d not in daily:
            continue

        acute_start = d - _timedelta(days=acute_days - 1)
        acute = sum(full_daily[dd] for dd in dates_list if acute_start <= dd <= d)

        chronic_start = d - _timedelta(days=chronic_days - 1)
        chronic_days_list = [
            full_daily[dd] for dd in dates_list if chronic_start <= dd <= d
        ]
        # Chronic = rolling average expressed as weekly rate
        if chronic_days_list:
            chronic_total = sum(chronic_days_list)
            chronic_weeks = len(chronic_days_list) / 7.0
            chronic = chronic_total / chronic_weeks if chronic_weeks > 0 else 0.0
        else:
            chronic = 0.0

        acwr = round(acute / chronic, 2) if chronic > 0 else None
        zone = _acwr_zone(acwr)

        rows.append(
            (
                d.isoformat(),
                round(acute, 1),
                round(chronic, 1),
                acwr,
                zone,
            )
        )

    return TableResult(["date", "acute_AU", "chronic_AU", "ACWR", "zone"], rows)


def _acwr_zone(acwr: float | None) -> str:
    """Classify ACWR into a training zone."""
    if acwr is None:
        return "N/A"
    if acwr < 0.8:
        return "undertraining"
    if acwr <= 1.3:
        return "sweet spot"
    if acwr <= 1.5:
        return "caution"
    return "danger"


def _monotony_report(
    data: list[tuple[str, float, float, float]],
) -> TableResult:
    """Weekly training monotony report.

    Monotony = mean daily TL / SD of daily TL (over a 7-day window).
    High monotony (>2.0) with high load predicts overtraining.
    """
    weeks = _weekly_daily_buckets(_daily_au(data))
    if not weeks:
        return TableResult(
            ["week", "weekly_AU", "mean_daily_AU", "sd_daily_AU", "monotony"],
            [],
        )

    rows = []
    for monday in sorted(weeks.keys()):
        vals = weeks[monday]
        weekly_au = sum(vals)
        mean = weekly_au / len(vals)
        if len(vals) > 1:
            sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        else:
            sd = 0.0
        monotony = round(mean / sd, 2) if sd > 0 else None

        rows.append(
            (
                monday.isoformat(),
                round(weekly_au, 1),
                round(mean, 1),
                round(sd, 1),
                monotony,
            )
        )

    return TableResult(
        ["week", "weekly_AU", "mean_daily_AU", "sd_daily_AU", "monotony"],
        rows,
    )


def _strain_report(
    data: list[tuple[str, float, float, float]],
) -> TableResult:
    """Weekly training strain report.

    Strain = weekly TL × monotony.
    High strain combined with high monotony predicts illness/overtraining.
    """
    weeks = _weekly_daily_buckets(_daily_au(data))
    if not weeks:
        return TableResult(
            ["week", "weekly_AU", "monotony", "strain", "risk"],
            [],
        )

    rows = []
    for monday in sorted(weeks.keys()):
        vals = weeks[monday]
        weekly_au = sum(vals)
        mean = weekly_au / len(vals)
        if len(vals) > 1:
            sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        else:
            sd = 0.0
        monotony = mean / sd if sd > 0 else None
        strain = round(weekly_au * monotony, 1) if monotony is not None else None
        risk = _strain_risk(monotony, strain)

        rows.append(
            (
                monday.isoformat(),
                round(weekly_au, 1),
                round(monotony, 2) if monotony is not None else None,
                strain,
                risk,
            )
        )

    return TableResult(
        ["week", "weekly_AU", "monotony", "strain", "risk"],
        rows,
    )


def _strain_risk(monotony: float | None, strain: float | None) -> str:
    """Classify weekly strain risk level."""
    if monotony is None or strain is None:
        return "N/A"
    if monotony > 2.0 and strain > 6000:
        return "HIGH"
    if monotony > 2.0 or strain > 4000:
        return "moderate"
    return "low"


def srpe_report(ctx: PluginContext, bin: str = "weekly", output: str = "table"):
    """Training load from session RPE over time.

    Args:
        ctx: Plugin context with db and log
        bin: Time bin size ("daily", "weekly", "monthly")
        output: Output format ("table", "plot", "acwr", "monotony", "strain")
    """
    _valid_outputs = ("table", "plot", "acwr", "monotony", "strain")
    if output not in _valid_outputs:
        raise ValueError(f"output must be one of: {', '.join(_valid_outputs)}")

    data = _extract_srpe_data(ctx)
    if not data:
        if output == "plot":
            return PlotResult(["No sRPE data found."])
        if output == "acwr":
            return _acwr_report([])
        if output == "monotony":
            return _monotony_report([])
        if output == "strain":
            return _strain_report([])
        return TableResult(["period", "sessions", "total_AU", "avg_AU", "max_AU"], [])

    # Dispatch to specialized reports
    if output == "acwr":
        return _acwr_report(data)
    if output == "monotony":
        return _monotony_report(data)
    if output == "strain":
        return _strain_report(data)

    # Group by time bin
    grouped = defaultdict(list)
    for date_str, rating, duration_min, au in data:
        # Compute the bin key using the same SQL logic, but in Python
        period = _compute_period(date_str, bin)
        grouped[period].append((rating, duration_min, au))

    periods = sorted(grouped.keys())

    if output == "plot":
        labels = [p for p in periods]
        values = [sum(e[2] for e in grouped[p]) for p in periods]
        return PlotResult(plot.bar(labels, values, y_label=f"total AU ({bin})"))

    # table output
    rows = []
    for period in periods:
        entries = grouped[period]
        count = len(entries)
        total_au = round(sum(e[2] for e in entries), 1)
        avg_au = round(total_au / count, 1)
        max_au = round(max(e[2] for e in entries), 1)
        rows.append((period, count, total_au, avg_au, max_au))

    return TableResult(
        ["period", "sessions", "total_AU", "avg_AU", "max_AU"],
        rows,
    )


def _compute_period(date_str: str, bin: str) -> str:
    """Compute the period string for a date given a bin size."""
    d = _date.fromisoformat(date_str)
    if bin == "daily":
        return d.isoformat()
    elif bin == "weekly":
        # Monday of the week
        monday = (
            d.isoformat()
            if d.weekday() == 0
            else (d - _timedelta(days=d.weekday())).isoformat()
        )
        return monday
    elif bin == "weekly-num":
        return d.strftime("%Y-W%W")
    elif bin == "monthly":
        return d.strftime("%Y-%m")
    else:
        raise ValueError(f"Unknown bin: {bin}")


def register():
    return [
        {
            "name": "srpe",
            "fn": srpe_report,
            "description": "Training load from session RPE (AU = rating × duration)",
            "params": [
                {
                    "name": "bin",
                    "type": str,
                    "default": "weekly",
                    "required": False,
                    "short": "b",
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

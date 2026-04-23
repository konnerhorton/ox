"""Plot facade for ox plugins.

Thin wrapper over the `plotext` library so plugins don't each reimplement
tick spacing, datetime axes, and label clipping. Returns `list[str]` to
match the `PlotResult.lines` contract consumed by the CLI.
"""

import calendar
import math
import re
from dataclasses import dataclass
from datetime import date as _date
from typing import Literal

import plotext as plt

Scale = Literal["week", "month", "quarter", "year"]
_SCALE_MONTHS = {"month": 1, "quarter": 3, "year": 12}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_DEFAULT_WIDTH = 60
_DEFAULT_HEIGHT = 22  # empirical: even 3-row tick spacing for 6–7 y-ticks

_EMPTY_MESSAGE = "Not enough data to plot."

_SCATTER_MARKERS = ["dot", "cross", "star", "heart", "at"]
_LINE_MARKER = "braille"


@dataclass(frozen=True, slots=True)
class Series:
    """A named data series for :func:`multi_series` plotting.

    Attributes:
        label: Legend label rendered by plotext.
        dates: ISO-formatted date strings ("YYYY-MM-DD"), one per value.
        values: Numeric y-values, aligned with ``dates``.
        style: "scatter" renders as discrete markers, "line" connects points.
    """

    label: str
    dates: list[str]
    values: list[float]
    style: Literal["scatter", "line"] = "scatter"


def _finalize() -> list[str]:
    """Render the current plotext figure to a list of plain-text rows.

    Calls ``plt.build()`` and strips ANSI escape sequences left by the
    "clear" theme so plugin output is monochrome.

    Returns:
        One string per rendered row, with trailing blank lines removed.
    """
    out = plt.build()
    out = _ANSI_RE.sub("", out)
    return out.rstrip("\n").split("\n")


def _nice_step(
    span: float, target_intervals: int = 5, max_step: float | None = None
) -> float:
    """Pick a whole-number step (1/2/5 × 10ⁿ) producing ~target_intervals.

    Args:
        span: Total range to be divided into ticks.
        target_intervals: Preferred number of intervals between ticks.
        max_step: Optional upper bound on the returned step.

    Returns:
        The chosen step size. Falls back to ``10 × 10^floor(log10(span/n))``
        (clamped to ``max_step`` when provided) if no candidate in
        ``{1, 2, 5, 10}`` satisfies the target.
    """
    if span <= 0:
        return 1.0
    raw = span / target_intervals
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 5, 10):
        step = mult * mag
        if max_step is not None and step > max_step:
            continue
        if span / step <= target_intervals + 1:
            return step
    fallback = 10 * mag
    return fallback if max_step is None else min(fallback, max_step)


def _whole_number_yticks(
    values: list[float], step: float | None = None
) -> tuple[list[float], float, float]:
    """Compute evenly-spaced y-ticks on whole-number boundaries.

    Args:
        values: Data values used to derive the tick range.
        step: Override the auto-picked tick increment. If None, a nice
            step is chosen via :func:`_nice_step` (max 25).

    Returns:
        A tuple ``(ticks, bottom, top)`` where ``ticks`` is the ascending
        list of tick values, ``bottom`` is ``floor(min / step) * step``,
        and ``top`` is ``ceil(max / step) * step``.
    """
    lo, hi = min(values), max(values)
    if step is None:
        step = _nice_step(hi - lo, max_step=25)
    top = math.ceil(hi / step) * step
    bottom = math.floor(lo / step) * step
    n = int(round((top - bottom) / step)) + 1
    ticks = [bottom + i * step for i in range(n)]
    if step >= 1:
        ticks = [float(round(t)) for t in ticks]
    return ticks, float(bottom), float(top)


def _step_back(d: _date, scale: Scale) -> _date:
    """Return ``d`` moved back by one unit of ``scale``.

    Args:
        d: The reference date.
        scale: "week" steps back 7 days; "month", "quarter", "year" step
            back 1, 3, or 12 calendar months. Day-of-month is clamped
            when the target month is shorter.

    Returns:
        The new date.
    """
    if scale == "week":
        return _date.fromordinal(d.toordinal() - 7)
    months = _SCALE_MONTHS[scale]
    total = d.year * 12 + (d.month - 1) - months
    y, m = divmod(total, 12)
    m += 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return _date(y, m, day)


def _anchored_date_xticks(
    dates: list[str],
    target_ticks: int = 4,
    scale: Scale | None = None,
) -> tuple[list[str], list[str], list[int]]:
    """Compute x-ticks anchored on the most recent date, stepping back regularly.

    Args:
        dates: ISO-formatted date strings; the min/max define the range.
        target_ticks: Preferred number of ticks; also drives decimation
            when ``scale`` produces too many ticks to fit.
        scale: If given, steps back by a calendar unit (see
            :func:`_step_back`) and caps at ``target_ticks * 2`` by
            striding the results. If None, a nice day-based step is
            chosen from the data span.

    Returns:
        A tuple ``(positions_iso, mm_dd_labels, years_per_tick)``, each
        of equal length, ordered oldest → newest.
    """
    parsed = sorted({_date.fromisoformat(d) for d in dates})
    if len(parsed) < 2:
        if parsed:
            return (
                [parsed[0].isoformat()],
                [parsed[0].strftime("%m-%d")],
                [parsed[0].year],
            )
        return [], [], []
    positions: list[_date] = []
    cur = parsed[-1]
    first = parsed[0]
    if scale is None:
        total_days = (parsed[-1] - parsed[0]).days
        step_days = max(1, int(round(_nice_step(total_days, target_ticks))))
        while cur >= first:
            positions.append(cur)
            cur = _date.fromordinal(cur.toordinal() - step_days)
    else:
        while cur >= first:
            positions.append(cur)
            cur = _step_back(cur, scale)
        max_ticks = target_ticks * 2
        if len(positions) > max_ticks:
            stride = math.ceil(len(positions) / max_ticks)
            positions = positions[::stride]
    positions.reverse()
    return (
        [p.isoformat() for p in positions],
        [p.strftime("%m-%d") for p in positions],
        [p.year for p in positions],
    )


def _inject_year_row(
    lines: list[str], labels: list[str], years: list[int]
) -> list[str]:
    """Insert a hierarchical year row below the mm-dd tick labels.

    Locates the rendered tick row by picking the line containing the
    most ``labels`` substrings, finds each label's column, groups
    contiguous same-year runs, and centers the year string under each
    run. Labels that plotext drops at the edges are skipped.

    Args:
        lines: The rendered plot rows returned by :func:`_finalize`.
        labels: The mm-dd tick labels in left-to-right order.
        years: The year for each label in ``labels``, same order.

    Returns:
        ``lines`` with a new year row inserted immediately below the
        tick-label row, or ``lines`` unchanged if no tick row can be
        identified or no labels were rendered.
    """
    tick_row_idx = None
    best_match_count = 0
    for i, row in enumerate(lines):
        found = sum(1 for lbl in labels if lbl in row)
        if found > best_match_count and found >= 2:
            best_match_count = found
            tick_row_idx = i
    if tick_row_idx is None:
        return lines

    tick_row = lines[tick_row_idx]
    centers: list[int | None] = []
    cursor = 0
    for lbl in labels:
        pos = tick_row.find(lbl, cursor)
        if pos < 0:
            centers.append(None)
        else:
            centers.append(pos + len(lbl) // 2)
            cursor = pos + len(lbl)

    found_years = [(y, c) for y, c in zip(years, centers, strict=True) if c is not None]
    if not found_years:
        return lines

    runs: list[tuple[int, int, int]] = []
    start = 0
    for i in range(1, len(found_years) + 1):
        if i == len(found_years) or found_years[i][0] != found_years[start][0]:
            runs.append(
                (found_years[start][0], found_years[start][1], found_years[i - 1][1])
            )
            start = i

    width = max(len(r) for r in lines)
    year_row = [" "] * width
    for year, left_c, right_c in runs:
        label = str(year)
        mid = (left_c + right_c) // 2
        start_col = max(0, mid - len(label) // 2)
        for j, ch in enumerate(label):
            if start_col + j < width:
                year_row[start_col + j] = ch

    return (
        lines[: tick_row_idx + 1]
        + ["".join(year_row).rstrip()]
        + lines[tick_row_idx + 1 :]
    )


def scatter(
    dates: list[str],
    values: list[float],
    *,
    y_label: str,
    title: str | None = None,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    y_step: float | None = None,
    x_scale: Scale | None = None,
) -> list[str]:
    """Scatter plot of values over an ISO-date x-axis.

    Y ticks anchor at the next step-boundary above max, descending at
    regular whole-number intervals. X ticks anchor on the most recent
    date, stepping back at regular intervals; year is shown in a
    hierarchical row beneath the mm-dd labels.

    Args:
        dates: ISO-formatted date strings ("YYYY-MM-DD"), one per value.
        values: Numeric y-values, aligned with ``dates``.
        y_label: Label rendered beneath the y-axis.
        title: Optional plot title.
        width: Plot width in characters.
        height: Plot height in rows. Affects tick visual spacing.
        y_step: Override the auto-picked y-tick increment. If None, a
            nice step (1/2/5 × 10ⁿ, max 25) is chosen from the data span.
        x_scale: One of "week", "month", "quarter", "year" to force
            calendar-aligned x-tick stepping. If None, a nice day-based
            step is chosen from the data span.

    Returns:
        One string per row of the rendered plot, including axes,
        tick labels, hierarchical year row, and y-label. Returns
        ``["Not enough data to plot."]`` when fewer than 2 values.
    """
    if len(values) < 2:
        return [_EMPTY_MESSAGE]
    plt.clf()
    plt.theme("clear")
    plt.plot_size(width, height)
    plt.date_form("Y-m-d")
    plt.scatter(dates, values)
    yticks, y_bottom, y_top = _whole_number_yticks(values, step=y_step)
    plt.yticks(yticks)
    plt.ylim(y_bottom, y_top)
    tick_positions, tick_labels, tick_years = _anchored_date_xticks(
        dates, scale=x_scale
    )
    plt.xticks(tick_positions, tick_labels)
    plt.ylabel(y_label)
    if title:
        plt.title(title)
    lines = _finalize()
    return _inject_year_row(lines, tick_labels, tick_years)


def multi_series(
    series: list[Series],
    *,
    y_label: str,
    title: str | None = None,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    y_step: float | None = None,
    x_scale: Scale | None = None,
) -> list[str]:
    """Plot multiple named series on a shared ISO-date x-axis.

    Scatter series cycle through distinct markers so they remain
    distinguishable under the monochrome "clear" theme; line series
    use a braille marker for continuous connection.

    Args:
        series: Data series to overlay. Empty series are skipped.
        y_label: Label rendered beneath the y-axis.
        title: Optional plot title.
        width: Plot width in characters.
        height: Plot height in rows.
        y_step: Override the auto-picked y-tick increment.
        x_scale: One of "week", "month", "quarter", "year" to force
            calendar-aligned x-tick stepping.

    Returns:
        Rendered rows. Returns ``["Not enough data to plot."]`` when
        fewer than 2 total points are supplied.
    """
    non_empty = [s for s in series if s.values]
    total = sum(len(s.values) for s in non_empty)
    if total < 2:
        return [_EMPTY_MESSAGE]

    plt.clf()
    plt.theme("clear")
    plt.plot_size(width, height)
    plt.date_form("Y-m-d")

    scatter_idx = 0
    for s in non_empty:
        if s.style == "line":
            plt.plot(s.dates, s.values, label=s.label, marker=_LINE_MARKER)
        else:
            marker = _SCATTER_MARKERS[scatter_idx % len(_SCATTER_MARKERS)]
            scatter_idx += 1
            plt.scatter(s.dates, s.values, label=s.label, marker=marker)

    all_values = [v for s in non_empty for v in s.values]
    yticks, y_bottom, y_top = _whole_number_yticks(all_values, step=y_step)
    plt.yticks(yticks)
    plt.ylim(y_bottom, y_top)

    all_dates = [d for s in non_empty for d in s.dates]
    tick_positions, tick_labels, tick_years = _anchored_date_xticks(
        all_dates, scale=x_scale
    )
    plt.xticks(tick_positions, tick_labels)
    plt.ylabel(y_label)
    if title:
        plt.title(title)
    lines = _finalize()
    return _inject_year_row(lines, tick_labels, tick_years)


def bar(
    labels: list[str],
    values: list[float],
    *,
    y_label: str,
    title: str | None = None,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    y_step: float | None = None,
) -> list[str]:
    """Vertical bar chart with categorical string labels.

    Plotext decimates x-labels automatically when too many bars are
    supplied; no year-row injection is done since bar categories are
    not assumed to be dates.

    Args:
        labels: Category labels, one per bar.
        values: Bar heights, aligned with ``labels``.
        y_label: Label rendered beneath the y-axis.
        title: Optional plot title.
        width: Plot width in characters.
        height: Plot height in rows.
        y_step: Override the auto-picked y-tick increment.

    Returns:
        Rendered rows. Returns ``["Not enough data to plot."]`` when
        fewer than 2 values are supplied.
    """
    if len(values) < 2:
        return [_EMPTY_MESSAGE]
    plt.clf()
    plt.theme("clear")
    plt.plot_size(width, height)
    plt.bar(labels, values, width=0.5)
    if y_step is not None:
        yticks, y_bottom, y_top = _whole_number_yticks([0.0, *values], step=y_step)
        plt.yticks(yticks)
        plt.ylim(y_bottom, y_top)
    plt.ylabel(y_label)
    if title:
        plt.title(title)
    return _finalize()

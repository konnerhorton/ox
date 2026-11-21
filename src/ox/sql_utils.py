"""SQL helper utilities for ox plugins.

Plugins may import `parse_plugin_args`, `plugin_usage`, `weight_sql_expr`,
`time_bin_expr`, and for time windows `time_window`, `Window`, `SINCE_PARAM` and
`UNTIL_PARAM` from here; see docs/plugins.md, "Helpers".
"""

import calendar
import re
import shlex
from dataclasses import dataclass
from datetime import date, timedelta

from ox.units import Q_, ureg

# Unit strings as stored in the DB (Pint internal names)
# TODO: Expand this as required in the future
_DB_UNITS = ["kilogram", "pound"]

# TODO: Add annual
TIME_BINS = {
    "daily": "strftime('%Y-%m-%d', {col})",
    "weekly": "date({col}, '-' || strftime('%w', {col}) || ' days')",
    "weekly-num": "strftime('%Y-W%W', {col})",
    "monthly": "strftime('%Y-%m', {col})",
}


def weight_sql_expr(magnitude_col: str, unit_col: str, target_unit: str) -> str:
    """SQL CASE expression converting weight_magnitude to target_unit.

    Uses Pint to derive conversion factors, so any valid mass unit string is accepted.

    Raises:
        ValueError: If target_unit is not a recognized Pint unit
    """
    try:
        target = ureg.parse_units(target_unit)
    except Exception:
        raise ValueError(f"Unknown unit: '{target_unit}'")
    cases = []
    for db_unit in _DB_UNITS:
        factor = float(Q_(1, db_unit).to(target).magnitude)
        cases.append(f"WHEN '{db_unit}' THEN {magnitude_col} * {factor}")
    return f"CASE {unit_col} {' '.join(cases)} ELSE {magnitude_col} END"


def time_bin_expr(bin: str, col: str = "date") -> str:
    """Return a SQL expression for a time bin name.

    Args:
        bin: One of "daily", "weekly", "weekly-num", "monthly"
        col: The date column name to use in the expression

    Raises:
        ValueError: If bin is not a recognized time bin
    """
    if bin not in TIME_BINS:
        raise ValueError(
            f"Unknown time bin '{bin}'. Choose from: {', '.join(TIME_BINS)}"
        )
    return TIME_BINS[bin].format(col=col)


SINCE_PARAM = {
    "name": "since",
    "type": str,
    "default": None,
    "required": False,
    "short": "s",
}
UNTIL_PARAM = {"name": "until", "type": str, "default": None, "required": False}

_RELATIVE = re.compile(r"([1-9][0-9]*)([dwmy])")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


@dataclass(frozen=True, slots=True)
class Window:
    """A date range, both ends inclusive; `None` leaves that end unbounded."""

    start: date | None = None
    end: date | None = None

    def contains(self, d: date | str) -> bool:
        """Whether `d` (a `date` or an ISO date string) falls in the window."""
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if self.start is not None and d < self.start:
            return False
        return self.end is None or d <= self.end

    def sql(self, col: str = "date") -> tuple[str, tuple[str, ...]]:
        """A `WHERE` clause and its params limiting `col` to the window.

        `col` is interpolated into the clause; the bounds are passed as ISO
        string params. With neither bound set, returns `("1 = 1", ())`.
        """
        clauses, params = [], []
        if self.start is not None:
            clauses.append(f"{col} >= ?")
            params.append(self.start.isoformat())
        if self.end is not None:
            clauses.append(f"{col} <= ?")
            params.append(self.end.isoformat())
        if not clauses:
            return "1 = 1", ()
        return " AND ".join(clauses), tuple(params)


def _months_back(d: date, n: int) -> date:
    """`d` moved back `n` calendar months, clamped to the end of a shorter month."""
    total = d.year * 12 + (d.month - 1) - n
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _parse_bound(value: str, flag: str, today: date) -> date:
    """One `--since`/`--until` value as a date (see `time_window`)."""
    if _ISO_DATE.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    elif m := _RELATIVE.fullmatch(value):
        n, unit = int(m.group(1)), m.group(2)
        if unit == "d":
            boundary = today - timedelta(days=n)
        elif unit == "w":
            boundary = today - timedelta(weeks=n)
        else:
            boundary = _months_back(today, n if unit == "m" else 12 * n)
        return boundary + timedelta(days=1) if flag == "--since" else boundary
    raise ValueError(
        f"{flag}: '{value}' isn't a window. "
        "Use a count and unit (30d, 8w, 6m, 1y) or a date (2026-01-01)"
    )


def time_window(
    since: str | None = None, until: str | None = None, today: date | None = None
) -> Window:
    """The window a plugin's `--since` and `--until` values describe.

    Each value is an ISO date (`2026-01-01`, exactly `YYYY-MM-DD`) or a count
    and unit: `d` days, `w` weeks, `m` calendar months, `y` calendar years
    (`30d`, `8w`, `6m`, `1y`). A count and unit names a boundary that many units
    before `today`, clamped to the end of a shorter month; `--since` starts the
    day after it and `--until` ends on it, so `--since 7d` is the last 7 days
    counting today and adjacent windows tile. Both ends are inclusive, and a
    missing value leaves that end unbounded.

    Args:
        since: The `--since` value, or None
        until: The `--until` value, or None
        today: The date relative values count back from (default `date.today()`)

    Raises:
        ValueError: If a value isn't one of the spellings above, or the start
            is after the end
    """
    today = today or date.today()
    start = None if since is None else _parse_bound(since, "--since", today)
    end = None if until is None else _parse_bound(until, "--until", today)
    if start is not None and end is not None and start > end:
        raise ValueError(
            f"--since {start.isoformat()} is after --until {end.isoformat()}"
        )
    return Window(start, end)


def flag_name(param: dict) -> str:
    """CLI long-flag name for a param: its name with `_` replaced by `-`."""
    return param["name"].replace("_", "-")


def parse_plugin_args(params: list[dict], arg_string: str) -> dict:
    """Parse --flag value pairs from a string against a param spec.

    A param's `name` is a Python identifier; its long flag is the name with
    `_` replaced by `-`, so `start_date` is passed only as `--start-date`.

    Args:
        params: List of param dicts with keys: name, type, required, default (optional)
        arg_string: Raw argument string (e.g. "--movement kb-swing --bin weekly")

    Returns:
        Dict of parsed keyword arguments

    Raises:
        ValueError: If required params are missing or unknown flags are given
    """
    tokens = shlex.split(arg_string) if arg_string.strip() else []
    parsed = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--"):
            key = token[2:]
            param = next((p for p in params if flag_name(p) == key), None)
            if param is None:
                hyphenated = key.replace("_", "-")
                if "_" in key and any(flag_name(p) == hyphenated for p in params):
                    raise ValueError(
                        f"Unknown flag: --{key} (did you mean --{hyphenated}?)"
                    )
                raise ValueError(f"Unknown flag: --{key}")
            flag = f"--{key}"
        elif token.startswith("-") and len(token) == 2:
            key = token[1:]
            param = next((p for p in params if p.get("short") == key), None)
            if param is None:
                raise ValueError(f"Unknown flag: -{key}")
            flag = f"-{key}"
        else:
            raise ValueError(f"Unexpected argument: {token}")
        if i + 1 >= len(tokens):
            raise ValueError(f"{flag} requires a value")
        parsed[param["name"]] = param["type"](tokens[i + 1])
        i += 2

    # Apply defaults and check required
    for param in params:
        name = param["name"]
        if name not in parsed:
            if param.get("required", False):
                required_names = [
                    f"--{flag_name(p)}" for p in params if p.get("required", False)
                ]
                raise ValueError(
                    f"Missing required flag(s): {', '.join(required_names)}"
                )
            parsed[name] = param.get("default")

    return parsed


def plugin_usage(name: str, entry: dict) -> str:
    """Generate a usage string for a plugin.

    Args:
        name: Plugin name
        entry: Registry entry with params list

    Returns:
        Formatted usage string (e.g. "volume --movement <movement>")
    """
    parts = [name]
    for p in entry["params"]:
        short = f"-{p['short']}/" if p.get("short") else ""
        flag = f"{short}--{flag_name(p)} <{flag_name(p)}>"
        if p.get("required", False):
            parts.append(flag)
        else:
            parts.append(f"[{flag}]")
    return " ".join(parts)

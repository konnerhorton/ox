"""Standard reports for training log analysis.

Each report function takes a sqlite3.Connection and keyword arguments,
and returns (columns, rows) — a list of column names and a list of tuples.
This keeps reports independent of any rendering layer.
"""

import shlex
import sqlite3
from collections import defaultdict

from ox.units import Q_, ureg

# Unit strings as stored in the DB (Pint internal names)
_DB_UNITS = ["kilogram", "pound"]

TIME_BINS = {
    "daily": "strftime('%Y-%m-%d', {col})",
    "weekly": "date({col}, '-' || strftime('%w', {col}) || ' days')",
    "weekly-num": "strftime('%Y-W%W', {col})",
    "monthly": "strftime('%Y-%m', {col})",
}


def _weight_sql_expr(magnitude_col: str, unit_col: str, target_unit: str) -> str:
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


def _time_bin_expr(bin: str, col: str = "date") -> str:
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


def volume_over_time(
    conn: sqlite3.Connection, movement: str, bin: str = "weekly", unit: str = "lb"
) -> tuple[list[str], list[tuple]]:
    """Volume over time for a single movement.

    Args:
        conn: SQLite connection with training data
        movement: Movement name to filter by
        bin: Time bin size ("daily", "weekly", "monthly")
        unit: Weight unit for output values (default "lb")

    Returns:
        (columns, rows) where columns are
        ["period", "total_volume (<unit>)", "total_reps", "avg_weight_per_rep (<unit>)"]
    """
    expr = _time_bin_expr(bin, "date")
    w = _weight_sql_expr("weight_magnitude", "weight_unit", unit)
    rows = conn.execute(
        f"""
        SELECT
            {expr} AS period,
            ROUND(SUM(reps * {w}), 1)                      AS total_volume,
            SUM(reps)                                       AS total_reps,
            ROUND(SUM(reps * {w}) * 1.0 / SUM(reps), 1)   AS avg_weight_per_rep
        FROM training
        WHERE movement_name = ?
        GROUP BY period
        ORDER BY period
        """,
        (movement,),
    ).fetchall()
    columns = [
        "period",
        f"total_volume ({unit})",
        "total_reps",
        f"avg_weight_per_rep ({unit})",
    ]
    return columns, rows


def session_matrix(
    conn: sqlite3.Connection, bin: str = "weekly"
) -> tuple[list[str], list[tuple]]:
    """Session count per movement per time period.

    Rows are time periods, columns are movement names (sorted by frequency,
    most common first).

    Args:
        conn: SQLite connection with training data
        bin: Time bin size ("daily", "weekly", "monthly")

    Returns:
        (columns, rows) where columns are ["period", movement1, movement2, ...]
    """
    expr = _time_bin_expr(bin, "s.date")

    # Get movement names sorted by total frequency (most common first)
    movement_names = [
        r[0]
        for r in conn.execute(
            """
            SELECT name, COUNT(DISTINCT session_id) AS freq
            FROM movements
            GROUP BY name
            ORDER BY freq DESC, name
            """
        ).fetchall()
    ]

    # Get per-period, per-movement session counts
    raw = conn.execute(
        f"""
        SELECT
            {expr} AS period,
            m.name AS movement_name,
            COUNT(DISTINCT s.id) AS session_count
        FROM sessions s
        JOIN movements m ON m.session_id = s.id
        GROUP BY period, movement_name
        ORDER BY period
        """
    ).fetchall()

    # Pivot into {period: {movement: count}}
    pivot = defaultdict(lambda: defaultdict(int))
    periods = []
    for period, movement_name, count in raw:
        if period not in pivot:
            periods.append(period)
        pivot[period][movement_name] = count

    # Flatten to rows
    columns = ["period"] + movement_names
    rows = []
    for period in periods:
        row = [period] + [pivot[period].get(m, 0) for m in movement_names]
        rows.append(tuple(row))

    return columns, rows


def parse_report_args(params: list[dict], arg_string: str) -> dict:
    """Parse --flag value pairs from a string against a param spec.

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
            param = next((p for p in params if p["name"] == key), None)
            if param is None:
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
                    f"--{p['name']}" for p in params if p.get("required", False)
                ]
                raise ValueError(
                    f"Missing required flag(s): {', '.join(required_names)}"
                )
            parsed[name] = param.get("default")

    return parsed


def report_usage(name: str, entry: dict, command: str = "report") -> str:
    """Generate a usage string for a report or generator.

    Args:
        name: Report/generator name
        entry: Registry entry with params list
        command: CLI command prefix ("report" or "generate")

    Returns:
        Formatted usage string
    """
    parts = [f"{command} {name}"]
    for p in entry["params"]:
        short = f"-{p['short']}/" if p.get("short") else ""
        flag = f"{short}--{p['name']} <{p['name']}>"
        if p.get("required", False):
            parts.append(flag)
        else:
            parts.append(f"[{flag}]")
    return " ".join(parts)


REPORTS = {
    "volume": {
        "fn": volume_over_time,
        "description": "Volume over time for a movement",
        "params": [
            {"name": "movement", "type": str, "required": True, "short": "m"},
            {
                "name": "bin",
                "type": str,
                "default": "weekly",
                "required": False,
                "short": "b",
            },
            {
                "name": "unit",
                "type": str,
                "default": "lb",
                "required": False,
                "short": "u",
            },
        ],
    },
    "matrix": {
        "fn": session_matrix,
        "description": "Session count per movement per time period",
        "params": [
            {
                "name": "bin",
                "type": str,
                "default": "weekly",
                "required": False,
                "short": "b",
            },
        ],
    },
}


def get_all_reports() -> dict[str, dict]:
    """Return built-in reports merged with plugin reports."""
    from ox.plugins import REPORT_PLUGINS

    merged = dict(REPORTS)
    for name, desc in REPORT_PLUGINS.items():
        merged[name] = {
            "fn": desc["fn"],
            "description": desc["description"],
            "params": desc["params"],
        }
    return merged

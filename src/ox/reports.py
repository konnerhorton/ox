"""Standard reports for training log analysis.

Each report function takes a sqlite3.Connection and keyword arguments,
and returns (columns, rows) — a list of column names and a list of tuples.
This keeps reports independent of any rendering layer.
"""

import shlex
import sqlite3
from collections import defaultdict

TIME_BINS = {
    "daily": "%Y-%m-%d",
    "weekly": "%Y-W%W",
    "monthly": "%Y-%m",
}


def _time_bin_format(bin: str) -> str:
    """Return strftime format string for a time bin name.

    Args:
        bin: One of "daily", "weekly", "monthly"

    Raises:
        ValueError: If bin is not a recognized time bin
    """
    if bin not in TIME_BINS:
        raise ValueError(
            f"Unknown time bin '{bin}'. Choose from: {', '.join(TIME_BINS)}"
        )
    return TIME_BINS[bin]


def volume_over_time(
    conn: sqlite3.Connection, movement: str, bin: str = "weekly"
) -> tuple[list[str], list[tuple]]:
    """Volume over time for a single movement.

    Args:
        conn: SQLite connection with training data
        movement: Movement name to filter by
        bin: Time bin size ("daily", "weekly", "monthly")

    Returns:
        (columns, rows) where columns are
        ["period", "total_volume", "total_reps", "avg_weight_per_rep"]
    """
    fmt = _time_bin_format(bin)
    rows = conn.execute(
        f"""
        SELECT
            strftime('{fmt}', date) AS period,
            ROUND(SUM(reps * weight_magnitude), 1) AS total_volume,
            SUM(reps) AS total_reps,
            ROUND(SUM(reps * weight_magnitude) * 1.0 / SUM(reps), 1) AS avg_weight_per_rep
        FROM training
        WHERE movement_name = ?
        GROUP BY period
        ORDER BY period
        """,
        (movement,),
    ).fetchall()
    columns = ["period", "total_volume", "total_reps", "avg_weight_per_rep"]
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
    fmt = _time_bin_format(bin)

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
            strftime('{fmt}', s.date) AS period,
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


def report_usage(name: str, entry: dict) -> str:
    """Generate a usage string for a report.

    Args:
        name: Report name
        entry: Report registry entry

    Returns:
        Formatted usage string
    """
    parts = [f"report {name}"]
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

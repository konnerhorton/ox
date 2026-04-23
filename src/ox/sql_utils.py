"""SQL helper utilities for ox plugins.

Shared functions used by plugins that query the SQLite database.
"""

import shlex

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


def parse_plugin_args(params: list[dict], arg_string: str) -> dict:
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
        flag = f"{short}--{p['name']} <{p['name']}>"
        if p.get("required", False):
            parts.append(flag)
        else:
            parts.append(f"[{flag}]")
    return " ".join(parts)

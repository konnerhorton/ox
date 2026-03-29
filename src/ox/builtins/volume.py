"""Volume over time plugin for ox.

Usage:
    run volume -m squat
    run volume -m squat -b monthly -u kg
"""

from ox.plugins import PluginContext, TableResult
from ox.sql_utils import _time_bin_expr, _weight_sql_expr


def volume(ctx: PluginContext, movement: str, bin: str = "weekly", unit: str = "lb"):
    """Volume over time for a single movement.

    Args:
        ctx: Plugin context with db and log
        movement: Movement name to filter by
        bin: Time bin size ("daily", "weekly", "monthly")
        unit: Weight unit for output values (default "lb")
    """
    expr = _time_bin_expr(bin, "date")
    w = _weight_sql_expr("weight_magnitude", "weight_unit", unit)
    rows = ctx.db.execute(
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
    return TableResult(columns, rows)


def register():
    return [
        {
            "name": "volume",
            "fn": volume,
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
        }
    ]

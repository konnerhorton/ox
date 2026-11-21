"""Volume over time plugin for ox.

Usage:
    volume -m squat
    volume -m squat -b monthly -u kg
    volume -m squat -s 8w
    volume -m squat --since 2025-01-01 --until 2025-12-31
"""

from ox.plugins import PluginContext, TableResult
from ox.sql_utils import (
    SINCE_PARAM,
    UNTIL_PARAM,
    time_bin_expr,
    time_window,
    weight_sql_expr,
)


def volume(
    ctx: PluginContext,
    movement: str,
    bin: str = "weekly",
    unit: str = "lb",
    since: str | None = None,
    until: str | None = None,
):
    """Volume over time for a single movement.

    Args:
        ctx: Plugin context with db and log
        movement: Movement name to filter by
        bin: Time bin size ("daily", "weekly", "monthly")
        unit: Weight unit for output values (default "lb")
        since: Start of the window (see `ox.sql_utils.time_window`)
        until: End of the window
    """
    span_clause, span_params = time_window(since, until).sql("date")
    expr = time_bin_expr(bin, "date")
    w = weight_sql_expr("weight_magnitude", "weight_unit", unit)
    rows = ctx.db.execute(
        f"""
        SELECT
            {expr} AS period,
            ROUND(SUM(reps * {w}), 1)                      AS total_volume,
            SUM(reps)                                       AS total_reps,
            ROUND(SUM(reps * {w}) * 1.0 / SUM(reps), 1)   AS avg_weight_per_rep
        FROM training
        WHERE movement_name = ? AND {span_clause}
        GROUP BY period
        ORDER BY period
        """,
        (movement, *span_params),
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
                SINCE_PARAM,
                UNTIL_PARAM,
            ],
        }
    ]

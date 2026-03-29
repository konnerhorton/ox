"""Movement history plugin for ox.

Usage:
    run history -e squat
"""

from ox.plugins import PluginContext, TableResult


def history(ctx: PluginContext, exercise: str):
    """Show training history for a specific exercise."""
    data = ctx.log.movement_history(exercise)

    if not data:
        return TableResult([], [])

    columns = ["date", "sets_x_reps", "top_weight", "volume"]
    rows = []
    for date, movement in data:
        sets_reps = " + ".join([str(s.reps) for s in movement.sets])
        top_weight = str(movement.top_set_weight) if movement.top_set_weight else "BW"
        vol = str(movement.total_volume()) if movement.total_volume() else "-"
        rows.append((str(date), sets_reps, top_weight, vol))

    return TableResult(columns, rows)


def register():
    return [
        {
            "name": "history",
            "fn": history,
            "description": "Show training history for an exercise",
            "params": [
                {"name": "exercise", "type": str, "required": True, "short": "e"},
            ],
        }
    ]

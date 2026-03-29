"""Summary statistics plugin for ox.

Usage:
    run stats
"""

from ox.plugins import PluginContext, TableResult


def stats(ctx: PluginContext):
    """Show summary statistics for completed exercises."""
    exercises = {}
    for date, movement in ctx.log.movements():
        if movement.name not in exercises:
            exercises[movement.name] = []
        exercises[movement.name].append((date, movement))

    columns = ["exercise", "sessions", "total_reps", "last_session"]
    rows = []
    for name, sessions in sorted(exercises.items()):
        total_reps = sum(m.total_reps for _, m in sessions)
        last_date = max(d for d, _ in sessions)
        rows.append((name, len(sessions), total_reps, str(last_date)))

    return TableResult(columns, rows)


def register():
    return [
        {
            "name": "stats",
            "fn": stats,
            "description": "Show summary statistics for all exercises",
            "params": [],
        }
    ]

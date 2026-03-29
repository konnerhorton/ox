"""Template for writing an ox plugin.

Copy this file and modify it to create your own plugin.
Reference it in your .ox file with: @plugin "path/to/your_plugin.py"

A plugin is a Python module with a register() function that returns a list
of plugin descriptors. Each plugin receives a PluginContext and returns one
of: TableResult, TextResult, or PlotResult.
"""

from ox.plugins import PluginContext, PlotResult, TableResult, TextResult


def my_plugin(ctx: PluginContext, exercise: str, unit: str = "lb"):
    """Example plugin that queries training data.

    Args:
        ctx.db:  sqlite3.Connection with tables: sessions, movements, sets,
                 weigh_ins, notes, queries, and the `training` view
        ctx.log: TrainingLog with in-memory parsed data
    """
    # Option A: query the database
    rows = ctx.db.execute(
        """
        SELECT date, movement_name, SUM(reps) as total_reps
        FROM training
        WHERE movement_name = ?
        GROUP BY date
        ORDER BY date
        """,
        (exercise,),
    ).fetchall()

    columns = ["date", "movement", "total_reps"]
    return TableResult(columns, rows)

    # Option B: use in-memory log data
    # data = ctx.log.movement_history(exercise)
    # ...
    # return TableResult(columns, rows)

    # Option C: return plain text (e.g. generated .ox content)
    # return TextResult("2025-01-01 * squat: 135lb 5x5")

    # Option D: return pre-rendered lines (e.g. from a plotting library)
    # return PlotResult(["line 1", "line 2", ...])


def register():
    return [
        {
            "name": "my-plugin",
            "fn": my_plugin,
            "description": "Short description shown in plugin list",
            "params": [
                {"name": "exercise", "type": str, "required": True, "short": "e"},
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

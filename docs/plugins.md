---
icon: material/puzzle-edit
---

# Plugins

Plugins extend ox with custom analysis and generation. Each plugin receives a `PluginContext` (with `db` and `log`) and returns a `TableResult`, `TextResult`, or `PlotResult`.

## Built-in Plugins

### `volume`

Volume over time for a movement.

```
ox> run volume -m squat
ox> run volume -m deadlift --bin monthly --unit kg
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | movement name |
| `-b/--bin` | `weekly` | `daily`, `weekly`, `weekly-num`, `monthly` |
| `-u/--unit` | `lb` | any mass unit |

### `e1rm`

Estimated 1RM progression. Only uses sets with `^rm` in the note.

```
ox> run e1rm -m deadlift
ox> run e1rm -m squat --formula epley --output plot
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | movement name |
| `-f/--formula` | `brzycki` | `brzycki`, `epley` |
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot` |

Mark max-effort sets in your log with `^rm`:

```
deadlift: 315lb 1x3 "^rm top set"
```

### `weighin`

Body weight tracking with statistics and trend analysis.

```
ox> run weighin
ox> run weighin --output plot --window 14
ox> run weighin --output stats
```

| Param | Default | Options |
|---|---|---|
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot`, `stats` |
| `-w/--window` | `7` | rolling average window (days) |

Supports multiple scales — `stats` output shows per-scale breakdowns.

### `srpe`

Training load analysis from session RPE (sRPE). Computes arbitrary units (AU = rating × duration in minutes) from sRPE entries recorded as session metadata or movement notes.

```
ox> run srpe
ox> run srpe -b monthly
ox> run srpe -o plot
ox> run srpe -o acwr
ox> run srpe -o monotony
ox> run srpe -o strain
```

| Param | Default | Options |
|---|---|---|
| `-b/--bin` | `weekly` | `daily`, `weekly`, `monthly` |
| `-o/--output` | `table` | `table`, `plot`, `acwr`, `monotony`, `strain` |

**Output modes:**

- **table** — AU totals per time bin (sessions, total/avg/max AU)
- **plot** — ASCII chart of AU over time
- **acwr** — Acute:Chronic Workload Ratio (7-day acute / 28-day chronic). Zones: undertraining (<0.8), sweet spot (0.8–1.3), caution (1.3–1.5), danger (>1.5)
- **monotony** — Weekly training monotony (mean daily AU / SD). High monotony (>2.0) with high load predicts overtraining
- **strain** — Weekly strain (AU × monotony). Risk levels: low, moderate, HIGH

**Recording sRPE in your log:**

```
# As session metadata (movement named "srpe")
@session
2025-01-06 * Lower Strength
srpe: "5; PT45M"
squat: 155lb 4x5
@end

# Embedded in a movement note
2025-01-08 * run: PT30M "easy pace, srpe: 3; PT30M"
```

### `wendler531`

Generates a 4-week Wendler 5/3/1 cycle as planned sessions.

```
ox> run wendler531 -m squat:315,bench:225
ox> run wendler531 -m deadlift:405 --unit kg --start-date 2026-03-01
```

| Param | Default | Options |
|---|---|---|
| `-m/--movements` | *required* | `name:max` pairs, comma-separated |
| `-u/--unit` | `lb` | `lb`, `kg` |
| `-d/--start-date` | today | `YYYY-MM-DD` |
| `-r/--rm` | `true` | `true`, `false` — tag sets with `^rm` |

## Loading Plugins

Plugins come from two sources:

1. **Built-ins** — shipped with ox (`volume`, `e1rm`, `weighin`, `wendler531`, `srpe`)
2. **`@plugin` directives** — Python files referenced from your `.ox` log

To load a custom plugin, add an `@plugin` directive to your log file. The path is resolved relative to the `.ox` file that contains it:

```
@plugin "plugins/my_plugin.py"
@plugin "../shared/team_plugin.py"
```

Plugins loaded via `@plugin` override built-ins with the same name.

## Writing a Plugin

Export a `register()` function returning a list of descriptors. Each plugin function receives a `PluginContext` as its first argument and returns a `TableResult`, `TextResult`, or `PlotResult`.

```python
from ox.plugins import PluginContext, TableResult, TextResult, PlotResult

def my_plugin(ctx: PluginContext, movement: str, unit: str = "lb"):
    """ctx.db is a sqlite3.Connection; ctx.log is the parsed TrainingLog."""
    rows = ctx.db.execute(
        "SELECT date, SUM(reps) FROM training WHERE movement_name = ? GROUP BY date",
        (movement,),
    ).fetchall()
    return TableResult(["date", "total_reps"], rows)

    # Or return TextResult("generated .ox content")
    # Or return PlotResult(["line1", "line2", ...])

def register():
    return [{
        "name": "my-plugin",
        "fn": my_plugin,
        "description": "Total reps per day",
        "params": [
            {"name": "movement", "type": str, "required": True, "short": "m"},
            {"name": "unit", "type": str, "required": False, "default": "lb", "short": "u"},
        ],
    }]
```

### Descriptor fields

**Plugin:**

| Field | Required | Description |
|---|---|---|
| `name` | yes | CLI name |
| `fn` | yes | Callable (receives `PluginContext` + params) |
| `description` | yes | Short description |
| `params` | yes | Parameter descriptors |

**Parameter:**

| Field | Required | Description |
|---|---|---|
| `name` | yes | `--name` flag |
| `type` | yes | Python type (`str`, `int`, etc.) |
| `required` | yes | Whether required |
| `default` | no | Default value |
| `short` | no | Single-char short flag |

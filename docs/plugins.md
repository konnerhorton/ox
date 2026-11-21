---
icon: material/puzzle-edit
---

# Plugins

Plugins extend ox with custom analysis and generation. Each plugin receives a `PluginContext` (with `db` and `log`) and returns a `TableResult`, `TextResult`, or `PlotResult`.

## Built-in Plugins

`volume`, `e1rm`, `weighin` and `srpe` take a time window: `-s/--since` and `--until` limit what they show to a
date range. Each takes a count and unit counted back from today, `d` days, `w` weeks, `m` calendar months or `y`
calendar years (`30d`, `8w`, `6m`, `1y`), or a date (`2026-01-01`). Both ends are inclusive, so `--since 7d` is
the last seven days counting today, and `--since 2y --until 1y` is the year that ended a year ago. Either flag
works alone. The window limits what's shown, not what's computed: a rolling value (`srpe -o acwr`, `weighin`'s
rolling average) still uses the days before the start, and a binned output (weekly `volume`) keeps the bins at
each edge, which may be partial.

### `volume`

Volume over time for a movement.

```
ox> volume -m squat
ox> volume -m deadlift --bin monthly --unit kg
ox> volume -m squat --since 8w
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | movement name |
| `-b/--bin` | `weekly` | `daily`, `weekly`, `weekly-num`, `monthly` |
| `-u/--unit` | `lb` | any mass unit |
| `-s/--since` | none | start of the window: `8w`, `2026-01-01` |
| `--until` | none | end of the window: `1y`, `2025-12-31` |

### `e1rm`

Estimated 1RM progression. Only uses sets with `^rm` in the note.

```
ox> e1rm -m deadlift
ox> e1rm -m squat --formula epley --output plot
ox> e1rm -m squat --since 2025-01-01 --until 2025-12-31
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | movement name |
| `-f/--formula` | `brzycki` | `brzycki`, `epley` |
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot` |
| `-s/--since` | none | start of the window: `8w`, `2026-01-01` |
| `--until` | none | end of the window: `1y`, `2025-12-31` |

Mark max-effort sets in your log with `^rm`:

```
2025-01-10 T deadlift: 315lb 1x3 "^rm top set"
```

### `weighin`

Body weight tracking with statistics and trend analysis.

```
ox> weighin
ox> weighin --output plot --window 14
ox> weighin --output stats
ox> weighin --output stats --since 3m
```

| Param | Default | Options |
|---|---|---|
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot`, `stats` |
| `-w/--window` | `0` | rolling average window (days) for `plot`; `0` draws no average |
| `-s/--since` | none | start of the window: `8w`, `2026-01-01` |
| `--until` | none | end of the window: `1y`, `2025-12-31` |

With a window, `table`, `stats` and the plot's points cover only the weigh-ins in it; the rolling average still
averages the days before its start.

Supports multiple scales — `stats` output shows per-scale breakdowns.

### `srpe`

Training load analysis from session RPE (sRPE). Computes arbitrary units (AU = rating × duration in minutes) from the `srpe:` line on each session.

```
ox> srpe
ox> srpe -b monthly
ox> srpe -o plot
ox> srpe -o acwr
ox> srpe -o monotony
ox> srpe -o strain
ox> srpe -o acwr --since 4w
```

| Param | Default | Options |
|---|---|---|
| `-b/--bin` | `weekly` | `daily`, `weekly`, `monthly` |
| `-o/--output` | `table` | `table`, `plot`, `acwr`, `monotony`, `strain` |
| `-s/--since` | none | start of the window: `8w`, `2026-01-01` |
| `--until` | none | end of the window: `1y`, `2025-12-31` |

**Output modes:**

- **table** — AU totals per time bin (sessions, total/avg/max AU)
- **plot** — ASCII chart of AU over time
- **acwr** — Acute:Chronic Workload Ratio (7-day acute / 28-day chronic). Zones: undertraining (<0.8), sweet spot (0.8–1.3), caution (1.3–1.5), danger (>1.5)
- **monotony** — Weekly training monotony (mean daily AU / SD). High monotony (>2.0) with high load predicts overtraining
- **strain** — Weekly strain (AU × monotony). Risk levels: low, moderate, HIGH

**Recording sRPE in your log:**

An `srpe:` line takes a 1–10 rating, how long the session ran, and an optional note. It can sit
anywhere in the block.

```
@session
date: 2025-01-06
name: Lower Strength
srpe: 5 PT45M "legs felt heavy"
squat: 155lb 4x5
@end
```

A session with no name works the same way, which is what a single run or a bit of grease-the-groove
work becomes when it needs a rating:

```
@session
date: 2025-01-08
run: PT30M "easy pace"
srpe: 3 PT30M
@end
```

The rating is stored on the session itself (`sessions.srpe_rating`, `srpe_duration_seconds`,
`srpe_note`), so it is queryable directly:

```sql
SELECT date, srpe_rating, srpe_duration_seconds / 60 AS minutes FROM sessions
WHERE srpe_rating IS NOT NULL ORDER BY date
```

### `wendler531`

Generates a 4-week Wendler 5/3/1 cycle as planned sessions (`completed: false`).

```
ox> wendler531 -m squat:315,bench:225
ox> wendler531 -m deadlift:405 --unit kg --start-date 2026-03-01
ox> wendler531 -m squat:315 -f log.ox
```

| Param | Default | Options |
|---|---|---|
| `-m/--movements` | *required* | `name:max` pairs, comma-separated |
| `-u/--unit` | `lb` | `lb`, `kg` |
| `-d/--start-date` | today | `YYYY-MM-DD` |
| `-r/--rm` | `true` | `true`, `false` — tag sets with `^rm` |
| `-f/--file` | none | Append the cycle to this `.ox` file (created if missing). Relative paths are relative to the current directory; `~` is expanded |

### `formats`

Reads each session's `format:` line against the format vocabulary below, and lists every value in
your log with what it means. A value that doesn't fit the vocabulary still loads and stays as you
wrote it; `formats` only reports it.

```
ox> formats
ox> formats -o problems
ox> formats -o vocabulary
```

| Param | Default | Options |
|---|---|---|
| `-o/--output` | `formats` | `formats`, `problems`, `vocabulary` |

**Output modes:**

- **formats** — one row per unique `format:` value: how many sessions use it, what it means, and
  any problem. Most-used first.
- **problems** — the same, only values with a problem.
- **vocabulary** — the rules below.

**The vocabulary.** The whole value is one quoted string: a name, then its arguments. Durations are
ISO 8601 (`PT30S`, `PT2M`).

| Value | Meaning |
|---|---|
| `"emom [interval]"` | One set starts every `interval` (default `PT1M`), e.g. `"emom PT2M"`, `"emom PT30S"` |
| `"alt-emom [interval]"` | Like `emom`, rotating through the movements, one per interval |
| `"intervals <work>:<rest>"` | Fixed work and rest durations, e.g. `"intervals PT4M:PT3M"` |
| `"superset <n>-<n>-…"` | Movements grouped in the order listed, e.g. `"superset 2-3-2"` for 7 movements |
| `"pavel-sprints"` | 6 sprints of 8s work / 22s rest per set, 2 min walk between sets |
| `"ladder"` | Reps climb by one each round |
| `"circuit"` | One set of each movement in turn, repeated |

Leave `format:` out for straight sets. The format describes timing only: the number of rounds comes
from the sets, and the session's length from `srpe:`.

```
@session
date: 2026-10-21
name: run-intervals
format: "intervals PT1M:PT1M"
run-warmup: PT10M
run-interval: 3x1 PT1M "80% effort"
run-recovery: 3x1 PT1M "easy jog"
srpe: 3 PT16M
@end
```

A value is reported when it isn't quoted, uses an unknown name, or has the wrong arguments for its
name; a `superset` is also reported, with the dates, when its groups don't add up to a session's
movement lines.

```
ox> formats
  format           sessions   meaning                  problem
 ──────────────────────────────────────────────────────────────────────────────────────────────────
  "emom"           3          one set every PT1M
  "emom PT2M"      2          one set every PT2M
  "e2mom"          1                                   unknown format "e2mom"
  "superset 2-2"   1          movements grouped 2, 2   groups add up to 4, not the movement count
                                                       on 2026-01-10

4 row(s)
```

## Loading Plugins

Plugins come from two sources:

1. **Built-ins** — shipped with ox (`volume`, `e1rm`, `weighin`, `wendler531`, `srpe`, `formats`)
2. **`@plugin` directives** — Python files referenced from your `.ox` log

To load a custom plugin, add an `@plugin` directive to your log file. A path ending in `.py` loads that file,
resolved relative to the `.ox` file that contains the directive:

```
@plugin "plugins/my_plugin.py"
@plugin "../shared/team_plugin.py"
```

Plugins loaded via `@plugin` override built-ins with the same name.

## Configuring a Plugin

A plugin can take settings from your log. Put a config after the plugin's name, or after the path that loads its
file:

```
@plugin "summary" "{'panels': ['sessions -n 5', 'mix --since 8w']}"
@plugin "plugins/mix.py" "{
  'categories': ['strength', 'conditioning', 'skill'],
}"
```

A built-in has no file, so it is configured by name. A user plugin can be configured either way; the name is the
one its `register()` gives.

The config is a Python literal (a dict, list, string, number, `True`/`False`/`None`) inside double quotes:

- It may span lines, and may hold comments (`#`) and blank lines.
- It can't contain `"`: write strings inside it with single quotes.
- Names, calls and arithmetic aren't literals, so `{'start': today()}` is rejected.
- What the keys mean is up to the plugin; its own docs list them.

If a plugin is configured more than once, the first config wins, in load order: a file's own directives, then each
`@include`d file's. The REPL warns about the configs it ignores; `lint` and the editor flag a name configured twice
in the same file.

A config that doesn't parse is an error in `lint` and the editor. When the log loads, that plugin is left
unconfigured and the REPL prints a warning, so it still starts. It also warns about a config for a name no plugin
registered. `@plugin "<name>"` with no config does nothing, and `lint` reports it.

A plugin reads its config with `ctx.log.plugin_config(name)`, which returns the parsed value, or `None` when the log
doesn't configure that plugin:

```python
def mix(ctx: PluginContext, since: str = "8w"):
    config = ctx.log.plugin_config("mix") or {}
    categories = config.get("categories", [])
    ...
```

### Reserved names

Avoid naming a plugin the same as a built-in REPL command (`query`, `tables`, `reload`, `lint`, `plugins`, `help`, `exit`, `quit`) — built-ins win the name lookup and the plugin will be unreachable.

## Writing a Plugin

Export a `register()` function returning the plugin's descriptor, a dict. A file registers one plugin. (A list
holding one descriptor also works; a file whose `register()` returns several isn't loaded, and the REPL says so.)
Each plugin function receives a `PluginContext` as its first argument and returns a `TableResult`, `TextResult`, or `PlotResult`.

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
    return {
        "name": "my-plugin",
        "fn": my_plugin,
        "description": "Total reps per day",
        "params": [
            {"name": "movement", "type": str, "required": True, "short": "m"},
            {"name": "unit", "type": str, "required": False, "default": "lb", "short": "u"},
        ],
    }
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
| `name` | yes | Python identifier, passed to `fn` as a keyword argument. The long flag is the name with `_` → `-` |
| `type` | yes | Python type (`str`, `int`, etc.) |
| `required` | yes | Whether required |
| `default` | no | Default value |
| `short` | no | Single-char short flag |

A multi-word param named `start_date` is passed as `--start-date`; `--start_date` is rejected.

A param named `movement` or `movements` gets movement-name completion in the REPL: pressing Tab
after its flag offers movement names from the log (for `movements`, per comma-separated item).

### Helpers

`ox.sql_utils` has helpers for building plugin SQL and for taking a time window the way the builtins do.

```python
from ox.sql_utils import SINCE_PARAM, UNTIL_PARAM, time_bin_expr, time_window, weight_sql_expr
```

`weight_sql_expr` and `time_bin_expr` each return a SQL expression as a string, to put in your query with an
f-string.

**`weight_sql_expr(magnitude_col, unit_col, target_unit)`** converts a weight column to
`target_unit`. `magnitude_col` and `unit_col` name the columns holding the number and its unit (in
the `training` view, `weight_magnitude` and `weight_unit`). `target_unit` is any Pint mass unit:
`"kg"`, `"lb"`, `"pound"`, `"oz"`. The units the database stores, `kilogram` and `pound`, are
converted; a value stored in any other unit passes through unconverted. A `target_unit` Pint doesn't
know raises `ValueError`, and one that isn't a mass (`"meter"`) raises Pint's `DimensionalityError`.

**`time_bin_expr(bin, col="date")`** groups a date column into periods. `bin` is one of `daily`
(`2025-01-08`), `weekly` (the date of that week's Sunday), `weekly-num` (`2025-W01`) or `monthly`
(`2025-01`); any other name raises `ValueError`. `col` names the date column.

**`time_window(since=None, until=None, today=None)`** turns `--since` and `--until` values into a `Window`, with
the spellings and boundaries the builtins use (see "Built-in Plugins"): a count and unit counted back from `today`
(default: today's date), or a `YYYY-MM-DD` date; months and years clamp to the end of a shorter month. A value
that isn't one of those, or a start after the end, raises `ValueError`, which the REPL prints like a bad flag.
Call it first in your plugin, so a bad value fails before any work.

**`Window`** has `start` and `end` (`datetime.date`, inclusive; `None` is unbounded) and two methods:
`contains(d)` takes a `date` or an ISO date string, for filtering rows in Python; `sql(col="date")` returns a
`(clause, params)` pair for a `WHERE`, such as `("date >= ? AND date <= ?", ("2026-01-01", "2026-03-31"))`, or
`("1 = 1", ())` with neither bound. `col` is put in the clause as written.

**`SINCE_PARAM`** and **`UNTIL_PARAM`** are the param descriptors for `-s/--since` and `--until`. Add them to your
`params` and take `since=None, until=None`; the values reach your function as strings, for `time_window`.

Weekly tonnage across all movements, in a unit you choose, over an optional window:

```python
from ox.plugins import PluginContext, TableResult
from ox.sql_utils import SINCE_PARAM, UNTIL_PARAM, time_bin_expr, time_window, weight_sql_expr


def tonnage(ctx: PluginContext, unit: str = "kg", bin: str = "weekly", since=None, until=None):
    span_clause, span_params = time_window(since, until).sql("date")
    period = time_bin_expr(bin, "date")
    weight = weight_sql_expr("weight_magnitude", "weight_unit", unit)
    rows = ctx.db.execute(
        f"""
        SELECT {period} AS period, ROUND(SUM(reps * {weight}), 1)
        FROM training
        WHERE weight_magnitude IS NOT NULL AND {span_clause}
        GROUP BY period
        ORDER BY period
        """,
        span_params,
    ).fetchall()
    return TableResult(["period", f"tonnage ({unit})"], rows)


def register():
    return {
        "name": "tonnage",
        "fn": tonnage,
        "description": "Total weight lifted per period",
        "params": [
            {"name": "unit", "type": str, "required": False, "default": "kg", "short": "u"},
            {"name": "bin", "type": str, "required": False, "default": "weekly", "short": "b"},
            SINCE_PARAM,
            UNTIL_PARAM,
        ],
    }
```

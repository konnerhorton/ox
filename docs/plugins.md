---
icon: material/puzzle-edit
---

# Plugins

Plugins extend ox with custom analysis and generation. Each plugin receives a `PluginContext` (with `db` and `log`) and returns a `TableResult`, `TextResult`, or `PlotResult`.

## Built-in Plugins

### `volume`

Volume over time for a movement.

```
ox> volume -m squat
ox> volume -m deadlift --bin monthly --unit kg
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | movement name |
| `-b/--bin` | `weekly` | `daily`, `weekly`, `weekly-num`, `monthly` |
| `-u/--unit` | `lb` | any mass unit |

### `e1rm`

Estimated 1RM progression. Only uses sets with `^rm` in the note.

```
ox> e1rm -m deadlift
ox> e1rm -m squat --formula epley --output plot
```

| Param | Default | Options |
|---|---|---|
| `-m/--movement` | *required* | movement name |
| `-f/--formula` | `brzycki` | `brzycki`, `epley` |
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot` |

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
```

| Param | Default | Options |
|---|---|---|
| `-u/--unit` | `lb` | any mass unit |
| `-o/--output` | `table` | `table`, `plot`, `stats` |
| `-w/--window` | `7` | rolling average window (days) |

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

1. **Built-ins** — shipped with ox (`volume`, `e1rm`, `weighin`, `wendler531`, `srpe`)
2. **`@plugin` directives** — Python files referenced from your `.ox` log

To load a custom plugin, add an `@plugin` directive to your log file. The path is resolved relative to the `.ox` file that contains it:

```
@plugin "plugins/my_plugin.py"
@plugin "../shared/team_plugin.py"
```

Plugins loaded via `@plugin` override built-ins with the same name.

### Reserved names

Avoid naming a plugin the same as a built-in REPL command (`query`, `tables`, `reload`, `lint`, `plugins`, `help`, `exit`, `quit`) — built-ins win the name lookup and the plugin will be unreachable.

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
| `name` | yes | Python identifier, passed to `fn` as a keyword argument. The long flag is the name with `_` → `-` |
| `type` | yes | Python type (`str`, `int`, etc.) |
| `required` | yes | Whether required |
| `default` | no | Default value |
| `short` | no | Single-char short flag |

A multi-word param named `start_date` is passed as `--start-date`; `--start_date` is rejected.

A param named `movement` or `movements` gets movement-name completion in the REPL: pressing Tab
after its flag offers movement names from the log (for `movements`, per comma-separated item).

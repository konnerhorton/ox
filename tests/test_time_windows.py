"""Tests for time windows: --since/--until and ox.sql_utils.time_window."""

import dataclasses
import json
from datetime import date
from functools import cache
from pathlib import Path

import pytest

from ox import plot
from ox.cli import load_log
from ox.plugins import PLUGINS, load_plugins
from ox.sql_utils import (
    SINCE_PARAM,
    UNTIL_PARAM,
    Window,
    parse_plugin_args,
    time_window,
)

ROOT = Path(__file__).parent.parent


def _recorder(name: str):
    """A stand-in for an `ox.plot` function: one line holding its arguments as JSON.

    Plotext's bar-chart x-labels depend on the hash seed (TODO #18), so plots are
    checked by the data plugins pass to `ox.plot`, not by the rendered lines.
    """

    def record(*args, **kwargs):
        def plain(v):
            if dataclasses.is_dataclass(v):
                return dataclasses.asdict(v)
            if isinstance(v, (list, tuple)):
                return [plain(x) for x in v]
            return v

        return [json.dumps({"fn": name, "args": plain(args), "kwargs": kwargs})]

    return record


@pytest.fixture
def recorded_plots(monkeypatch):
    for name in ("scatter", "bar", "multi_series"):
        monkeypatch.setattr(plot, name, _recorder(name))


@cache
def _ctx(log: str):
    return load_log(ROOT / log)[2]


def _run(log: str, plugin: str, args: str):
    ctx = _ctx(log)
    if plugin not in PLUGINS:  # other tests clear the registry
        load_plugins()
    entry = PLUGINS[plugin]
    return entry["fn"](ctx, **parse_plugin_args(entry["params"], args))


# --- time_window and Window (AC 1-6) ---------------------------------------

NOV19 = date(2026, 11, 19)


@pytest.mark.parametrize(
    "since, start",
    [
        ("7d", date(2026, 11, 13)),
        ("1d", date(2026, 11, 19)),
        ("8w", date(2026, 9, 25)),
        ("3m", date(2026, 8, 20)),
        ("1y", date(2025, 11, 20)),
    ],
)
def test_relative_since(since, start):
    """AC 1."""
    assert time_window(since, today=NOV19) == Window(start, None)


@pytest.mark.parametrize(
    "until, end", [("7d", date(2026, 11, 12)), ("1y", date(2025, 11, 19))]
)
def test_relative_until(until, end):
    """AC 2."""
    assert time_window(until=until, today=NOV19) == Window(None, end)


def test_relative_windows_tile():
    """AC 2: --since 2y --until 1y ends the day before --since 1y starts."""
    assert time_window("2y", "1y", today=NOV19) == Window(
        date(2024, 11, 20), date(2025, 11, 19)
    )
    assert time_window("1y", today=NOV19).start == date(2025, 11, 20)


@pytest.mark.parametrize(
    "today, since, until, expected",
    [
        (date(2026, 3, 31), "1m", None, Window(date(2026, 3, 1), None)),
        (date(2026, 3, 31), None, "1m", Window(None, date(2026, 2, 28))),
        (date(2028, 2, 29), "1y", None, Window(date(2027, 3, 1), None)),
    ],
)
def test_month_end_clamping(today, since, until, expected):
    """AC 3."""
    assert time_window(since, until, today=today) == expected


def test_iso_dates():
    """AC 4."""
    assert time_window("2025-01-01", "2025-12-31", today=NOV19) == Window(
        date(2025, 1, 1), date(2025, 12, 31)
    )
    assert time_window(until="2025-06-30", today=NOV19) == Window(
        None, date(2025, 6, 30)
    )


def test_neither_value_is_unbounded():
    assert time_window(today=NOV19) == Window(None, None)


def test_today_defaults_to_today():
    assert time_window("1d").start == date.today()


BAD = ["8x", "8W", "0d", "-3d", "8", "w", "20260101", "2026-02-30", "", "8w\n"]


@pytest.mark.parametrize("value", BAD)
@pytest.mark.parametrize("flag", ["since", "until"])
def test_bad_values_raise(value, flag):
    """AC 5: the message names the flag and the accepted forms."""
    msg = (
        f"--{flag}: '{value}' isn't a window. "
        "Use a count and unit (30d, 8w, 6m, 1y) or a date (2026-01-01)"
    )
    with pytest.raises(ValueError) as exc:
        time_window(**{flag: value}, today=NOV19)
    assert str(exc.value) == msg


def test_start_after_end_raises():
    """AC 5."""
    with pytest.raises(ValueError) as exc:
        time_window("2026-02-01", "2026-01-01", today=NOV19)
    assert str(exc.value) == "--since 2026-02-01 is after --until 2026-01-01"
    with pytest.raises(ValueError, match="is after"):
        time_window("1y", "2y", today=NOV19)


def test_equal_bounds_are_one_day():
    """AC 5 / spec decision 4."""
    one = date(2026, 1, 1)
    assert time_window("2026-01-01", "2026-01-01", today=NOV19) == Window(one, one)


def test_future_dates_allowed():
    """Spec decision 3: an empty window, not an error."""
    assert time_window("2027-01-01", today=NOV19).start == date(2027, 1, 1)


SPAN = Window(date(2025, 1, 10), date(2025, 1, 12))


@pytest.mark.parametrize(
    "d, inside",
    [
        (date(2025, 1, 9), False),
        (date(2025, 1, 10), True),
        (date(2025, 1, 12), True),
        (date(2025, 1, 13), False),
    ],
)
def test_contains_at_bounds(d, inside):
    """AC 6: true at both bounds, false one day outside each, date or string."""
    assert SPAN.contains(d) is inside
    assert SPAN.contains(d.isoformat()) is inside


def test_unbounded_contains_everything():
    """AC 6."""
    assert Window().contains(date(1900, 1, 1))
    assert Window(start=date(2025, 1, 1)).contains("2999-12-31")
    assert Window(end=date(2025, 1, 1)).contains("1900-01-01")


@pytest.mark.parametrize(
    "span, clause, params, dates",
    [
        (Window(), "1 = 1", (), ["2025-01-10", "2025-01-11", "2025-01-12"]),
        (
            Window(start=date(2025, 1, 11)),
            "date >= ?",
            ("2025-01-11",),
            ["2025-01-11", "2025-01-12"],
        ),
        (
            Window(end=date(2025, 1, 11)),
            "date <= ?",
            ("2025-01-11",),
            ["2025-01-10", "2025-01-11"],
        ),
        (
            Window(date(2025, 1, 11), date(2025, 1, 11)),
            "date >= ? AND date <= ?",
            ("2025-01-11", "2025-01-11"),
            ["2025-01-11"],
        ),
    ],
)
def test_sql(simple_db, span, clause, params, dates):
    """AC 6: the clause and params, and the rows they select from simple_db."""
    assert span.sql() == (clause, params)
    rows = simple_db.execute(
        f"SELECT DISTINCT date FROM training WHERE {clause} ORDER BY date", params
    ).fetchall()
    assert [r[0] for r in rows] == dates


def test_sql_column_name():
    assert Window(date(2025, 1, 1)).sql("t.date") == ("t.date >= ?", ("2025-01-01",))


def test_shared_params():
    """Spec: the flags parse as strings; --until has no short flag."""
    params = [SINCE_PARAM, UNTIL_PARAM]
    assert parse_plugin_args(params, "-s 8w --until 2025-12-31") == {
        "since": "8w",
        "until": "2025-12-31",
    }
    assert parse_plugin_args(params, "") == {"since": None, "until": None}
    with pytest.raises(ValueError, match="Unknown flag: -u"):
        parse_plugin_args(params, "-u 1y")


# --- volume and e1rm (AC 7, AC 10) ------------------------------------------

EXAMPLE = "examples/example.ox"
RM_SETS = "tests/data/rm_sets.ox"


def test_volume_iso_window_keeps_matching_rows():
    """AC 7: a Sunday-to-Saturday window keeps exactly those weeks' rows."""
    full = _run(EXAMPLE, "volume", "-m squat").rows
    got = _run(EXAMPLE, "volume", "-m squat --since 2024-02-04 --until 2024-02-24")
    assert [r[0] for r in got.rows] == ["2024-02-04", "2024-02-11", "2024-02-18"]
    assert got.rows == [r for r in full if "2024-02-04" <= r[0] <= "2024-02-18"]


def test_volume_partial_first_and_last_bins():
    """AC 7: a mid-week bound keeps the partial bin, with only in-window days.

    Week of Sun 2024-02-04 in example.ox: Mon 02-05 `squat: 135lb 5x10` (6750 lb,
    50 reps) and Wed 02-07 `135/155/175/195/175lb 5/5/5/3/5` (675 + 775 + 875 +
    585 + 875 = 3785 lb, 23 reps).
    """
    full = dict((r[0], r[1:]) for r in _run(EXAMPLE, "volume", "-m squat").rows)
    assert full["2024-02-04"] == (10535.0, 73, 144.3)
    since = _run(EXAMPLE, "volume", "-m squat --since 2024-02-06").rows
    assert since[0] == ("2024-02-04", 3785.0, 23, 164.6)
    until = _run(EXAMPLE, "volume", "-m squat --until 2024-02-06").rows
    assert until[-1] == ("2024-02-04", 6750.0, 50, 135.0)


def test_volume_empty_window():
    assert _run(EXAMPLE, "volume", "-m squat --since 2030-01-01").rows == []


@pytest.mark.parametrize("movement", ["squat", "deadlift"])
def test_e1rm_iso_window_keeps_matching_rows(movement):
    """AC 7."""
    full = _run(RM_SETS, "e1rm", f"-m {movement}").rows
    got = _run(RM_SETS, "e1rm", f"-m {movement} --since 2025-01-20 --until 2025-02-05")
    expected = [r for r in full if "2025-01-20" <= r[0] <= "2025-02-05"]
    assert len(expected) == 2
    assert got.rows == expected


def test_e1rm_plot_window(recorded_plots):
    got = _run(RM_SETS, "e1rm", "-m squat -o plot --since 2025-02-01")
    assert json.loads(got.lines[0])["args"][0] == ["2025-02-05", "2025-03-05"]


def test_e1rm_empty_window():
    assert _run(RM_SETS, "e1rm", "-m squat --until 2024-12-31").rows == []
    assert _run(RM_SETS, "e1rm", "-m squat -o plot --until 2024-12-31").lines == []


@pytest.mark.parametrize("plugin", ["volume", "e1rm"])
def test_flags_parse(plugin):
    """AC 10: -s and --since parse; --until has no short flag; -u is still --unit."""
    load_plugins()
    params = PLUGINS[plugin]["params"]
    for args in ("-m squat -s 8w", "-m squat --since 8w"):
        assert parse_plugin_args(params, args)["since"] == "8w"
    parsed = parse_plugin_args(params, "-m squat --until 2025-12-31 -u kg")
    assert parsed["until"] == "2025-12-31"
    assert parsed["unit"] == "kg"


@pytest.mark.parametrize("plugin", ["volume", "e1rm"])
def test_bad_value_prints_error(plugin, capsys):
    """AC 10: a bad value prints the error and returns, as a bad flag does."""
    from ox.cli import run_plugin

    run_plugin(_ctx(EXAMPLE), plugin, "-m squat --since 8x")
    out = " ".join(capsys.readouterr().out.split())
    assert (
        "--since: '8x' isn't a window. "
        "Use a count and unit (30d, 8w, 6m, 1y) or a date (2026-01-01)"
    ) in out


# --- srpe (AC 8, AC 10) -----------------------------------------------------

ADVANCED = "examples/advanced.ox"


def test_srpe_table_partial_first_bin():
    """AC 8. Week of Mon 2025-01-13 in advanced.ox: 5x50 + 5x40 + 4x35 + 5x45 + 5x40
    = 1015 AU over 5 sessions; from Wed 01-15 only 140 + 225 + 200 = 565 AU over 3.
    """
    full = _run(ADVANCED, "srpe", "").rows
    assert full[1] == ("2025-01-13", 5, 1015.0, 203.0, 250.0)
    got = _run(ADVANCED, "srpe", "--since 2025-01-15").rows
    assert got[0] == ("2025-01-13", 3, 565.0, 188.3, 225.0)
    assert got[1:] == full[2:]


@pytest.mark.parametrize("output", ["monotony", "strain"])
def test_srpe_weekly_outputs_partial_first_week(output):
    """AC 8: monotony and strain bucket only the window's days."""
    got = _run(ADVANCED, "srpe", f"-o {output} --since 2025-01-15").rows
    assert got[0][:2] == ("2025-01-13", 565.0)


def test_srpe_plot_window(recorded_plots):
    got = _run(ADVANCED, "srpe", "-o plot --since 2025-02-10 --until 2025-02-23")
    labels, values = json.loads(got.lines[0])["args"]
    full = {r[0]: r[2] for r in _run(ADVANCED, "srpe", "").rows}
    assert labels == ["2025-02-10", "2025-02-17"]
    assert values == [full["2025-02-10"], full["2025-02-17"]]


def test_srpe_acwr_window_keeps_rolling_values():
    """AC 8: rows in the window match the unwindowed rows value for value.

    2025-02-03 is four weeks in, so recomputing over only the window's sessions
    would give different acute and chronic values; the second assert shows it.
    """
    from ox.builtins.srpe import _acwr_report, _extract_srpe_data

    full = _run(ADVANCED, "srpe", "-o acwr").rows
    got = _run(ADVANCED, "srpe", "-o acwr --since 2025-02-03").rows
    assert got == [r for r in full if r[0] >= "2025-02-03"]
    assert got and len(got) < len(full)
    data = [r for r in _extract_srpe_data(_ctx(ADVANCED)) if r[0] >= "2025-02-03"]
    assert _acwr_report(data).rows != got


def test_srpe_acwr_until():
    full = _run(ADVANCED, "srpe", "-o acwr").rows
    got = _run(ADVANCED, "srpe", "-o acwr --until 2025-01-20").rows
    assert got == [r for r in full if r[0] <= "2025-01-20"]


@pytest.mark.parametrize("output", ["table", "acwr", "monotony", "strain"])
def test_srpe_empty_window(output):
    """Spec decision 8: each output's existing empty result."""
    got = _run(ADVANCED, "srpe", f"-o {output} --since 2030-01-01")
    assert got.rows == []
    assert got.columns == _run(EXAMPLE, "srpe", f"-o {output}").columns


def test_srpe_plot_empty_window():
    got = _run(ADVANCED, "srpe", "-o plot --since 2030-01-01")
    assert got.lines == ["No sRPE data found."]


def test_srpe_flags_parse(capsys):
    """AC 10 for srpe."""
    from ox.cli import run_plugin

    load_plugins()
    params = PLUGINS["srpe"]["params"]
    for args in ("-s 8w", "--since 8w"):
        assert parse_plugin_args(params, args)["since"] == "8w"
    assert parse_plugin_args(params, "--until 2025-12-31")["until"] == "2025-12-31"
    run_plugin(_ctx(ADVANCED), "srpe", "-o acwr --since 8x")
    assert "--since: '8x' isn't a window." in capsys.readouterr().out


# --- user plugins (AC 12) ---------------------------------------------------

USER_PLUGIN = """\
from ox.plugins import TableResult
from ox.sql_utils import SINCE_PARAM, UNTIL_PARAM, time_window


def sessions(ctx, since=None, until=None):
    span = time_window(since, until)
    rows = ctx.db.execute(
        "SELECT DISTINCT date FROM training ORDER BY date"
    ).fetchall()
    return TableResult(["date"], [r for r in rows if span.contains(r[0])])


def register():
    return {
        "name": "sessions",
        "fn": sessions,
        "description": "Training dates",
        "params": [SINCE_PARAM, UNTIL_PARAM],
    }
"""


def _user_log(tmp_path: Path, plugin_file: str, code: str):
    (tmp_path / plugin_file).write_text(code)
    log = (ROOT / EXAMPLE).read_text()
    (tmp_path / "log.ox").write_text(f'@plugin "{plugin_file}"\n{log}')
    return load_log(tmp_path / "log.ox")[2]


def _run_loaded(ctx, plugin: str, args: str):
    entry = PLUGINS[plugin]
    return entry["fn"](ctx, **parse_plugin_args(entry["params"], args))


def test_user_plugin_filters_like_builtins(tmp_path):
    """AC 12: a user plugin with the shared params windows like volume does."""
    ctx = _user_log(tmp_path, "sessions.py", USER_PLUGIN)
    got = _run_loaded(ctx, "sessions", "-s 2024-02-05 --until 2024-02-07").rows
    assert [r[0] for r in got] == ["2024-02-05", "2024-02-07"]
    assert len(_run_loaded(ctx, "sessions", "").rows) > 2
    with pytest.raises(ValueError, match="isn't a window"):
        _run_loaded(ctx, "sessions", "--since 8x")


def test_docs_tonnage_example_runs(tmp_path):
    """AC 12: the windowed tonnage example in docs/plugins.md runs."""
    doc = (ROOT / "docs" / "plugins.md").read_text()
    blocks = doc.split("```python\n")[1:]
    code = next(b.split("```")[0] for b in blocks if "def tonnage" in b)
    ctx = _user_log(tmp_path, "tonnage.py", code)
    full = _run_loaded(ctx, "tonnage", "-u lb")
    got = _run_loaded(ctx, "tonnage", "-u lb --since 2024-02-04 --until 2024-02-24")
    assert [r[0] for r in got.rows] == ["2024-02-04", "2024-02-11", "2024-02-18"]
    assert got.rows == [r for r in full.rows if "2024-02-04" <= r[0] <= "2024-02-18"]

"""Tests for time windows: --since/--until and ox.sql_utils.time_window."""

import dataclasses
import json
from functools import cache
from pathlib import Path

import pytest

from ox import plot
from ox.cli import load_log
from ox.plugins import PLUGINS, PlotResult, TableResult, TextResult
from ox.sql_utils import parse_plugin_args

ROOT = Path(__file__).parent.parent
SNAPSHOT = json.loads((ROOT / "tests" / "data" / "no_window.json").read_text())


def _recorder(name: str):
    """A stand-in for an `ox.plot` function: one line holding its arguments as JSON.

    Plotext's bar-chart x-labels depend on the hash seed, so plots are compared by
    the data plugins pass to `ox.plot`, not by the rendered lines.
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
    ctx = _ctx(log)  # loading registers the builtins
    entry = PLUGINS[plugin]
    return entry["fn"](ctx, **parse_plugin_args(entry["params"], args))


def _dump(result) -> dict:
    if isinstance(result, TableResult):
        return json.loads(json.dumps({"table": [result.columns, result.rows]}))
    if isinstance(result, PlotResult):
        return {"plot": result.lines}
    if isinstance(result, TextResult):
        return {"text": result.text}
    raise TypeError(result)


@pytest.mark.parametrize(
    "case", SNAPSHOT, ids=lambda c: f"{Path(c['log']).stem}:{c['plugin']} {c['args']}"
)
def test_no_flags_unchanged(case, recorded_plots):
    """AC 11: with neither flag, each plugin's output is what it was before."""
    expected = {k: v for k, v in case.items() if k in ("table", "plot", "text")}
    assert _dump(_run(case["log"], case["plugin"], case["args"])) == expected

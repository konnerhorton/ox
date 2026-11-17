"""Tests for the session `format:` vocabulary (ox.formats) and the formats plugin."""

from datetime import timedelta

import pytest

from ox.builtins.formats import formats_report
from ox.cli import parse_file, run_plugin
from ox.db import create_db
from ox.formats import check_movement_count, parse_format
from ox.plugins import PLUGINS, PluginContext, load_plugins


class TestParseFormat:
    @pytest.mark.parametrize(
        "value, seconds",
        [('"emom"', 60), ('"emom PT2M"', 120), ('"emom PT30S"', 30)],
    )
    def test_emom(self, value, seconds):
        parsed = parse_format(value)
        assert parsed.problem is None
        assert parsed.name == "emom"
        assert parsed.interval == timedelta(seconds=seconds)
        assert not parsed.rotating

    @pytest.mark.parametrize(
        "value, seconds", [('"alt-emom"', 60), ('"alt-emom PT30S"', 30)]
    )
    def test_alt_emom(self, value, seconds):
        parsed = parse_format(value)
        assert parsed.problem is None
        assert parsed.interval == timedelta(seconds=seconds)
        assert parsed.rotating

    @pytest.mark.parametrize(
        "value, work, rest",
        [('"intervals PT1M:PT1M"', 60, 60), ('"intervals PT4M:PT3M"', 240, 180)],
    )
    def test_intervals(self, value, work, rest):
        parsed = parse_format(value)
        assert parsed.problem is None
        assert parsed.work == timedelta(seconds=work)
        assert parsed.rest == timedelta(seconds=rest)

    def test_superset(self):
        parsed = parse_format('"superset 2-3-2"')
        assert parsed.problem is None
        assert parsed.groups == (2, 3, 2)
        assert check_movement_count(parsed, 7)

    @pytest.mark.parametrize(
        "value, meaning",
        [
            (
                '"pavel-sprints"',
                "6 sprints of 8s work / 22s rest per set, 2 min walk between sets",
            ),
            ('"ladder"', "reps climb by one each round"),
            ('"circuit"', "one set of each movement in turn, repeated"),
        ],
    )
    def test_named_protocols(self, value, meaning):
        parsed = parse_format(value)
        assert parsed.problem is None
        assert parsed.meaning == meaning
        assert parsed.interval is None
        assert parsed.work is None and parsed.rest is None
        assert parsed.groups is None

    @pytest.mark.parametrize(
        "value, meaning",
        [
            ('"emom"', "one set every PT1M"),
            ('"emom PT2M"', "one set every PT2M"),
            ('"alt-emom PT30S"', "one set every PT30S, rotating through movements"),
            ('"intervals PT4M:PT3M"', "PT4M work, PT3M rest"),
            ('"superset 2-3-2"', "movements grouped 2, 3, 2"),
        ],
    )
    def test_meaning(self, value, meaning):
        assert parse_format(value).meaning == meaning

    def test_not_quoted(self):
        parsed = parse_format("emom PT2M")
        assert parsed.problem == "not quoted"
        assert parsed.meaning == ""

    @pytest.mark.parametrize("value", ['""', '"  "'])
    def test_empty(self, value):
        assert parse_format(value).problem == "empty"

    @pytest.mark.parametrize("name", ["tabata", "EMOM", "e2mom"])
    def test_unknown(self, name):
        assert parse_format(f'"{name}"').problem == f'unknown format "{name}"'

    @pytest.mark.parametrize(
        "value, usage",
        [
            ('"emom PT2M PT3M"', "emom [interval]"),
            ('"emom 2"', "emom [interval]"),
            ('"emom PT0S"', "emom [interval]"),
            ('"emom PT1M/PT2M"', "emom [interval]"),
            ('"intervals"', "intervals <work>:<rest>"),
            ('"intervals PT1M"', "intervals <work>:<rest>"),
            ('"intervals PT1M:"', "intervals <work>:<rest>"),
            ('"intervals PT1M:PT0S"', "intervals <work>:<rest>"),
            ('"intervals PT1M PT1M"', "intervals <work>:<rest>"),
            ('"superset"', "superset <n>-<n>-…"),
            ('"superset 2-0"', "superset <n>-<n>-…"),
            ('"superset 2/3"', "superset <n>-<n>-…"),
            ('"ladder 5"', "ladder"),
        ],
    )
    def test_bad_arguments(self, value, usage):
        parsed = parse_format(value)
        assert parsed.problem == f'expected "{usage}"'
        assert parsed.meaning == ""

    def test_superset_mismatch(self):
        parsed = parse_format('"superset 2-3-2"')
        assert parsed.groups == (2, 3, 2)
        assert not check_movement_count(parsed, 6)

    def test_movement_count_ignores_non_supersets(self):
        assert check_movement_count(parse_format('"emom"'), 3)


def _session(date, fmt=None, movements=("squat: 100kg 5x5",)):
    lines = ["@session", f"date: {date}"]
    if fmt is not None:
        lines.append(f"format: {fmt}")
    lines += list(movements) + ["@end", ""]
    return "\n".join(lines)


def _ctx(tmp_path, *sessions):
    path = tmp_path / "log.ox"
    path.write_text("\n".join(sessions))
    log = parse_file(path)
    return PluginContext(db=create_db(log), log=log)


@pytest.fixture
def mixed_ctx(tmp_path):
    return _ctx(
        tmp_path,
        _session("2026-01-01", '"emom"'),
        _session("2026-01-02", '"intervals PT1M:PT1M"'),
        _session("2026-01-03", "emom PT2M"),
        _session("2026-01-04", '"emom"'),
        _session("2026-01-05"),
    )


class TestFormatsPlugin:
    def test_formats_view(self, mixed_ctx):
        result = formats_report(mixed_ctx)
        assert result.columns == ["format", "sessions", "meaning", "problem"]
        assert result.rows == [
            ('"emom"', 2, "one set every PT1M", ""),
            ('"intervals PT1M:PT1M"', 1, "PT1M work, PT1M rest", ""),
            ("emom PT2M", 1, "", "not quoted"),
        ]

    def test_problems_view(self, mixed_ctx):
        result = formats_report(mixed_ctx, output="problems")
        assert result.rows == [("emom PT2M", 1, "", "not quoted")]

    def test_superset_dates(self, tmp_path):
        three = ("a: 5x5", "b: 5x5", "c: 5x5")
        four = three + ("d: 5x5",)
        ctx = _ctx(
            tmp_path,
            _session("2026-02-03", '"superset 2-2"', three),
            _session("2026-02-01", '"superset 2-2"', four),
            _session("2026-02-02", '"superset 2-2"', three),
        )
        assert formats_report(ctx).rows == [
            (
                '"superset 2-2"',
                3,
                "movements grouped 2, 2",
                "groups add up to 4, not the movement count on 2026-02-02, 2026-02-03",
            )
        ]

    def test_vocabulary_view(self, mixed_ctx):
        result = formats_report(mixed_ctx, output="vocabulary")
        assert result.columns == ["format", "description"]
        assert [row[0] for row in result.rows] == [
            "emom [interval]",
            "alt-emom [interval]",
            "intervals <work>:<rest>",
            "superset <n>-<n>-…",
            "pavel-sprints",
            "ladder",
            "circuit",
        ]

    def test_bad_output(self, mixed_ctx):
        with pytest.raises(
            ValueError,
            match="output must be 'formats', 'problems', or 'vocabulary'",
        ):
            formats_report(mixed_ctx, output="table")

    def test_registered_and_runs_in_repl(self, mixed_ctx, capsys):
        load_plugins()
        assert "formats" in PLUGINS
        run_plugin(mixed_ctx, "formats", "-o problems")
        out = capsys.readouterr().out
        assert "not quoted" in out
        assert "intervals" not in out

    def test_nothing_dropped(self, tmp_path):
        ctx = _ctx(
            tmp_path,
            _session("2026-03-01", "emom PT2M"),
            _session("2026-03-02", '"tabata"'),
        )
        assert ctx.log.diagnostics == ()
        sessions = sorted(ctx.log.sessions, key=lambda s: s.date)
        assert "format: emom PT2M\n" in sessions[0].to_ox()
        assert 'format: "tabata"\n' in sessions[1].to_ox()

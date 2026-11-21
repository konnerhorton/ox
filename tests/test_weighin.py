"""Tests for the weighin builtin report plugin."""

import pytest

from ox.builtins.weighin import (
    _linear_trend,
    _rolling_avg,
    _windowed_rolling_avg,
    weigh_in_report,
)
from ox.data import TrainingLog
from ox.plugins import PluginContext, PlotResult


def _ctx(db):
    """Create a PluginContext wrapping a db connection."""
    return PluginContext(db=db, log=TrainingLog(sessions=()))


def _run_weighin(db, **kwargs):
    """Run weigh_in_report and return (columns, rows) tuple for test compat."""
    result = weigh_in_report(_ctx(db), **kwargs)
    if isinstance(result, PlotResult):
        return ["plot"], [(line,) for line in result.lines]
    return result.columns, result.rows


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestRollingAvg:
    def test_single_point_window_includes_only_itself(self):
        data = [("2025-01-01", 185.0, None)]
        result = _rolling_avg(data, 7)
        assert result == [("2025-01-01", 185.0)]

    def test_window_excludes_points_before_cutoff(self):
        # 3-day window: Jan 08 should only see Jan 06, 07, 08
        data = [
            ("2025-01-01", 100.0, None),
            ("2025-01-06", 180.0, None),
            ("2025-01-08", 200.0, None),
        ]
        result = _rolling_avg(data, window_days=3)
        # For Jan 08: cutoff = Jan 06, so Jan 06 and Jan 08 are included → avg=190
        assert result[2] == ("2025-01-08", 190.0)

    def test_window_includes_all_when_close_together(self):
        data = [
            ("2025-01-01", 180.0, None),
            ("2025-01-03", 184.0, None),
            ("2025-01-05", 182.0, None),
        ]
        result = _rolling_avg(data, window_days=7)
        # All three fall within 7 days of Jan 05
        avg_last = (180.0 + 184.0 + 182.0) / 3
        assert abs(result[2][1] - avg_last) < 1e-9

    def test_window_is_count_of_days_not_measurements(self):
        # 2-day window: only the day-of and one prior day
        data = [
            ("2025-01-01", 100.0, None),
            ("2025-01-02", 200.0, None),
            ("2025-01-03", 300.0, None),
        ]
        result = _rolling_avg(data, window_days=2)
        # Jan 03 window [Jan 02, Jan 03]: avg of 200 and 300 = 250
        assert result[2] == ("2025-01-03", 250.0)

    def test_scale_ignored_in_average(self):
        data = [
            ("2025-01-01", 180.0, None),
            ("2025-01-02", 182.0, "home scale"),
        ]
        result = _rolling_avg(data, window_days=7)
        assert abs(result[1][1] - 181.0) < 1e-9


class TestLinearTrend:
    def test_returns_none_for_single_point(self):
        assert _linear_trend([("2025-01-01", 185.0)]) is None

    def test_returns_none_for_empty(self):
        assert _linear_trend([]) is None

    def test_flat_trend_is_zero(self):
        pairs = [("2025-01-01", 180.0), ("2025-01-08", 180.0)]
        assert _linear_trend(pairs) == 0.0

    def test_positive_slope(self):
        # +1 lb/day over 7 days → slope ~1.0/day → 7.0/week
        pairs = [
            ("2025-01-01", 180.0),
            ("2025-01-08", 187.0),
        ]
        slope = _linear_trend(pairs)
        assert abs(slope - 1.0) < 1e-6

    def test_negative_slope(self):
        pairs = [
            ("2025-01-01", 187.0),
            ("2025-01-08", 180.0),
        ]
        slope = _linear_trend(pairs)
        assert abs(slope - (-1.0)) < 1e-6


# ---------------------------------------------------------------------------
# Integration tests against the DB
# ---------------------------------------------------------------------------


class TestWeighInReportTable:
    def test_returns_all_rows(self, weigh_in_multi_scale_db):
        cols, rows = _run_weighin(weigh_in_multi_scale_db, output="table")
        assert len(rows) == 8

    def test_columns(self, weigh_in_multi_scale_db):
        cols, rows = _run_weighin(weigh_in_multi_scale_db, output="table")
        assert cols == ["date", "weight (lb)", "scale"]

    def test_unit_conversion(self, log_with_weigh_ins_file, tmp_path):
        """Weigh-in stored as kg should convert to lb correctly."""
        from ox.cli import parse_file
        from ox.db import create_db

        log = parse_file(log_with_weigh_ins_file)
        conn = create_db(log)
        cols, rows = _run_weighin(conn, unit="lb", output="table")
        # 84kg in lb ≈ 185.19
        kg_row = next(r for r in rows if r[2] == "gym scale")
        assert abs(kg_row[1] - 185.19) < 0.1
        conn.close()

    def test_empty_db_returns_empty_rows(self, simple_db):
        cols, rows = _run_weighin(simple_db, output="table")
        assert rows == []

    def test_scale_none_shown_as_empty_string(self, weigh_in_multi_scale_db):
        cols, rows = _run_weighin(weigh_in_multi_scale_db, output="table")
        no_scale_rows = [r for r in rows if r[2] == ""]
        assert len(no_scale_rows) > 0

    def test_invalid_output_raises(self, weigh_in_multi_scale_db):
        with pytest.raises(ValueError, match="output must be"):
            _run_weighin(weigh_in_multi_scale_db, output="csv")


class TestWeighInReportPlot:
    def test_returns_plot_lines(self, weigh_in_multi_scale_db):
        cols, rows = _run_weighin(weigh_in_multi_scale_db, output="plot")
        assert cols == ["plot"]
        assert len(rows) > 0

    def test_legend_shows_both_scales(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="plot")
        text = "\n".join(r[0] for r in rows)
        assert "home scale" in text
        assert "(no scale)" in text

    def test_rolling_avg_hidden_by_default(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="plot")
        text = "\n".join(r[0] for r in rows)
        assert "rolling avg" not in text

    def test_rolling_avg_shown_when_window_set(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="plot", window=7)
        text = "\n".join(r[0] for r in rows)
        assert "7-day rolling avg" in text

    def test_custom_window_in_legend(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="plot", window=14)
        text = "\n".join(r[0] for r in rows)
        assert "14-day rolling avg" in text

    def test_both_scale_series_labeled(self, weigh_in_multi_scale_db):
        """Two scales must each appear as labeled series in the legend."""
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="plot")
        text = "\n".join(r[0] for r in rows)
        assert "home scale" in text
        assert "(no scale)" in text

    def test_not_enough_data_message(self, tmp_path):
        """Single weigh-in produces a 'Not enough data' message."""
        from ox.cli import parse_file
        from ox.db import create_db

        f = tmp_path / "single.ox"
        f.write_text("2025-01-01 W 185lb\n")
        conn = create_db(parse_file(f))
        _cols, rows = _run_weighin(conn, output="plot")
        assert "Not enough data" in rows[0][0]
        conn.close()

    def test_no_data_message(self, simple_db):
        """No weigh-ins at all returns a message row."""
        _cols, rows = _run_weighin(simple_db, output="plot")
        assert len(rows) == 1
        assert "No weigh-in data" in rows[0][0]


class TestWeighInReportStats:
    def test_columns(self, weigh_in_multi_scale_db):
        cols, _rows = _run_weighin(weigh_in_multi_scale_db, output="stats")
        assert cols[0] == "scale"
        assert "count" in cols
        assert any("min" in c for c in cols)
        assert any("max" in c for c in cols)
        assert any("avg" in c for c in cols)
        assert any("trend" in c for c in cols)

    def test_one_row_per_scale_plus_all(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="stats")
        labels = [r[0] for r in rows]
        assert "(no scale)" in labels
        assert "home scale" in labels
        assert "(all)" in labels

    def test_no_all_row_for_single_scale(self, log_with_weigh_ins_file, tmp_path):
        """When all entries share one scale (or all are None), no (all) row."""
        from ox.cli import parse_file
        from ox.db import create_db

        content = "2025-01-01 W 185lb\n2025-01-02 W 184lb\n"
        f = tmp_path / "single.ox"
        f.write_text(content)
        log = parse_file(f)
        conn = create_db(log)
        _cols, rows = _run_weighin(conn, output="stats")
        labels = [r[0] for r in rows]
        assert "(all)" not in labels
        conn.close()

    def test_count_matches_measurements(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="stats")
        row_map = {r[0]: r for r in rows}
        # 4 entries with no scale, 4 with "home scale"
        assert row_map["(no scale)"][1] == 4
        assert row_map["home scale"][1] == 4
        assert row_map["(all)"][1] == 8

    def test_min_lte_max(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="stats")
        for row in rows:
            mn, mx = row[3], row[4]
            assert mn <= mx

    def test_trend_is_numeric_or_none(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, output="stats")
        for row in rows:
            trend = row[6]
            assert trend is None or isinstance(trend, float)

    def test_unit_conversion_in_stats(self, weigh_in_multi_scale_db):
        _cols_lb, rows_lb = _run_weighin(
            weigh_in_multi_scale_db, unit="lb", output="stats"
        )
        _cols_kg, rows_kg = _run_weighin(
            weigh_in_multi_scale_db, unit="kg", output="stats"
        )
        # avg in lb should be ~2.205× avg in kg
        avg_lb = next(r[5] for r in rows_lb if r[0] == "(all)")
        avg_kg = next(r[5] for r in rows_kg if r[0] == "(all)")
        assert abs(avg_lb / avg_kg - 2.20462) < 0.01


class TestWeighInPluginRegistration:
    def test_weighin_registered(self):
        from ox.plugins import load_plugins, PLUGINS

        load_plugins()
        assert "weighin" in PLUGINS

    def test_weighin_has_expected_params(self):
        from ox.plugins import load_plugins, PLUGINS

        load_plugins()
        params = {p["name"] for p in PLUGINS["weighin"]["params"]}
        assert params == {"unit", "output", "window", "since", "until"}


class TestTimeWindow:
    """AC 9. In the window 2025-01-05..08: 01-05 184.0 (no scale), 01-06 184.6
    (home), 01-08 183.5 (no scale)."""

    WINDOW = {"since": "2025-01-05", "until": "2025-01-08"}

    def test_table_keeps_only_window_rows(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(weigh_in_multi_scale_db, **self.WINDOW)
        assert rows == [
            ("2025-01-05", 184.0, ""),
            ("2025-01-06", 184.6, "home scale"),
            ("2025-01-08", 183.5, ""),
        ]

    def test_stats_cover_only_the_window(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(
            weigh_in_multi_scale_db, output="stats", **self.WINDOW
        )
        by_label = {r[0]: r for r in rows}
        assert by_label["(no scale)"][1:3] == (2, 183.5)
        assert by_label["home scale"][1:3] == (1, 184.6)
        # (184.0 + 184.6 + 183.5) / 3 = 184.03
        assert by_label["(all)"][1:6] == (3, 183.5, 183.5, 184.6, 184.03)

    def test_rolling_avg_uses_days_before_start(self, weigh_in_multi_scale_db):
        """7-day average on 01-05: all data gives (185.0 + 184.5 + 184.8 +
        185.2 + 184.0) / 5 = 184.7; the window's data alone gives 184.0."""
        from ox.sql_utils import time_window

        rows = weigh_in_multi_scale_db.execute(
            "SELECT date, weight_magnitude, scale FROM weigh_ins ORDER BY date"
        ).fetchall()
        span = time_window(**self.WINDOW)
        shown = [r for r in rows if span.contains(r[0])]
        windowed = _windowed_rolling_avg(rows, 7, span)
        assert [d for d, _ in windowed] == [r[0] for r in shown]
        assert windowed[0][1] == pytest.approx(184.7)
        assert dict(_rolling_avg(rows, 7))["2025-01-05"] == windowed[0][1]
        assert _rolling_avg(shown, 7)[0][1] == pytest.approx(184.0)

    def test_plot_uses_window(self, weigh_in_multi_scale_db, monkeypatch):
        from ox import plot

        calls = []
        monkeypatch.setattr(plot, "multi_series", lambda s, **kw: calls.append(s))
        weigh_in_report(
            _ctx(weigh_in_multi_scale_db), output="plot", window=7, **self.WINDOW
        )
        *points, line = calls[0]
        assert sorted(d for s in points for d in s.dates) == [
            "2025-01-05",
            "2025-01-06",
            "2025-01-08",
        ]
        assert line.values[0] == pytest.approx(184.7)

    def test_one_weigh_in_is_not_enough_to_plot(self, weigh_in_multi_scale_db):
        _cols, rows = _run_weighin(
            weigh_in_multi_scale_db, output="plot", since="2025-01-09"
        )
        assert rows == [("Not enough data to plot.",)]

    @pytest.mark.parametrize(
        "output, expected",
        [
            ("plot", [("No weigh-in data found.",)]),
            ("table", []),
            ("stats", []),
        ],
    )
    def test_empty_window(self, weigh_in_multi_scale_db, output, expected):
        _cols, rows = _run_weighin(
            weigh_in_multi_scale_db, output=output, since="2025-02-01"
        )
        assert rows == expected

    def test_flags_parse(self, weigh_in_multi_scale_db, capsys):
        """AC 10 for weighin: -u is still --unit and -w still --window."""
        from ox.cli import run_plugin
        from ox.plugins import PLUGINS, load_plugins
        from ox.sql_utils import parse_plugin_args

        load_plugins()
        params = PLUGINS["weighin"]["params"]
        for args in ("-s 8w", "--since 8w"):
            assert parse_plugin_args(params, args)["since"] == "8w"
        parsed = parse_plugin_args(params, "--until 2025-12-31 -u kg -w 7")
        assert (parsed["until"], parsed["unit"], parsed["window"]) == (
            "2025-12-31",
            "kg",
            7,
        )
        run_plugin(_ctx(weigh_in_multi_scale_db), "weighin", "--since 8x")
        assert "--since: '8x' isn't a window." in capsys.readouterr().out

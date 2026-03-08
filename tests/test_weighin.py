"""Tests for the weighin builtin report plugin."""

import pytest

from ox.builtins.weighin import _rolling_avg, _linear_trend, weigh_in_report


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
        cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="table")
        assert len(rows) == 8

    def test_columns(self, weigh_in_multi_scale_db):
        cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="table")
        assert cols == ["date", "weight (lb)", "scale"]

    def test_unit_conversion(self, log_with_weigh_ins_file, tmp_path):
        """Weigh-in stored as kg should convert to lb correctly."""
        from ox.cli import parse_file
        from ox.db import create_db

        log = parse_file(log_with_weigh_ins_file)
        conn = create_db(log)
        cols, rows = weigh_in_report(conn, unit="lb", output="table")
        # 84kg in lb ≈ 185.19
        kg_row = next(r for r in rows if r[2] == "gym scale")
        assert abs(kg_row[1] - 185.19) < 0.1
        conn.close()

    def test_empty_db_returns_empty_rows(self, simple_db):
        cols, rows = weigh_in_report(simple_db, output="table")
        assert rows == []

    def test_scale_none_shown_as_empty_string(self, weigh_in_multi_scale_db):
        cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="table")
        no_scale_rows = [r for r in rows if r[2] == ""]
        assert len(no_scale_rows) > 0

    def test_invalid_output_raises(self, weigh_in_multi_scale_db):
        with pytest.raises(ValueError, match="output must be"):
            weigh_in_report(weigh_in_multi_scale_db, output="csv")


class TestWeighInReportPlot:
    def test_returns_plot_lines(self, weigh_in_multi_scale_db):
        cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="plot")
        assert cols == ["plot"]
        assert len(rows) > 0

    def test_legend_shows_both_scales(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="plot")
        text = "\n".join(r[0] for r in rows)
        assert "home scale" in text
        assert "(no scale)" in text

    def test_legend_shows_rolling_avg(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="plot")
        text = "\n".join(r[0] for r in rows)
        assert "rolling avg" in text

    def test_custom_window_in_legend(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="plot", window=14)
        text = "\n".join(r[0] for r in rows)
        assert "14-day rolling avg" in text

    def test_two_different_markers_used(self, weigh_in_multi_scale_db):
        """Two scales must produce two distinct markers in the legend."""
        from ox.builtins.weighin import _MARKERS

        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="plot")
        text = "\n".join(r[0] for r in rows)
        markers_found = [m for m in _MARKERS if m in text]
        assert len(markers_found) >= 2

    def test_not_enough_data_message(self, tmp_path):
        """Single weigh-in produces a 'Not enough data' message."""
        from ox.cli import parse_file
        from ox.db import create_db

        f = tmp_path / "single.ox"
        f.write_text("2025-01-01 W 185lb\n")
        conn = create_db(parse_file(f))
        _cols, rows = weigh_in_report(conn, output="plot")
        assert "Not enough data" in rows[0][0]
        conn.close()

    def test_no_data_message(self, simple_db):
        """No weigh-ins at all returns a message row."""
        _cols, rows = weigh_in_report(simple_db, output="plot")
        assert len(rows) == 1
        assert "No weigh-in data" in rows[0][0]


class TestWeighInReportStats:
    def test_columns(self, weigh_in_multi_scale_db):
        cols, _rows = weigh_in_report(weigh_in_multi_scale_db, output="stats")
        assert cols[0] == "scale"
        assert "count" in cols
        assert any("min" in c for c in cols)
        assert any("max" in c for c in cols)
        assert any("avg" in c for c in cols)
        assert any("trend" in c for c in cols)

    def test_one_row_per_scale_plus_all(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="stats")
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
        _cols, rows = weigh_in_report(conn, output="stats")
        labels = [r[0] for r in rows]
        assert "(all)" not in labels
        conn.close()

    def test_count_matches_measurements(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="stats")
        row_map = {r[0]: r for r in rows}
        # 4 entries with no scale, 4 with "home scale"
        assert row_map["(no scale)"][1] == 4
        assert row_map["home scale"][1] == 4
        assert row_map["(all)"][1] == 8

    def test_min_lte_max(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="stats")
        for row in rows:
            mn, mx = row[3], row[4]
            assert mn <= mx

    def test_trend_is_numeric_or_none(self, weigh_in_multi_scale_db):
        _cols, rows = weigh_in_report(weigh_in_multi_scale_db, output="stats")
        for row in rows:
            trend = row[6]
            assert trend is None or isinstance(trend, float)

    def test_unit_conversion_in_stats(self, weigh_in_multi_scale_db):
        _cols_lb, rows_lb = weigh_in_report(
            weigh_in_multi_scale_db, unit="lb", output="stats"
        )
        _cols_kg, rows_kg = weigh_in_report(
            weigh_in_multi_scale_db, unit="kg", output="stats"
        )
        # avg in lb should be ~2.205× avg in kg
        avg_lb = next(r[5] for r in rows_lb if r[0] == "(all)")
        avg_kg = next(r[5] for r in rows_kg if r[0] == "(all)")
        assert abs(avg_lb / avg_kg - 2.20462) < 0.01


class TestWeighInPluginRegistration:
    def test_weighin_registered(self):
        from ox.plugins import load_plugins, REPORT_PLUGINS

        load_plugins()
        assert "weighin" in REPORT_PLUGINS

    def test_weighin_has_expected_params(self):
        from ox.plugins import load_plugins, REPORT_PLUGINS

        load_plugins()
        params = {p["name"] for p in REPORT_PLUGINS["weighin"]["params"]}
        assert params == {"unit", "output", "window"}

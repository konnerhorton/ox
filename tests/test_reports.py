"""Tests for SQL utilities and builtin plugins."""

import pytest

from ox.data import TrainingLog
from ox.plugins import PLUGINS, PluginContext, TableResult, load_plugins
from ox.sql_utils import _time_bin_expr, parse_plugin_args, plugin_usage
from ox.builtins.volume import volume


class TestTimeBins:
    """Test time bin expression helper."""

    def test_daily(self):
        assert _time_bin_expr("daily") == "strftime('%Y-%m-%d', date)"

    def test_weekly(self):
        assert (
            _time_bin_expr("weekly")
            == "date(date, '-' || strftime('%w', date) || ' days')"
        )

    def test_weekly_num(self):
        assert _time_bin_expr("weekly-num") == "strftime('%Y-W%W', date)"

    def test_monthly(self):
        assert _time_bin_expr("monthly") == "strftime('%Y-%m', date)"

    def test_custom_col(self):
        assert _time_bin_expr("daily", "s.date") == "strftime('%Y-%m-%d', s.date)"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown time bin"):
            _time_bin_expr("yearly")


class TestVolumeOverTime:
    """Test the volume plugin."""

    def _run(self, db, log=None, **kwargs):
        if log is None:
            log = TrainingLog(sessions=())
        ctx = PluginContext(db=db, log=log)
        result = volume(ctx, **kwargs)
        assert isinstance(result, TableResult)
        return result.columns, result.rows

    def test_columns(self, example_db):
        columns, _ = self._run(example_db, movement="squat")
        assert columns == [
            "period",
            "total_volume (lb)",
            "total_reps",
            "avg_weight_per_rep (lb)",
        ]

    def test_weekly_grouping(self, example_db):
        _, rows = self._run(example_db, movement="squat", bin="weekly")
        # squat appears in many weeks in example.ox
        assert len(rows) > 1
        # Each row's period should be a date string (Sunday of that week)
        for row in rows:
            assert row[0].startswith("2024-")
            assert len(row[0]) == 10  # "2024-01-14"

    def test_weekly_period_is_sunday(self, example_db):
        """Weekly bin periods should fall on a Sunday."""
        import datetime

        _, rows = self._run(example_db, movement="squat", bin="weekly")
        for row in rows:
            dt = datetime.date.fromisoformat(row[0])
            assert dt.weekday() == 6, f"{row[0]} is not a Sunday"

    def test_weekly_num_grouping(self, example_db):
        _, rows = self._run(example_db, movement="squat", bin="weekly-num")
        assert len(rows) > 1
        for row in rows:
            assert row[0].startswith("2024-W")

    def test_monthly_grouping(self, example_db):
        _, rows = self._run(example_db, movement="squat", bin="monthly")
        assert len(rows) > 1
        for row in rows:
            assert row[0].startswith("2024-")
            assert len(row[0]) == 7  # "2024-01"

    def test_daily_grouping(self, example_db):
        _, rows = self._run(example_db, movement="squat", bin="daily")
        for row in rows:
            assert len(row[0]) == 10  # "2024-01-15"

    def test_single_movement_filter(self, example_db):
        _, rows = self._run(example_db, movement="squat")
        # All rows should have non-None volume (squat always has weight)
        for row in rows:
            assert row[1] is not None  # total_volume
            assert row[2] > 0  # total_reps

    def test_bodyweight_movement(self, example_db):
        """Bodyweight movements have NULL volume since weight_magnitude is NULL."""
        _, rows = self._run(example_db, movement="pullup")
        # Some pullup sets are bodyweight (NULL magnitude), so volume may be None
        assert len(rows) > 0

    def test_nonexistent_movement(self, example_db):
        _, rows = self._run(example_db, movement="nonexistent-exercise")
        assert rows == []

    def test_volume_values(self, simple_db):
        """Verify volume calculation against known data.

        simple_log has bench-press: 135lbs 5x5 on 2025-01-11.
        Total volume = 135 * 25 = 3375.
        """
        _, rows = self._run(simple_db, movement="bench-press", bin="daily")
        assert len(rows) == 1
        assert rows[0][0] == "2025-01-11"
        assert rows[0][1] == 3375.0  # total_volume
        assert rows[0][2] == 25  # total_reps
        assert rows[0][3] == 135.0  # avg_weight_per_rep


class TestParsePluginArgs:
    """Test the argument parser."""

    def test_basic_flags(self):
        params = [
            {"name": "movement", "type": str, "required": True},
            {"name": "bin", "type": str, "default": "weekly", "required": False},
        ]
        result = parse_plugin_args(params, "--movement kb-swing --bin monthly")
        assert result == {"movement": "kb-swing", "bin": "monthly"}

    def test_default_applied(self):
        params = [
            {"name": "bin", "type": str, "default": "weekly", "required": False},
        ]
        result = parse_plugin_args(params, "")
        assert result == {"bin": "weekly"}

    def test_missing_required_raises(self):
        params = [
            {"name": "movement", "type": str, "required": True},
        ]
        with pytest.raises(ValueError, match="Missing required"):
            parse_plugin_args(params, "")

    def test_unknown_flag_raises(self):
        params = [
            {"name": "movement", "type": str, "required": True},
        ]
        with pytest.raises(ValueError, match="Unknown flag"):
            parse_plugin_args(params, "--foo bar")

    def test_flag_without_value_raises(self):
        params = [
            {"name": "movement", "type": str, "required": True},
        ]
        with pytest.raises(ValueError, match="requires a value"):
            parse_plugin_args(params, "--movement")

    def test_unexpected_positional_raises(self):
        params = [
            {"name": "movement", "type": str, "required": True},
        ]
        with pytest.raises(ValueError, match="Unexpected argument"):
            parse_plugin_args(params, "kb-swing")

    def test_quoted_value(self):
        params = [
            {"name": "movement", "type": str, "required": True},
        ]
        result = parse_plugin_args(params, '--movement "kb-swing"')
        assert result == {"movement": "kb-swing"}

    def test_short_flag(self):
        params = [
            {"name": "movement", "type": str, "required": True, "short": "m"},
        ]
        result = parse_plugin_args(params, "-m kb-swing")
        assert result == {"movement": "kb-swing"}

    def test_mixed_short_and_long(self):
        params = [
            {"name": "movement", "type": str, "required": True, "short": "m"},
            {
                "name": "bin",
                "type": str,
                "default": "weekly",
                "required": False,
                "short": "b",
            },
        ]
        result = parse_plugin_args(params, "-m kb-swing --bin monthly")
        assert result == {"movement": "kb-swing", "bin": "monthly"}

    def test_unknown_short_flag_raises(self):
        params = [
            {"name": "movement", "type": str, "required": True, "short": "m"},
        ]
        with pytest.raises(ValueError, match="Unknown flag: -x"):
            parse_plugin_args(params, "-x foo")

    def test_short_flag_without_value_raises(self):
        params = [
            {"name": "movement", "type": str, "required": True, "short": "m"},
        ]
        with pytest.raises(ValueError, match="-m requires a value"):
            parse_plugin_args(params, "-m")


class TestPluginUsage:
    """Test usage string generation."""

    def test_volume_usage(self):
        load_plugins()
        usage = plugin_usage("volume", PLUGINS["volume"])
        assert "--movement" in usage
        assert "--bin" in usage
        assert usage.startswith("volume ")
        assert "run " not in usage

    def test_required_not_bracketed(self):
        load_plugins()
        usage = plugin_usage("volume", PLUGINS["volume"])
        # Required params should not be in brackets
        assert "[--movement" not in usage

    def test_optional_bracketed(self):
        load_plugins()
        usage = plugin_usage("volume", PLUGINS["volume"])
        # Optional params should be in brackets
        assert "[-b/--bin" in usage

    def test_short_flags_shown(self):
        load_plugins()
        usage = plugin_usage("volume", PLUGINS["volume"])
        assert "-m/--movement" in usage
        assert "-b/--bin" in usage


class TestRegistry:
    """Test that built-in plugins are well-formed."""

    def test_all_builtins_registered(self):
        load_plugins()
        for name in ("volume", "e1rm", "weighin", "wendler531"):
            assert name in PLUGINS, f"Builtin '{name}' not registered"

    def test_all_plugins_have_fn(self):
        load_plugins()
        for name, entry in PLUGINS.items():
            assert "fn" in entry, f"Plugin '{name}' missing 'fn'"
            assert callable(entry["fn"])

    def test_all_plugins_have_description(self):
        load_plugins()
        for name, entry in PLUGINS.items():
            assert "description" in entry, f"Plugin '{name}' missing 'description'"

    def test_all_plugins_have_params(self):
        load_plugins()
        for name, entry in PLUGINS.items():
            assert "params" in entry, f"Plugin '{name}' missing 'params'"
            assert isinstance(entry["params"], list)

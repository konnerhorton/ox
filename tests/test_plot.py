"""Tests for the plot facade (src/ox/plot.py)."""

from ox import plot


def _text(lines):
    return "\n".join(lines)


# --- scatter ---


class TestScatter:
    def test_empty_returns_sentinel(self):
        assert plot.scatter([], [], y_label="x") == ["Not enough data to plot."]

    def test_single_point_returns_sentinel(self):
        result = plot.scatter(["2025-01-01"], [10.0], y_label="x")
        assert result == ["Not enough data to plot."]

    def test_y_label_in_output(self):
        lines = plot.scatter(
            ["2025-01-01", "2025-02-01", "2025-03-01"],
            [100.0, 110.0, 120.0],
            y_label="e1rm (lb)",
        )
        assert "e1rm (lb)" in _text(lines)

    def test_first_and_last_dates_represented(self):
        """First and last dates should appear somewhere on axis — guards #49 clipping."""
        lines = plot.scatter(
            ["2025-01-15", "2025-02-15", "2025-03-15"],
            [100.0, 110.0, 120.0],
            y_label="v",
        )
        text = _text(lines)
        # mm-dd of first OR last should appear
        assert "01-15" in text or "03-15" in text

    def test_returns_nonempty_rows(self):
        lines = plot.scatter(["2025-01-01", "2025-02-01"], [50.0, 60.0], y_label="v")
        assert len(lines) > 3


# --- multi_series ---


class TestMultiSeries:
    def test_empty_series_returns_sentinel(self):
        assert plot.multi_series([], y_label="v") == ["Not enough data to plot."]

    def test_all_empty_series_returns_sentinel(self):
        series = [plot.Series(label="a", dates=[], values=[])]
        assert plot.multi_series(series, y_label="v") == ["Not enough data to plot."]

    def test_single_point_across_all_series_returns_sentinel(self):
        series = [plot.Series(label="a", dates=["2025-01-01"], values=[10.0])]
        assert plot.multi_series(series, y_label="v") == ["Not enough data to plot."]

    def test_labels_appear_in_output(self):
        series = [
            plot.Series(
                label="home",
                dates=["2025-01-01", "2025-02-01"],
                values=[180.0, 181.0],
            ),
            plot.Series(
                label="rolling",
                dates=["2025-01-01", "2025-02-01"],
                values=[180.5, 180.8],
                style="line",
            ),
        ]
        text = _text(plot.multi_series(series, y_label="weight (lb)"))
        assert "home" in text
        assert "rolling" in text
        assert "weight (lb)" in text

    def test_mixed_series_lengths_ok(self):
        series = [
            plot.Series(
                label="a", dates=["2025-01-01", "2025-01-15"], values=[1.0, 2.0]
            ),
            plot.Series(label="b", dates=["2025-01-10"], values=[1.5], style="line"),
        ]
        lines = plot.multi_series(series, y_label="v")
        assert len(lines) > 3


# --- bar ---


class TestBar:
    def test_empty_returns_sentinel(self):
        assert plot.bar([], [], y_label="v") == ["Not enough data to plot."]

    def test_single_bar_returns_sentinel(self):
        assert plot.bar(["a"], [1.0], y_label="v") == ["Not enough data to plot."]

    def test_y_label_in_output(self):
        lines = plot.bar(
            ["2025-W01", "2025-W02", "2025-W03"],
            [100.0, 200.0, 150.0],
            y_label="total AU (weekly)",
        )
        assert "total AU (weekly)" in _text(lines)

    def test_returns_nonempty_rows(self):
        lines = plot.bar(["a", "b", "c"], [1.0, 2.0, 3.0], y_label="v")
        assert len(lines) > 3

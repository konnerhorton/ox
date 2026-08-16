"""Tests for ISO 8601 duration parsing and formatting.

Testing philosophy:
- Cover every form the grammar's `duration` token can emit
- Pin round-trip stability, since these back to_ox() serialization
"""

import pytest
from datetime import timedelta

from ox.duration import parse_iso_duration, format_iso_duration


class TestParseIsoDuration:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("PT30M", timedelta(minutes=30)),
            ("PT45S", timedelta(seconds=45)),
            ("PT1H", timedelta(hours=1)),
            ("PT1H30M", timedelta(hours=1, minutes=30)),
            ("PT30M15S", timedelta(minutes=30, seconds=15)),
            ("PT1H30M15S", timedelta(hours=1, minutes=30, seconds=15)),
            ("PT30M15.5S", timedelta(minutes=30, seconds=15.5)),
            ("PT0S", timedelta(0)),
        ],
    )
    def test_valid(self, text, expected):
        assert parse_iso_duration(text) == expected

    def test_lowercase_accepted(self):
        assert parse_iso_duration("pt30m") == timedelta(minutes=30)

    def test_surrounding_whitespace_stripped(self):
        assert parse_iso_duration("  PT30M  ") == timedelta(minutes=30)

    @pytest.mark.parametrize(
        "text",
        [
            "PT",  # no components
            "30M",  # missing PT prefix
            "P1D",  # date component, not supported
            "PT30X",  # unknown unit
            "",
            "abc",
        ],
    )
    def test_invalid_raises(self, text):
        with pytest.raises(ValueError, match="Invalid ISO 8601 duration"):
            parse_iso_duration(text)


class TestFormatIsoDuration:
    @pytest.mark.parametrize(
        "td,expected",
        [
            (timedelta(minutes=30), "PT30M"),
            (timedelta(seconds=45), "PT45S"),
            (timedelta(hours=1), "PT1H"),
            (timedelta(hours=1, minutes=30), "PT1H30M"),
            (timedelta(minutes=1, seconds=30), "PT1M30S"),
            (timedelta(hours=1, minutes=30, seconds=15), "PT1H30M15S"),
            (timedelta(0), "PT0S"),
        ],
    )
    def test_valid(self, td, expected):
        assert format_iso_duration(td) == expected

    def test_seconds_overflow_into_minutes(self):
        """90 seconds is canonicalized, not emitted as PT90S."""
        assert format_iso_duration(timedelta(seconds=90)) == "PT1M30S"

    def test_fractional_seconds_preserved(self):
        assert format_iso_duration(timedelta(seconds=15.5)) == "PT15.5S"

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="negative duration"):
            format_iso_duration(timedelta(seconds=-1))


class TestRoundTrip:
    @pytest.mark.parametrize(
        "text",
        ["PT30M", "PT45S", "PT1H", "PT1H30M", "PT30M15S", "PT1H30M15S", "PT0S"],
    )
    def test_parse_format_round_trip(self, text):
        assert format_iso_duration(parse_iso_duration(text)) == text

    @pytest.mark.parametrize(
        "td",
        [
            timedelta(minutes=30),
            timedelta(hours=2, minutes=5, seconds=3),
            timedelta(seconds=1),
            timedelta(0),
        ],
    )
    def test_format_parse_round_trip(self, td):
        assert parse_iso_duration(format_iso_duration(td)) == td

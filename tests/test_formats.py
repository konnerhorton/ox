"""Tests for the session `format:` vocabulary (ox.formats) and the formats plugin."""

from datetime import timedelta

import pytest

from ox.formats import check_movement_count, parse_format


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

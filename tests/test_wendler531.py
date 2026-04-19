"""Tests for the Wendler 5/3/1 plugin."""

from datetime import date

import pytest

from ox.builtins.wendler531 import (
    WEEK_SCHEMES,
    _parse_movements,
    _pint_unit,
    _round_weight,
    register,
    wendler531,
)
from ox.plugins import PluginContext, TextResult


# --- _round_weight ---


@pytest.mark.parametrize(
    "weight, unit, expected",
    [
        (204.75, "lb", 205),
        (203.0, "lb", 205),
        (207.4, "lb", 205),
        (100.1, "kg", 100.0),
        (103.74, "kg", 102.5),
        (104.0, "kg", 105.0),
    ],
)
def test_round_weight(weight, unit, expected):
    assert _round_weight(weight, unit) == expected


# --- _parse_movements ---


def test_parse_movements_single():
    assert _parse_movements("squat:315") == [("squat", 315.0)]


def test_parse_movements_multi():
    assert _parse_movements("squat:315,bench-press:200") == [
        ("squat", 315.0),
        ("bench-press", 200.0),
    ]


def test_parse_movements_strips_whitespace():
    assert _parse_movements(" squat : 315 , deadlift : 405 ") == [
        ("squat", 315.0),
        ("deadlift", 405.0),
    ]


def test_parse_movements_invalid_format():
    with pytest.raises(ValueError, match="Invalid movement format"):
        _parse_movements("squat315")


# --- _pint_unit ---


@pytest.mark.parametrize(
    "short, full",
    [("lb", "pound"), ("lbs", "pound"), ("kg", "kilogram"), ("stone", "stone")],
)
def test_pint_unit(short, full):
    assert _pint_unit(short) == full


# --- Cycle generation ---


def _ctx():
    return PluginContext(db=None, log=None)


def test_wendler531_returns_text_result():
    result = wendler531(_ctx(), movements="squat:300", start_date="2026-01-05")
    assert isinstance(result, TextResult)


def test_wendler531_week_dates():
    result = wendler531(_ctx(), movements="squat:300", start_date="2026-01-05")
    text = result.text
    assert "2026-01-05" in text
    assert "2026-01-12" in text
    assert "2026-01-19" in text
    assert "2026-01-26" in text


def test_wendler531_has_four_weeks():
    result = wendler531(_ctx(), movements="squat:300", start_date="2026-01-05")
    for week in ("5/3/1 Week 1", "5/3/1 Week 2", "5/3/1 Week 3", "5/3/1 Week 4"):
        assert week in result.text


def test_wendler531_all_sessions_planned():
    result = wendler531(_ctx(), movements="squat:300", start_date="2026-01-05")
    assert result.text.count(" ! ") >= 4


def test_wendler531_week1_weights_lb():
    # 300 * 0.65=195, 0.75=225, 0.85=255 (already round 5)
    result = wendler531(_ctx(), movements="squat:300", start_date="2026-01-05")
    text = result.text.split("5/3/1 Week 2")[0]
    assert "195lb" in text.replace("pound", "lb") or "195 pound" in text
    assert "225" in text
    assert "255" in text


def test_wendler531_deload_weights():
    # Week 4: 40/50/60%
    result = wendler531(_ctx(), movements="squat:300", start_date="2026-01-05")
    week4 = result.text.split("5/3/1 Week 4")[1]
    # 300 * 0.4=120, 0.5=150, 0.6=180
    assert "120" in week4
    assert "150" in week4
    assert "180" in week4


def test_wendler531_kg_rounding():
    # 100kg * 0.65 = 65.0kg (exact), * 0.75 = 75kg, * 0.85 = 85kg
    result = wendler531(
        _ctx(), movements="squat:100", unit="kg", start_date="2026-01-05"
    )
    text = result.text
    assert "kg" in text or "kilogram" in text


def test_wendler531_multiple_movements():
    result = wendler531(
        _ctx(), movements="squat:300,bench-press:200", start_date="2026-01-05"
    )
    assert "squat" in result.text
    assert "bench-press" in result.text


def test_wendler531_rm_tag_on_weeks_1_to_3():
    result = wendler531(
        _ctx(), movements="squat:300", start_date="2026-01-05", rm="true"
    )
    parts = result.text.split("5/3/1 Week ")
    # parts[1]=week1..., parts[4]=week4
    assert "^rm" in parts[1]
    assert "^rm" in parts[2]
    assert "^rm" in parts[3]
    assert "^rm" not in parts[4]


def test_wendler531_rm_disabled():
    result = wendler531(
        _ctx(), movements="squat:300", start_date="2026-01-05", rm="false"
    )
    assert "^rm" not in result.text


def test_wendler531_default_date_is_today():
    # Should not raise; uses datetime.now().date()
    result = wendler531(_ctx(), movements="squat:300")
    today = date.today().isoformat()
    assert today in result.text


def test_wendler531_invalid_date_raises():
    with pytest.raises(ValueError):
        wendler531(_ctx(), movements="squat:300", start_date="01/05/2026")


# --- Scheme correctness ---


def test_week_schemes_structure():
    for wk, sets in WEEK_SCHEMES.items():
        assert len(sets) == 3
        assert all(
            isinstance(pct, float) and isinstance(reps, int) for pct, reps in sets
        )


def test_week_schemes_percentages():
    assert [p for p, _ in WEEK_SCHEMES[1]] == [0.65, 0.75, 0.85]
    assert [p for p, _ in WEEK_SCHEMES[2]] == [0.70, 0.80, 0.90]
    assert [p for p, _ in WEEK_SCHEMES[3]] == [0.75, 0.85, 0.95]
    assert [p for p, _ in WEEK_SCHEMES[4]] == [0.40, 0.50, 0.60]


# --- Registration ---


def test_register_returns_descriptor():
    descriptors = register()
    assert len(descriptors) == 1
    desc = descriptors[0]
    assert desc["name"] == "wendler531"
    assert desc["fn"] is wendler531
    param_names = {p["name"] for p in desc["params"]}
    assert param_names == {"movements", "unit", "start_date", "rm"}


def test_register_movements_required():
    desc = register()[0]
    movements_param = next(p for p in desc["params"] if p["name"] == "movements")
    assert movements_param["required"] is True
    assert movements_param["short"] == "m"

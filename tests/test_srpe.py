"""Tests for the sRPE (Session Rate of Perceived Exertion) plugin."""

from datetime import date, timedelta

import pytest

from ox.builtins.srpe import (
    _acwr_report,
    _acwr_zone,
    _daily_au,
    _extract_srpe_data,
    _parse_iso_duration_minutes,
    _parse_srpe,
    _strain_risk,
    srpe_report,
)
from ox.cli import parse_file
from ox.db import create_db
from ox.plugins import PlotResult, PluginContext, TableResult


# --- Duration parsing ---


@pytest.mark.parametrize(
    "duration_str, expected_minutes",
    [
        ("PT30M", 30.0),
        ("PT1H", 60.0),
        ("PT1H30M", 90.0),
        ("PT50M", 50.0),
        ("PT90S", 1.5),
        ("PT1H15M30S", 75.5),
        ("PT0M", 0.0),
    ],
)
def test_parse_iso_duration(duration_str, expected_minutes):
    assert _parse_iso_duration_minutes(duration_str) == expected_minutes


def test_parse_iso_duration_invalid():
    with pytest.raises(ValueError, match="Invalid ISO 8601 duration"):
        _parse_iso_duration_minutes("30M")


# --- sRPE string parsing ---


def test_parse_srpe_semicolon():
    result = _parse_srpe("srpe: 4; PT30M")
    assert result == (4.0, 30.0, 120.0)


def test_parse_srpe_comma():
    result = _parse_srpe("srpe: 7, PT50M")
    assert result == (7.0, 50.0, 350.0)


def test_parse_srpe_no_space():
    result = _parse_srpe("srpe:4;PT30M")
    assert result == (4.0, 30.0, 120.0)


def test_parse_srpe_decimal_rating():
    result = _parse_srpe("srpe: 6.5; PT45M")
    assert result == (6.5, 45.0, 292.5)


def test_parse_srpe_no_match():
    assert _parse_srpe("just a regular note") is None
    assert _parse_srpe("rpe: 4") is None


# --- Fixtures ---


@pytest.fixture
def srpe_session_log_content():
    """Log with sRPE as session metadata (item_line in session block)."""
    return (
        "@session\n"
        "2025-03-10 * Upper EMOM\n"
        'srpe: "4; PT30M"\n'
        "bench-press: 135lb 5x5\n"
        "@end\n"
        "\n"
        "@session\n"
        "2025-03-12 * Lower EMOM\n"
        'srpe: "7; PT45M"\n'
        "squat: 185lb 3x5\n"
        "@end\n"
        "\n"
        "@session\n"
        "2025-03-17 * Upper EMOM\n"
        'srpe: "5, PT30M"\n'
        "bench-press: 145lb 5x5\n"
        "@end\n"
    )


@pytest.fixture
def srpe_note_log_content():
    """Log with sRPE embedded in a single-line entry note."""
    return (
        '2025-03-10 * run: PT50M "srpe: 4; PT50M"\n'
        '2025-03-14 * run: PT30M "srpe: 6; PT30M"\n'
    )


@pytest.fixture
def srpe_mixed_log_content():
    """Log with sRPE in both session metadata and single-line notes."""
    return (
        "@session\n"
        "2025-03-10 * Upper EMOM\n"
        'srpe: "5; PT30M"\n'
        "bench-press: 135lb 5x5\n"
        "@end\n"
        "\n"
        '2025-03-11 * run: PT40M "srpe: 3; PT40M"\n'
        "\n"
        "@session\n"
        "2025-03-17 * Upper EMOM\n"
        'srpe: "6; PT30M"\n'
        "bench-press: 145lb 5x5\n"
        "@end\n"
    )


def _make_ctx(content, tmp_path):
    f = tmp_path / "test.ox"
    f.write_text(content)
    log = parse_file(f)
    db = create_db(log)
    return PluginContext(db=db, log=log)


# --- Data extraction ---


def test_extract_srpe_from_session(srpe_session_log_content, tmp_path):
    ctx = _make_ctx(srpe_session_log_content, tmp_path)
    data = _extract_srpe_data(ctx)
    assert len(data) == 3
    # First entry: rating=4, duration=30min, AU=120
    assert data[0] == ("2025-03-10", 4.0, 30.0, 120.0)
    # Second entry: rating=7, duration=45min, AU=315
    assert data[1] == ("2025-03-12", 7.0, 45.0, 315.0)
    # Third entry: comma separator, rating=5, duration=30min, AU=150
    assert data[2] == ("2025-03-17", 5.0, 30.0, 150.0)


def test_extract_srpe_from_note(srpe_note_log_content, tmp_path):
    ctx = _make_ctx(srpe_note_log_content, tmp_path)
    data = _extract_srpe_data(ctx)
    assert len(data) == 2
    assert data[0] == ("2025-03-10", 4.0, 50.0, 200.0)
    assert data[1] == ("2025-03-14", 6.0, 30.0, 180.0)


def test_extract_srpe_mixed(srpe_mixed_log_content, tmp_path):
    ctx = _make_ctx(srpe_mixed_log_content, tmp_path)
    data = _extract_srpe_data(ctx)
    assert len(data) == 3
    dates = [d[0] for d in data]
    assert dates == ["2025-03-10", "2025-03-11", "2025-03-17"]


# --- Plugin output: table ---


def test_srpe_table_weekly(srpe_session_log_content, tmp_path):
    ctx = _make_ctx(srpe_session_log_content, tmp_path)
    result = srpe_report(ctx, bin="weekly", output="table")
    assert isinstance(result, TableResult)
    assert result.columns == ["period", "sessions", "total_AU", "avg_AU", "max_AU"]
    assert len(result.rows) >= 1
    # All three sessions should appear
    total_sessions = sum(r[1] for r in result.rows)
    assert total_sessions == 3


def test_srpe_table_monthly(srpe_session_log_content, tmp_path):
    ctx = _make_ctx(srpe_session_log_content, tmp_path)
    result = srpe_report(ctx, bin="monthly", output="table")
    assert isinstance(result, TableResult)
    # All in March 2025
    assert len(result.rows) == 1
    assert result.rows[0][0] == "2025-03"
    assert result.rows[0][1] == 3  # 3 sessions


def test_srpe_table_empty(tmp_path):
    ctx = _make_ctx("2025-01-10 * pullups: BW 5x10\n", tmp_path)
    result = srpe_report(ctx, output="table")
    assert isinstance(result, TableResult)
    assert result.rows == []


def test_srpe_table_au_values(srpe_session_log_content, tmp_path):
    ctx = _make_ctx(srpe_session_log_content, tmp_path)
    result = srpe_report(ctx, bin="monthly", output="table")
    # Monthly: 120 + 315 + 150 = 585 total AU
    row = result.rows[0]
    assert row[2] == 585.0  # total_AU


# --- Plugin output: plot ---


def test_srpe_plot(srpe_mixed_log_content, tmp_path):
    ctx = _make_ctx(srpe_mixed_log_content, tmp_path)
    result = srpe_report(ctx, bin="weekly", output="plot")
    assert isinstance(result, PlotResult)
    assert len(result.lines) > 0


def test_srpe_plot_empty(tmp_path):
    ctx = _make_ctx("2025-01-10 * pullups: BW 5x10\n", tmp_path)
    result = srpe_report(ctx, output="plot")
    assert isinstance(result, PlotResult)
    assert result.lines == ["No sRPE data found."]


def test_srpe_invalid_output(srpe_session_log_content, tmp_path):
    ctx = _make_ctx(srpe_session_log_content, tmp_path)
    with pytest.raises(ValueError, match="output must be one of"):
        srpe_report(ctx, output="stats")


# --- ACWR zone classification ---


@pytest.mark.parametrize(
    "acwr, expected",
    [
        (None, "N/A"),
        (0.5, "undertraining"),
        (0.8, "sweet spot"),
        (1.0, "sweet spot"),
        (1.3, "sweet spot"),
        (1.4, "caution"),
        (1.5, "caution"),
        (1.6, "danger"),
        (2.0, "danger"),
    ],
)
def test_acwr_zone(acwr, expected):
    assert _acwr_zone(acwr) == expected


# --- Strain risk classification ---


@pytest.mark.parametrize(
    "monotony, strain, expected",
    [
        (None, None, "N/A"),
        (1.5, 2000, "low"),
        (2.5, 3000, "moderate"),  # monotony > 2.0
        (1.5, 5000, "moderate"),  # strain > 4000
        (2.5, 7000, "HIGH"),  # both thresholds exceeded
    ],
)
def test_strain_risk(monotony, strain, expected):
    assert _strain_risk(monotony, strain) == expected


# --- Multi-week fixture for ACWR / monotony / strain ---


@pytest.fixture
def srpe_multiweek_content():
    """6 weeks of sRPE data for ACWR/monotony/strain testing."""
    lines = []
    # Week 1: Mon/Wed/Fri pattern
    for dt, rpe, dur in [
        ("2025-02-03", 5, "PT40M"),  # Mon
        ("2025-02-05", 6, "PT45M"),  # Wed
        ("2025-02-07", 4, "PT30M"),  # Fri
    ]:
        lines.append(
            f'@session\n{dt} * Training\nsrpe: "{rpe}; {dur}"\nsquat: 135lb 3x5\n@end\n'
        )
    # Week 2
    for dt, rpe, dur in [
        ("2025-02-10", 6, "PT45M"),
        ("2025-02-12", 7, "PT50M"),
        ("2025-02-14", 5, "PT35M"),
    ]:
        lines.append(
            f'@session\n{dt} * Training\nsrpe: "{rpe}; {dur}"\nsquat: 145lb 3x5\n@end\n'
        )
    # Week 3
    for dt, rpe, dur in [
        ("2025-02-17", 7, "PT50M"),
        ("2025-02-19", 7, "PT55M"),
        ("2025-02-21", 6, "PT40M"),
    ]:
        lines.append(
            f'@session\n{dt} * Training\nsrpe: "{rpe}; {dur}"\nsquat: 155lb 3x5\n@end\n'
        )
    # Week 4
    for dt, rpe, dur in [
        ("2025-02-24", 7, "PT50M"),
        ("2025-02-26", 8, "PT55M"),
        ("2025-02-28", 6, "PT40M"),
    ]:
        lines.append(
            f'@session\n{dt} * Training\nsrpe: "{rpe}; {dur}"\nsquat: 165lb 3x5\n@end\n'
        )
    # Week 5: higher intensity spike
    for dt, rpe, dur in [
        ("2025-03-03", 8, "PT60M"),
        ("2025-03-05", 9, "PT55M"),
        ("2025-03-07", 7, "PT45M"),
    ]:
        lines.append(
            f'@session\n{dt} * Training\nsrpe: "{rpe}; {dur}"\nsquat: 175lb 3x5\n@end\n'
        )
    # Week 6: deload
    for dt, rpe, dur in [
        ("2025-03-10", 3, "PT30M"),
        ("2025-03-12", 4, "PT30M"),
    ]:
        lines.append(
            f'@session\n{dt} * Training\nsrpe: "{rpe}; {dur}"\nsquat: 95lb 3x5\n@end\n'
        )
    return "\n".join(lines)


# --- ACWR report ---


def test_acwr_report(srpe_multiweek_content, tmp_path):
    ctx = _make_ctx(srpe_multiweek_content, tmp_path)
    result = srpe_report(ctx, output="acwr")
    assert isinstance(result, TableResult)
    assert result.columns == ["date", "acute_AU", "chronic_AU", "ACWR", "zone"]
    # Should have a row for each training day
    assert len(result.rows) > 0
    # All rows should have 5 elements
    for row in result.rows:
        assert len(row) == 5


def test_acwr_zones_appear(srpe_multiweek_content, tmp_path):
    ctx = _make_ctx(srpe_multiweek_content, tmp_path)
    result = srpe_report(ctx, output="acwr")
    zones = {row[4] for row in result.rows}
    # At least some zones should be classified
    assert zones.issubset({"undertraining", "sweet spot", "caution", "danger", "N/A"})


def test_acwr_empty(tmp_path):
    ctx = _make_ctx("2025-01-10 * pullups: BW 5x10\n", tmp_path)
    result = srpe_report(ctx, output="acwr")
    assert isinstance(result, TableResult)
    assert result.rows == []


# --- Monotony report ---


def test_monotony_report(srpe_multiweek_content, tmp_path):
    ctx = _make_ctx(srpe_multiweek_content, tmp_path)
    result = srpe_report(ctx, output="monotony")
    assert isinstance(result, TableResult)
    assert result.columns == [
        "week",
        "weekly_AU",
        "mean_daily_AU",
        "sd_daily_AU",
        "monotony",
    ]
    assert len(result.rows) > 0


def test_monotony_values(srpe_multiweek_content, tmp_path):
    ctx = _make_ctx(srpe_multiweek_content, tmp_path)
    result = srpe_report(ctx, output="monotony")
    for row in result.rows:
        week, weekly_au, mean_daily, sd_daily, monotony = row
        assert weekly_au > 0
        assert mean_daily > 0
        # Monotony can be None if sd == 0 (e.g., only one day)
        if monotony is not None:
            assert monotony > 0


def test_monotony_empty(tmp_path):
    ctx = _make_ctx("2025-01-10 * pullups: BW 5x10\n", tmp_path)
    result = srpe_report(ctx, output="monotony")
    assert isinstance(result, TableResult)
    assert result.rows == []


# --- Strain report ---


def test_strain_report(srpe_multiweek_content, tmp_path):
    ctx = _make_ctx(srpe_multiweek_content, tmp_path)
    result = srpe_report(ctx, output="strain")
    assert isinstance(result, TableResult)
    assert result.columns == ["week", "weekly_AU", "monotony", "strain", "risk"]
    assert len(result.rows) > 0


def test_strain_risk_levels(srpe_multiweek_content, tmp_path):
    ctx = _make_ctx(srpe_multiweek_content, tmp_path)
    result = srpe_report(ctx, output="strain")
    risks = {row[4] for row in result.rows}
    assert risks.issubset({"low", "moderate", "HIGH", "N/A"})


def test_strain_empty(tmp_path):
    ctx = _make_ctx("2025-01-10 * pullups: BW 5x10\n", tmp_path)
    result = srpe_report(ctx, output="strain")
    assert isinstance(result, TableResult)
    assert result.rows == []


# --- Unit tests for helper functions ---


def test_daily_au_aggregation():
    data = [
        ("2025-03-10", 5.0, 30.0, 150.0),
        ("2025-03-10", 3.0, 20.0, 60.0),  # same day
        ("2025-03-11", 6.0, 40.0, 240.0),
    ]
    result = _daily_au(data)
    assert result[date(2025, 3, 10)] == 210.0  # 150 + 60
    assert result[date(2025, 3, 11)] == 240.0


def test_acwr_report_direct():
    """Test _acwr_report with known data."""
    # 4 weeks of consistent training then a spike
    data = []
    # Weeks 1-4: ~300 AU per week (Mon/Wed/Fri, 100 AU each)
    for week_offset in range(4):
        base = date(2025, 1, 6) + timedelta(weeks=week_offset)
        for day_offset in [0, 2, 4]:  # Mon, Wed, Fri
            d = base + timedelta(days=day_offset)
            data.append((d.isoformat(), 5.0, 20.0, 100.0))

    # Week 5: spike to 600 AU
    base = date(2025, 2, 3)
    for day_offset in [0, 2, 4]:
        d = base + timedelta(days=day_offset)
        data.append((d.isoformat(), 10.0, 20.0, 200.0))

    result = _acwr_report(data)
    # Last row should show the spike week
    last_row = result.rows[-1]
    acwr = last_row[3]
    # Acute should be higher than chronic due to spike
    assert acwr > 1.0

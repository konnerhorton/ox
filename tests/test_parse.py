"""Tests for parsing functions.

Testing philosophy:
- Focus on the weight_text_to_quantity and process_weights functions
- These are the most error-prone and have known bugs
- Test edge cases from the documentation
"""

import pytest
from datetime import timedelta

from ox.parse import (
    weight_text_to_quantity,
    process_weights,
    process_distances,
    process_durations,
    process_details,
)
from ox.units import ureg


class TestWeightTextToQuantity:
    """Test parsing individual weight strings."""

    @pytest.mark.parametrize(
        "text,magnitude,unit",
        [
            ("24kg", 24, "kilogram"),
            ("135lb", 135, "pound"),
            ("500g", 500, "gram"),
            ("16oz", 16, "ounce"),
            ("12stone", 12, "stone"),
            ("135pound", 135, "pound"),
            ("24kilogram", 24, "kilogram"),
            ("2.5kg", 2.5, "kilogram"),
        ],
    )
    def test_valid(self, text, magnitude, unit):
        assert weight_text_to_quantity(text) == magnitude * ureg.parse_units(unit)

    @pytest.mark.parametrize("text", ["100m", "30min", "100", "abc"])
    def test_invalid_returns_none(self, text):
        assert weight_text_to_quantity(text) is None


class TestProcessWeights:
    """Test parsing weight strings into lists of Quantity objects.

    This handles the complex formats:
    - Single weight: "24kg"
    - Combined weights: "24kg+32kg"
    - Progressive weights: "160/185/210lbs"
    """

    def test_single_weight(self):
        """Single weight is the simplest case."""
        result = process_weights("24kg")

        assert len(result) == 1
        assert result[0] == 24 * ureg.kilogram

    def test_combined_weights(self):
        """Test combined weights (e.g., two kettlebells).

        Example: 24kg+32kg means 56kg total.
        """
        result = process_weights("24kg+32kg")

        assert len(result) == 1
        # Should sum the weights
        assert result[0] == (24 + 32) * ureg.kilogram

    def test_progressive_weights_explicit_units(self):
        """Test progressive weights where each has a unit.

        Example: 24kg/32kg/48kg means three different weights.
        """
        result = process_weights("24kg/32kg/48kg")

        assert len(result) == 3
        assert result[0] == 24 * ureg.kilogram
        assert result[1] == 32 * ureg.kilogram
        assert result[2] == 48 * ureg.kilogram

    def test_progressive_weights_implied_unit(self):
        """Progressive weights inherit the nearest succeeding unit."""
        result = process_weights("160/185/210lb")

        assert len(result) == 3
        assert result[0] == 160 * ureg.pound
        assert result[1] == 185 * ureg.pound
        assert result[2] == 210 * ureg.pound

    def test_progressive_weights_mixed_implied_units(self):
        """Mixed implied/explicit units: each unitless segment takes the next unit."""
        result = process_weights("60/70kg/160/180lb")

        assert len(result) == 4
        assert result[0] == 60 * ureg.kilogram
        assert result[1] == 70 * ureg.kilogram
        assert result[2] == 160 * ureg.pound
        assert result[3] == 180 * ureg.pound

    def test_progressive_weights_bw_with_implied_unit(self):
        """BW segments pass through while implied units resolve."""
        result = process_weights("BW/5/10lb")

        assert len(result) == 3
        assert result[0] is None
        assert result[1] == 5 * ureg.pound
        assert result[2] == 10 * ureg.pound

    def test_combined_and_progressive(self):
        """Test mixing combined and progressive weights.

        Example: 24kg+32kg/48kg+56kg means two combined weights.
        """
        result = process_weights("24kg+32kg/48kg+56kg")

        assert len(result) == 2
        assert result[0] == (24 + 32) * ureg.kilogram
        assert result[1] == (48 + 56) * ureg.kilogram

    def test_mixed_bw_weight_progressive(self):
        """Test mixed BW and weighted progressive sequence.

        Example: BW/BW/25lb/50lb means 4 sets: two bodyweight, then 25lb, 50lb.
        BW segments become None (no weight value).
        """
        result = process_weights("BW/BW/25lb/50lb")

        assert len(result) == 4
        assert result[0] is None
        assert result[1] is None
        assert result[2] == 25 * ureg.pound
        assert result[3] == 50 * ureg.pound

    def test_mixed_bw_weight_two_segments(self):
        """Test minimal mixed BW/weight progressive (two segments).

        Example: BW/25lb means one bodyweight set then one weighted set.
        """
        result = process_weights("BW/25lb")

        assert len(result) == 2
        assert result[0] is None
        assert result[1] == 25 * ureg.pound


class TestProcessDistances:
    """Test parsing distance strings into lists of Quantity objects."""

    def test_single_distance(self):
        result = process_distances("5km")
        assert result == [5 * ureg.kilometer]

    def test_imperial_distance(self):
        """Distance is dimension-checked, not metric-only."""
        assert process_distances("3mi") == [3 * ureg.mile]

    def test_progressive_explicit_units(self):
        result = process_distances("100m/200m/400m")
        assert result == [100 * ureg.meter, 200 * ureg.meter, 400 * ureg.meter]

    def test_progressive_implied_unit(self):
        """Unitless segments inherit the nearest succeeding unit."""
        result = process_distances("100/200/400m")
        assert result == [100 * ureg.meter, 200 * ureg.meter, 400 * ureg.meter]

    def test_mass_unit_rejected(self):
        """A mass where a length belongs yields None, not a wrong-dimension value."""
        assert process_distances("24kg") == [None]


class TestProcessDurations:
    """Test parsing duration strings into lists of timedeltas."""

    def test_single_duration(self):
        assert process_durations("PT30M") == [timedelta(minutes=30)]

    def test_progressive(self):
        result = process_durations("PT30S/PT25S/PT20S")
        assert result == [
            timedelta(seconds=30),
            timedelta(seconds=25),
            timedelta(seconds=20),
        ]


class TestProcessDetails:
    """Test assembling detail fields into TrainingSets.

    Set count comes from the rep scheme when present; otherwise from the longest
    progressive list, defaulting to a single set. Weight, duration, and distance
    each broadcast across the set count.
    """

    def test_rep_scheme_nxr(self):
        sets, _ = process_details({"weight": "185lb", "rep_scheme": "3x5"})
        assert len(sets) == 3
        assert all(s.reps == 5 and s.weight == 185 * ureg.pound for s in sets)

    def test_rep_scheme_per_set(self):
        sets, _ = process_details({"weight": "185lb", "rep_scheme": "5/5/3"})
        assert [s.reps for s in sets] == [5, 5, 3]

    def test_weight_broadcasts_across_sets(self):
        sets, _ = process_details({"weight": "24kg/32kg", "rep_scheme": "2x5"})
        assert [s.weight for s in sets] == [24 * ureg.kilogram, 32 * ureg.kilogram]

    def test_duration_only_yields_one_set(self):
        """run: PT30M — previously produced zero sets."""
        sets, _ = process_details({"duration": "PT30M"})
        assert len(sets) == 1
        assert sets[0].reps == 1
        assert sets[0].duration == timedelta(minutes=30)
        assert sets[0].weight is None

    def test_duration_broadcasts_across_rep_scheme(self):
        """plank: BW PT30S 3x1 — three identical holds."""
        sets, _ = process_details(
            {"weight": "BW", "duration": "PT30S", "rep_scheme": "3x1"}
        )
        assert len(sets) == 3
        assert all(s.duration == timedelta(seconds=30) for s in sets)
        assert all(s.weight is None for s in sets)

    def test_weight_and_duration_co_occur(self):
        """weighted-plank: 45lb PT30S 3x1."""
        sets, _ = process_details(
            {"weight": "45lb", "duration": "PT30S", "rep_scheme": "3x1"}
        )
        assert len(sets) == 3
        assert all(s.weight == 45 * ureg.pound for s in sets)
        assert all(s.duration == timedelta(seconds=30) for s in sets)

    def test_distance_and_duration_co_occur(self):
        """run: 5km PT25M — one set carrying both."""
        sets, _ = process_details({"distance": "5km", "duration": "PT25M"})
        assert len(sets) == 1
        assert sets[0].distance == 5 * ureg.kilometer
        assert sets[0].duration == timedelta(minutes=25)

    def test_all_fields_together(self):
        """row: 500m PT2M 5x1."""
        sets, _ = process_details(
            {"distance": "500m", "duration": "PT2M", "rep_scheme": "5x1"}
        )
        assert len(sets) == 5
        assert all(
            s.reps == 1
            and s.distance == 500 * ureg.meter
            and s.duration == timedelta(minutes=2)
            for s in sets
        )

    def test_progressive_duration_sets_count_without_rep_scheme(self):
        """Set count falls back to the longest progressive list."""
        sets, _ = process_details({"duration": "PT30S/PT25S/PT20S"})
        assert [s.duration for s in sets] == [
            timedelta(seconds=30),
            timedelta(seconds=25),
            timedelta(seconds=20),
        ]

    def test_progressive_distance_maps_per_set(self):
        sets, _ = process_details({"distance": "100m/200m/400m", "rep_scheme": "3x1"})
        assert [s.distance for s in sets] == [
            100 * ureg.meter,
            200 * ureg.meter,
            400 * ureg.meter,
        ]

    def test_note_only_yields_no_sets(self):
        """A movement with only a note has nothing to measure."""
        sets, note = process_details({"note": '"felt easy"'})
        assert sets == []
        assert note == "felt easy"

    def test_empty_details_yields_no_sets(self):
        sets, note = process_details({})
        assert sets == []
        assert note is None

    def test_note_extracted_alongside_sets(self):
        sets, note = process_details(
            {"weight": "185lb", "rep_scheme": "3x5", "note": '"felt strong"'}
        )
        assert len(sets) == 3
        assert note == "felt strong"


def _parse_str(content: str):
    """Parse a raw .ox string and return (tree, diagnostics)."""
    import tree_sitter_ox
    from tree_sitter import Language, Parser
    from ox.lint import collect_diagnostics

    language = Language(tree_sitter_ox.language())
    parser = Parser(language)
    tree = parser.parse(bytes(content, encoding="utf-8"))
    return tree, collect_diagnostics(tree)


class TestDurationToken:
    """Test that ISO 8601 PT duration strings are accepted by the grammar."""

    @pytest.mark.parametrize(
        "duration",
        ["PT30M", "PT30M15S", "PT1H", "PT1H30M", "PT1H30M15S", "PT30M15.5S", "PT45S"],
    )
    def test_accepted(self, duration):
        _, diags = _parse_str(f"2025-01-10 * run: {duration}\n")
        assert not diags

    def test_old_time_format_rejected(self):
        _, diags = _parse_str("2025-01-10 * run: 30min\n")
        assert len(diags) > 0


def _detail_fields(content: str) -> dict[str, str]:
    """Parse one entry and return its detail fields as {field_name: text}."""
    tree, diags = _parse_str(content)
    assert not diags, f"unexpected syntax error in {content!r}"
    found = {}

    def walk(node):
        for i, child in enumerate(node.children):
            name = node.field_name_for_child(i)
            if name in ("weight", "duration", "distance", "rep_scheme"):
                found[name] = child.text.decode("utf-8")
            walk(child)

    walk(tree.root_node)
    return found


class TestProgressiveDuration:
    """Grammar accepts /-separated per-set durations."""

    @pytest.mark.parametrize(
        "duration",
        ["PT30S/PT25S", "PT30S/PT25S/PT20S", "PT1M/PT45S", "PT1H30M/PT1H"],
    )
    def test_accepted(self, duration):
        fields = _detail_fields(f"2025-01-10 * plank: {duration} 3x1\n")
        assert fields["duration"] == duration

    def test_single_duration_still_one_token(self):
        """The progressive form must not fragment the single form."""
        fields = _detail_fields("2025-01-10 * run: PT30M\n")
        assert fields["duration"] == "PT30M"


class TestProgressiveDistance:
    """Grammar accepts /-separated per-set distances, with implied units."""

    @pytest.mark.parametrize(
        "distance",
        ["100m/200m", "100m/200m/400m", "1km/2km", "100/200/400m", "5/10km"],
    )
    def test_accepted(self, distance):
        fields = _detail_fields(f"2025-01-10 * sprints: {distance} 3x1\n")
        assert fields["distance"] == distance

    def test_single_distance_still_one_token(self):
        fields = _detail_fields("2025-01-10 * run: 5km\n")
        assert fields["distance"] == "5km"


class TestDetailFieldCombinations:
    """Independent detail fields coexist on one line and land in the right slot."""

    @pytest.mark.parametrize(
        "details,expected",
        [
            ("5km PT25M", {"distance": "5km", "duration": "PT25M"}),
            (
                "500m PT2M 5x1",
                {"distance": "500m", "duration": "PT2M", "rep_scheme": "5x1"},
            ),
            (
                "BW PT30S 3x1",
                {"weight": "BW", "duration": "PT30S", "rep_scheme": "3x1"},
            ),
            (
                "45lb PT30S 3x1",
                {"weight": "45lb", "duration": "PT30S", "rep_scheme": "3x1"},
            ),
        ],
    )
    def test_fields_land_correctly(self, details, expected):
        assert _detail_fields(f"2025-01-10 * x: {details}\n") == expected

    @pytest.mark.parametrize(
        "details,expected",
        [
            ("24kg/32kg/48kg 3x5", "24kg/32kg/48kg"),
            ("160/185/210lb 3x5", "160/185/210lb"),
            ("BW/25lb 2x5", "BW/25lb"),
            ("24kg+32kg 3x5", "24kg+32kg"),
        ],
    )
    def test_weight_forms_unaffected(self, details, expected):
        """Adding progressive distance must not poach weight's progressive forms."""
        assert _detail_fields(f"2025-01-10 * squat: {details}\n")["weight"] == expected


class TestWeighInEntry:
    """Grammar accepts weigh-in forms without producing diagnostics."""

    @pytest.mark.parametrize(
        "line",
        [
            "2025-01-10 W 185lb\n",
            "2025-01-10 W 185lb T06:30\n",
            '2025-01-10 W 185lb "bathroom scale"\n',
            '2025-01-10 W 83.5kg T06:30 "home scale"\n',
            "2025-01-10 W 83.5kg\n",
        ],
    )
    def test_accepted(self, line):
        _, diags = _parse_str(line)
        assert not diags


class TestBlockDirectives:
    """Grammar accepts top-level @-directives without diagnostics.

    These aren't yet promoted to data structures, but the grammar must not reject them.
    """

    def test_movement_block(self):
        src = (
            "@movement squat\n"
            "equipment: barbell\n"
            "tags: squat, lower\n"
            "note: back squat\n"
            "@end\n"
        )
        _, diags = _parse_str(src)
        assert not diags

    def test_template_block(self):
        src = "@template upper\nbench-press: 135lb 5x5\n@end\n"
        _, diags = _parse_str(src)
        assert not diags

    def test_plugin_directive(self):
        _, diags = _parse_str('@plugin "my_plugin.py"\n')
        assert not diags

    def test_include_directive(self):
        _, diags = _parse_str('@include "other.ox"\n')
        assert not diags


class TestMovementDefinitionParsing:
    """Test that @movement blocks are parsed into MovementDefinition objects."""

    def _parse_log(self, tmp_path, src):
        from ox.cli import parse_file

        p = tmp_path / "log.ox"
        p.write_text(src)
        return parse_file(p)

    def test_single_definition(self, tmp_path):
        log = self._parse_log(
            tmp_path,
            "@movement kb-oh-press\n"
            "equipment: kettlebell\n"
            "tag: press\n"
            "url: https://example.com/kb-press\n"
            "note: keep elbow tight\n"
            "@end\n",
        )
        assert len(log.movement_definitions) == 1
        m = log.movement_definitions[0]
        assert m.name == "kb-oh-press"
        assert m.equipment == "kettlebell"
        assert m.tags == ("press",)
        assert m.note == "keep elbow tight"
        assert m.url == "https://example.com/kb-press"

    def test_tags_plural_comma_separated(self, tmp_path):
        log = self._parse_log(
            tmp_path,
            "@movement squat\nequipment: barbell\ntags: squat, lower\n@end\n",
        )
        assert log.movement_definitions[0].tags == ("squat", "lower")

    def test_no_metadata(self, tmp_path):
        log = self._parse_log(tmp_path, "@movement burpee\n@end\n")
        m = log.movement_definitions[0]
        assert m.name == "burpee"
        assert m.equipment is None
        assert m.tags == ()
        assert m.note is None


class TestQueryEntryParsing:
    """Test that query_entry nodes are parsed into StoredQuery objects."""

    def test_stored_query_name(self, log_with_query_file):
        from ox.cli import parse_file

        log = parse_file(log_with_query_file)
        assert len(log.queries) == 1
        assert log.queries[0].name == "max-pullups"

    def test_stored_query_sql(self, log_with_query_file):
        from ox.cli import parse_file

        log = parse_file(log_with_query_file)
        assert "pullups" in log.queries[0].sql

    def test_stored_query_date(self, log_with_query_file):
        from datetime import date
        from ox.cli import parse_file

        log = parse_file(log_with_query_file)
        assert log.queries[0].date == date(2025, 1, 15)

    pass

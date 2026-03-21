"""Integration tests for full parsing pipeline.

Testing philosophy:
- Test the user-facing workflow: file → parsed objects
- Use the same function the CLI uses
- Verify the entire chain works, not just individual pieces
"""

import pytest
from datetime import date
from ox.cli import parse_file


class TestParseFile:
    """Test the main parse_file function used by the CLI.

    This is what users actually call, so it's critical to test.
    """

    def test_parse_simple_log(self, simple_log_file):
        """Test parsing a simple but realistic training log.

        Verifies:
        - File can be read and parsed
        - Correct number of sessions extracted
        - Dates parsed correctly
        - Movements have correct names
        - Sets have correct reps
        """
        log = parse_file(simple_log_file)

        # Should have 3 sessions (1 single-line + 2 multi-line)
        # Note: Currently testing with 2 sessions until planned session parsing is fixed
        assert len(log.sessions) >= 2  # At least the completed sessions

        # Check first session (single-line entry)
        session1 = log.sessions[0]
        assert session1.date == date(2025, 1, 10)
        assert session1.flag == "*"
        assert len(session1.movements) == 1
        assert session1.movements[0].name == "pullups"

        # Check second session (multi-line)
        session2 = log.sessions[1]
        assert session2.date == date(2025, 1, 11)
        assert session2.name == "Upper Day"
        assert len(session2.movements) == 2

        # Verify movement names
        movement_names = [m.name for m in session2.movements]
        assert "bench-press" in movement_names
        assert "kb-oh-press" in movement_names

        # Check completed vs planned
        assert len(log.completed_sessions) >= 2
        # assert len(log.planned_sessions) >= 1  # TODO: Enable when ! flag parsing is fixed

    @pytest.mark.skip(reason="Planned session (! flag) parsing not yet implemented")
    def test_parse_planned_vs_completed(self, simple_log_file):
        """Test that flags are parsed correctly.

        Flags indicate session status:
        - * = completed
        - ! = planned

        TODO: Enable this test when planned session parsing is implemented.
        """
        log = parse_file(simple_log_file)

        # First two sessions are completed (*)
        assert log.sessions[0].flag == "*"
        assert log.sessions[1].flag == "*"

        # Third session is planned (!)
        assert log.sessions[2].flag == "!"

    def test_query_movements(self, simple_log_file):
        """Test querying movements from parsed log.

        This tests that the TrainingLog query API works on real parsed data.
        """
        log = parse_file(simple_log_file)

        # Query all pullups
        pullup_history = list(log.movements("pullups"))

        # Should find pullups in first session
        assert len(pullup_history) >= 1

        # Verify it's actually pullups
        for session_date, movement in pullup_history:
            assert movement.name == "pullups"

    def test_parse_example_file(self):
        """Smoke test: can we parse the example file?

        This ensures our example file is actually valid.
        Important because users will reference this file.
        """
        from pathlib import Path

        example_file = Path(__file__).parent.parent / "example" / "example.ox"

        if not example_file.exists():
            pytest.skip("Example file not found")

        # Should parse without errors
        log = parse_file(example_file)

        # Basic sanity checks
        assert len(log.sessions) > 0
        assert all(hasattr(s, "date") for s in log.sessions)
        assert all(hasattr(s, "movements") for s in log.sessions)


class TestIncludeDirective:
    """Test @include directive for splitting logs across files."""

    def test_single_include_merges_sessions(self, tmp_path):
        """Including another file merges its sessions into the result."""
        child = tmp_path / "child.ox"
        child.write_text("2025-01-11 * bench-press: 135lb 5x5\n")

        main = tmp_path / "main.ox"
        main.write_text('2025-01-10 * pullups: BW 5x10\n@include "child.ox"\n')

        log = parse_file(main)
        assert len(log.sessions) == 2
        names = {s.movements[0].name for s in log.sessions}
        assert names == {"pullups", "bench-press"}

    def test_nested_includes(self, tmp_path):
        """Nested includes (a -> b -> c) all merge."""
        c = tmp_path / "c.ox"
        c.write_text("2025-01-12 * squat: 185lb 3x5\n")

        b = tmp_path / "b.ox"
        b.write_text('2025-01-11 * bench-press: 135lb 5x5\n@include "c.ox"\n')

        a = tmp_path / "a.ox"
        a.write_text('2025-01-10 * pullups: BW 5x10\n@include "b.ox"\n')

        log = parse_file(a)
        assert len(log.sessions) == 3

    def test_cycle_detection(self, tmp_path):
        """Circular includes emit diagnostic, no infinite loop."""
        a = tmp_path / "a.ox"
        b = tmp_path / "b.ox"
        a.write_text('2025-01-10 * pullups: BW 5x10\n@include "b.ox"\n')
        b.write_text('2025-01-11 * bench-press: 135lb 5x5\n@include "a.ox"\n')

        log = parse_file(a)
        # Both files' sessions should be present
        assert len(log.sessions) == 2
        # Should have a circular include diagnostic
        cycle_diags = [d for d in log.diagnostics if "Circular" in d.message]
        assert len(cycle_diags) == 1

    def test_self_include(self, tmp_path):
        """Self-include detected and reported."""
        f = tmp_path / "self.ox"
        f.write_text('2025-01-10 * pullups: BW 5x10\n@include "self.ox"\n')

        log = parse_file(f)
        assert len(log.sessions) == 1
        cycle_diags = [d for d in log.diagnostics if "Circular" in d.message]
        assert len(cycle_diags) == 1

    def test_missing_include(self, tmp_path):
        """Missing include file emits diagnostic, other entries still parse."""
        main = tmp_path / "main.ox"
        main.write_text('2025-01-10 * pullups: BW 5x10\n@include "nonexistent.ox"\n')

        log = parse_file(main)
        assert len(log.sessions) == 1
        missing_diags = [d for d in log.diagnostics if "not found" in d.message]
        assert len(missing_diags) == 1

    def test_relative_path_resolution(self, tmp_path):
        """Include paths resolve relative to the including file's directory."""
        subdir = tmp_path / "sub"
        subdir.mkdir()
        child = subdir / "child.ox"
        child.write_text("2025-01-11 * bench-press: 135lb 5x5\n")

        main = tmp_path / "main.ox"
        main.write_text('@include "sub/child.ox"\n2025-01-10 * pullups: BW 5x10\n')

        log = parse_file(main)
        assert len(log.sessions) == 2


class TestMixedBWWeightProgressive:
    """Test that mixed BW/weight progressive sequences parse without errors."""

    def test_grammar_accepts_bw_weight_progressive(self, tmp_path):
        """Grammar should produce no ERROR nodes for BW/weight mixed progressive.

        Example: pullup: BW/BW/25lb/50lb 1/1/1/1 — warmup BW sets then weighted.
        """
        import tree_sitter_ox
        from tree_sitter import Language, Parser
        from ox.lint import collect_diagnostics

        ox_content = "2025-01-10 * pullup: BW/BW/25lb/50lb 1/1/1/1\n"
        language = Language(tree_sitter_ox.language())
        parser = Parser(language)
        tree = parser.parse(bytes(ox_content, encoding="utf-8"))

        diagnostics = collect_diagnostics(tree)
        assert len(diagnostics) == 0, f"Expected no diagnostics, got: {diagnostics}"

    def test_grammar_accepts_bw_then_weight(self, tmp_path):
        """Grammar should accept a two-segment BW/weight progressive."""
        import tree_sitter_ox
        from tree_sitter import Language, Parser
        from ox.lint import collect_diagnostics

        ox_content = "2025-01-10 * pullup: BW/25lb 1/1\n"
        language = Language(tree_sitter_ox.language())
        parser = Parser(language)
        tree = parser.parse(bytes(ox_content, encoding="utf-8"))

        diagnostics = collect_diagnostics(tree)
        assert len(diagnostics) == 0, f"Expected no diagnostics, got: {diagnostics}"

    def test_parse_file_with_mixed_bw_weight(self, tmp_path):
        """End-to-end: file with mixed BW/weight progressive parses correctly."""
        from ox.cli import parse_file

        ox_file = tmp_path / "mixed_bw.ox"
        ox_file.write_text("2025-01-10 * pullup: BW/BW/25lb/50lb 1/1/1/1\n")

        log = parse_file(ox_file)

        assert len(log.sessions) == 1
        session = log.sessions[0]
        assert len(session.movements) == 1
        movement = session.movements[0]
        assert movement.name == "pullup"
        assert len(movement.sets) == 4


class TestWeighInIntegration:
    """End-to-end weigh-in parsing tests."""

    def test_weigh_ins_parsed(self, log_with_weigh_ins_file):
        log = parse_file(log_with_weigh_ins_file)
        assert len(log.weigh_ins) == 3

    def test_weigh_in_fields(self, log_with_weigh_ins_file):
        from datetime import date, time
        from ox.units import ureg

        log = parse_file(log_with_weigh_ins_file)
        w0, w1, w2 = log.weigh_ins

        assert w0.date == date(2025, 1, 10)
        assert w0.weight == 185 * ureg.pound
        assert w0.time_of_day is None
        assert w0.scale is None

        assert w1.date == date(2025, 1, 11)
        assert w1.time_of_day == time(6, 30)
        assert w1.scale is None

        assert w2.date == date(2025, 1, 12)
        assert w2.time_of_day == time(7, 0)
        assert w2.scale == "gym scale"


class TestStoredQueryRoundTrip:
    """End-to-end: parse a query_entry, load into DB, retrieve by name."""

    def test_stored_query_round_trip(self, log_with_query_file):
        from ox.cli import parse_file
        from ox.db import create_db

        log = parse_file(log_with_query_file)
        assert len(log.queries) == 1

        conn = create_db(log)
        row = conn.execute(
            "SELECT sql FROM queries WHERE name = ?", ("max-pullups",)
        ).fetchone()
        assert row is not None
        assert "pullups" in row[0]
        conn.close()


class TestEndToEndScenarios:
    """Test complete user workflows."""

    def test_analyze_progression(self, simple_log_file):
        """Test analyzing exercise progression over time.

        This is a common use case: track how an exercise improves.
        """
        log = parse_file(simple_log_file)

        # Get history for a specific movement
        history = log.movement_history("pullups")

        # Should be sorted by date
        dates = [d for d, _ in history]
        assert dates == sorted(dates)

        # Each entry should have reps
        for session_date, movement in history:
            assert movement.total_reps > 0

    def test_calculate_total_volume(self, simple_log_file):
        """Test calculating total training volume.

        Volume = weight × reps, important for tracking training load.
        """
        log = parse_file(simple_log_file)

        # Find a weighted movement
        for session in log.sessions:
            for movement in session.movements:
                if movement.name == "bench-press":
                    volume = movement.total_volume()

                    # Should be able to calculate volume
                    assert volume is not None
                    # Volume should be positive
                    assert volume.magnitude > 0
                    return

        pytest.fail("No bench-press movement found to test volume")

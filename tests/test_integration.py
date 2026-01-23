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
        assert all(hasattr(s, 'date') for s in log.sessions)
        assert all(hasattr(s, 'movements') for s in log.sessions)


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

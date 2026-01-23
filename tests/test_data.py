"""Tests for data structures.

Testing philosophy:
- Test the public API and computed properties
- Don't test private implementation details
- Focus on edge cases and business logic
"""

import pytest
from datetime import date
from ox.data import TrainingSet, Movement, TrainingSession, TrainingLog
from ox.units import ureg


class TestTrainingSet:
    """Test TrainingSet dataclass and its methods."""

    def test_create_bodyweight_set(self):
        """Most basic case: bodyweight exercise."""
        training_set = TrainingSet(reps=10, weight=None)
        assert training_set.reps == 10
        assert training_set.weight is None
        assert training_set.volume is None  # No weight, no volume

    def test_create_weighted_set(self):
        """Weighted exercise set."""
        weight = 24 * ureg.kilogram
        training_set = TrainingSet(reps=5, weight=weight)

        assert training_set.reps == 5
        assert training_set.weight == weight

        # Volume = reps * weight
        expected_volume = 5 * 24 * ureg.kilogram
        assert training_set.volume == expected_volume


class TestMovement:
    """Test Movement dataclass and aggregation methods."""

    def test_total_reps(self):
        """Test total_reps sums across all sets."""
        sets = [
            TrainingSet(reps=5, weight=None),
            TrainingSet(reps=5, weight=None),
            TrainingSet(reps=5, weight=None),
        ]
        movement = Movement(name="pullups", sets=sets, note=None)

        assert movement.total_reps == 15

    def test_total_volume_bodyweight(self):
        """Bodyweight exercises have no volume."""
        sets = [
            TrainingSet(reps=10, weight=None),
            TrainingSet(reps=10, weight=None),
        ]
        movement = Movement(name="pushups", sets=sets, note=None)

        assert movement.total_volume() is None

    def test_total_volume_weighted(self):
        """Test total_volume sums across all sets."""
        weight = 100 * ureg.pounds
        sets = [
            TrainingSet(reps=5, weight=weight),
            TrainingSet(reps=5, weight=weight),
            TrainingSet(reps=5, weight=weight),
        ]
        movement = Movement(name="bench-press", sets=sets, note=None)

        # Total volume = 3 sets * 5 reps * 100 lbs = 1500 lbs
        expected = 1500 * ureg.pounds
        assert movement.total_volume() == expected

    def test_top_set_weight(self):
        """Test top_set_weight finds heaviest weight."""
        sets = [
            TrainingSet(reps=5, weight=135 * ureg.pounds),
            TrainingSet(reps=5, weight=155 * ureg.pounds),  # Heaviest
            TrainingSet(reps=5, weight=145 * ureg.pounds),
        ]
        movement = Movement(name="squat", sets=sets, note=None)

        assert movement.top_set_weight == 155 * ureg.pounds

    def test_top_set_weight_bodyweight(self):
        """Bodyweight exercises return None for top_set_weight."""
        sets = [TrainingSet(reps=10, weight=None)]
        movement = Movement(name="pullups", sets=sets, note=None)

        assert movement.top_set_weight is None


class TestTrainingLog:
    """Test TrainingLog query methods."""

    @pytest.fixture
    def sample_log(self):
        """Create a sample training log for testing queries.

        Design: 2 sessions with overlapping and unique movements.
        """
        session1 = TrainingSession(
            date=date(2025, 1, 10),
            flag="*",
            name="Upper Day",
            movements=(
                Movement("pullups", [TrainingSet(10, None)], None),
                Movement("bench-press", [TrainingSet(5, 135 * ureg.pounds)], None),
            )
        )

        session2 = TrainingSession(
            date=date(2025, 1, 12),
            flag="*",
            name="Lower Day",
            movements=(
                Movement("squat", [TrainingSet(5, 185 * ureg.pounds)], None),
                Movement("pullups", [TrainingSet(8, None)], None),  # Same exercise, different day
            )
        )

        return TrainingLog(sessions=(session1, session2))

    def test_movements_all(self, sample_log):
        """Test movements() without filter returns all movements."""
        all_movements = list(sample_log.movements())

        # Should have 4 total movement instances (2 from each session)
        assert len(all_movements) == 4

    def test_movements_filtered(self, sample_log):
        """Test movements() with filter returns only matching movements."""
        pullup_movements = list(sample_log.movements("pullups"))

        # Should find 2 pullup instances (one in each session)
        assert len(pullup_movements) == 2

        # Verify they're both pullups
        for session_date, movement in pullup_movements:
            assert movement.name == "pullups"

    def test_movement_history_sorted(self, sample_log):
        """Test movement_history returns sorted list."""
        history = sample_log.movement_history("pullups")

        # Should be sorted by date (earliest first)
        dates = [session_date for session_date, _ in history]
        assert dates == sorted(dates)

    def test_most_recent_session(self, sample_log):
        """Test most_recent_session returns latest instance."""
        recent_date, recent_movement = sample_log.most_recent_session("pullups")

        # Most recent pullups should be from Jan 12
        assert recent_date == date(2025, 1, 12)
        assert recent_movement.name == "pullups"

    def test_completed_sessions_filter(self, sample_log):
        """Test completed_sessions property filters by flag."""
        completed = sample_log.completed_sessions

        # Both sessions in sample_log are completed (flag="*")
        assert len(completed) == 2
        assert all(s.flag == "*" for s in completed)

    def test_planned_sessions_filter(self, sample_log):
        """Test planned_sessions property filters by flag."""
        planned = sample_log.planned_sessions

        # No planned sessions in sample_log
        assert len(planned) == 0

    def test_mixed_sessions(self):
        """Test filtering with both completed and planned sessions."""
        completed = TrainingSession(
            date=date(2025, 1, 10),
            flag="*",
            name="Completed",
            movements=(Movement("pullups", [TrainingSet(10, None)], None),)
        )

        planned = TrainingSession(
            date=date(2025, 1, 11),
            flag="!",
            name="Planned",
            movements=(Movement("squat", [TrainingSet(5, 185 * ureg.pounds)], None),)
        )

        log = TrainingLog(sessions=(completed, planned))

        # Should have 1 completed, 1 planned
        assert len(log.completed_sessions) == 1
        assert len(log.planned_sessions) == 1
        assert log.completed_sessions[0].name == "Completed"
        assert log.planned_sessions[0].name == "Planned"

"""Tests for data structures.

Testing philosophy:
- Test the public API and computed properties
- Don't test private implementation details
- Focus on edge cases and business logic
"""

from pathlib import Path

import pytest
from datetime import date, time, timedelta
from ox.data import TrainingSet, Movement, TrainingSession, TrainingLog, WeighIn
from ox.units import ureg


class TestWeighIn:
    """Test WeighIn dataclass and to_ox() round-trips."""

    def test_weight_only(self):
        w = WeighIn(date=date(2025, 1, 10), weight=185 * ureg.pound)
        assert w.to_ox() == "2025-01-10 W 185lb"

    def test_with_timestamp(self):
        w = WeighIn(
            date=date(2025, 1, 10), weight=185 * ureg.pound, time_of_day=time(6, 30)
        )
        assert w.to_ox() == "2025-01-10 W 185lb T06:30"

    def test_with_scale(self):
        w = WeighIn(
            date=date(2025, 1, 10), weight=185 * ureg.pound, scale="bathroom scale"
        )
        assert w.to_ox() == '2025-01-10 W 185lb "bathroom scale"'

    def test_with_timestamp_and_scale(self):
        w = WeighIn(
            date=date(2025, 1, 10),
            weight=83.5 * ureg.kilogram,
            time_of_day=time(6, 30),
            scale="home scale",
        )
        assert w.to_ox() == '2025-01-10 W 83.5kg T06:30 "home scale"'


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

    def test_defaults_are_none(self):
        """duration and distance are optional and default to None."""
        training_set = TrainingSet(reps=5)
        assert training_set.duration is None
        assert training_set.distance is None

    def test_duration_set(self):
        """An isometric hold: reps=1 with a duration."""
        training_set = TrainingSet(reps=1, duration=timedelta(seconds=30))
        assert training_set.duration == timedelta(seconds=30)
        assert training_set.weight is None

    def test_weighted_duration_set(self):
        """Weight and duration co-occur (weighted-plank: 45lb PT30S 3x1)."""
        training_set = TrainingSet(
            reps=1, weight=45 * ureg.pound, duration=timedelta(seconds=30)
        )
        assert training_set.weight == 45 * ureg.pound
        assert training_set.duration == timedelta(seconds=30)
        # Volume still derives from reps * weight only
        assert training_set.volume == 45 * ureg.pound

    def test_distance_set(self):
        """A distance-only set (run: 5km)."""
        training_set = TrainingSet(reps=1, distance=5 * ureg.kilometer)
        assert training_set.distance == 5 * ureg.kilometer

    def test_all_fields_co_occur(self):
        """No invariant forbids reps, weight, duration, and distance together."""
        training_set = TrainingSet(
            reps=1,
            weight=20 * ureg.pound,
            duration=timedelta(minutes=2),
            distance=500 * ureg.meter,
        )
        assert training_set.reps == 1
        assert training_set.weight == 20 * ureg.pound
        assert training_set.duration == timedelta(minutes=2)
        assert training_set.distance == 500 * ureg.meter


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


def reparse_movement(line: str) -> Movement:
    """Parse a single movement line back into a Movement."""
    from ox.cli import parse_file
    import tempfile

    p = Path(tempfile.mktemp(suffix=".ox"))
    p.write_text(f"2025-01-10 * {line}\n")
    return parse_file(p).sessions[0].movements[0]


class TestToOxRoundTrip:
    """Movement and TrainingSession to_ox() should emit a form that re-parses to an equal object."""

    def _reparse_movement(self, line: str) -> Movement:
        return reparse_movement(line)

    def test_movement_uniform_weight(self):
        m = Movement(
            name="bench-press",
            sets=[TrainingSet(reps=5, weight=135 * ureg.pound) for _ in range(3)],
            note=None,
        )
        assert m.to_ox() == "bench-press: 135lb 3x5"
        round_tripped = self._reparse_movement(m.to_ox())
        assert round_tripped.name == m.name
        assert round_tripped.total_reps == m.total_reps
        assert round_tripped.top_set_weight == m.top_set_weight

    def test_movement_bodyweight(self):
        m = Movement(
            name="pullups",
            sets=[TrainingSet(reps=10, weight=None) for _ in range(5)],
            note=None,
        )
        assert m.to_ox() == "pullups: BW 5x10"

    def test_movement_progressive_weight(self):
        m = Movement(
            name="squat",
            sets=[TrainingSet(reps=5, weight=w * ureg.pound) for w in (135, 185, 225)],
            note=None,
        )
        # varied weights → progressive form
        assert "/" in m.to_ox()
        round_tripped = self._reparse_movement(m.to_ox())
        assert [s.weight for s in round_tripped.sets] == [
            135 * ureg.pound,
            185 * ureg.pound,
            225 * ureg.pound,
        ]

    def test_movement_with_note_round_trip(self):
        m = Movement(
            name="bench-press",
            sets=[TrainingSet(reps=5, weight=135 * ureg.pound)],
            note="paused",
        )
        round_tripped = self._reparse_movement(m.to_ox())
        assert round_tripped.note == "paused"

    def test_session_single_line(self):
        m = Movement(
            name="pullups", sets=[TrainingSet(reps=10, weight=None)], note=None
        )
        s = TrainingSession(
            date=date(2025, 1, 10), completed=True, name=None, movements=(m,)
        )
        assert s.to_ox() == "2025-01-10 T pullups: BW 1x10"

    def test_session_block(self):
        m1 = Movement(
            name="bench-press",
            sets=[TrainingSet(reps=5, weight=135 * ureg.pound) for _ in range(5)],
            note=None,
        )
        s = TrainingSession(
            date=date(2025, 1, 11), completed=True, name="Upper Day", movements=(m1,)
        )
        out = s.to_ox()
        assert out.startswith("@session\ndate: 2025-01-11\nname: Upper Day")
        assert out.endswith("@end")
        assert "bench-press: 135lb 5x5" in out


class TestToOxDurationDistance:
    """to_ox() emission of the duration and distance set fields."""

    def _movement(self, name, sets):
        return Movement(name=name, sets=sets, note=None)

    def test_single_duration(self):
        m = self._movement("run", [TrainingSet(reps=1, duration=timedelta(minutes=30))])
        assert m.to_ox() == "run: PT30M"

    def test_single_distance(self):
        m = self._movement("run", [TrainingSet(reps=1, distance=5 * ureg.kilometer)])
        assert m.to_ox() == "run: 5km"

    def test_distance_and_duration(self):
        m = self._movement(
            "run",
            [
                TrainingSet(
                    reps=1, distance=5 * ureg.kilometer, duration=timedelta(minutes=25)
                )
            ],
        )
        assert m.to_ox() == "run: 5km PT25M"

    def test_imperial_distance_keeps_its_unit(self):
        m = self._movement("run", [TrainingSet(reps=1, distance=3 * ureg.mile)])
        assert m.to_ox() == "run: 3mi"

    def test_weight_and_duration(self):
        m = self._movement(
            "weighted-plank",
            [
                TrainingSet(
                    reps=1, weight=45 * ureg.pound, duration=timedelta(seconds=30)
                )
                for _ in range(3)
            ],
        )
        assert m.to_ox() == "weighted-plank: 45lb PT30S 3x1"

    def test_all_four_fields(self):
        m = self._movement(
            "sled-push",
            [
                TrainingSet(
                    reps=2,
                    weight=90 * ureg.kilogram,
                    duration=timedelta(seconds=45),
                    distance=20 * ureg.meter,
                )
                for _ in range(3)
            ],
        )
        assert m.to_ox() == "sled-push: 90kg 20m PT45S 3x2"

    def test_uniform_values_collapse(self):
        m = self._movement(
            "row",
            [
                TrainingSet(
                    reps=1, distance=500 * ureg.meter, duration=timedelta(minutes=2)
                )
                for _ in range(5)
            ],
        )
        assert m.to_ox() == "row: 500m PT2M 5x1"

    def test_varying_duration_expands(self):
        m = self._movement(
            "plank",
            [TrainingSet(reps=1, duration=timedelta(seconds=s)) for s in (30, 25, 20)],
        )
        assert m.to_ox() == "plank: PT30S/PT25S/PT20S"

    def test_varying_distance_expands(self):
        m = self._movement(
            "sprints",
            [TrainingSet(reps=1, distance=d * ureg.meter) for d in (100, 200, 400)],
        )
        assert m.to_ox() == "sprints: 100m/200m/400m"

    def test_bw_omitted_when_measured_by_time(self):
        """A timed hold has no load to mark, so the BW token is dropped."""
        m = self._movement(
            "plank",
            [TrainingSet(reps=1, duration=timedelta(seconds=30)) for _ in range(3)],
        )
        assert m.to_ox() == "plank: PT30S 3x1"

    def test_bw_kept_without_duration_or_distance(self):
        m = self._movement("pullups", [TrainingSet(reps=10) for _ in range(5)])
        assert m.to_ox() == "pullups: BW 5x10"

    def test_rep_scheme_omitted_when_implied_by_set_count(self):
        """One set of one rep needs no "1x1" — the lone measure states it."""
        m = self._movement("run", [TrainingSet(reps=1, duration=timedelta(minutes=30))])
        assert "x" not in m.to_ox()

    def test_rep_scheme_kept_when_set_count_not_recoverable(self):
        """A collapsed measure loses the set count, so the rep scheme carries it."""
        m = self._movement(
            "sprints",
            [TrainingSet(reps=1, distance=100 * ureg.meter) for _ in range(6)],
        )
        assert m.to_ox() == "sprints: 100m 6x1"

    def test_rep_scheme_kept_when_reps_are_not_one(self):
        m = self._movement(
            "kb-swing",
            [TrainingSet(reps=10, duration=timedelta(seconds=30)) for _ in range(3)],
        )
        assert m.to_ox() == "kb-swing: PT30S 3x10"

    def test_duration_is_canonicalized(self):
        """90 seconds serializes as PT1M30S, not as typed."""
        m = self._movement(
            "hold", [TrainingSet(reps=1, duration=timedelta(seconds=90))]
        )
        assert m.to_ox() == "hold: PT1M30S"

    def test_partial_duration_raises(self):
        m = self._movement(
            "plank",
            [TrainingSet(reps=1, duration=timedelta(seconds=30)), TrainingSet(reps=1)],
        )
        with pytest.raises(ValueError, match="present on only some sets"):
            m.to_ox()

    @pytest.mark.parametrize(
        "line",
        [
            "run: PT30M",
            "run: 5km PT25M",
            "row: 500m PT2M 5x1",
            "sprints: 100m 6x1",
            "plank: PT30S 3x1",
            "weighted-plank: 45lb PT30S 3x1",
            "plank: PT30S/PT25S/PT20S",
            "sprints: 100m/200m/400m",
            "run: 3mi PT24M",
        ],
    )
    def test_round_trip_is_stable(self, line):
        """Each canonical form re-parses and re-emits unchanged."""
        assert reparse_movement(line).to_ox() == line

    def test_implied_distance_units_normalize(self):
        """Implied units are resolved on parse, so they come back explicit."""
        assert (
            reparse_movement("sprints: 100/200/400m").to_ox()
            == "sprints: 100m/200m/400m"
        )

    def test_bw_prefix_round_trips_without_the_token(self):
        m = reparse_movement("plank: BW PT30S 3x1")
        assert m.to_ox() == "plank: PT30S 3x1"
        assert [s.duration for s in m.sets] == [timedelta(seconds=30)] * 3


class TestCompletedSerialization:
    """`completed` is a bool internally and a `completed:` line on the page."""

    def _session(self, completed):
        m = Movement(name="pullups", sets=[TrainingSet(reps=10)], note=None)
        return TrainingSession(
            date=date(2025, 1, 10), completed=completed, name=None, movements=(m,)
        )

    def test_completed_entry_is_a_single_line(self):
        assert self._session(True).to_ox() == "2025-01-10 T pullups: BW 1x10"

    def test_planned_entry_needs_a_block(self):
        """`T` cannot say "planned", so planning forces the block form."""
        out = self._session(False).to_ox()
        assert out.splitlines()[:3] == [
            "@session",
            "date: 2025-01-10",
            "completed: false",
        ]

    def test_completed_true_is_left_implicit(self):
        m = Movement(name="squat", sets=[TrainingSet(reps=5)], note=None)
        s = TrainingSession(
            date=date(2025, 1, 10),
            completed=True,
            name="Lower Day",
            movements=(m,),
        )
        assert "completed:" not in s.to_ox()


class TestSessionSrpe:
    """TrainingSession carries sRPE and emits it from to_ox()."""

    def _session(self, **kwargs):
        m = Movement(name="squat", sets=[TrainingSet(reps=5)], note=None)
        kwargs.setdefault("name", "Lower Strength")
        return TrainingSession(
            date=date(2025, 1, 6), completed=True, movements=(m,), **kwargs
        )

    def test_fields_default_to_none(self):
        s = self._session()
        assert s.srpe_rating is None
        assert s.srpe_duration is None
        assert s.srpe_note is None

    def test_emits_srpe_line(self):
        s = self._session(srpe_rating=5, srpe_duration=timedelta(minutes=45))
        assert "srpe: 5 PT45M" in s.to_ox()

    def test_emits_note(self):
        s = self._session(
            srpe_rating=5,
            srpe_duration=timedelta(minutes=45),
            srpe_note="felt strong",
        )
        assert 'srpe: 5 PT45M "felt strong"' in s.to_ox()

    def test_omitted_when_absent(self):
        assert "srpe" not in self._session().to_ox()

    def test_line_precedes_movements_and_notes(self):
        s = self._session(srpe_rating=5, srpe_duration=timedelta(minutes=45))
        lines = s.to_ox().split("\n")
        assert lines[3].startswith("srpe:")

    def test_round_trip(self):
        import tempfile
        from ox.cli import parse_file

        s = self._session(
            srpe_rating=8,
            srpe_duration=timedelta(hours=1, minutes=30),
            srpe_note="brutal",
        )
        f = Path(tempfile.mktemp(suffix=".ox"))
        f.write_text(s.to_ox() + "\n")
        parsed = parse_file(f).sessions[0]
        assert parsed.srpe_rating == 8
        assert parsed.srpe_duration == timedelta(hours=1, minutes=30)
        assert parsed.srpe_note == "brutal"
        assert parsed.to_ox() == s.to_ox()


class TestTrainingLog:
    """Test TrainingLog query methods."""

    @pytest.fixture
    def sample_log(self):
        """Create a sample training log for testing queries.

        Design: 2 sessions with overlapping and unique movements.
        """
        session1 = TrainingSession(
            date=date(2025, 1, 10),
            completed=True,
            name="Upper Day",
            movements=(
                Movement("pullups", [TrainingSet(10, None)], None),
                Movement("bench-press", [TrainingSet(5, 135 * ureg.pounds)], None),
            ),
        )

        session2 = TrainingSession(
            date=date(2025, 1, 12),
            completed=True,
            name="Lower Day",
            movements=(
                Movement("squat", [TrainingSet(5, 185 * ureg.pounds)], None),
                Movement(
                    "pullups", [TrainingSet(8, None)], None
                ),  # Same exercise, different day
            ),
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
        """Test completed_sessions property filters on the bool."""
        completed = sample_log.completed_sessions

        # Both sessions in sample_log are completed
        assert len(completed) == 2
        assert all(s.completed for s in completed)

    def test_planned_sessions_filter(self, sample_log):
        """Test planned_sessions property filters on the bool."""
        planned = sample_log.planned_sessions

        # No planned sessions in sample_log
        assert len(planned) == 0

    def test_mixed_sessions(self):
        """Test filtering with both completed and planned sessions."""
        completed = TrainingSession(
            date=date(2025, 1, 10),
            completed=True,
            name="Completed",
            movements=(Movement("pullups", [TrainingSet(10, None)], None),),
        )

        planned = TrainingSession(
            date=date(2025, 1, 11),
            completed=False,
            name="Planned",
            movements=(Movement("squat", [TrainingSet(5, 185 * ureg.pounds)], None),),
        )

        log = TrainingLog(sessions=(completed, planned))

        # Should have 1 completed, 1 planned
        assert len(log.completed_sessions) == 1
        assert len(log.planned_sessions) == 1
        assert log.completed_sessions[0].name == "Completed"
        assert log.planned_sessions[0].name == "Planned"

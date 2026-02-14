"""Data structures for training logs."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Iterator
from pint import Quantity

DATE_FORMAT = "%Y-%m-%d"
ITEM_FIELDS = ["weight", "rep_scheme", "time", "distance", "note"]


def _format_weight(weight: Quantity) -> str:
    """Format a Quantity as an ox weight string like '24kg' or '135lbs'."""
    unit_map = {"kilogram": "kg", "pound": "lbs"}
    unit_str = unit_map.get(str(weight.units), str(weight.units))
    mag = (
        int(weight.magnitude)
        if weight.magnitude == int(weight.magnitude)
        else weight.magnitude
    )
    return f"{mag}{unit_str}"


@dataclass(frozen=True, slots=True)
class Entry:
    """Base class for log entries.

    Attributes:
        date: Entry date
        flag: Entry status (*=completed, !=planned, W=weigh-in)
    """

    date: datetime.date
    flag: str


@dataclass(frozen=True, slots=True)
class TrainingSet:
    """A single set of an exercise.

    Attributes:
        reps: Number of repetitions
        weight: Weight used (optional), assumes bodyweight if no weight listed
    """

    reps: int
    weight: Optional[Quantity] = None

    @property
    def volume(self) -> Optional[Quantity]:
        """Calculate volume (reps * weight)."""
        return self.weight * self.reps if self.weight else None


@dataclass(frozen=True, slots=True)
class Movement:
    """An exercise with its sets and notes.

    Attributes:
        name: Exercise name (e.g., "kb-oh-press")
        sets: List of training sets
        note: Optional notes about the exercise
    """

    name: str
    sets: List[TrainingSet]
    note: Optional[str]

    @property
    def total_reps(self) -> int:
        """Total reps across all sets."""
        return sum(s.reps for s in self.sets)

    def total_volume(self) -> Optional[Quantity]:
        """Total volume across all sets."""
        volumes = [s.volume for s in self.sets if s.volume is not None]
        return sum(volumes) if volumes else None

    @property
    def top_set_weight(self) -> Optional[Quantity]:
        """Heaviest weight used across all sets."""
        weights = [s.weight for s in self.sets if s.weight is not None]
        return max(weights) if weights else None

    def to_ox(self, compact_reps: bool = False) -> str:
        """Serialize to ox format string (e.g., 'squat: 185lbs 5x5').

        Args:
            compact_reps: If True, always use NxR format when reps are uniform.
                If False (default), only use NxR when weight is uniform;
                use R/R/R when weights vary per set.
        """
        parts = []
        if self.sets:
            weights = [s.weight for s in self.sets]
            reps = [s.reps for s in self.sets]

            uniform_weight = all(w is None for w in weights) or all(
                w is not None and w == weights[0] for w in weights
            )

            if all(w is None for w in weights):
                parts.append("BW")
            elif uniform_weight:
                parts.append(_format_weight(weights[0]))
            else:
                parts.append(
                    "/".join(
                        _format_weight(w) if w is not None else "BW" for w in weights
                    )
                )

            use_compact = all(r == reps[0] for r in reps) and (
                compact_reps or uniform_weight
            )
            if use_compact:
                parts.append(f"{len(reps)}x{reps[0]}")
            else:
                parts.append("/".join(str(r) for r in reps))

        if self.note:
            parts.append(f'"{self.note}"')

        detail_str = " ".join(parts)
        return f"{self.name}: {detail_str}" if detail_str else f"{self.name}:"


@dataclass(frozen=True, slots=True)
class TrainingSession(Entry):
    """A training session containing one or more movements.

    Attributes:
        name: Session name (e.g., "Upper Day"), None for single-line entries
        movements: Tuple of Movement objects
        date: Inherited from Entry
        flag: Inherited from Entry
    """

    name: str = field()
    movements: tuple[Movement, ...]

    def to_ox(self) -> str:
        """Serialize to ox format string."""
        date_str = self.date.strftime(DATE_FORMAT)
        if self.name is None:
            return f"{date_str} {self.flag} {self.movements[0].to_ox()}"
        else:
            lines = ["@session"]
            lines.append(f"{date_str} {self.flag} {self.name}")
            for m in self.movements:
                lines.append(m.to_ox())
            lines.append("@end")
            return "\n".join(lines)


@dataclass
class TrainingLog:
    """A collection of training sessions with query methods.

    Attributes:
        sessions: Tuple of TrainingSession objects
    """

    sessions: tuple[TrainingSession, ...]

    @property
    def completed_sessions(self) -> tuple[TrainingSession, ...]:
        """Return only completed sessions (flag="*").

        Returns:
            Tuple of completed TrainingSession objects
        """
        return tuple(s for s in self.sessions if s.flag == "*")

    @property
    def planned_sessions(self) -> tuple[TrainingSession, ...]:
        """Return only planned sessions (flag="!").

        Returns:
            Tuple of planned TrainingSession objects
        """
        return tuple(s for s in self.sessions if s.flag == "!")

    def movements(self, name: Optional[str] = None) -> Iterator[tuple[date, Movement]]:
        """Iterate over movements, optionally filtered by name.

        Args:
            name: Exercise name to filter by (None returns all)

        Yields:
            Tuple of (date, Movement)
        """
        for session in self.sessions:
            for movement in session.movements:
                if name is None or movement.name == name:
                    yield session.date, movement

    def movement_history(self, name: str) -> list[tuple[date, Movement]]:
        """Get sorted history of a specific movement.

        Args:
            name: Exercise name

        Returns:
            List of (date, Movement) tuples sorted by date
        """
        return sorted(self.movements(name), key=lambda x: x[0])

    def most_recent_session(self, name: str) -> Movement:
        """Get most recent instance of a movement.

        Args:
            name: Exercise name

        Returns:
            Tuple of (date, Movement) for most recent session
        """
        return self.movement_history(name)[-1]

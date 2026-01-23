"""Data structures for training logs."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Iterator
from pint import Quantity

DATE_FORMAT = "%Y-%m-%d"
ITEM_FIELDS = ["weight", "rep_scheme", "time", "distance", "note"]


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
        return self.weight * self.reps  if self.weight else None


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

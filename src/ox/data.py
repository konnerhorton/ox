"""Data structures for training logs."""

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Iterator
from pint import Quantity

from ox.duration import format_iso_duration

DATE_FORMAT = "%Y-%m-%d"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    line: int  # 1-based line number
    col: int  # 0-based column
    end_line: int
    end_col: int
    message: str
    severity: str  # "error" | "warning"


@dataclass(frozen=True, slots=True)
class Note:
    text: str
    date: Optional[date] = (
        None  # set for standalone note_entry; None for in-session note_line
    )

    def to_ox(self) -> str:
        return f'{self.date.strftime(DATE_FORMAT)} note "{self.text}"'


@dataclass(frozen=True, slots=True)
class StoredQuery:
    name: str
    sql: str
    date: date


def _format_magnitude(quantity: Quantity) -> str:
    """Render a magnitude, dropping the decimal point when the value is whole."""
    mag = quantity.magnitude
    return str(int(mag) if mag == int(mag) else mag)


def _format_weight(weight: Quantity) -> str:
    """Format a Quantity as an ox weight string like '24kg' or '135lb'."""
    unit_map = {"kilogram": "kg", "pound": "lb"}
    unit_str = unit_map.get(str(weight.units), str(weight.units))
    return f"{_format_magnitude(weight)}{unit_str}"


# pint's canonical unit names are spelled out; the grammar accepts both these
# symbols and the long names, so emitting the symbol keeps lines terse.
_DISTANCE_SYMBOLS = {
    "meter": "m",
    "kilometer": "km",
    "centimeter": "cm",
    "millimeter": "mm",
    "inch": "in",
    "foot": "ft",
    "yard": "yd",
    "mile": "mi",
    "nautical_mile": "nmi",
}


def _format_distance(distance: Quantity) -> str:
    """Format a Quantity as an ox distance string like '500m' or '3mi'."""
    unit_str = str(distance.units)
    return f"{_format_magnitude(distance)}{_DISTANCE_SYMBOLS.get(unit_str, unit_str)}"


def _format_measure(values: list, format_one) -> Optional[str]:
    """Collapse a per-set field to a single token, or a `/`-list when it varies.

    Args:
        values: One entry per set, each the field's value or None
        format_one: Renders a single non-None value

    Returns:
        The serialized field, or None if no set carries it

    Raises:
        ValueError: If the field is present on some sets but not others. The
            .ox format has no token for "absent here", and the parser cannot
            produce this shape — every measure broadcasts across all sets.
    """
    present = [v is not None for v in values]
    if not any(present):
        return None
    if not all(present):
        raise ValueError(
            "Cannot serialize a measure present on only some sets: "
            f"{[format_one(v) if v is not None else None for v in values]}"
        )
    if all(v == values[0] for v in values):
        return format_one(values[0])
    return "/".join(format_one(v) for v in values)


@dataclass(frozen=True, slots=True)
class WeighIn:
    date: date
    weight: Quantity
    time_of_day: Optional[time] = None
    scale: Optional[str] = None

    def to_ox(self) -> str:
        date_str = self.date.strftime(DATE_FORMAT)
        w = _format_weight(self.weight)
        ts = f" T{self.time_of_day.strftime('%H:%M')}" if self.time_of_day else ""
        sc = f' "{self.scale}"' if self.scale else ""
        return f"{date_str} W {w}{ts}{sc}"


@dataclass(frozen=True, slots=True)
class Entry:
    """Base class for log entries.

    Attributes:
        date: Entry date
        completed: Whether the training actually happened. False marks a
            planned session and forces the block form, since a single-line
            entry has no way to say it.
    """

    date: datetime.date
    completed: bool


@dataclass(frozen=True, slots=True)
class TrainingSet:
    """A single set of an exercise.

    The four attributes are independent and may co-occur: a set can carry reps,
    weight, duration, and distance at once (e.g. `row: 500m PT2M 5x1`).

    Attributes:
        reps: Number of repetitions. Always present; a movement with no rep
            scheme yields a single set of reps=1.
        weight: Weight used (optional), assumes bodyweight if no weight listed
        duration: Time under load for this set (optional), e.g. an isometric hold
        distance: Distance covered in this set (optional)
    """

    reps: int
    weight: Optional[Quantity] = None
    duration: Optional[timedelta] = None
    distance: Optional[Quantity] = None

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

        Weight, distance, and duration each collapse to a single token when
        uniform across sets and expand to a `/`-list when they vary.

        Args:
            compact_reps: If True, always use NxR format when reps are uniform.
                If False (default), only use NxR when weight is uniform;
                use R/R/R when weights vary per set.
        """
        parts = []
        if self.sets:
            weights = [s.weight for s in self.sets]
            reps = [s.reps for s in self.sets]
            distance_str = _format_measure(
                [s.distance for s in self.sets], _format_distance
            )
            duration_str = _format_measure(
                [s.duration for s in self.sets], format_iso_duration
            )

            uniform_weight = all(w is None for w in weights) or all(
                w is not None and w == weights[0] for w in weights
            )

            if all(w is None for w in weights):
                # "BW" marks a bodyweight load. A set measured by distance or
                # time carries no load to mark, so the token is omitted there.
                if not (distance_str or duration_str):
                    parts.append("BW")
            elif uniform_weight:
                parts.append(_format_weight(weights[0]))
            else:
                parts.append(
                    "/".join(
                        _format_weight(w) if w is not None else "BW" for w in weights
                    )
                )

            if distance_str:
                parts.append(distance_str)
            if duration_str:
                parts.append(duration_str)

            # A progressive list already states the set count, so a rep scheme
            # of all-1s is redundant: "run: PT30M" beats "run: PT30M 1x1".
            implied_sets = max(
                (p.count("/") + 1 for p in parts if p != "BW"), default=0
            )
            reps_implied = (
                all(r == 1 for r in reps)
                and (distance_str or duration_str)
                and implied_sets == len(reps)
            )

            use_compact = all(r == reps[0] for r in reps) and (
                compact_reps or uniform_weight
            )
            if reps_implied:
                pass
            elif use_compact:
                parts.append(f"{len(reps)}x{reps[0]}")
            else:
                parts.append("/".join(str(r) for r in reps))

        if self.note:
            parts.append(f'"{self.note}"')

        detail_str = " ".join(parts)
        return f"{self.name}: {detail_str}" if detail_str else f"{self.name}:"


@dataclass(frozen=True, slots=True)
class MovementDefinition:
    """A movement definition from an @movement block.

    Attributes:
        name: Movement name (e.g., "kb-oh-press")
        equipment: Equipment used (e.g., "kettlebell")
        tags: Movement tags (e.g., ("press", "upper"))
        note: Freeform description
        url: Reference URL
    """

    name: str
    equipment: Optional[str] = None
    tags: tuple[str, ...] = ()
    note: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TrainingSession(Entry):
    """A training session containing one or more movements.

    Attributes:
        movements: Tuple of Movement objects
        name: Session name (e.g., "Upper Day"), None for ad hoc sessions
        notes: Freeform notes attached to the session
        format: Free-text stub naming the session's shape, e.g. "5/3/1 wave"
        date: Inherited from Entry
        completed: Inherited from Entry
        srpe_rating: Session RPE, 1-10 perceived exertion for the whole session
        srpe_duration: Wall-clock length of the session
        srpe_note: Freeform comment on the session's exertion
    """

    movements: tuple[Movement, ...]
    name: Optional[str] = None
    notes: tuple[Note, ...] = ()
    format: Optional[str] = None
    srpe_rating: Optional[int] = None
    srpe_duration: Optional[timedelta] = None
    srpe_note: Optional[str] = None

    @property
    def _is_single_line(self) -> bool:
        """Whether this session fits on one line.

        Only a lone completed movement with no session-level metadata does:
        anything else needs a block to carry what the line cannot say.
        """
        return (
            self.name is None
            and self.completed
            and self.format is None
            and self.srpe_rating is None
            and not self.notes
            and len(self.movements) == 1
        )

    def to_ox(self) -> str:
        """Serialize to ox format string."""
        date_str = self.date.strftime(DATE_FORMAT)
        if self._is_single_line:
            return f"{date_str} T {self.movements[0].to_ox()}"

        lines = ["@session", f"date: {date_str}"]
        if self.name is not None:
            lines.append(f"name: {self.name}")
        if not self.completed:
            # true is the default, so it is left implicit
            lines.append("completed: false")
        if self.format is not None:
            lines.append(f"format: {self.format}")
        if self.srpe_rating is not None:
            srpe = f"srpe: {self.srpe_rating} {format_iso_duration(self.srpe_duration)}"
            if self.srpe_note:
                srpe += f' "{self.srpe_note}"'
            lines.append(srpe)
        for n in self.notes:
            lines.append(f'note: "{n.text}"')
        for m in self.movements:
            lines.append(m.to_ox())
        lines.append("@end")
        return "\n".join(lines)


@dataclass
class TrainingLog:
    """A collection of training sessions with query methods.

    Attributes:
        sessions: Tuple of TrainingSession objects
        diagnostics: Tuple of parse diagnostics (errors/warnings)
    """

    # TODO: Add attributes to docstring and improve description
    sessions: tuple[TrainingSession, ...]
    notes: tuple[Note, ...] = field(default_factory=tuple)
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)
    queries: tuple[StoredQuery, ...] = field(default_factory=tuple)
    weigh_ins: tuple[WeighIn, ...] = field(default_factory=tuple)
    plugin_paths: tuple[str, ...] = field(default_factory=tuple)
    movement_definitions: tuple[MovementDefinition, ...] = field(default_factory=tuple)

    @property
    def completed_sessions(self) -> tuple[TrainingSession, ...]:
        """Return only sessions that were carried out.

        Returns:
            Tuple of completed TrainingSession objects
        """
        return tuple(s for s in self.sessions if s.completed)

    @property
    def planned_sessions(self) -> tuple[TrainingSession, ...]:
        """Return only sessions that were planned but not carried out.

        Returns:
            Tuple of planned TrainingSession objects
        """
        return tuple(s for s in self.sessions if not s.completed)

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

"""Parse tree-sitter nodes into training data structures."""

from tree_sitter import Node
from datetime import datetime, timedelta
from ox.duration import parse_iso_duration
from ox.data import (
    DATE_FORMAT,
    Movement,
    MovementDefinition,
    Note,
    StoredQuery,
    TrainingSession,
    TrainingSet,
    WeighIn,
)
import re
from pint import Quantity
from ox.units import ureg


def get_or_last(lst, i):
    """Return the ith element if it exists, else the last element."""
    return lst[min(i, len(lst) - 1)]


def get_flag(raw_entry: Node) -> str:
    """Extract flag from node."""
    return raw_entry.child_by_field_name("flag").text.decode("utf-8")


def flag_to_completed(flag: str) -> bool:
    """Map the grammar's `*` / `!` flag onto the completed bool.

    Transitional: slice C replaces the flag with an explicit `completed:` line.
    """
    return flag == "*"


def get_name(raw_entry: Node) -> str:
    """Extract session name from node."""
    return raw_entry.child_by_field_name("name").text.decode("utf-8").strip().strip('"')


def get_date(raw_entry: Node) -> datetime.date:
    """Extract and parse date from node."""
    date_str = raw_entry.child_by_field_name("date").text.decode("utf-8")
    return datetime.strptime(date_str, DATE_FORMAT).date()


def get_details(raw_entry) -> dict[str, str]:
    """Extract details as dict of field names to values."""
    details = raw_entry.child_by_field_name("details")

    return {
        details.field_name_for_child(i): d.text.decode("utf-8")
        for i, d in enumerate(details.children)
    }


def get_item(raw_entry: Node) -> str:
    """Extract item name from node."""
    return raw_entry.child_by_field_name("item").text.decode("utf-8").strip().strip(":")


def get_note_text(node: Node) -> str:
    """Extract note text from a note_entry or note_line node."""
    return node.child_by_field_name("text").text.decode("utf-8").strip('"')


def get_srpe(
    raw_entry: Node,
) -> tuple[int | None, timedelta | None, str | None]:
    """Extract the session RPE from a session block's `srpe_line`, if it has one.

    Returns:
        Tuple of (rating, duration, note), all None when the block has no
        srpe_line. The rating node's text carries the keyword ("srpe: 5"),
        since the grammar fuses them into one token — see grammar.js.
    """
    line = next((c for c in raw_entry.children if c.type == "srpe_line"), None)
    if line is None:
        return None, None, None

    rating_text = line.child_by_field_name("rating").text.decode("utf-8")
    rating = int(rating_text.split(":", 1)[1])
    duration = parse_iso_duration(
        line.child_by_field_name("duration").text.decode("utf-8")
    )
    note_node = line.child_by_field_name("note")
    note = note_node.text.decode("utf-8").strip('"') if note_node else None
    return rating, duration, note


def _text_to_quantity(text: str, dimension: str) -> Quantity | None:
    """Convert a "<number><unit>" string to a Quantity of the given dimension.

    The unit is preserved as written — "135lb" stays in pounds, "5mi" in miles.
    Only the dimension is constrained, and dimensions are unit-system agnostic,
    so imperial and metric units are equally accepted.

    Args:
        text: A magnitude immediately followed by a unit, e.g. "24kg" or "5km"
        dimension: Required pint dimension, "[mass]" or "[length]"

    Returns:
        The Quantity, or None if malformed, unknown, or the wrong dimension
    """
    match = re.match(r"^(\d+(?:\.\d+)?)(\w+)$", text)
    if not match:
        return None
    magnitude = float(match[1])
    unit_str = match[2]
    try:
        unit = ureg.parse_units(unit_str)
        if not unit.dimensionality == dimension:
            return None
        return magnitude * unit
    except Exception:
        return None


def weight_text_to_quantity(weight_text: str) -> Quantity:
    """Convert weight string like "24kg" or "135lb" to Quantity."""
    return _text_to_quantity(weight_text, "[mass]")


def distance_text_to_quantity(distance_text: str) -> Quantity:
    """Convert distance string like "5km" or "3mi" to Quantity."""
    return _text_to_quantity(distance_text, "[length]")


def _resolve_implied_units(segments: list[str], is_special) -> list[str]:
    """Resolve omitted units in a progressive sequence.

    A segment without a unit inherits the nearest succeeding unit, so
    "160/185/210lb" resolves to ["160lb", "185lb", "210lb"]. Segments for which
    is_special() returns True pass through untouched.
    """
    carried_unit = None
    resolved = [None] * len(segments)
    for i in range(len(segments) - 1, -1, -1):
        segment = segments[i]
        if is_special(segment):
            resolved[i] = segment
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)(\w+)?$", segment)
        if not m:
            resolved[i] = segment
            continue
        num, unit = m.group(1), m.group(2)
        if unit is None:
            # No succeeding unit to inherit: leave as-is, fails downstream.
            resolved[i] = segment if carried_unit is None else f"{num}{carried_unit}"
        else:
            carried_unit = unit
            resolved[i] = segment
    return resolved


def process_weights(weight_str: str) -> list[Quantity]:
    """Parse weight string into list of Quantity objects.

    Handles formats like "24kg", "24kg+32kg", "24kg/32kg/48kg".

    In progressive sequences, a segment may omit its unit; it inherits the
    nearest succeeding unit. E.g. "160/185/210lb" → three lb weights;
    "60/70kg/160/180lb" → [60kg, 70kg, 160lb, 180lb].
    """
    resolved = _resolve_implied_units(
        weight_str.split("/"),
        is_special=lambda w: w == "BW" or "+" in w,
    )

    weight_objs = []
    for w in resolved:
        if "+" in w:
            result = sum([weight_text_to_quantity(i) for i in w.split("+")])
            weight_objs.append(result)
        else:
            result = weight_text_to_quantity(w)
            weight_objs.append(result)

    return weight_objs


def process_distances(distance_str: str) -> list[Quantity]:
    """Parse distance string into list of Quantity objects.

    Handles "5km" and progressive forms like "100m/200m/400m". As with weights,
    a segment may omit its unit and inherits the nearest succeeding one, so
    "100/200/400m" → three metre distances.
    """
    resolved = _resolve_implied_units(
        distance_str.split("/"),
        is_special=lambda d: False,
    )
    return [distance_text_to_quantity(d) for d in resolved]


def process_durations(duration_str: str) -> list[timedelta]:
    """Parse duration string into list of timedeltas.

    Handles "PT30M" and progressive forms like "PT30S/PT25S/PT20S".
    """
    return [parse_iso_duration(d) for d in duration_str.split("/")]


def process_details(details: dict[str, str]) -> tuple[list[TrainingSet], str | None]:
    """Parse item details into training sets and notes.

    The rep scheme determines the set count when present. Otherwise the count is
    the longest of the progressive weight/duration/distance lists, defaulting to
    a single set — so "run: PT30M" is one 30-minute set. Each of weight,
    duration, and distance broadcasts across the sets: given once it applies to
    all, given as a /-list it maps per set.

    Args:
        details: Dict of detail field names to values

    Returns:
        Tuple of (sets, note)
    """
    note = None
    if "note" in details.keys():
        note = re.sub(
            "'|\"",
            "",
            details["note"],
        ).strip()

    reps = None
    if "rep_scheme" in details.keys():
        reps_raw = details["rep_scheme"]
        if "/" in reps_raw:
            reps = [int(r) for r in reps_raw.split("/")]
        elif "x" in reps_raw:
            s, r = reps_raw.split("x")
            reps = [int(r) for _ in range(int(s))]

    weights = process_weights(details["weight"]) if "weight" in details else None
    durations = (
        process_durations(details["duration"]) if "duration" in details else None
    )
    distances = (
        process_distances(details["distance"]) if "distance" in details else None
    )

    measures = [m for m in (weights, durations, distances) if m]
    if reps is not None:
        set_count = len(reps)
        if any(len(m) > 1 and len(m) != set_count for m in measures):
            print("potentially incomplete entry, assume same value across sets")
    elif measures:
        # No rep scheme: one set per progressive value, each a single rep.
        set_count = max(len(m) for m in measures)
    else:
        return [], note

    sets = [
        TrainingSet(
            reps=get_or_last(reps, i) if reps is not None else 1,
            weight=get_or_last(weights, i) if weights else None,
            duration=get_or_last(durations, i) if durations else None,
            distance=get_or_last(distances, i) if distances else None,
        )
        for i in range(set_count)
    ]

    return sets, note


def process_singleline_completed_session(
    raw_entry: Node,
) -> tuple[datetime.date, tuple[Movement, ...]]:
    """Process a completed single-line entry.

    Returns:
        Tuple of (date, movements)
    """
    item = get_item(raw_entry)
    date = get_date(raw_entry)
    details = get_details(raw_entry)
    sets, note = process_details(details)
    movement = tuple([Movement(name=item, sets=sets, note=note)])
    return date, movement


def process_session_block_completed(
    raw_entry: Node,
) -> tuple[
    datetime.date,
    str,
    list[Movement],
    tuple[Note, ...],
    tuple[int | None, timedelta | None, str | None],
]:
    """Process a completed session block.

    Returns:
        Tuple of (date, name, movements, notes, srpe)
    """
    movements = []
    date = get_date(raw_entry)
    name = get_name(raw_entry)
    item_lines = [c for c in raw_entry.children if c.type == "item_line"]
    for m in item_lines:
        item = get_item(m)
        details = get_details(m)
        sets, note = process_details(details)
        movements.append(Movement(name=item, sets=sets, note=note))
    note_lines = [c for c in raw_entry.children if c.type == "note_line"]
    notes = tuple(Note(text=get_note_text(n)) for n in note_lines)
    return date, name, movements, notes, get_srpe(raw_entry)


def process_singleline_entry(raw_entry: Node) -> TrainingSession | None:
    """Process a single-line entry node.

    Returns:
        TrainingSession or None (for weigh-ins, not yet implemented)
    """
    flag = get_flag(raw_entry)

    if flag in ["*", "!"]:
        date, movement = process_singleline_completed_session(raw_entry)
        return TrainingSession(
            name=movement[0].name,
            date=date,
            completed=flag_to_completed(flag),
            movements=movement,
        )
    return None


def process_session_block_pending(raw_entry: Node) -> TrainingSession | None:
    """Process a pending session block (completed=False).

    Deferred: planned sessions are parsed but not materialized for analysis.
    See SPEC.md "What's incomplete".
    """
    return None


def process_session_block(raw_entry: Node) -> TrainingSession | None:
    """Process a session block node.

    Returns:
        TrainingSession or None (for pending sessions)
    """
    flag = get_flag(raw_entry)

    if flag in ["*", "!"]:
        date, name, movements, notes, srpe = process_session_block_completed(raw_entry)
        srpe_rating, srpe_duration, srpe_note = srpe
        return TrainingSession(
            name=name,
            completed=flag_to_completed(flag),
            date=date,
            movements=tuple(movements),
            notes=notes,
            srpe_rating=srpe_rating,
            srpe_duration=srpe_duration,
            srpe_note=srpe_note,
        )
    else:
        return process_session_block_pending(raw_entry)


def process_note_entry(node: Node) -> Note:
    """Process a standalone note_entry node."""
    return Note(text=get_note_text(node), date=get_date(node))


def process_weigh_in_entry(node: Node) -> WeighIn:
    """Process a weigh_in_entry node."""
    from datetime import time

    entry_date = get_date(node)
    weight_text = node.child_by_field_name("weight").text.decode("utf-8")
    weight = weight_text_to_quantity(weight_text)
    tod_node = node.child_by_field_name("time_of_day")
    time_of_day = None
    if tod_node:
        time_of_day = time.fromisoformat(tod_node.text.decode("utf-8")[1:])  # strip T
    scale_node = node.child_by_field_name("scale")
    scale = scale_node.text.decode("utf-8").strip('"') if scale_node else None
    return WeighIn(date=entry_date, weight=weight, time_of_day=time_of_day, scale=scale)


def process_query_entry(node: Node) -> StoredQuery:
    """Process a query_entry node."""
    date = get_date(node)
    name = node.child_by_field_name("name").text.decode("utf-8").strip('"')
    sql = node.child_by_field_name("sql").text.decode("utf-8").strip('"')
    return StoredQuery(name=name, sql=sql, date=date)


def process_movement_block(node: Node) -> MovementDefinition:
    """Process a movement_block node into a MovementDefinition."""
    name = node.child_by_field_name("name").text.decode("utf-8")
    metadata: dict[str, str] = {}
    for child in node.children:
        if child.type != "metadata_line":
            continue
        key_node = child.child_by_field_name("key")
        value_node = child.child_by_field_name("value")
        if key_node is None or value_node is None:
            continue
        metadata[key_node.text.decode("utf-8")] = value_node.text.decode(
            "utf-8"
        ).strip()

    tags_raw = metadata.get("tags") or metadata.get("tag")
    tags: tuple[str, ...] = ()
    if tags_raw:
        tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip())

    return MovementDefinition(
        name=name,
        equipment=metadata.get("equipment"),
        tags=tags,
        note=metadata.get("note"),
        url=metadata.get("url"),
    )


def process_include_directive(node: Node) -> str:
    """Extract file path from an include_directive node."""
    raw = node.child_by_field_name("path").text.decode("utf-8")
    return raw.strip('"')


def process_plugin_directive(node: Node) -> str:
    """Extract file path from a plugin_directive node."""
    raw = node.child_by_field_name("path").text.decode("utf-8")
    return raw.strip('"')


def process_node(node: Node) -> TrainingSession | Note | StoredQuery | None:
    """Process any node type and return appropriate data structure.

    Args:
        node: Tree-sitter node to process

    Returns:
        TrainingSession, Note, StoredQuery, or None
    """
    if node.type == "singleline_entry":
        return process_singleline_entry(node)
    if node.type == "session_block":
        return process_session_block(node)
    if node.type == "note_entry":
        return process_note_entry(node)
    if node.type == "query_entry":
        return process_query_entry(node)
    if node.type == "weigh_in_entry":
        return process_weigh_in_entry(node)
    if node.type == "movement_block":
        return process_movement_block(node)
    # Skip comments, template_block for now
    return None

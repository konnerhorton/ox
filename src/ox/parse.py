"""Parse tree-sitter nodes into training data structures."""

from tree_sitter import Node
from datetime import datetime
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


def weight_text_to_quantity(weight_text: str) -> Quantity:
    """Convert weight string like "24kg" to Quantity."""
    match = re.match(r"^(\d+(?:\.\d+)?)(\w+)$", weight_text)
    if match:
        magnitude = float(match[1])
        unit_str = match[2]
        try:
            unit = ureg.parse_units(unit_str)
            if not unit.dimensionality == ureg.kilogram.dimensionality:
                return None
            return magnitude * unit
        except Exception:
            return None
    else:
        return None


def process_weights(weight_str: str) -> list[Quantity]:
    """Parse weight string into list of Quantity objects.

    Handles formats like "24kg", "24kg+32kg", "24kg/32kg/48kg".

    In progressive sequences, a segment may omit its unit; it inherits the
    nearest succeeding unit. E.g. "160/185/210lb" → three lb weights;
    "60/70kg/160/180lb" → [60kg, 70kg, 160lb, 180lb].
    """
    weight_str_split = weight_str.split("/")
    # Right-to-left pass to resolve implied units.
    carried_unit = None
    resolved = [None] * len(weight_str_split)
    for i in range(len(weight_str_split) - 1, -1, -1):
        w = weight_str_split[i]
        if w == "BW" or "+" in w:
            resolved[i] = w
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)(\w+)?$", w)
        if not m:
            resolved[i] = w
            continue
        num, unit = m.group(1), m.group(2)
        if unit is None:
            if carried_unit is None:
                resolved[i] = w  # will fail to parse downstream
            else:
                resolved[i] = f"{num}{carried_unit}"
        else:
            carried_unit = unit
            resolved[i] = w

    weight_objs = []
    for w in resolved:
        if "+" in w:
            result = sum([weight_text_to_quantity(i) for i in w.split("+")])
            weight_objs.append(result)
        else:
            result = weight_text_to_quantity(w)
            weight_objs.append(result)

    return weight_objs


def process_details(details: dict[str, str]) -> tuple[list[TrainingSet], str | None]:
    """Parse item details into training sets and notes.

    Args:
        details: Dict of detail field names to values

    Returns:
        Tuple of (sets, note)
    """
    weights = None
    reps = None
    note = None
    sets = []
    if "rep_scheme" in details.keys():
        reps_raw = details["rep_scheme"]
        if "/" in reps_raw:
            reps = [int(r) for r in details["rep_scheme"].split("/")]
        elif "x" in reps_raw:
            s, r = reps_raw.split("x")
            reps = [int(r) for i in range(int(s))]

    if "weight" in details.keys():
        weights = process_weights(details["weight"])
    if weights and reps:
        if len(weights) > 1 and len(weights) != len(reps):
            print("potentially incomplete entry, assume same weight across sets")
        for i, r in enumerate(reps):
            training_set = TrainingSet(reps=r, weight=get_or_last(weights, i))
            sets.append(training_set)
    if "note" in details.keys():
        note = re.sub(
            "'|\"",
            "",
            details["note"],
        ).strip()

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
) -> tuple[datetime.date, str, list[Movement], tuple[Note, ...]]:
    """Process a completed session block.

    Returns:
        Tuple of (date, name, movements, notes)
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
    return date, name, movements, notes


def process_singleline_entry(raw_entry: Node) -> TrainingSession | None:
    """Process a single-line entry node.

    Returns:
        TrainingSession or None (for weigh-ins, not yet implemented)
    """
    flag = get_flag(raw_entry)

    if flag in ["*", "!"]:
        date, movement = process_singleline_completed_session(raw_entry)
        return TrainingSession(
            name=movement[0].name, date=date, flag=flag, movements=movement
        )
    return None


def process_session_block_pending(raw_entry: Node) -> TrainingSession | None:
    """Process a pending session block (flag='!').

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
        date, name, movements, notes = process_session_block_completed(raw_entry)
        return TrainingSession(
            name=name, flag=flag, date=date, movements=tuple(movements), notes=notes
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

"""Parse tree-sitter nodes into training data structures."""

from tree_sitter import Node
from datetime import datetime
from ox.data import DATE_FORMAT, Movement, TrainingSession, TrainingSet
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


def weight_text_to_quantity(weight_text: str) -> Quantity:
    """Convert weight string like "24kg" to Quantity."""
    match = re.match(r"^(\d+)(\w+)$|'BW'", weight_text)
    if match:
        if match[2] == "kg":
            return float(match[1]) * ureg.kilogram
        elif match[2] == "lbs":
            return float(match[1]) * ureg.pounds
        else:
            return None
    else:
        return None


def process_weights(weight_str: str) -> list[Quantity]:
    """Parse weight string into list of Quantity objects.

    Handles formats like "24kg", "24kg+32kg", "24kg/32kg/48kg".
    """
    weight_str_split = weight_str.split("/")
    weight_objs = []
    for w in weight_str_split:
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
) -> tuple[datetime.date, str, list[Movement]]:
    """Process a completed session block.

    Returns:
        Tuple of (date, name, movements)
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
    return date, name, movements


def process_singleline_entry(raw_entry: Node) -> TrainingSession | None:
    """Process a single-line entry node.

    Returns:
        TrainingSession or None (for weigh-ins, not yet implemented)
    """
    flag = get_flag(raw_entry)

    if flag == "W":
        # TODO: implement weigh-in processing
        return None
    if flag in ["*", "!"]:
        date, movement = process_singleline_completed_session(raw_entry)
        return TrainingSession(name=None, date=date, flag=flag, movements=movement)
    return None


def process_session_block_pending(raw_entry: Node) -> TrainingSession | None:
    """Process a pending session block (flag='!').

    Not yet implemented.
    """
    # TODO: implement pending session processing
    pass


def process_session_block(raw_entry: Node) -> TrainingSession | None:
    """Process a session block node.

    Returns:
        TrainingSession or None (for pending sessions)
    """
    flag = get_flag(raw_entry)

    if flag in ["*", "!"]:
        date, name, movements = process_session_block_completed(raw_entry)
        return TrainingSession(
            name=name, flag=flag, date=date, movements=tuple(movements)
        )
    else:
        # TODO: handle pending sessions
        return process_session_block_pending(raw_entry)


def process_node(node: Node) -> TrainingSession | None:
    """Process any node type and return appropriate data structure.

    Args:
        node: Tree-sitter node to process

    Returns:
        TrainingSession or None
    """
    if node.type == "singleline_entry":
        return process_singleline_entry(node)
    if node.type == "session_block":
        return process_session_block(node)
    # Skip comments, exercise_block, template_block for now
    return None

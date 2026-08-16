"""ISO 8601 duration parsing and formatting.

Durations appear in .ox files as the `PT#H#M#S` subset of ISO 8601 — no date
components, since a training duration is never measured in days or months.
"""

import re
from datetime import timedelta

# Permissive on parse: accepts a fractional value in any position, which is a
# superset of what the grammar's `duration` token emits.
_ISO_DURATION = re.compile(
    r"PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$",
    re.IGNORECASE,
)


def parse_iso_duration(text: str) -> timedelta:
    """Parse an ISO 8601 duration string into a timedelta.

    Args:
        text: Duration string such as "PT30M", "PT1H30M15S", or "PT30.5S"

    Returns:
        The equivalent timedelta

    Raises:
        ValueError: If the string is not a valid PT-form duration, or carries
            no components at all (bare "PT")
    """
    m = _ISO_DURATION.match(text.strip())
    if not m or not any(m.groups()):
        raise ValueError(f"Invalid ISO 8601 duration: {text}")
    hours, minutes, seconds = (float(g or 0) for g in m.groups())
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def format_iso_duration(td: timedelta) -> str:
    """Serialize a timedelta back to canonical ISO 8601 PT form.

    Zero-valued components are omitted, so 90 seconds renders as "PT1M30S".
    A zero duration renders as "PT0S". Round-trips with parse_iso_duration.

    Args:
        td: The duration to serialize

    Returns:
        Duration string such as "PT30M" or "PT1H30M15S"

    Raises:
        ValueError: If the duration is negative
    """
    total = td.total_seconds()
    if total < 0:
        raise ValueError(f"Cannot format a negative duration: {td}")
    if total == 0:
        return "PT0S"

    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = []
    if hours:
        parts.append(f"{int(hours)}H")
    if minutes:
        parts.append(f"{int(minutes)}M")
    if seconds:
        # Drop the decimal point when the value is whole: 30.0 -> "30"
        parts.append(f"{int(seconds) if seconds == int(seconds) else seconds}S")
    return "PT" + "".join(parts)

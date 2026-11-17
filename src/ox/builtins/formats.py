"""Session format plugin for ox.

Lists the `format:` values in the log, what each means under the format
vocabulary (`ox.formats`), and any value that doesn't fit it. Values outside the
vocabulary still load; this plugin only reports them.

Usage:
    formats                 # each unique format value, its meaning and any problem
    formats -o problems     # only the values with a problem
    formats -o vocabulary   # the vocabulary itself
"""

from collections import defaultdict

from ox.formats import VOCABULARY, check_movement_count, parse_format
from ox.plugins import PluginContext, TableResult

_OUTPUTS = ("formats", "problems", "vocabulary")
_COLUMNS = ["format", "sessions", "meaning", "problem"]


def formats_report(ctx: PluginContext, output: str = "formats") -> TableResult:
    """Report the log's session formats, or the format vocabulary.

    Args:
        ctx: Plugin context; only `ctx.log` is used
        output: "formats" (every unique value), "problems" (only values with a
            problem) or "vocabulary" (the rules)

    Returns:
        A TableResult. For "formats" and "problems", one row per unique value as
        written, most-used first: format, sessions, meaning, problem.

    Raises:
        ValueError: If `output` is not one of the three views
    """
    if output not in _OUTPUTS:
        raise ValueError("output must be 'formats', 'problems', or 'vocabulary'")

    if output == "vocabulary":
        return TableResult(
            columns=["format", "description"],
            rows=[(rule.usage, rule.description) for rule in VOCABULARY],
        )

    sessions_by_value = defaultdict(list)
    for session in ctx.log.sessions:
        if session.format:
            sessions_by_value[session.format].append(session)

    rows = []
    for value, sessions in sessions_by_value.items():
        parsed = parse_format(value)
        problem = parsed.problem or ""
        if not problem:
            mismatched = sorted(
                s.date
                for s in sessions
                if not check_movement_count(parsed, len(s.movements))
            )
            if mismatched:
                dates = ", ".join(d.isoformat() for d in mismatched)
                problem = (
                    f"groups add up to {sum(parsed.groups)}, "
                    f"not the movement count on {dates}"
                )
        if output == "problems" and not problem:
            continue
        rows.append((value, len(sessions), parsed.meaning, problem))

    rows.sort(key=lambda row: (-row[1], row[0]))
    return TableResult(columns=list(_COLUMNS), rows=rows)


def register():
    return [
        {
            "name": "formats",
            "fn": formats_report,
            "description": "Session format values, their meaning, and problems",
            "params": [
                {
                    "name": "output",
                    "type": str,
                    "default": "formats",
                    "required": False,
                    "short": "o",
                },
            ],
        }
    ]

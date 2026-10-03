"""Lint utilities for ox training log files."""

import re

from ox.data import Diagnostic

# The pre-0.6 quoted sRPE form, e.g. `srpe: "5; PT45M"`.
OLD_SRPE = re.compile(r'srpe:\s*"')

OLD_SRPE_MESSAGE = (
    'Old sRPE syntax: write `srpe: 5 PT45M ["note"]`, '
    "or convert the log with scripts/migrate_ox.py"
)


def collect_diagnostics(tree) -> tuple[Diagnostic, ...]:
    """Walk a tree-sitter tree and collect ERROR/MISSING nodes as Diagnostics."""
    diagnostics = []

    def visit(node):
        if node.type == "srpe_line" and node.has_error:
            text = node.text.decode("utf-8").rstrip("\n")
            if OLD_SRPE.match(text):
                diagnostics.append(
                    Diagnostic(
                        line=node.start_point[0] + 1,
                        col=node.start_point[1],
                        end_line=node.start_point[0] + 1,
                        end_col=node.start_point[1] + len(text),
                        message=OLD_SRPE_MESSAGE,
                        severity="error",
                    )
                )
                return  # one diagnostic for the line, not one per ERROR node
        if node.type == "ERROR":
            diagnostics.append(
                Diagnostic(
                    line=node.start_point[0] + 1,
                    col=node.start_point[1],
                    end_line=node.end_point[0] + 1,
                    end_col=node.end_point[1],
                    message="Syntax error",
                    severity="error",
                )
            )
            return  # don't recurse into ERROR subtrees
        if node.is_missing:
            diagnostics.append(
                Diagnostic(
                    line=node.start_point[0] + 1,
                    col=node.start_point[1],
                    end_line=node.end_point[0] + 1,
                    end_col=node.end_point[1],
                    message=f"Missing {node.type}",
                    severity="error",
                )
            )
            return
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return tuple(diagnostics)

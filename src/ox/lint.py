"""Lint utilities for ox training log files."""

from ox.data import Diagnostic


def collect_diagnostics(tree) -> tuple[Diagnostic, ...]:
    """Walk a tree-sitter tree and collect ERROR/MISSING nodes as Diagnostics."""
    diagnostics = []

    def visit(node):
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

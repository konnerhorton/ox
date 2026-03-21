"""Language Server Protocol implementation for ox."""

import re
from pathlib import Path

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer
from tree_sitter import Language, Parser
import tree_sitter_ox

from ox.lint import collect_diagnostics as _collect_diagnostics

server = LanguageServer(name="ox-lsp", version="0.1.0")

# Initialize tree-sitter parser
_language = Language(tree_sitter_ox.language())
_parser = Parser(_language)


def get_diagnostics(text: str) -> list[lsp.Diagnostic]:
    """Parse text and return diagnostics for any errors."""
    tree = _parser.parse(bytes(text, encoding="utf-8"))
    ox_diagnostics = _collect_diagnostics(tree)
    return [
        lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=d.line - 1, character=d.col),
                end=lsp.Position(line=d.end_line - 1, character=d.end_col),
            ),
            message=d.message,
            severity=lsp.DiagnosticSeverity.Error,
            source="ox",
        )
        for d in ox_diagnostics
    ]


def _validate_includes(tree, doc_uri: str) -> list[lsp.Diagnostic]:
    """Check include_directive nodes for missing files."""
    diagnostics = []
    doc_path = Path(doc_uri.replace("file://", ""))
    for node in tree.root_node.children:
        if node.type == "include_directive":
            path_node = node.child_by_field_name("path")
            if path_node:
                inc_path = path_node.text.decode("utf-8").strip('"')
                resolved = (doc_path.parent / inc_path).resolve()
                if not resolved.exists():
                    diagnostics.append(
                        lsp.Diagnostic(
                            range=lsp.Range(
                                start=lsp.Position(
                                    line=node.start_point[0],
                                    character=path_node.start_point[1],
                                ),
                                end=lsp.Position(
                                    line=node.end_point[0],
                                    character=path_node.end_point[1],
                                ),
                            ),
                            message=f"Included file not found: {inc_path}",
                            severity=lsp.DiagnosticSeverity.Warning,
                            source="ox",
                        )
                    )
    return diagnostics


def publish_diagnostics(uri: str, diagnostics: list[lsp.Diagnostic]):
    """Publish diagnostics to the client."""
    server.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )


def _get_all_diagnostics(text: str, uri: str) -> list[lsp.Diagnostic]:
    """Get parse diagnostics and include validation diagnostics."""
    tree = _parser.parse(bytes(text, encoding="utf-8"))
    diagnostics = get_diagnostics(text)
    diagnostics.extend(_validate_includes(tree, uri))
    return diagnostics


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: lsp.DidOpenTextDocumentParams):
    """Handle document open - publish initial diagnostics."""
    text = params.text_document.text
    diagnostics = _get_all_diagnostics(text, params.text_document.uri)
    publish_diagnostics(params.text_document.uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: lsp.DidChangeTextDocumentParams):
    """Handle document change - update diagnostics."""
    document = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = _get_all_diagnostics(document.source, params.text_document.uri)
    publish_diagnostics(params.text_document.uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(params: lsp.DidSaveTextDocumentParams):
    """Handle document save - refresh diagnostics."""
    document = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = _get_all_diagnostics(document.source, params.text_document.uri)
    publish_diagnostics(params.text_document.uri, diagnostics)


def _collect_movement_names(tree) -> set[str]:
    """Walk the tree and collect all movement names from item fields."""
    names: set[str] = set()
    for node in tree.root_node.children:
        if node.type == "singleline_entry":
            item = node.child_by_field_name("item")
            if item:
                names.add(item.text.decode("utf-8"))
        elif node.type in ("session_block", "template_block"):
            for child in node.children:
                if child.type == "item_line":
                    item = child.child_by_field_name("item")
                    if item:
                        names.add(item.text.decode("utf-8"))
    return names


_SINGLELINE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}\s+[*!]\s+")


def _cursor_wants_movement(text: str, line: int, col: int, tree) -> bool:
    """Check whether the cursor position is a movement-name context."""
    lines = text.split("\n")
    if line >= len(lines):
        return False
    current_line = lines[line]

    # Context A: singleline entry — line matches date+flag prefix, cursor after it
    m = _SINGLELINE_PREFIX.match(current_line)
    if m and col >= m.end():
        # Make sure we're not inside a session/template block
        node = tree.root_node.descendant_for_point_range((line, col), (line, col))
        while node:
            if node.type in ("session_block", "template_block"):
                return False
            node = node.parent
        return True

    # Context B: inside a session/template block on an item line
    stripped = current_line.lstrip()
    if stripped.startswith("@") or stripped.startswith("note:"):
        return False
    node = tree.root_node.descendant_for_point_range((line, col), (line, col))
    while node:
        if node.type in ("session_block", "template_block"):
            # Exclude the header line (date/flag/name line)
            header_line = node.start_point[0] + 1  # header is 1 line after @session
            if line == header_line:
                return False
            return True
        node = node.parent
    return False


@server.feature(lsp.TEXT_DOCUMENT_FOLDING_RANGE)
def folding_range(params: lsp.FoldingRangeParams) -> list[lsp.FoldingRange]:
    """Provide folding ranges between comment lines."""
    document = server.workspace.get_text_document(params.text_document.uri)
    lines = document.source.split("\n")
    comment_lines = [i for i, line in enumerate(lines) if line.lstrip().startswith("#")]

    ranges: list[lsp.FoldingRange] = []
    for idx, start in enumerate(comment_lines):
        if idx + 1 < len(comment_lines):
            end = comment_lines[idx + 1] - 1
        else:
            end = len(lines) - 1
        # Skip trailing blank lines
        while end > start and not lines[end].strip():
            end -= 1
        if end > start:
            ranges.append(
                lsp.FoldingRange(
                    start_line=start,
                    end_line=end,
                    kind=lsp.FoldingRangeKind.Region,
                )
            )
    return ranges


@server.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=[" "]),
)
def completion(params: lsp.CompletionParams) -> lsp.CompletionList:
    """Provide movement name completions."""
    document = server.workspace.get_text_document(params.text_document.uri)
    text = document.source
    tree = _parser.parse(bytes(text, encoding="utf-8"))
    line = params.position.line
    col = params.position.character

    if not _cursor_wants_movement(text, line, col, tree):
        return lsp.CompletionList(is_incomplete=False, items=[])

    names = _collect_movement_names(tree)
    items = [
        lsp.CompletionItem(
            label=name,
            insert_text=name + ": ",
            kind=lsp.CompletionItemKind.Value,
            detail="movement",
        )
        for name in sorted(names)
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


def main():
    """Run the language server."""
    server.start_io()


if __name__ == "__main__":
    main()

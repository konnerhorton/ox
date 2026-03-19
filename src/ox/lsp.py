"""Language Server Protocol implementation for ox."""

import re

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


def publish_diagnostics(uri: str, diagnostics: list[lsp.Diagnostic]):
    """Publish diagnostics to the client."""
    server.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: lsp.DidOpenTextDocumentParams):
    """Handle document open - publish initial diagnostics."""
    text = params.text_document.text
    diagnostics = get_diagnostics(text)
    publish_diagnostics(params.text_document.uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: lsp.DidChangeTextDocumentParams):
    """Handle document change - update diagnostics."""
    document = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = get_diagnostics(document.source)
    publish_diagnostics(params.text_document.uri, diagnostics)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(params: lsp.DidSaveTextDocumentParams):
    """Handle document save - refresh diagnostics."""
    document = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = get_diagnostics(document.source)
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

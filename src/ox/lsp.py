"""Language Server Protocol implementation for ox."""

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer
from tree_sitter import Language, Parser, Node
import tree_sitter_ox

server = LanguageServer(name="ox-lsp", version="0.1.0")

# Initialize tree-sitter parser
_language = Language(tree_sitter_ox.language())
_parser = Parser(_language)


def get_diagnostics(text: str) -> list[lsp.Diagnostic]:
    """Parse text and return diagnostics for any errors."""
    tree = _parser.parse(bytes(text, encoding="utf-8"))
    diagnostics = []

    def visit_node(node: Node):
        # Check for ERROR nodes (syntax errors)
        if node.type == "ERROR":
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(
                            line=node.start_point[0], character=node.start_point[1]
                        ),
                        end=lsp.Position(
                            line=node.end_point[0], character=node.end_point[1]
                        ),
                    ),
                    message="Syntax error",
                    severity=lsp.DiagnosticSeverity.Error,
                    source="ox",
                )
            )
            return  # Don't recurse into ERROR nodes

        # Check for MISSING nodes (expected tokens that weren't found)
        if node.is_missing:
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(
                            line=node.start_point[0], character=node.start_point[1]
                        ),
                        end=lsp.Position(
                            line=node.end_point[0], character=node.end_point[1]
                        ),
                    ),
                    message=f"Missing {node.type}",
                    severity=lsp.DiagnosticSeverity.Error,
                    source="ox",
                )
            )
            return

        # Recurse into children
        for child in node.children:
            visit_node(child)

    visit_node(tree.root_node)
    return diagnostics


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


def main():
    """Run the language server."""
    server.start_io()


if __name__ == "__main__":
    main()

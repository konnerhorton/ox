"""Language Server Protocol implementation for ox."""

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


def main():
    """Run the language server."""
    server.start_io()


if __name__ == "__main__":
    main()

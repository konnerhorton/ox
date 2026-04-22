"""Tests for the Language Server Protocol implementation."""

from types import SimpleNamespace

import pytest
from lsprotocol import types as lsp
from tree_sitter import Language, Parser
import tree_sitter_ox

from ox import lsp as ox_lsp
from ox.lsp import (
    _collect_movement_names,
    _cursor_wants_movement,
    _get_all_diagnostics,
    _validate_includes,
    completion,
    did_change,
    did_open,
    did_save,
    folding_range,
    get_diagnostics,
)


def _parse_tree(text: str):
    parser = Parser(Language(tree_sitter_ox.language()))
    return parser.parse(bytes(text, encoding="utf-8"))


class TestGetDiagnostics:
    def test_valid_text_no_diagnostics(self):
        assert get_diagnostics("2025-01-10 * pullups: BW 5x10\n") == []

    def test_invalid_unit_produces_error_diagnostic(self):
        diags = get_diagnostics("2025-01-10 * bench-press: 135lbs 5x5\n")
        assert len(diags) >= 1
        d = diags[0]
        assert d.severity == lsp.DiagnosticSeverity.Error
        assert d.source == "ox"

    def test_positions_are_zero_based(self):
        # Bad entry on line 2 (1-based) of file -> line 1 in LSP
        text = "2025-01-10 * pullups: BW 5x10\n2025-01-11 * squat: 225lbs 3x5\n"
        diags = get_diagnostics(text)
        assert len(diags) >= 1
        assert any(d.range.start.line == 1 for d in diags)


class TestValidateIncludes:
    def test_missing_include_warns(self, tmp_path):
        doc = tmp_path / "main.ox"
        doc.write_text('@include "missing.ox"\n')
        tree = _parse_tree(doc.read_text())
        diags = _validate_includes(tree, f"file://{doc}")
        assert len(diags) == 1
        assert diags[0].severity == lsp.DiagnosticSeverity.Warning
        assert "missing.ox" in diags[0].message

    def test_existing_include_no_diagnostic(self, tmp_path):
        doc = tmp_path / "main.ox"
        other = tmp_path / "other.ox"
        other.write_text("")
        doc.write_text('@include "other.ox"\n')
        tree = _parse_tree(doc.read_text())
        diags = _validate_includes(tree, f"file://{doc}")
        assert diags == []

    def test_relative_path_resolved_against_doc_dir(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        doc = sub / "main.ox"
        (tmp_path / "other.ox").write_text("")
        doc.write_text('@include "../other.ox"\n')
        tree = _parse_tree(doc.read_text())
        diags = _validate_includes(tree, f"file://{doc}")
        assert diags == []


class TestGetAllDiagnostics:
    def test_combines_parse_and_include(self, tmp_path):
        doc = tmp_path / "main.ox"
        doc.write_text('@include "nope.ox"\n2025-01-10 * squat: 1lbs 5x5\n')
        diags = _get_all_diagnostics(doc.read_text(), f"file://{doc}")
        severities = {d.severity for d in diags}
        assert lsp.DiagnosticSeverity.Error in severities
        assert lsp.DiagnosticSeverity.Warning in severities


class TestCollectMovementNames:
    def test_collects_from_singleline(self):
        tree = _parse_tree("2025-01-10 * pullups: BW 5x10\n")
        assert _collect_movement_names(tree) == {"pullups"}

    def test_collects_from_session_block(self):
        text = (
            "@session\n"
            "2025-01-11 * Upper Day\n"
            "bench-press: 135lb 5x5\n"
            "pullups: BW 5x10\n"
            "@end\n"
        )
        assert _collect_movement_names(_parse_tree(text)) == {"bench-press", "pullups"}

    def test_collects_from_template(self):
        text = '@template "t"\nsquat: 225lb 3x5\n@end\n'
        assert _collect_movement_names(_parse_tree(text)) == {"squat"}

    def test_dedupes_across_entries(self):
        text = "2025-01-10 * pullups: BW 5x10\n2025-01-11 * pullups: BW 5x10\n"
        assert _collect_movement_names(_parse_tree(text)) == {"pullups"}


class TestCursorWantsMovement:
    def test_after_singleline_prefix_true(self):
        text = "2025-01-10 * \n"
        tree = _parse_tree(text)
        assert _cursor_wants_movement(text, 0, 13, tree) is True

    def test_before_flag_false(self):
        text = "2025-01-10 * pullups: BW 5x10\n"
        tree = _parse_tree(text)
        assert _cursor_wants_movement(text, 0, 0, tree) is False

    def test_inside_session_item_line_true(self):
        text = "@session\n2025-01-11 * Upper Day\n\n@end\n"
        tree = _parse_tree(text)
        assert _cursor_wants_movement(text, 2, 0, tree) is True

    def test_on_session_header_line_false(self):
        text = "@session\n2025-01-11 * Upper Day\nbench-press: 135lb 5x5\n@end\n"
        tree = _parse_tree(text)
        # Header line is row 1
        assert _cursor_wants_movement(text, 1, 15, tree) is False

    def test_at_directive_line_false(self):
        text = "@session\n2025-01-11 * Upper Day\n@end\n"
        tree = _parse_tree(text)
        assert _cursor_wants_movement(text, 0, 2, tree) is False

    def test_note_line_false(self):
        text = "@session\n2025-01-11 * Upper Day\nnote: feeling tired\n@end\n"
        tree = _parse_tree(text)
        assert _cursor_wants_movement(text, 2, 2, tree) is False

    def test_line_out_of_range_false(self):
        text = "2025-01-10 * pullups: BW 5x10\n"
        tree = _parse_tree(text)
        assert _cursor_wants_movement(text, 99, 0, tree) is False


@pytest.fixture
def captured_publish(monkeypatch):
    calls: list[tuple[str, list[lsp.Diagnostic]]] = []

    def fake_publish(uri, diagnostics):
        calls.append((uri, diagnostics))

    monkeypatch.setattr(ox_lsp, "publish_diagnostics", fake_publish)
    return calls


class TestDidOpen:
    def test_publishes_diagnostics(self, captured_publish, tmp_path):
        text = "2025-01-10 * bench-press: 135lbs 5x5\n"
        uri = f"file://{tmp_path / 'a.ox'}"
        params = lsp.DidOpenTextDocumentParams(
            text_document=lsp.TextDocumentItem(
                uri=uri, language_id="ox", version=1, text=text
            )
        )
        did_open(params)
        assert len(captured_publish) == 1
        pub_uri, diags = captured_publish[0]
        assert pub_uri == uri
        assert diags == _get_all_diagnostics(text, uri)


@pytest.fixture
def stub_workspace(monkeypatch):
    documents: dict[str, str] = {}

    def get_doc(uri):
        return SimpleNamespace(source=documents[uri])

    fake_server = SimpleNamespace(workspace=SimpleNamespace(get_text_document=get_doc))
    monkeypatch.setattr(ox_lsp, "server", fake_server)
    return documents


class TestDidChangeAndSave:
    def test_did_change_publishes(self, captured_publish, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = "2025-01-10 * squat: 225lbs 3x5\n"
        params = lsp.DidChangeTextDocumentParams(
            text_document=lsp.VersionedTextDocumentIdentifier(uri=uri, version=2),
            content_changes=[],
        )
        did_change(params)
        assert len(captured_publish) == 1
        assert captured_publish[0][0] == uri
        assert len(captured_publish[0][1]) >= 1

    def test_did_save_publishes(self, captured_publish, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = "2025-01-10 * pullups: BW 5x10\n"
        params = lsp.DidSaveTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier(uri=uri)
        )
        did_save(params)
        assert len(captured_publish) == 1
        assert captured_publish[0][1] == []


class TestFoldingRange:
    def test_ranges_between_comments(self, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = (
            "# Section A\n"
            "2025-01-10 * pullups: BW 5x10\n"
            "2025-01-11 * pullups: BW 5x10\n"
            "# Section B\n"
            "2025-01-12 * pullups: BW 5x10\n"
        )
        params = lsp.FoldingRangeParams(
            text_document=lsp.TextDocumentIdentifier(uri=uri)
        )
        ranges = folding_range(params)
        assert len(ranges) == 2
        assert ranges[0].start_line == 0
        assert ranges[0].end_line == 2
        assert ranges[1].start_line == 3
        assert ranges[1].end_line == 4

    def test_adjacent_comments_no_range(self, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = "# A\n# B\n2025-01-10 * pullups: BW 5x10\n"
        params = lsp.FoldingRangeParams(
            text_document=lsp.TextDocumentIdentifier(uri=uri)
        )
        ranges = folding_range(params)
        # First comment has no body (adjacent to next comment), second spans the rest
        assert len(ranges) == 1
        assert ranges[0].start_line == 1

    def test_trailing_blanks_trimmed(self, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = "# A\n2025-01-10 * pullups: BW 5x10\n\n\n"
        params = lsp.FoldingRangeParams(
            text_document=lsp.TextDocumentIdentifier(uri=uri)
        )
        ranges = folding_range(params)
        assert len(ranges) == 1
        assert ranges[0].end_line == 1


class TestCompletion:
    def test_returns_movements_in_context(self, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = (
            "2025-01-10 * pullups: BW 5x10\n"
            "2025-01-11 * bench-press: 135lb 5x5\n"
            "2025-01-12 * \n"
        )
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri=uri),
            position=lsp.Position(line=2, character=13),
        )
        result = completion(params)
        labels = [i.label for i in result.items]
        assert labels == sorted(labels)
        assert set(labels) == {"pullups", "bench-press"}
        for item in result.items:
            assert item.insert_text.endswith(": ")
            assert item.kind == lsp.CompletionItemKind.Value

    def test_empty_outside_context(self, stub_workspace, tmp_path):
        uri = f"file://{tmp_path / 'a.ox'}"
        stub_workspace[uri] = "2025-01-10 * pullups: BW 5x10\n"
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri=uri),
            position=lsp.Position(line=0, character=0),
        )
        result = completion(params)
        assert result.items == []

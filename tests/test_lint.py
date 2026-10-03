"""Tests for lint/diagnostic reporting."""

from unittest.mock import patch

from click.testing import CliRunner

from ox.cli import cli, parse_file
from ox.lint import collect_diagnostics
from ox.data import Diagnostic

from tree_sitter import Language, Parser
import tree_sitter_ox


def _parse_tree(text: str):
    language = Language(tree_sitter_ox.language())
    parser = Parser(language)
    return parser.parse(bytes(text, encoding="utf-8"))


class TestCollectDiagnostics:
    def test_valid_file_no_diagnostics(self):
        text = "2025-01-10 T pullups: BW 5x10\n"
        tree = _parse_tree(text)
        assert collect_diagnostics(tree) == ()

    def test_lbs_unit_produces_diagnostic(self):
        # "lbs" is not a valid unit; valid unit is "lb"
        text = "2025-01-10 T bench-press: 135lbs 5x5\n"
        tree = _parse_tree(text)
        diagnostics = collect_diagnostics(tree)
        assert len(diagnostics) == 1
        d = diagnostics[0]
        assert isinstance(d, Diagnostic)
        assert d.line == 1
        assert d.severity == "error"

    def test_multiple_errors_all_collected(self):
        text = "2025-01-10 T bench-press: 135lbs 5x5\n2025-01-11 T squat: 225lbs 3x5\n"
        tree = _parse_tree(text)
        diagnostics = collect_diagnostics(tree)
        assert len(diagnostics) >= 2

    def test_diagnostic_fields(self):
        text = "2025-01-10 T bench-press: 135lbs 5x5\n"
        tree = _parse_tree(text)
        diagnostics = collect_diagnostics(tree)
        assert len(diagnostics) >= 1
        d = diagnostics[0]
        assert d.line >= 1
        assert d.col >= 0
        assert d.end_line >= d.line
        assert d.message in ("Syntax error", f"Missing {d.message.split()[-1]}")
        assert d.severity == "error"

    def test_multiline_session_valid(self):
        text = "@session\ndate: 2025-01-11\nname: Upper Day\nbench-press: 135lb 5x5\n@end\n"
        tree = _parse_tree(text)
        assert collect_diagnostics(tree) == ()

    def test_old_srpe_form_gets_migration_hint(self):
        text = (
            '@session\ndate: 2025-01-11\n  srpe: "5; PT45M"\nsquat: 135lb 5x5\n@end\n'
        )
        diagnostics = collect_diagnostics(_parse_tree(text))
        assert len(diagnostics) == 1
        d = diagnostics[0]
        assert "Old sRPE syntax" in d.message
        assert "migrate_ox.py" in d.message
        assert (d.line, d.col) == (3, 2)
        assert (d.end_line, d.end_col) == (3, 18)

    def test_other_malformed_srpe_keeps_generic_message(self):
        text = "@session\ndate: 2025-01-11\nsrpe: 5.5 PT45M\n@end\n"
        diagnostics = collect_diagnostics(_parse_tree(text))
        assert diagnostics
        assert all("Old sRPE" not in d.message for d in diagnostics)


class TestTrainingLogDiagnostics:
    def test_parse_file_valid_log_no_diagnostics(self, simple_log_file):
        log = parse_file(simple_log_file)
        assert log.diagnostics == ()

    def test_parse_file_invalid_log_has_diagnostics(self, tmp_path):
        bad_file = tmp_path / "bad.ox"
        bad_file.write_text("2025-01-10 T bench-press: 135lbs 5x5\n")
        log = parse_file(bad_file)
        assert len(log.diagnostics) >= 1
        assert all(isinstance(d, Diagnostic) for d in log.diagnostics)

    def test_diagnostics_correct_line(self, tmp_path):
        content = (
            "# comment\n"
            "2025-01-10 T pullups: BW 5x10\n"
            "2025-01-11 T bench-press: 135lbs 5x5\n"
        )
        bad_file = tmp_path / "bad.ox"
        bad_file.write_text(content)
        log = parse_file(bad_file)
        assert len(log.diagnostics) >= 1
        # The bad line is line 3
        assert any(d.line == 3 for d in log.diagnostics)


def _invoke_repl(file_path, commands: list[str]):
    """Invoke the CLI REPL with a sequence of commands, mocking prompt_toolkit."""
    runner = CliRunner()
    cmd_iter = iter(commands + ["exit"])

    def mock_prompt(_self, *args, **kwargs):
        return next(cmd_iter)

    with patch("prompt_toolkit.PromptSession.prompt", mock_prompt):
        return runner.invoke(cli, [str(file_path)])


class TestLintCommand:
    def test_lint_no_errors(self, simple_log_file):
        result = _invoke_repl(simple_log_file, ["lint"])
        assert result.exit_code == 0
        assert "No parse errors found" in result.output

    def test_lint_shows_errors(self, tmp_path):
        bad_file = tmp_path / "bad.ox"
        bad_file.write_text("2025-01-10 T bench-press: 135lbs 5x5\n")
        result = _invoke_repl(bad_file, ["lint"])
        assert result.exit_code == 0
        assert "Line" in result.output
        assert "Syntax error" in result.output

    def test_load_warning_shown_when_errors(self, tmp_path):
        bad_file = tmp_path / "bad.ox"
        bad_file.write_text("2025-01-10 T bench-press: 135lbs 5x5\n")
        result = _invoke_repl(bad_file, [])
        assert result.exit_code == 0
        assert "parse error" in result.output.lower()
        assert "lint" in result.output

    def test_no_load_warning_for_valid_file(self, simple_log_file):
        result = _invoke_repl(simple_log_file, [])
        assert result.exit_code == 0
        assert "parse error" not in result.output.lower()

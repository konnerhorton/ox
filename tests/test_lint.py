"""Tests for lint/diagnostic reporting."""

from unittest.mock import patch

import pytest

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
        # An unknown unit with no hint falls back to the generic message
        text = "2025-01-10 T bench-press: 135zz 5x5\n"
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


def _session(*lines: str) -> str:
    body = "".join(f"{line}\n" for line in lines)
    return f"@session\ndate: 2025-01-11\n{body}@end\n"


def _only(text: str) -> Diagnostic:
    """The single diagnostic `text` produces."""
    diagnostics = collect_diagnostics(_parse_tree(text))
    assert len(diagnostics) == 1, diagnostics
    return diagnostics[0]


class TestLintHints:
    """Recognized mistakes get one targeted message instead of "Syntax error"."""

    @pytest.mark.parametrize(
        "text, line, message",
        [
            # Curly quotes, standing in for one or both straight quotes
            ("2025-01-10 note “knee sore”\n", 1, "Curly quote"),
            (_session("note: “sore”"), 3, "Curly quote"),
            (_session('deadlift: 245lb 3x3 “tm 350"'), 3, "Curly quote"),
            (_session('note: "bow.”', "srpe: 3 PT60M"), 3, "Curly quote"),
            # Pre-0.6 syntax
            ("2025-01-10 * pullups: BW 5x10\n", 1, "replace `*` with `T`"),
            ("2025-01-10 ! squat: 100kg 5x5\n", 1, "replace `!` with `T`"),
            ('@session\ndate: 2025-01-11\n  srpe: "5; PT45M"\n@end\n', 3, "Old sRPE"),
            # sRPE lines
            (_session("srpe: 5.5 PT45M"), 3, "whole number"),
            (_session("srpe: X PTXXM"), 3, "sRPE line is"),
            (_session("srpe: 5", "squat: 5x5"), 3, "sRPE line is"),
            # Values
            (_session("completed: yes", "squat: 5x5"), 3, "`completed:` takes"),
            ("@session\ndate: 2025-1-10\nsquat: 5x5\n@end\n", 2, "YYYY-MM-DD"),
            ("2025-01-10 T bench-press: 135lbs 5x5\n", 1, "use `lb`"),
            (_session("squat: 100kgs 5x5", "bench: 60kg 5x5"), 3, "use `kg`"),
            ("2025-01-10 T run: 5km 25min\n", 1, "write `PT25M`"),
            (_session("plank: BW 45s 3x1"), 3, "write `PT45S`"),
            (_session('squat: 100kg 5x5 "felt good', "bench: 60kg 5x5"), 3, "Unclosed"),
            ("2025-01-10 squat: 100kg 5x5\n", 1, "needs `T`"),
            # Block structure
            ("@session\nname: Upper\nsquat: 5x5\n@end\n", 1, "start with a `date:`"),
            (
                "@session\nname: Upper\ndate: 2025-01-10\nsquat: 5x5\n@end\n",
                1,
                "start with a `date:`",
            ),
            (
                "@session\ndate: 2025-01-10\nsquat: 5x5\n\n"
                "@session\ndate: 2025-01-11\nbench: 5x5\n@end\n",
                1,
                "`@session` block is missing `@end`",
            ),
            ("@session\ndate: 2025-01-10\nsquat: 5x5\n", 1, "missing `@end`"),
        ],
    )
    def test_hint(self, text, line, message):
        d = _only(text)
        assert d.line == line
        assert message in d.message
        assert d.severity == "error"

    def test_old_session_header_hint(self):
        text = "@session\n2025-01-12 * Lower\nsquat: 100kg 5x5\n@end\n"
        diagnostics = collect_diagnostics(_parse_tree(text))
        assert diagnostics[0].line == 2
        assert "Old session header" in diagnostics[0].message
        assert all("start with a `date:`" not in d.message for d in diagnostics)

    def test_migration_hints_name_the_script(self):
        assert "migrate_ox.py" in _only("2025-01-10 * pullups: BW 5x10\n").message
        assert "migrate_ox.py" in _only(_session('srpe: "5; PT45M"')).message

    def test_hint_columns_cover_the_mistake(self):
        d = _only("2025-01-10 T bench-press: 135lbs 5x5\n")
        assert (d.col, d.end_col) == (29, 32)
        d = _only('@session\ndate: 2025-01-11\n  srpe: "5; PT45M"\n@end\n')
        assert (d.line, d.col, d.end_line, d.end_col) == (3, 2, 3, 18)

    def test_hint_columns_count_characters_not_bytes(self):
        # “ is three bytes in UTF-8 but one character for an editor
        d = _only("2025-01-10 note “knee sore”\n")
        assert (d.col, d.end_col) == (16, 27)

    def test_unclosed_quote_does_not_swallow_later_lines(self):
        """A quoted string stops at the end of its line."""
        text = (
            _session('note: "half open')
            + "2025-01-12 T squat: 100kg 5x5\n"
            + '2025-01-13 T bench: 60kg 5x5 "fine"\n'
        )
        diagnostics = collect_diagnostics(_parse_tree(text))
        assert [d.line for d in diagnostics] == [3]
        assert "Unclosed" in diagnostics[0].message

    @pytest.mark.parametrize(
        "breaker, line",
        [
            ("completed: yes", 'squat: 100kg 5x5 "he said “go”"'),
            ("completed: yes", 'squat: 100kg 5x5 "30 minutes, 135lbs bar"'),
            ("completed: yes", "plank: BW PT45S 3x1"),
            ("completed: yes", "completed: false"),
            ("srpe: 5", "srpe: 3 PT60M"),
            ("srpe: 5", 'srpe: 3 PT60M "solid"'),
        ],
    )
    def test_valid_lines_inside_an_error_get_no_hint(self, breaker, line):
        """A broken line can pull its neighbours into one ERROR; they stay quiet."""
        text = _session(breaker, line)
        tree = _parse_tree(text)

        covered = set()

        def walk(node):
            if node.type == "ERROR":
                end = node.end_point[0] - (node.end_point[1] == 0)
                covered.update(range(node.start_point[0], end + 1))
                return
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        assert 3 in covered, "the valid line must sit inside the ERROR node"

        diagnostics = collect_diagnostics(tree)
        assert [d.line for d in diagnostics] == [3]

    def test_unrecognized_error_stays_generic(self):
        assert _only("2025-01-10 T bench-press: 135zz 5x5\n").message == (
            "Syntax error"
        )


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
        assert "Unknown unit `lbs`: use `lb`" in result.output

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

"""Tests for the old-to-new syntax migration script.

Testing philosophy:
- Pin each transformation against a golden old/new pair
- Pin what the script refuses to convert, since refusing is the feature
"""

import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from migrate_ox import MigrationError, migrate_text  # noqa: E402


def convert(text: str) -> str:
    return migrate_text(dedent(text).lstrip("\n"))


class TestSingleLineEntries:
    """The `*` completion flag becomes the `T` type marker."""

    def test_flag_becomes_marker(self):
        assert convert("2025-01-10 * pullups: BW 5x10\n") == (
            "2025-01-10 T pullups: BW 5x10\n"
        )

    def test_note_is_preserved(self):
        assert convert('2025-01-10 * squat: 135lb 5x5 "felt good"\n') == (
            '2025-01-10 T squat: 135lb 5x5 "felt good"\n'
        )

    def test_duration_and_distance_untouched(self):
        assert (
            convert("2025-01-10 * run: 5km PT25M\n") == "2025-01-10 T run: 5km PT25M\n"
        )

    def test_planned_entry_refused(self):
        """Planning has no single-line form in the new syntax."""
        with pytest.raises(MigrationError, match="planned single-line entries"):
            convert("2025-01-10 ! squat: 185lb 5x5\n")


class TestPassThrough:
    """Entry types the redesign does not touch survive byte for byte."""

    @pytest.mark.parametrize(
        "line",
        [
            "# a comment",
            '2025-01-10 W 185lb T06:30 "home"',
            '2025-01-10 note "deload week"',
            '2025-01-10 query "recent" "SELECT * FROM training"',
            '@include "other.ox"',
            '@plugin "my_plugin.py"',
        ],
    )
    def test_unchanged(self, line):
        assert convert(f"{line}\n") == f"{line}\n"

    def test_movement_block_unchanged(self):
        text = """
        @movement squat
        equipment: barbell
        note: back squat
        @end
        """
        assert convert(text) == dedent(text).lstrip("\n")


class TestSessionHeaders:
    """The positional header becomes `date:` / `name:` / `completed:` lines."""

    def test_completed_session(self):
        assert convert("""
        @session
        2025-01-06 * Lower Strength
        squat: 155lb 4x5
        @end
        """) == dedent("""
        @session
        date: 2025-01-06
        name: Lower Strength
        squat: 155lb 4x5
        @end
        """).lstrip("\n")

    def test_planned_session_gains_completed_false(self):
        out = convert("""
        @session
        2025-01-15 ! Upper Day
        bench-press: 185lb 5x5
        @end
        """)
        assert "completed: false" in out
        assert out.index("name:") < out.index("completed:")

    def test_completed_true_is_left_implicit(self):
        out = convert("""
        @session
        2025-01-06 * Lower
        squat: 155lb 4x5
        @end
        """)
        assert "completed:" not in out

    def test_movement_lines_untouched(self):
        out = convert("""
        @session
        2025-01-06 * Lower
        squat: 155lb 4x5
        note: "good day"
        @end
        """)
        assert "squat: 155lb 4x5" in out
        assert 'note: "good day"' in out

    def test_missing_header_refused(self):
        with pytest.raises(MigrationError, match="not followed by a date header"):
            convert("@session\nsquat: 155lb 4x5\n@end\n")


class TestSrpeLines:
    """The quoted movement hack becomes a real srpe line."""

    def test_semicolon_separator(self):
        out = convert("""
        @session
        2025-01-06 * Lower
        srpe: "5; PT45M"
        @end
        """)
        assert "srpe: 5 PT45M" in out

    def test_comma_separator(self):
        out = convert("""
        @session
        2025-01-06 * Lower
        srpe: "4, PT35M"
        @end
        """)
        assert "srpe: 4 PT35M" in out

    def test_fractional_rating_refused(self):
        """Rounding 6.5 would be a guess, so the script stops."""
        with pytest.raises(MigrationError, match="not a whole number"):
            convert("""
            @session
            2025-01-06 * Lower
            srpe: "6.5; PT45M"
            @end
            """)


class TestHoistedSrpe:
    """sRPE trailing a single-line note becomes an unnamed session block."""

    def test_hoisted(self):
        assert convert('2025-01-08 * run: PT30M "easy pace, srpe: 3; PT30M"\n') == (
            dedent("""
            @session
            date: 2025-01-08
            run: PT30M "easy pace"
            srpe: 3 PT30M
            @end
            """).lstrip("\n")
        )

    def test_note_remainder_is_kept(self):
        out = convert('2025-01-08 * run: PT40M "long run with hills, srpe: 6; PT45M"\n')
        assert 'run: PT40M "long run with hills"' in out

    def test_note_dropped_when_it_held_only_srpe(self):
        """Nothing is left of the note once the sRPE is lifted out of it."""
        out = convert('2025-01-08 * run: PT30M "srpe: 3; PT30M"\n')
        assert "run: PT30M\n" in out
        assert "srpe: 3 PT30M" in out

    def test_non_trailing_srpe_refused(self):
        with pytest.raises(MigrationError, match="cannot hoist|not as a trailing"):
            convert('2025-01-08 * run: PT30M "srpe: 3; PT30M then easy"\n')

    def test_fractional_hoisted_rating_refused(self):
        with pytest.raises(MigrationError, match="not a whole number"):
            convert('2025-01-08 * run: PT30M "easy, srpe: 3.5; PT30M"\n')


class TestGoldenPair:
    """The checked-in old file converts to the checked-in new file, exactly."""

    FIXTURES = Path(__file__).parent / "fixtures"

    def test_matches_golden_output(self):
        old = (self.FIXTURES / "migrate_old.ox").read_text()
        new = (self.FIXTURES / "migrate_new.ox").read_text()
        assert migrate_text(old) == new

    def test_golden_output_parses(self):
        """The converted file is valid under the current grammar."""
        import tree_sitter_ox
        from tree_sitter import Language, Parser

        from ox.lint import collect_diagnostics

        parser = Parser(Language(tree_sitter_ox.language()))
        text = (self.FIXTURES / "migrate_new.ox").read_text()
        assert not collect_diagnostics(parser.parse(text.encode()))

    def test_already_converted_input_is_refused(self):
        """Re-running on a new-syntax file stops rather than mangling it."""
        new = (self.FIXTURES / "migrate_new.ox").read_text()
        with pytest.raises(MigrationError, match="not followed by a date header"):
            migrate_text(new)

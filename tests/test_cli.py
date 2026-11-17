"""Tests for ox.cli output rendering."""

import sqlite3

from ox.cli import render_result, show_query
from ox.plugins import TableResult


def test_table_cells_are_plain_text(capsys):
    """Square brackets in a cell are data, not rich markup."""
    render_result(TableResult(columns=["format"], rows=[("emom [interval]",)]))
    assert "emom [interval]" in capsys.readouterr().out


def test_query_cells_are_plain_text(capsys):
    show_query(sqlite3.connect(":memory:"), "SELECT '[pr] felt strong' AS note")
    assert "[pr] felt strong" in capsys.readouterr().out

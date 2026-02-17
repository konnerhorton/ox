"""Tests for the plugin system."""

import textwrap

from ox.plugins import (
    GENERATOR_PLUGINS,
    REPORT_PLUGINS,
    _load_from_directory,
    _register_descriptors,
    load_plugins,
)
from ox.reports import REPORTS, get_all_reports, report_usage


def _dummy_report(conn, movement="x"):
    return ["col"], [("row",)]


def _dummy_generator(movement="x"):
    return "output"


class TestRegisterDescriptors:
    """Test descriptor routing and validation."""

    def setup_method(self):
        REPORT_PLUGINS.clear()
        GENERATOR_PLUGINS.clear()

    def test_routes_report(self):
        _register_descriptors(
            [
                {
                    "type": "report",
                    "name": "test-report",
                    "fn": _dummy_report,
                    "description": "A test",
                    "params": [],
                }
            ],
            "test",
        )
        assert "test-report" in REPORT_PLUGINS
        assert GENERATOR_PLUGINS == {}

    def test_routes_generator(self):
        _register_descriptors(
            [
                {
                    "type": "generator",
                    "name": "test-gen",
                    "fn": _dummy_generator,
                    "description": "A test",
                    "params": [],
                }
            ],
            "test",
        )
        assert "test-gen" in GENERATOR_PLUGINS
        assert REPORT_PLUGINS == {}

    def test_skips_missing_fn(self):
        _register_descriptors(
            [{"type": "report", "name": "bad", "description": "no fn"}],
            "test",
        )
        assert REPORT_PLUGINS == {}

    def test_skips_missing_name(self):
        _register_descriptors(
            [{"type": "report", "fn": _dummy_report}],
            "test",
        )
        assert REPORT_PLUGINS == {}

    def test_skips_missing_type(self):
        _register_descriptors(
            [{"name": "bad", "fn": _dummy_report}],
            "test",
        )
        assert REPORT_PLUGINS == {}

    def test_skips_unknown_type(self):
        _register_descriptors(
            [{"type": "widget", "name": "bad", "fn": _dummy_report}],
            "test",
        )
        assert REPORT_PLUGINS == {}
        assert GENERATOR_PLUGINS == {}

    def test_name_collision_overwrites(self):
        desc = {
            "type": "report",
            "name": "dup",
            "fn": _dummy_report,
            "description": "first",
            "params": [],
        }
        _register_descriptors([desc], "first-source")
        assert REPORT_PLUGINS["dup"]["description"] == "first"

        desc2 = {**desc, "description": "second"}
        _register_descriptors([desc2], "second-source")
        assert REPORT_PLUGINS["dup"]["description"] == "second"

    def test_multiple_descriptors_in_one_call(self):
        _register_descriptors(
            [
                {
                    "type": "report",
                    "name": "r1",
                    "fn": _dummy_report,
                    "description": "r",
                    "params": [],
                },
                {
                    "type": "generator",
                    "name": "g1",
                    "fn": _dummy_generator,
                    "description": "g",
                    "params": [],
                },
            ],
            "test",
        )
        assert "r1" in REPORT_PLUGINS
        assert "g1" in GENERATOR_PLUGINS


class TestLoadFromDirectory:
    """Test file-based plugin discovery."""

    def setup_method(self):
        REPORT_PLUGINS.clear()
        GENERATOR_PLUGINS.clear()

    def test_loads_plugin_from_directory(self, tmp_path, monkeypatch):
        plugin_code = textwrap.dedent("""\
            def _my_fn(conn, x="y"):
                return ["col"], [("row",)]

            def register():
                return [
                    {
                        "type": "report",
                        "name": "from-dir",
                        "fn": _my_fn,
                        "description": "loaded from dir",
                        "params": [],
                    }
                ]
        """)
        (tmp_path / "my_plugin.py").write_text(plugin_code)
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path)
        _load_from_directory()
        assert "from-dir" in REPORT_PLUGINS

    def test_ignores_file_without_register(self, tmp_path, monkeypatch):
        (tmp_path / "no_register.py").write_text("x = 1\n")
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path)
        _load_from_directory()
        assert REPORT_PLUGINS == {}

    def test_handles_register_error(self, tmp_path, monkeypatch):
        plugin_code = textwrap.dedent("""\
            def register():
                raise RuntimeError("boom")
        """)
        (tmp_path / "bad_plugin.py").write_text(plugin_code)
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path)
        _load_from_directory()
        assert REPORT_PLUGINS == {}

    def test_handles_import_error(self, tmp_path, monkeypatch):
        (tmp_path / "broken.py").write_text("import nonexistent_module_xyz\n")
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path)
        _load_from_directory()
        assert REPORT_PLUGINS == {}

    def test_nonexistent_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path / "nope")
        _load_from_directory()
        assert REPORT_PLUGINS == {}


class TestLoadPlugins:
    """Test the top-level load_plugins function."""

    def test_idempotent(self, tmp_path, monkeypatch):
        plugin_code = textwrap.dedent("""\
            def _fn(conn):
                return [], []

            def register():
                return [
                    {
                        "type": "report",
                        "name": "idem",
                        "fn": _fn,
                        "description": "test",
                        "params": [],
                    }
                ]
        """)
        (tmp_path / "idem.py").write_text(plugin_code)
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path)

        load_plugins()
        assert "idem" in REPORT_PLUGINS

        load_plugins()
        assert "idem" in REPORT_PLUGINS
        assert len(REPORT_PLUGINS) == 1

    def test_clears_previous(self, tmp_path, monkeypatch):
        """After removing a plugin file, reload should not keep stale entries."""
        plugin_code = textwrap.dedent("""\
            def _fn(conn):
                return [], []

            def register():
                return [
                    {
                        "type": "report",
                        "name": "gone",
                        "fn": _fn,
                        "description": "test",
                        "params": [],
                    }
                ]
        """)
        plugin_file = tmp_path / "gone.py"
        plugin_file.write_text(plugin_code)
        monkeypatch.setattr("ox.plugins.PLUGIN_DIR", tmp_path)

        load_plugins()
        assert "gone" in REPORT_PLUGINS

        plugin_file.unlink()
        load_plugins()
        assert "gone" not in REPORT_PLUGINS


class TestGetAllReports:
    """Test merging built-in reports with plugin reports."""

    def setup_method(self):
        REPORT_PLUGINS.clear()

    def test_returns_builtins_when_no_plugins(self):
        result = get_all_reports()
        assert "volume" in result
        assert "matrix" in result

    def test_merges_plugin_reports(self):
        REPORT_PLUGINS["custom"] = {
            "type": "report",
            "name": "custom",
            "fn": _dummy_report,
            "description": "Custom report",
            "params": [{"name": "x", "type": str, "required": True}],
        }
        result = get_all_reports()
        assert "volume" in result
        assert "custom" in result
        assert result["custom"]["fn"] is _dummy_report

    def test_does_not_mutate_builtins(self):
        REPORT_PLUGINS["custom"] = {
            "type": "report",
            "name": "custom",
            "fn": _dummy_report,
            "description": "Custom report",
            "params": [],
        }
        get_all_reports()
        assert "custom" not in REPORTS


class TestReportUsageCommand:
    """Test that report_usage respects the command parameter."""

    def test_default_command(self):
        entry = {"params": [{"name": "x", "type": str, "required": True}]}
        usage = report_usage("test", entry)
        assert usage.startswith("report test")

    def test_generate_command(self):
        entry = {"params": [{"name": "x", "type": str, "required": True}]}
        usage = report_usage("test", entry, command="generate")
        assert usage.startswith("generate test")

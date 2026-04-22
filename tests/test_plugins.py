"""Tests for the plugin system."""

import textwrap

from ox.data import TrainingLog
from ox.plugins import (
    PLUGINS,
    _load_from_log_directives,
    _register_descriptors,
    load_plugins,
)
from ox.sql_utils import plugin_usage


def _dummy_fn(ctx, movement="x"):
    return ["col"], [("row",)]


def _make_log(plugin_paths: tuple[str, ...]) -> TrainingLog:
    return TrainingLog(
        sessions=(),
        notes=(),
        diagnostics=(),
        queries=(),
        weigh_ins=(),
        plugin_paths=plugin_paths,
    )


class TestRegisterDescriptors:
    """Test descriptor routing and validation."""

    def setup_method(self):
        PLUGINS.clear()

    def test_registers_plugin(self):
        _register_descriptors(
            [
                {
                    "name": "test-plugin",
                    "fn": _dummy_fn,
                    "description": "A test",
                    "params": [],
                }
            ],
            "test",
        )
        assert "test-plugin" in PLUGINS

    def test_skips_missing_fn(self):
        _register_descriptors(
            [{"name": "bad", "description": "no fn"}],
            "test",
        )
        assert PLUGINS == {}

    def test_skips_missing_name(self):
        _register_descriptors(
            [{"fn": _dummy_fn}],
            "test",
        )
        assert PLUGINS == {}

    def test_name_collision_overwrites(self):
        desc = {
            "name": "dup",
            "fn": _dummy_fn,
            "description": "first",
            "params": [],
        }
        _register_descriptors([desc], "first-source")
        assert PLUGINS["dup"]["description"] == "first"

        desc2 = {**desc, "description": "second"}
        _register_descriptors([desc2], "second-source")
        assert PLUGINS["dup"]["description"] == "second"

    def test_multiple_descriptors_in_one_call(self):
        _register_descriptors(
            [
                {
                    "name": "p1",
                    "fn": _dummy_fn,
                    "description": "first",
                    "params": [],
                },
                {
                    "name": "p2",
                    "fn": _dummy_fn,
                    "description": "second",
                    "params": [],
                },
            ],
            "test",
        )
        assert "p1" in PLUGINS
        assert "p2" in PLUGINS


class TestLoadFromLogDirectives:
    """Test @plugin directive discovery."""

    def setup_method(self):
        PLUGINS.clear()

    def test_loads_plugin_from_directive(self, tmp_path):
        plugin_code = textwrap.dedent("""\
            def _my_fn(ctx, x="y"):
                return ["col"], [("row",)]

            def register():
                return [
                    {
                        "name": "from-directive",
                        "fn": _my_fn,
                        "description": "loaded from @plugin",
                        "params": [],
                    }
                ]
        """)
        (tmp_path / "my_plugin.py").write_text(plugin_code)
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("my_plugin.py",))
        _load_from_log_directives(log, base)
        assert "from-directive" in PLUGINS

    def test_ignores_file_without_register(self, tmp_path):
        (tmp_path / "no_register.py").write_text("x = 1\n")
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("no_register.py",))
        _load_from_log_directives(log, base)
        assert PLUGINS == {}

    def test_handles_register_error(self, tmp_path):
        plugin_code = textwrap.dedent("""\
            def register():
                raise RuntimeError("boom")
        """)
        (tmp_path / "bad_plugin.py").write_text(plugin_code)
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("bad_plugin.py",))
        _load_from_log_directives(log, base)
        assert PLUGINS == {}

    def test_handles_import_error(self, tmp_path):
        (tmp_path / "broken.py").write_text("import nonexistent_module_xyz\n")
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("broken.py",))
        _load_from_log_directives(log, base)
        assert PLUGINS == {}

    def test_missing_file(self, tmp_path):
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("does_not_exist.py",))
        _load_from_log_directives(log, base)
        assert PLUGINS == {}


class TestLoadPlugins:
    """Test the top-level load_plugins function."""

    def test_idempotent(self, tmp_path):
        plugin_code = textwrap.dedent("""\
            def _fn(ctx):
                return [], []

            def register():
                return [
                    {
                        "name": "idem",
                        "fn": _fn,
                        "description": "test",
                        "params": [],
                    }
                ]
        """)
        (tmp_path / "idem.py").write_text(plugin_code)
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("idem.py",))

        load_plugins(log, base)
        assert "idem" in PLUGINS

        load_plugins(log, base)
        assert "idem" in PLUGINS

    def test_clears_previous(self, tmp_path):
        """After removing a plugin file, reload should not keep stale entries."""
        plugin_code = textwrap.dedent("""\
            def _fn(ctx):
                return [], []

            def register():
                return [
                    {
                        "name": "gone",
                        "fn": _fn,
                        "description": "test",
                        "params": [],
                    }
                ]
        """)
        plugin_file = tmp_path / "gone.py"
        plugin_file.write_text(plugin_code)
        base = tmp_path / "log.ox"
        base.write_text("")
        log = _make_log(("gone.py",))

        load_plugins(log, base)
        assert "gone" in PLUGINS

        plugin_file.unlink()
        load_plugins(log, base)
        assert "gone" not in PLUGINS


class TestPluginUsageCommand:
    """Test that plugin_usage respects the command parameter."""

    def test_default_command(self):
        entry = {"params": [{"name": "x", "type": str, "required": True}]}
        usage = plugin_usage("test", entry)
        assert usage.startswith("run test")

    def test_custom_command(self):
        entry = {"params": [{"name": "x", "type": str, "required": True}]}
        usage = plugin_usage("test", entry, command="custom")
        assert usage.startswith("custom test")

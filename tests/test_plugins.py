"""Tests for the plugin system."""

import textwrap
from pathlib import Path

from ox.data import PluginDirective, TrainingLog
from ox.plugins import (
    LOAD_WARNINGS,
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
        plugin_directives=tuple(
            PluginDirective(p, None, Path("log.ox").resolve(), i + 1)
            for i, p in enumerate(plugin_paths)
        ),
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

    def test_refuses_more_than_one(self):
        LOAD_WARNINGS.clear()
        name = _register_descriptors(
            [
                {"name": "p1", "fn": _dummy_fn, "description": "", "params": []},
                {"name": "p2", "fn": _dummy_fn, "description": "", "params": []},
            ],
            "two.py",
        )
        assert name is None
        assert PLUGINS == {}
        assert LOAD_WARNINGS == [
            "two.py registers 2 plugins; a file may register one. Not loaded."
        ]

    def test_accepts_dict(self):
        desc = {"name": "one", "fn": _dummy_fn, "description": "", "params": []}
        assert _register_descriptors(desc, "test") == "one"
        assert PLUGINS["one"] is desc

    def test_accepts_one_item_list(self):
        desc = {"name": "one", "fn": _dummy_fn, "description": "", "params": []}
        assert _register_descriptors([desc], "test") == "one"
        assert PLUGINS["one"] is desc

    def test_empty_list_registers_nothing(self):
        LOAD_WARNINGS.clear()
        assert _register_descriptors([], "test") is None
        assert PLUGINS == {}
        assert LOAD_WARNINGS == []

    def test_every_builtin_registers_one(self):
        from ox.builtins import e1rm, formats, srpe, volume, weighin, wendler531

        for mod in (volume, e1rm, weighin, wendler531, srpe, formats):
            descs = mod.register()
            if isinstance(descs, dict):
                descs = [descs]
            assert len(descs) == 1, mod.__name__


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
    """Test plugin_usage output format."""

    def test_starts_with_name(self):
        entry = {"params": [{"name": "x", "type": str, "required": True}]}
        usage = plugin_usage("test", entry)
        assert usage.startswith("test ")
        assert "run " not in usage

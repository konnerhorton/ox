"""Tests for the plugin system."""

import textwrap
from pathlib import Path

import pytest

from ox.cli import load_log, print_load_summary
from ox.plugins import (
    LOAD_WARNINGS,
    PLUGINS,
    USER_PLUGINS,
    _register_descriptors,
    load_plugins,
    read_plugin_config,
)
from ox.sql_utils import plugin_usage


def _dummy_fn(ctx, movement="x"):
    return ["col"], [("row",)]


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


def _plugin_code(name: str) -> str:
    return textwrap.dedent(f"""\
        def _fn(ctx):
            return [], []

        def register():
            return {{"name": "{name}", "fn": _fn, "description": "", "params": []}}
    """)


def _load(tmp_path: Path, src: str, files: dict[str, str] | None = None):
    """Write the log and any other files under tmp_path, then load_log it."""
    for rel, text in (files or {}).items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    log_file = tmp_path / "log.ox"
    log_file.write_text(src)
    return load_log(log_file)


class TestLoadFromLogDirectives:
    """Test @plugin directive discovery."""

    def test_loads_plugin_from_directive(self, tmp_path):
        _load(
            tmp_path,
            '@plugin "my_plugin.py"\n',
            {"my_plugin.py": _plugin_code("from-directive")},
        )
        assert "from-directive" in PLUGINS
        assert "from-directive" in USER_PLUGINS

    def test_one_item_list(self, tmp_path):
        code = textwrap.dedent("""\
            def register():
                return [{"name": "listed", "fn": print, "description": "", "params": []}]
        """)
        _load(tmp_path, '@plugin "p.py"\n', {"p.py": code})
        assert "listed" in PLUGINS

    def test_two_item_list_refused(self, tmp_path):
        code = textwrap.dedent("""\
            def register():
                d = {"fn": print, "description": "", "params": []}
                return [{**d, "name": "a"}, {**d, "name": "b"}]
        """)
        _load(tmp_path, '@plugin "p.py"\n', {"p.py": code})
        assert "a" not in PLUGINS and "b" not in PLUGINS
        path = (tmp_path / "p.py").resolve()
        assert LOAD_WARNINGS == [
            f"{path} registers 2 plugins; a file may register one. Not loaded."
        ]

    def test_ignores_file_without_register(self, tmp_path):
        _load(tmp_path, '@plugin "no_register.py"\n', {"no_register.py": "x = 1\n"})
        assert USER_PLUGINS == set()

    def test_handles_register_error(self, tmp_path):
        code = 'def register():\n    raise RuntimeError("boom")\n'
        _load(tmp_path, '@plugin "bad_plugin.py"\n', {"bad_plugin.py": code})
        assert USER_PLUGINS == set()

    def test_handles_import_error(self, tmp_path):
        code = "import nonexistent_module_xyz\n"
        _load(tmp_path, '@plugin "broken.py"\n', {"broken.py": code})
        assert USER_PLUGINS == set()

    def test_missing_file(self, tmp_path):
        _load(tmp_path, '@plugin "does_not_exist.py"\n')
        assert USER_PLUGINS == set()

    def test_path_in_include_resolves_against_its_file(self, tmp_path):
        _load(
            tmp_path,
            '@include "sub/inc.ox"\n',
            {
                "sub/inc.ox": '@plugin "plugins/x.py"\n',
                "sub/plugins/x.py": _plugin_code("x"),
            },
        )
        assert "x" in USER_PLUGINS


class TestLoadPlugins:
    """Test the top-level load_plugins function."""

    def test_idempotent(self, tmp_path):
        log, _, _ = _load(
            tmp_path, '@plugin "idem.py"\n', {"idem.py": _plugin_code("idem")}
        )
        assert "idem" in PLUGINS
        load_plugins(log)
        assert "idem" in PLUGINS

    def test_clears_previous(self, tmp_path):
        """After removing a plugin file, reload should not keep stale entries."""
        log, _, _ = _load(
            tmp_path, '@plugin "gone.py"\n', {"gone.py": _plugin_code("gone")}
        )
        assert "gone" in PLUGINS
        (tmp_path / "gone.py").unlink()
        load_plugins(log)
        assert "gone" not in PLUGINS

    def test_no_log(self):
        assert load_plugins() == {}
        assert "volume" in PLUGINS


class TestPluginConfig:
    """Configs from @plugin directives reach the plugin through ctx.log."""

    def test_config_on_file_line(self, tmp_path):
        _, _, ctx = _load(
            tmp_path,
            '@plugin "fixture.py" "{\'a\': [1, 2]}"\n',
            {"fixture.py": _plugin_code("fixture")},
        )
        assert ctx.log.plugin_config("fixture") == {"a": [1, 2]}
        assert LOAD_WARNINGS == []

    def test_config_by_name(self, tmp_path):
        _, _, ctx = _load(
            tmp_path,
            '@plugin "fixture.py"\n@plugin "fixture" "{\n  \'a\': [1, 2],  # c\n}"\n',
            {"fixture.py": _plugin_code("fixture")},
        )
        assert ctx.log.plugin_config("fixture") == {"a": [1, 2]}

    def test_unconfigured_is_none(self, tmp_path):
        _, _, ctx = _load(
            tmp_path, '@plugin "fixture.py"\n', {"fixture.py": _plugin_code("fixture")}
        )
        assert ctx.log.plugin_config("fixture") is None
        assert ctx.log.plugin_config("volume") is None

    def test_builtin_by_name(self, tmp_path):
        _, _, ctx = _load(tmp_path, '@plugin "volume" "{\'x\': 1}"\n')
        assert ctx.log.plugin_config("volume") == {"x": 1}

    def test_config_in_include(self, tmp_path):
        _, _, ctx = _load(
            tmp_path,
            '@include "sub/inc.ox"\n',
            {"sub/inc.ox": '@plugin "volume" "[1]"\n'},
        )
        assert ctx.log.plugin_config("volume") == [1]

    def test_first_wins_same_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _, _, ctx = _load(tmp_path, '@plugin "volume" "1"\n\n@plugin "volume" "2"\n')
        assert ctx.log.plugin_config("volume") == 1
        assert LOAD_WARNINGS == [
            "log.ox:3: 'volume' is already configured at log.ox:1; "
            "this config is ignored"
        ]

    def test_first_wins_across_include(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _, _, ctx = _load(
            tmp_path,
            '@plugin "volume" "1"\n@include "inc.ox"\n',
            {"inc.ox": '@plugin "volume" "2"\n'},
        )
        assert ctx.log.plugin_config("volume") == 1
        assert LOAD_WARNINGS == [
            "inc.ox:1: 'volume' is already configured at log.ox:1; "
            "this config is ignored"
        ]

    def test_first_wins_file_then_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _, _, ctx = _load(
            tmp_path,
            '@plugin "fixture.py" "1"\n@plugin "fixture" "2"\n',
            {"fixture.py": _plugin_code("fixture")},
        )
        assert ctx.log.plugin_config("fixture") == 1
        assert LOAD_WARNINGS == [
            "log.ox:2: 'fixture' is already configured at log.ox:1; "
            "this config is ignored"
        ]

    @pytest.mark.parametrize(
        "config,reason",
        [
            ("{'a': [}", "doesn't parse: closing parenthesis '}' does not match"),
            ("open('x')", "doesn't parse: \"open('x')\" is not a literal (line 1)"),
        ],
    )
    def test_unparsable(self, tmp_path, monkeypatch, config, reason):
        monkeypatch.chdir(tmp_path)
        _, _, ctx = _load(
            tmp_path,
            f'@plugin "volume" "{config}"\n2025-01-10 T pullups: BW 5x10\n',
        )
        assert ctx.log.plugin_config("volume") is None
        assert len(LOAD_WARNINGS) == 1
        assert LOAD_WARNINGS[0].startswith(f"log.ox:1: config for 'volume' {reason}")
        assert ctx.db.execute("SELECT count(*) FROM sessions").fetchone() == (1,)

    def test_unknown_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _load(tmp_path, '@plugin "nope" "{}"\n')
        assert LOAD_WARNINGS == ["log.ox:1: config for unknown plugin 'nope'"]

    def test_failed_file_with_config_adds_no_warning(self, tmp_path):
        _load(tmp_path, '@plugin "missing.py" "{}"\n')
        assert LOAD_WARNINGS == []

    def test_load_summary_prints_warnings(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        log, _, _ = _load(tmp_path, '@plugin "nope" "{}"\n')
        print_load_summary(log)
        out = capsys.readouterr().out
        lines = out.splitlines()
        assert lines.index("log.ox:1: config for unknown plugin 'nope'") > 0
        assert "Loaded 0 completed" in lines[0]


class TestReadPluginConfig:
    def test_literals(self):
        assert read_plugin_config(" {'a': (1, 'b'), 'c': None} ") == {
            "a": (1, "b"),
            "c": None,
        }

    @pytest.mark.parametrize(
        "text,reason",
        [
            ("{'a': [}", "closing parenthesis '}' does not match"),
            ("{\n  'a': x,\n}", "'x' is not a literal (line 2)"),
            ("{'a': 1 + 'b'}", "not a Python literal"),
            ("1 +", "invalid syntax (line 1)"),
            ("  \n ", "the config is empty"),
        ],
    )
    def test_rejects(self, text, reason):
        with pytest.raises(ValueError) as e:
            read_plugin_config(text)
        assert str(e.value).startswith(reason)
        assert "\n" not in str(e.value)


class TestPluginUsageCommand:
    """Test plugin_usage output format."""

    def test_starts_with_name(self):
        entry = {"params": [{"name": "x", "type": str, "required": True}]}
        usage = plugin_usage("test", entry)
        assert usage.startswith("test ")
        assert "run " not in usage

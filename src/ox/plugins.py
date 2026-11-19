"""Plugin discovery and loading for ox.

Plugins are Python modules that export a register() function returning
one plugin descriptor (a dict), or a one-item list of it: a file registers
one plugin. Each plugin receives a PluginContext
and returns a TableResult, TextResult, or PlotResult.

Discovery sources (loaded in order):
1. Built-in plugins (volume, e1rm, weighin, wendler531, srpe)
2. @plugin directives in .ox files

A log configures a plugin with `@plugin "<name>" "<config>"`, or on the line
that loads its file, `@plugin "<file>.py" "<config>"`. The config is a Python
literal; load_plugins parses it and the plugin reads it with
`ctx.log.plugin_config(name)`.
"""

import ast
import importlib.util
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ox.data import PluginDirective, TrainingLog

logger = logging.getLogger(__name__)

PLUGINS: dict[str, dict] = {}
USER_PLUGINS: set[str] = set()
# Problems found while loading plugins, shown after the load summary
LOAD_WARNINGS: list[str] = []


@dataclass(frozen=True, slots=True)
class PluginContext:
    db: sqlite3.Connection
    log: TrainingLog


@dataclass(frozen=True, slots=True)
class TableResult:
    columns: list[str]
    rows: list[tuple]


@dataclass(frozen=True, slots=True)
class TextResult:
    text: str


@dataclass(frozen=True, slots=True)
class PlotResult:
    lines: list[str]


def _load_module_from_path(path: Path) -> ModuleType | None:
    """Import a .py file as a module. Returns None on failure."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        logger.warning("Could not load plugin: %s", path)
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        logger.warning("Error loading plugin %s", path, exc_info=True)
        return None
    return module


def _register_descriptors(
    descriptors: dict | list[dict], source: str, is_user: bool = False
) -> str | None:
    """Register the one plugin a file's register() returned.

    Args:
        descriptors: A descriptor dict, or a list holding at most one
        source: Where it came from, for warnings
        is_user: Whether it came from a user plugin file

    Returns:
        The registered plugin's name, or None if nothing was registered
    """
    if isinstance(descriptors, dict):
        descriptors = [descriptors]
    if len(descriptors) > 1:
        LOAD_WARNINGS.append(
            f"{source} registers {len(descriptors)} plugins; a file may register "
            "one. Not loaded."
        )
        return None
    if not descriptors:
        return None

    desc = descriptors[0]
    name = desc.get("name")
    if not name or "fn" not in desc:
        logger.warning("Skipping malformed plugin descriptor from %s: %s", source, desc)
        return None

    if name in PLUGINS:
        logger.warning("Plugin '%s' redefined by %s", name, source)
    PLUGINS[name] = desc
    if is_user:
        USER_PLUGINS.add(name)
    return name


def _load_plugin_file(path: Path) -> str | None:
    """Load a user plugin file and return the name it registered, if any."""
    module = _load_module_from_path(path)
    if module is None or not hasattr(module, "register"):
        return None
    try:
        descriptors = module.register()
    except Exception:
        logger.warning("Error calling register() in %s", path, exc_info=True)
        return None
    return _register_descriptors(descriptors, str(path), is_user=True)


# Nodes that may appear in a literal (ast.literal_eval's rules; `1+2j` is a BinOp)
_LITERAL_NODES = (
    ast.Constant,
    ast.Tuple,
    ast.List,
    ast.Set,
    ast.Dict,
    ast.Load,
    ast.UnaryOp,
    ast.UAdd,
    ast.USub,
    ast.BinOp,
    ast.Add,
    ast.Sub,
)


def read_plugin_config(text: str) -> object:
    """Parse a plugin config, a Python literal, into its value.

    Args:
        text: The config, without its surrounding double quotes

    Returns:
        The value of the literal (a dict, list, str, number, ...)

    Raises:
        ValueError: The text isn't a Python literal; the message is a
            one-line reason
    """
    if not text.strip():
        raise ValueError("the config is empty")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"{e.msg} (line {e.lineno})") from None
    try:
        return ast.literal_eval(tree)
    except (ValueError, TypeError, MemoryError, RecursionError):
        pass
    for node in ast.walk(tree.body):
        if not isinstance(node, _LITERAL_NODES):
            source = ast.get_source_segment(text.strip(), node)
            raise ValueError(
                f"{source!r} is not a literal (line {node.lineno})"
            ) from None
    raise ValueError("not a Python literal")


def _where(directive: PluginDirective) -> str:
    """`<file>:<line>` for a directive, the file relative to the working directory."""
    try:
        file = directive.file.relative_to(Path.cwd())
    except ValueError:
        file = directive.file
    return f"{file}:{directive.line}"


def _resolve_configs(
    directives: tuple[PluginDirective, ...], file_names: dict[int, str | None]
) -> dict[str, object]:
    """Read each directive's config; the first config for a name wins.

    Args:
        directives: The log's plugin directives, in load order
        file_names: For each file directive's index, the plugin its file
            registered (None if it registered none)
    """
    configs: dict[str, object] = {}
    first: dict[str, PluginDirective] = {}
    for i, d in enumerate(directives):
        if d.config is None:
            continue
        name = file_names[i] if d.loads_file else d.target
        if name is None:
            continue  # the file failed to load; its failure already says so
        if name in first:
            LOAD_WARNINGS.append(
                f"{_where(d)}: '{name}' is already configured at "
                f"{_where(first[name])}; this config is ignored"
            )
            continue
        first[name] = d
        try:
            configs[name] = read_plugin_config(d.config)
        except ValueError as e:
            LOAD_WARNINGS.append(f"{_where(d)}: config for '{name}' doesn't parse: {e}")
    for name, d in first.items():
        if name not in PLUGINS:
            LOAD_WARNINGS.append(f"{_where(d)}: config for unknown plugin '{name}'")
    return configs


def _load_builtins() -> None:
    """Load plugins that ship with ox."""
    from ox.builtins import e1rm, formats, srpe, volume, weighin, wendler531

    for mod in (volume, e1rm, weighin, wendler531, srpe, formats):
        _register_descriptors(mod.register(), f"builtin:{mod.__name__}")


def load_plugins(log: TrainingLog | None = None) -> dict[str, object]:
    """Discover and load all plugins, and read the log's plugin configs.

    Loads the builtins, then each `@plugin` file, resolved against the `.ox`
    file that holds its directive. Problems go to LOAD_WARNINGS.

    Args:
        log: The log whose `@plugin` directives to load and configure

    Returns:
        Each configured plugin's parsed config, by plugin name
    """
    PLUGINS.clear()
    USER_PLUGINS.clear()
    LOAD_WARNINGS.clear()
    _load_builtins()
    if log is None:
        return {}
    file_names = {
        i: _load_plugin_file((d.file.parent / d.target).resolve())
        for i, d in enumerate(log.plugin_directives)
        if d.loads_file
    }
    return _resolve_configs(log.plugin_directives, file_names)

"""Plugin discovery and loading for ox.

Plugins are Python modules that export a register() function returning
a list of plugin descriptors (dicts). Each plugin receives a PluginContext
and returns a TableResult, TextResult, or PlotResult.

Discovery sources (loaded in order):
1. Built-in plugins (volume, e1rm, weighin, wendler531, srpe)
2. @plugin directives in .ox files
"""

import importlib.util
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ox.data import TrainingLog

logger = logging.getLogger(__name__)

PLUGINS: dict[str, dict] = {}
USER_PLUGINS: set[str] = set()


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


PluginResult = TableResult | TextResult | PlotResult


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
    descriptors: list[dict], source: str, is_user: bool = False
) -> None:
    """Register plugin descriptors into the unified registry."""
    for desc in descriptors:
        name = desc.get("name")

        if not name or "fn" not in desc:
            logger.warning(
                "Skipping malformed plugin descriptor from %s: %s", source, desc
            )
            continue

        if name in PLUGINS:
            logger.warning("Plugin '%s' redefined by %s", name, source)
        PLUGINS[name] = desc
        if is_user:
            USER_PLUGINS.add(name)


def _load_from_log_directives(log: TrainingLog, base_path: Path) -> None:
    """Load plugins declared via @plugin directives in the .ox file."""
    for rel_path in log.plugin_paths:
        resolved = (base_path.parent / rel_path).resolve()
        module = _load_module_from_path(resolved)
        if module and hasattr(module, "register"):
            try:
                descriptors = module.register()
                _register_descriptors(descriptors, str(resolved), is_user=True)
            except Exception:
                logger.warning(
                    "Error calling register() in %s", resolved, exc_info=True
                )


def _load_builtins() -> None:
    """Load plugins that ship with ox."""
    from ox.builtins import e1rm, srpe, volume, weighin, wendler531

    for mod in (volume, e1rm, weighin, wendler531, srpe):
        _register_descriptors(mod.register(), f"builtin:{mod.__name__}")


def load_plugins(log: TrainingLog | None = None, base_path: Path | None = None) -> None:
    """Discover and load all plugins. Call once at startup."""
    PLUGINS.clear()
    USER_PLUGINS.clear()
    _load_builtins()
    if log is not None and base_path is not None:
        _load_from_log_directives(log, base_path)

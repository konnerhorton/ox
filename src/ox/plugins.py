"""Plugin discovery and loading for ox.

Plugins are Python modules that export a register() function returning
a list of plugin descriptors (dicts). Two plugin types are supported:

- "report": query SQLite, return (columns, rows)
- "generator": accept parameters, return .ox formatted text

Discovery sources (loaded in order):
1. ~/.ox/plugins/*.py  (personal scripts)
2. Entry points in the "ox.plugins" group (installable packages)
"""

import importlib.util
import logging
from importlib.metadata import entry_points
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path.home() / ".ox" / "plugins"
ENTRY_POINT_GROUP = "ox.plugins"

REPORT_PLUGINS: dict[str, dict] = {}
GENERATOR_PLUGINS: dict[str, dict] = {}


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


def _register_descriptors(descriptors: list[dict], source: str) -> None:
    """Register plugin descriptors into the appropriate registry."""
    for desc in descriptors:
        plugin_type = desc.get("type")
        name = desc.get("name")

        if not plugin_type or not name or "fn" not in desc:
            logger.warning(
                "Skipping malformed plugin descriptor from %s: %s", source, desc
            )
            continue

        if plugin_type == "report":
            if name in REPORT_PLUGINS:
                logger.warning("Report plugin '%s' redefined by %s", name, source)
            REPORT_PLUGINS[name] = desc
        elif plugin_type == "generator":
            if name in GENERATOR_PLUGINS:
                logger.warning("Generator plugin '%s' redefined by %s", name, source)
            GENERATOR_PLUGINS[name] = desc
        else:
            logger.warning("Unknown plugin type '%s' from %s", plugin_type, source)


def _load_from_directory() -> None:
    """Load all .py files from ~/.ox/plugins/."""
    if not PLUGIN_DIR.is_dir():
        return
    for path in sorted(PLUGIN_DIR.glob("*.py")):
        module = _load_module_from_path(path)
        if module and hasattr(module, "register"):
            try:
                descriptors = module.register()
                _register_descriptors(descriptors, str(path))
            except Exception:
                logger.warning("Error calling register() in %s", path, exc_info=True)


def _load_from_entry_points() -> None:
    """Load plugins registered via entry points."""
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            module = ep.load()
            if hasattr(module, "register"):
                descriptors = module.register()
                _register_descriptors(descriptors, f"entry_point:{ep.name}")
        except Exception:
            logger.warning("Error loading entry point '%s'", ep.name, exc_info=True)


def load_plugins() -> None:
    """Discover and load all plugins. Call once at startup."""
    REPORT_PLUGINS.clear()
    GENERATOR_PLUGINS.clear()
    _load_from_directory()
    _load_from_entry_points()

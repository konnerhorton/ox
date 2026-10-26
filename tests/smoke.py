"""Smoke test for an installed ox-train: parse a log with the compiled grammar.

Run against a built wheel or sdist (no pytest needed):

    python tests/smoke.py examples/example.ox
"""

import sys
from pathlib import Path

import ox.lsp  # noqa: F401  (the language server module imports cleanly)
from ox.cli import parse_file

log = parse_file(Path(sys.argv[1]))
errors = [d for d in log.diagnostics if d.severity == "error"]
if not log.sessions or errors:
    sys.exit(f"smoke test failed: {len(log.sessions)} sessions, errors: {errors}")
print(f"ok: {len(log.sessions)} sessions")

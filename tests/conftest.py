"""Shared test fixtures and configuration."""

from pathlib import Path

import pytest

from ox.cli import parse_file
from ox.db import create_db


@pytest.fixture
def simple_log_content():
    """Simple training log for testing.

    Design choices:
    - Uses single-line entry (simplest case)
    - Uses multi-line session (common case)
    - Tests both completed (*) and planned (!) flags
    - Includes weights in kg and lbs
    - Uses different rep schemes (5x5 and 5/5/5)
    """
    return """# Test training log
2025-01-10 * pullups: BW 5x10

@session
2025-01-11 * Upper Day
bench-press: 135lb 5x5
kb-oh-press: 24kg 5/5/5
@end

@session
2025-01-12 ! Lower Day
squat: 185lb 3x5
@end
"""


@pytest.fixture
def simple_log_file(simple_log_content, tmp_path):
    """Create a temporary file with simple training log content.

    Using tmp_path fixture ensures cleanup after test.
    """
    file_path = tmp_path / "test_log.ox"
    file_path.write_text(simple_log_content)
    return file_path


@pytest.fixture
def weight_edge_cases():
    """Edge cases for weight parsing.

    These are the formats mentioned in the docs that we need to support:
    - Single weight: "24kg"
    - Combined weights: "24kg+32kg" (two kettlebells)
    - Progressive weights: "160/185/210lbs" (different weights per set)
    """
    return {
        "single_kg": "24kg",
        "single_lb": "135lb",
        "combined": "24kg+32kg",
        "progressive_explicit": "24kg/32kg/48kg",
        "progressive_implied": "160/185/210lb",  # This is the known bug
    }


@pytest.fixture
def simple_db(simple_log_file):
    """In-memory SQLite database loaded from the simple test log."""
    log = parse_file(simple_log_file)
    conn = create_db(log)
    yield conn
    conn.close()


@pytest.fixture
def example_db():
    """In-memory SQLite database loaded from the example training log."""
    log = parse_file(Path(__file__).parent.parent / "example" / "example.ox")
    conn = create_db(log)
    yield conn
    conn.close()

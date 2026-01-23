# Tests

Minimal test suite for ox v0.1.

## Running Tests

```bash
# Install test dependencies
uv pip install --dev

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_data.py

# Run specific test
pytest tests/test_data.py::TestTrainingSet::test_create_bodyweight_set
```

## Test Structure

### conftest.py
Shared fixtures used across test files:
- `simple_log_content` - Simple training log string for testing
- `simple_log_file` - Temporary file with training log content
- `weight_edge_cases` - Edge cases for weight parsing

### test_data.py
Tests for data structures in isolation:
- `TestTrainingSet` - TrainingSet properties (reps, weight, volume)
- `TestMovement` - Movement aggregations (total_reps, total_volume, top_set_weight)
- `TestTrainingLog` - Query methods (movements, movement_history, most_recent_session)

**Why**: These tests verify business logic without needing the parser.

### test_parse.py
Tests for parsing functions:
- `TestWeightTextToQuantity` - Parsing individual weights ("24kg", "135lbs")
- `TestProcessWeights` - Complex weight formats (combined, progressive)
  - **Note**: Contains `@pytest.mark.xfail` for known bug with implied units

**Why**: Weight parsing is the most error-prone part and has a known bug.

### test_integration.py
End-to-end tests:
- `TestParseFile` - Full pipeline from text file to data structures
- `TestEndToEndScenarios` - User workflows (analyze progression, calculate volume)

**Why**: These verify the complete user experience works.

## Test Philosophy

For v0.1, we focus on:

1. **Critical paths work** - Can users parse files and query data?
2. **Known problem areas** - Weight parsing is tested thoroughly
3. **Example file validity** - The example file we ship must be valid
4. **Business logic** - Calculations like total_volume are correct

We explicitly don't test:
- Every possible edge case (not needed for v0.1)
- CLI interactive features (hard to test, low value)
- Error messages (can improve later)
- Performance (not a concern yet)

## Known Issues

### Weight Parsing Bug
The test `test_progressive_weights_implied_unit` is marked as `xfail` because we know it fails:

```python
# This doesn't work yet:
process_weights("160/185/210lbs")

# But this does:
process_weights("160lbs/185lbs/210lbs")
```

This is tracked as a known issue for v0.1 release.

## Coverage

We don't measure coverage for v0.1. These tests give us confidence the core functionality works, which is sufficient for an initial release.

If you want to add coverage later:
```bash
pip install pytest-cov
pytest --cov=ox --cov-report=html
```

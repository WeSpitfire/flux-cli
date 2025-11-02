# Flux CLI Test Suite

## Overview

Comprehensive test suite for Flux CLI using pytest.

## Structure

```
tests/
├── __init__.py           # Test package
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── test_file_ops.py  # File operations tests
│   └── test_codebase_intelligence.py  # Graph tests
└── integration/          # Integration tests (TODO)
    └── test_workflow.py  # End-to-end workflow tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov pytest-asyncio
```

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest -m unit
```

### Run Integration Tests Only

```bash
pytest -m integration
```

### Run with Coverage

```bash
pytest --cov=flux --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/unit/test_file_ops.py
```

### Run Specific Test

```bash
pytest tests/unit/test_file_ops.py::TestReadFilesTool::test_read_single_file
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (> 1 second)

## Writing Tests

### Unit Test Example

```python
import pytest

@pytest.mark.unit
def test_something(temp_dir):
    # Use fixtures
    # Test a specific function/class
    assert True
```

### Integration Test Example

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
async def test_complete_workflow(temp_dir, mock_config):
    # Test complete user workflow
    pass
```

## Fixtures

See `conftest.py` for available fixtures:

- `temp_dir` - Temporary directory for testing
- `sample_python_file` - Sample Python file
- `sample_js_file` - Sample JavaScript file
- `mock_config` - Mock configuration

## Coverage

After running tests with coverage, open `htmlcov/index.html` to view detailed coverage report.

## TODO

- [ ] Add integration tests for complete workflows
- [ ] Add tests for LLM provider mocking
- [ ] Add tests for approval system
- [ ] Add tests for undo/redo functionality
- [ ] Add performance benchmarks

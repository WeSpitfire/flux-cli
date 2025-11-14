# Flux CLI Testing Strategy

## Overview

This document outlines the testing strategy for Flux CLI to ensure production readiness and prevent regression bugs.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_conversation_flow.py      # Core conversation flow tests (NEW)
├── test_providers.py              # Provider-specific tests
├── test_error_handling.py         # Error handling tests
└── unit/                          # Unit tests
    ├── test_codebase_intelligence.py
    └── test_file_ops.py
```

## Test Categories

### 1. Integration Tests (`test_conversation_flow.py`)

**Purpose**: Verify end-to-end conversation flows work correctly

**Coverage**:
- ✅ Single turn conversations (user → assistant)
- ✅ Tool execution flow (user → assistant → tool_use → tool_result → assistant)
- ✅ Multi-turn conversations with context
- ✅ Context pruning preserves tool pairs
- ✅ Incomplete tool pairs are removed

**Run**:
```bash
pytest tests/test_conversation_flow.py -v
```

### 2. Provider Tests (`test_providers.py`)

**Purpose**: Verify both Anthropic and OpenAI providers work

**Coverage**:
- API message formatting
- Token counting
- Streaming responses
- Tool execution protocol

**Run**:
```bash
python tests/test_providers.py  # Requires API keys
```

### 3. Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation

**Coverage**:
- Context manager logic
- File operations
- Codebase intelligence
- Tool schemas

**Run**:
```bash
pytest tests/unit/ -v
```

## Critical Test Scenarios

### Scenario 1: Multi-Turn Tool Execution

**What it tests**: The bug we fixed where conversations would hang after 2-3 turns

**Flow**:
1. User sends message
2. Assistant responds with tool_use
3. Tool executes, result added to history
4. Assistant continues with text response
5. User sends follow-up message
6. **CRITICAL**: This should NOT error or hang

**Test**: `test_conversation_flow.py::TestContinueWithToolResults::test_continue_after_tools`

### Scenario 2: Context Pruning with Tool Pairs

**What it tests**: The bug where context pruning broke tool_use/tool_result pairs

**Flow**:
1. Long conversation with multiple tool uses
2. Context pruning activates
3. **CRITICAL**: Tool_use and tool_result pairs must stay together or be removed together

**Test**: `test_conversation_flow.py::TestContextPruning::test_anthropic_tool_pairs_preserved`

### Scenario 3: API Protocol Compliance

**What it tests**: Anthropic's strict protocol requirements

**Flow**:
1. User message → assistant with tool_use → user with tool_result → assistant response
2. **CRITICAL**: No extra "continue" messages should be added

**Verified by**: Code inspection in `conversation_manager.py` line 468 (uses `continue_with_tool_results`)

## Running Tests

### Quick Validation
```bash
./run_tests.sh
```

### All Tests
```bash
pytest tests/ -v
```

### With Coverage
```bash
pytest tests/ --cov=flux --cov-report=html
open htmlcov/index.html
```

### Specific Categories
```bash
pytest -m integration  # Integration tests only
pytest -m unit         # Unit tests only
```

### Watch Mode (for development)
```bash
pytest-watch tests/
```

## Pre-Production Checklist

Before deploying or cutting a release:

- [ ] All conversation flow tests pass
- [ ] Provider tests pass (with real API keys)
- [ ] No regressions in existing tests
- [ ] Manual smoke test: multi-turn conversation with tool use
- [ ] Manual smoke test: context pruning with tools
- [ ] Check for any new error patterns in logs

## Known Issues & Monitoring

### Fixed Issues
✅ Token errors after 2-3 conversation turns (invalid "continue" message)
✅ Context pruning breaking tool pairs
✅ Missing `continue_with_tool_results` method

### Current Monitoring Points
- Debug logging shows conversation history size
- Tool pair validation in context manager
- API protocol compliance

## Adding New Tests

When adding features, ensure you add tests for:

1. **Happy path**: Feature works as expected
2. **Error cases**: Feature handles errors gracefully
3. **Edge cases**: Empty inputs, long inputs, malformed data
4. **Integration**: Feature works with rest of system

Example:
```python
@pytest.mark.asyncio
async def test_new_feature(anthropic_provider):
    \"\"\"Test description.\"\"\"
    # Arrange
    # ... setup
    
    # Act
    result = await provider.new_method()
    
    # Assert
    assert result == expected
```

## CI/CD Integration

### GitHub Actions (example)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=flux
```

### Pre-commit Hooks
```bash
#!/bin/sh
# .git/hooks/pre-commit
pytest tests/test_conversation_flow.py -v
if [ $? -ne 0 ]; then
  echo "❌ Tests failed. Commit aborted."
  exit 1
fi
```

## Debugging Failed Tests

### View detailed output
```bash
pytest tests/test_conversation_flow.py -v -s
```

### Run specific test
```bash
pytest tests/test_conversation_flow.py::TestToolExecution::test_tool_use_and_result -v
```

### Drop into debugger on failure
```bash
pytest tests/ --pdb
```

## Test Coverage Goals

- Core conversation flow: **100%** (critical path)
- Context management: **90%+** (complex logic)
- Tool execution: **90%+** (critical for UX)
- Provider implementations: **80%+** (covered by integration tests)

## Future Improvements

- [ ] Add performance benchmarks
- [ ] Add stress tests (1000+ message conversations)
- [ ] Add security tests (prompt injection, etc.)
- [ ] Add provider compatibility matrix
- [ ] Add automated regression testing

## Support

For test failures or questions:
1. Check this document first
2. Review test output carefully
3. Check debug logs (`[DEBUG]` messages)
4. Review recent code changes in conversation_manager.py and providers

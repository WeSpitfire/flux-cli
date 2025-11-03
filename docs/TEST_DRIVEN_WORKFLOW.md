# Test-Driven Workflow Mode

## Overview

Flux's Test-Driven Workflow Mode provides intelligent, automatic test execution that monitors your codebase and runs relevant tests whenever files change. This feature creates a continuous feedback loop, catching issues immediately as you code.

## Features

### 🎯 Smart Test Runner
- **Automatic Framework Detection**: Detects pytest, unittest, jest, mocha, and vitest
- **Result Parsing**: Extracts detailed test statistics, failures, and timing
- **Failure Analysis**: Shows test names, file paths, line numbers, and error messages
- **Pass Rate Calculation**: Tracks test success rates over time

### 👁️ Intelligent Test Watcher
- **File Monitoring**: Watches all source and test files for changes
- **Smart Test Selection**: Runs only affected tests based on file relationships
- **Debouncing**: Collects multiple rapid changes before running tests
- **Non-blocking Execution**: Tests run in background without blocking workflow

### 📊 Beautiful Result Display
- **Colored Output**: Green for passes, red for failures, yellow for skipped
- **Rich Panels**: Clean, organized test result summaries
- **Failure Details**: Truncated error messages with file paths and line numbers
- **Duration Tracking**: Shows test execution time

## Commands

### Run Tests Once

```bash
# Slash command
/test

# Natural language
run the tests
test the code
execute tests
```

**Example Output:**
```
Running tests... (Framework: pytest)

╭─ ✓ Test Results ─────────────────────────╮
│ PYTEST Test Results                      │
│                                           │
│ Tests: 15                                 │
│ Passed: 14                                │
│ Failed: 1                                 │
│ Duration: 2.34s                          │
│ Pass Rate: 93.3%                         │
╰───────────────────────────────────────────╯

Failures:

  ❌ test_file_analyzer::test_count_functions
     File: tests/unit/test_file_analyzer.py
     Error: AssertionError: Expected 3, got 2
```

### Start Watch Mode

```bash
# Slash command
/watch

# Natural language
start test watching
watch tests
monitor files
enable watch mode
```

**What happens:**
1. Initial test suite runs immediately
2. File watcher activates for project directory
3. Tests auto-run when source or test files change
4. Results display automatically after each run
5. Continues until stopped with Ctrl+C or `/watch-stop`

**Example Output:**
```
Starting test watch mode...
Framework: pytest
Watching: /Users/developer/my-project

Tests will run automatically when files change
Press Ctrl+C to stop

Running initial test suite...

[test results display...]

────────────────────────────────────────────────────────
Tests completed

[subsequent test results after file changes...]
```

### Stop Watch Mode

```bash
# Slash command
/watch-stop

# Natural language
stop watch mode
disable watching
end test monitoring
```

## How It Works

### Test Framework Detection

Flux automatically detects your test framework by examining:

1. **Python Projects**:
   - Looks for `pytest.ini`, `pyproject.toml` with pytest config
   - Checks `setup.py` for test dependencies
   - Falls back to unittest if test files match `test_*.py` pattern

2. **JavaScript/TypeScript Projects**:
   - Reads `package.json` dependencies
   - Detects jest, mocha, or vitest
   - Checks for framework-specific config files

### Smart Test Selection

When a file changes, the watcher:

1. **If it's a test file**: Runs that test file directly
2. **If it's a source file**: Finds related test files using:
   - Name-based patterns (`test_<file>.py`, `<file>.test.js`)
   - Directory structure (tests in `tests/`, `__tests__/`, `test/`)
   - Proximity (tests near source files)

3. **Fallback**: If no related tests found, runs all tests

### Debouncing & Batching

To avoid excessive test runs:
- **Debounce delay**: 300ms after last file change
- **Batch collection**: Groups multiple rapid changes
- **Single test in progress**: Won't start new run until current completes

## Supported Test Frameworks

### Python

**pytest**
```bash
# Detected commands
pytest -v
pytest -v tests/unit/test_file.py
```

**unittest**
```bash
# Detected commands
python -m unittest discover
python -m unittest tests.unit.test_file
```

### JavaScript/TypeScript

**Jest**
```bash
# Detected commands
npm test --
npm test -- path/to/test.js
```

**Mocha**
```bash
# Detected commands
npm test
npm test -- path/to/test.js
```

**Vitest**
```bash
# Detected commands
npm run test
npm run test -- path/to/test.js
```

## Configuration

### Ignored Paths

The watcher automatically ignores:
- `__pycache__`, `.pytest_cache`
- `node_modules`
- `.git`
- `.venv`, `venv`
- `.egg-info`, `.pyc` files

### Watched File Extensions

- Python: `.py`
- JavaScript: `.js`, `.jsx`
- TypeScript: `.ts`, `.tsx`

## Integration with Other Features

### State Tracking

Test results integrate with Flux's project state awareness:
- Test failures recorded in state tracker
- Suggestions engine uses test status for recommendations
- State command shows last test run results

### Error Parser

Failed tests feed into the error parser:
- Automatic error detection and categorization
- Smart suggestions for fixing test failures
- Integration with `/fix` command for automated repairs

### Memory System

Test runs saved in project memory:
- Track test success/failure over time
- Link tests to specific checkpoints
- Reference test results in conversation context

## Best Practices

### 1. Start Watch Mode Early
Enable watch mode at the beginning of your coding session to catch issues immediately.

### 2. Keep Tests Fast
Watch mode works best with fast tests. Consider:
- Unit tests for watch mode
- Integration tests for manual runs
- Use test marks/tags to filter slow tests

### 3. Fix Failures Quickly
Don't let failures accumulate. Address them as they appear to maintain clean state.

### 4. Use Natural Language
Leverage Flux's natural language support:
```
"start watching tests"
"what's the test status?"
"fix the failing test"
```

### 5. Combine with Other Features
```
# Example workflow
flux: start watching tests
[Edit code, tests run automatically]
flux: show me what changed
flux: commit the changes
```

## Troubleshooting

### Tests Not Running Automatically

**Symptom**: File changes don't trigger test runs

**Solutions**:
1. Check watch mode is active: Look for "Watch mode already running" message
2. Verify file extensions: Only `.py`, `.js`, `.ts`, `.jsx`, `.tsx` trigger tests
3. Check ignore patterns: Ensure your files aren't in ignored directories
4. Restart watch mode: `/watch-stop` then `/watch`

### Wrong Test Framework Detected

**Symptom**: Using pytest but unittest runs, or vice versa

**Solutions**:
1. Add framework config file (`pytest.ini` for pytest)
2. Add framework to `pyproject.toml` or `package.json`
3. Check current detection: Framework shown when starting watch mode

### Tests Run Multiple Times

**Symptom**: Same test runs repeatedly for single change

**Solutions**:
1. Debouncing should prevent this - if occurring, may be a bug
2. Check if multiple files being saved simultaneously (e.g., auto-format)
3. Stop and restart watch mode

### High CPU Usage

**Symptom**: CPU usage increases significantly during watch mode

**Solutions**:
1. Reduce watched directories (currently watches entire project)
2. Use more specific test commands
3. Ensure no infinite save loops (e.g., test modifying source files)
4. Stop watch mode when not actively coding

## Examples

### Python Project with pytest

```bash
# Start watch mode
$ flux /watch

Starting test watch mode...
Framework: pytest
Watching: /Users/dev/my-api

Tests will run automatically when files change
Press Ctrl+C to stop

Running initial test suite...

╭─ ✓ Test Results ────────────────╮
│ PYTEST Test Results             │
│                                  │
│ Tests: 42                        │
│ Passed: 42                       │
│ Failed: 0                        │
│ Duration: 3.21s                 │
│ Pass Rate: 100.0%               │
╰──────────────────────────────────╯

# Edit src/api/users.py
[File saved]

────────────────────────────────────
Tests completed

╭─ ✗ Test Results ────────────────╮
│ PYTEST Test Results             │
│                                  │
│ Tests: 5                         │
│ Passed: 4                        │
│ Failed: 1                        │
│ Duration: 0.52s                 │
│ Pass Rate: 80.0%                │
╰──────────────────────────────────╯

Failures:

  ❌ test_users::test_create_user
     File: tests/test_users.py
     Error: AssertionError: Expected status 201, got 400
```

### JavaScript Project with Jest

```bash
$ flux /watch

Starting test watch mode...
Framework: jest
Watching: /Users/dev/react-app

# Edit src/components/Button.jsx
[File saved - tests auto-run]

────────────────────────────────────
Tests completed

╭─ ✓ Test Results ────────────────╮
│ JEST Test Results                │
│                                  │
│ Tests: 8                         │
│ Passed: 8                        │
│ Failed: 0                        │
│ Skipped: 2                       │
│ Duration: 1.85s                 │
│ Pass Rate: 100.0%               │
╰──────────────────────────────────╯
```

## Future Enhancements

Planned improvements for test-driven workflow:

1. **Coverage Tracking**: Show code coverage metrics in watch mode
2. **Performance Regression**: Alert on significant test slowdowns
3. **Smart Reruns**: Only rerun tests that failed last time first
4. **Parallel Execution**: Run independent tests in parallel
5. **Custom Filters**: User-defined patterns for test selection
6. **Visual Diff**: Show test output diff between runs
7. **Notification Support**: System notifications for test results
8. **CI Integration**: Compare local results with CI pipeline

## Related Commands

- `/test` - Run tests once
- `/validate` - Validate code without running tests
- `/fix` - Auto-fix detected errors including test failures
- `/state` - Show current project state including test status
- `/debug-on` - Enable debug logging for test run troubleshooting

## Summary

Test-Driven Workflow Mode transforms Flux into a continuous testing companion, giving you instant feedback as you code. By automatically detecting frameworks, selecting relevant tests, and displaying beautiful results, it removes friction from the test-driven development process and helps you maintain high code quality effortlessly.

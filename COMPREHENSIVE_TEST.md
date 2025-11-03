# Comprehensive Flux Test

This test validates all major Flux features including the multi-line input fix.

## Test Task

Paste this entire task into Flux (desktop app or CLI) to test:

```
Create a comprehensive demo module in flux/demos/comprehensive_test.py that showcases multiple Flux capabilities:

1. FILE OPERATIONS:
   - Create a class called FluxComprehensiveDemo
   - Add an __init__ method that takes a project_path: Path parameter
   - Store it as self.project_path

2. CODE ANALYSIS:
   - Add method analyze_python_files() -> Dict[str, Any] that:
     * Uses pathlib to recursively find all .py files in project_path
     * Counts total files, total lines of code
     * Uses ast module to count functions and classes
     * Returns a dictionary with these metrics

3. GIT INTEGRATION:
   - Add method get_recent_commits(count: int = 5) -> List[Dict] that:
     * Uses subprocess to run: git log -n {count} --pretty=format:"%H|%an|%s|%ad" --date=short
     * Parses the output into list of dicts with keys: hash, author, message, date
     * Handles errors if not in a git repo

4. FILE GENERATION:
   - Add method generate_report(output_file: str = "report.md") that:
     * Calls analyze_python_files() and get_recent_commits()
     * Creates a markdown report with both sets of data
     * Writes to output_file using pathlib
     * Returns the path to the generated file

5. MAIN FUNCTION:
   - Create a main() function that:
     * Takes current directory as project path
     * Creates FluxComprehensiveDemo instance
     * Calls analyze_python_files() and prints results
     * Calls get_recent_commits() and prints results
     * Calls generate_report()
     * Add if __name__ == "__main__": block

6. DOCUMENTATION:
   - Add comprehensive Google-style docstrings for all methods
   - Include Args, Returns, and Raises sections where appropriate
   - Add type hints for all parameters and return values

7. ERROR HANDLING:
   - Add try-except blocks for file operations
   - Add try-except for git operations with informative messages
   - Create a custom exception class ProjectAnalysisError

8. TESTING:
   - Create tests/test_comprehensive_demo.py with:
     * Test for analyze_python_files using a temp directory
     * Test for get_recent_commits with mocked subprocess
     * Test for generate_report checking file creation
     * Test error handling for non-existent directories
     * Use pytest and unittest.mock

9. AFTER CREATION:
   - Run: python -m py_compile flux/demos/comprehensive_test.py
   - Run: python -m pytest tests/test_comprehensive_demo.py -v
   - Show me the git diff of changes
   - Create a checkpoint with message "Comprehensive test complete"

Requirements:
- Use pathlib for ALL file operations (no os.path)
- Use subprocess.run() with capture_output=True for git
- Follow PEP 8 style guidelines
- Python 3.8+ compatible
- Include proper type hints from typing module
- Make all paths work cross-platform
```

## What This Tests

### ✅ Multi-line Input Fix
- **Long multi-line prompt** with numbered sections
- **Nested sub-bullets** and formatting
- **Code blocks** within the task description
- Tests that Flux receives this as ONE consolidated message

### ✅ Core Flux Features
1. **File creation** - Creates new Python module
2. **Code generation** - Multiple classes and methods
3. **Documentation** - Docstrings and type hints
4. **Git integration** - subprocess calls to git
5. **Testing** - Creates pytest tests with mocks
6. **Validation** - Runs py_compile and pytest
7. **Workflow** - Git diff and checkpoints
8. **Error handling** - Custom exceptions and try-catch

### ✅ Tool Usage
- `write_file` - Creates new files
- `run_command` - Runs py_compile, pytest, git diff
- `validate_syntax` - Code validation
- Memory commands - Checkpoint

## Expected Behavior

**If multi-line fix works:**
- ✅ Flux understands ALL requirements at once
- ✅ Creates complete module with all 9 sections
- ✅ Creates comprehensive tests
- ✅ Runs validation commands
- ✅ Creates checkpoint
- ✅ No questions like "What do you want?" or "Please specify..."

**If multi-line fix fails:**
- ❌ Flux processes line-by-line
- ❌ Asks "What would you like me to do?"
- ❌ Only implements first few items
- ❌ Needs clarification on each section

## How to Run

### Option 1: Desktop App (Tests newline encoding)
1. Restart desktop app: `cd flux-desktop && npm start`
2. Enable debug: `/debug-on`
3. Copy the entire test task above (from "Create a comprehensive..." to "...cross-platform")
4. Paste into textarea
5. Press Enter
6. Observe: Should process as ONE task

### Option 2: CLI Direct (Tests paste mode)
1. Run: `cd /Users/developer/SynologyDrive/flux-cli && python -m flux`
2. Enable debug: `/debug-on`
3. Paste the entire test task
4. Press Enter twice (auto-submit)
5. Observe: Should process as ONE task

## Verification

After Flux completes:

```bash
# Check files were created
ls -la flux/demos/comprehensive_test.py
ls -la tests/test_comprehensive_demo.py

# Check debug logs show ONE user_input
/debug
# Should show single user_input event with full multi-line content

# Run the generated code
python flux/demos/comprehensive_test.py

# Run the tests
pytest tests/test_comprehensive_demo.py -v
```

## Success Criteria

1. ✅ Flux processes entire task without asking for clarification
2. ✅ Both files created with all required sections
3. ✅ Code compiles without syntax errors
4. ✅ Tests run successfully
5. ✅ Checkpoint created
6. ✅ Debug log shows ONE consolidated user_input (not fragmented)

## If It Fails

Check debug logs:
```bash
cat ~/.flux/debug/debug_*.jsonl | tail -100 | grep user_input
```

Should show ONE event with length ~2000+ chars, not multiple events with lengths of 50-100 chars each.

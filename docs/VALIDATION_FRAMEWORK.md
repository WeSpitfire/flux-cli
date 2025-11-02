# Validation Framework

Comprehensive input validation and error handling for all Flux tools to prevent security issues and improve error messages.

## Overview

The validation framework provides:
- **Command validation** - Prevents command injection and dangerous operations
- **Path validation** - Blocks access to system files and validates file paths
- **Input validation** - Ensures tool inputs are safe and well-formed
- **Better error messages** - Clear, actionable error messages with suggestions

## Command Validation

### Location
`flux/tools/command.py::validate_command_string()`

### Features
- Detects shell metacharacters that enable command injection (`;`, `&&`, `||`, `|`, `` ` ``, `$(`)
- Blocks dangerous operations (`rm -rf /`, fork bombs, disk writes)
- Returns detailed error messages explaining why a command was rejected

### Usage
```python
from flux.tools.command import validate_command_string

is_valid, message = validate_command_string("echo 'hello'")
# Returns: (True, "Command is safe.")

is_valid, message = validate_command_string("echo test && rm file")
# Returns: (False, "Command contains unsafe sequence '&&' which could enable command injection.")
```

### Protected Against
- Command injection via shell metacharacters
- Fork bombs: `:(){ :|:& };:`
- System file deletion: `rm -rf /`
- Bulk file deletion: `rm -rf *`
- Direct disk writes: `dd if=/dev/zero of=/dev/sda`

## File Path Validation

### Location
`flux/tools/file_ops.py::validate_file_path()`

### Features
- Blocks access to sensitive system directories (`/etc/passwd`, `/etc/shadow`, etc.)
- Detects null byte injection attacks
- Validates characters based on operation type (read/write/delete)
- Extra protection for delete operations on critical directories

### Usage
```python
from flux.tools.file_ops import validate_file_path
from pathlib import Path

is_valid, error_msg = validate_file_path("test.py", Path.cwd(), "read")
# Returns: (True, None)

is_valid, error_msg = validate_file_path("/etc/passwd", Path.cwd(), "read")
# Returns: (False, "Access to system path '/etc/passwd' is not allowed for security reasons.")
```

### Protected Against
- Access to system configuration files (`/etc/*`, `/boot`, `/sys`, `/proc`)
- Windows system directories (`C:\Windows\System32`)
- Null byte injection (`path\x00injection`)
- Invalid filename characters in write operations
- Deletion of critical directories (`/`, `/home`, `/usr`, `/var`)

## Tool Integration

### RunCommandTool
Validates all commands before execution:

```python
tool = RunCommandTool(Path.cwd())

# Safe command - executes normally
result = await tool.execute("echo 'test'")

# Unsafe command - rejected with error
result = await tool.execute("echo test && rm file")
# Returns: {"error": "Command contains unsafe sequence '&&'..."}
```

### ReadFilesTool
Validates all file paths before reading:

```python
tool = ReadFilesTool(Path.cwd())

# Safe path - reads normally
result = await tool.execute(["test.py"])

# Dangerous path - rejected with error
result = await tool.execute(["/etc/passwd"])
# Returns: {"error": {"code": "INVALID_PATH", "message": "Access to system path..."}}
```

### WriteFileTool
Validates paths and prevents writes to system directories:

```python
tool = WriteFileTool(Path.cwd())

# Safe write - succeeds
result = await tool.execute("myfile.txt", "content")

# Dangerous path - rejected
result = await tool.execute("/etc/passwd", "malicious")
# Returns: {"error": {"code": "INVALID_PATH", ...}}
```

### EditFileTool
Validates paths and search/replace inputs:

```python
tool = EditFileTool(Path.cwd())

# Valid edit - succeeds
result = await tool.execute("test.py", "old_text", "new_text")

# Empty search string - rejected
result = await tool.execute("test.py", "", "replacement")
# Returns: {"error": {"code": "INVALID_INPUT", "message": "Search string cannot be empty.", ...}}

# Too short search string - rejected
result = await tool.execute("test.py", "ab", "replacement")
# Returns: {"error": {"code": "INVALID_INPUT", "message": "Search string is too short...", ...}}
```

## Error Message Improvements

All validation errors now return structured error objects with:
- **Error code** - Categorizes the error (`INVALID_PATH`, `INVALID_INPUT`, etc.)
- **Message** - Human-readable explanation
- **Suggestion** - Actionable advice for fixing the error

Example error response:
```python
{
    "error": {
        "code": "INVALID_PATH",
        "message": "Access to system path '/etc/passwd' is not allowed for security reasons.",
        "path": "/etc/passwd",
        "suggestion": "Check the file path for invalid characters or access to restricted directories."
    }
}
```

## Testing

### Run Tests
```bash
python test_validation_integration.py
```

### Test Coverage
- **Command validation** (4 tests)
  - Safe commands pass
  - Unsafe characters detected
  - Dangerous operations blocked
  - Integration with RunCommandTool

- **Path validation** (3 tests)
  - Safe paths pass
  - Dangerous paths blocked
  - Invalid characters detected

- **Tool integration** (3 tests)
  - ReadFilesTool validation
  - WriteFileTool validation
  - EditFileTool validation

### Expected Output
```
============================================================
TEST SUMMARY
============================================================
Total: 10
Passed: 10
Failed: 0

✓ ALL TESTS PASSED!
```

## Security Considerations

### Defense in Depth
The validation framework provides multiple layers of protection:
1. **Input validation** - Reject dangerous inputs before processing
2. **Path resolution** - Validate resolved paths, not just inputs
3. **Operation-specific checks** - Different rules for read/write/delete
4. **Tool-level enforcement** - Each tool validates its inputs

### Known Limitations
- **Platform-specific** - Some validations are OS-specific (Windows vs Unix)
- **Not foolproof** - Determined attackers may find bypasses
- **Performance overhead** - Validation adds small overhead to each operation
- **False positives** - May block some legitimate edge cases

### Best Practices
- Always validate user input before passing to tools
- Use the most restrictive validation for the operation
- Log validation failures for security monitoring
- Regularly update validation patterns for new threats

## Extending the Framework

### Adding New Validations

1. **Command validation** - Add patterns to `validate_command_string()`:
```python
dangerous_patterns = [
    (r'your_pattern', "Description of why it's dangerous"),
    ...
]
```

2. **Path validation** - Add paths to dangerous_paths list in `validate_file_path()`:
```python
dangerous_paths = [
    '/new/dangerous/path',
    ...
]
```

3. **Tool-specific validation** - Add checks in tool's `execute()` method:
```python
# Example: Validate file size
if len(content) > MAX_FILE_SIZE:
    return {
        "error": {
            "code": "FILE_TOO_LARGE",
            "message": f"File exceeds maximum size of {MAX_FILE_SIZE} bytes.",
            "suggestion": "Split the file into smaller chunks."
        }
    }
```

## Related Files

- `flux/tools/command.py` - Command validation and RunCommandTool
- `flux/tools/file_ops.py` - Path validation and file operation tools
- `flux/tools/validation.py` - Code validation tool (separate concern)
- `test_validation_integration.py` - Comprehensive test suite
- `docs/SMART_RELIABILITY.md` - Related reliability improvements

## Future Enhancements

Planned improvements:
1. **Rate limiting** - Prevent abuse via repeated operations
2. **Audit logging** - Log all validation failures for security analysis
3. **Configurable policies** - Allow users to customize validation rules
4. **Machine learning** - Detect anomalous patterns in tool usage
5. **Sandboxing** - Isolate dangerous operations in containers

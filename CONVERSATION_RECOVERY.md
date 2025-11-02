# Conversation Recovery Fix

## Problem
When users cancelled operations mid-stream (Ctrl+C or rejecting changes), Flux would crash with error:
```
Error: 'str' object has no attribute 'get'
```

After this error, **the conversation would be permanently broken** - users couldn't continue chatting.

## Root Causes

### 1. String Error Parsing Bug
**Location**: `flux/ui/cli.py`, line 620

**Before**:
```python
error_dict = result.get("error", {})
error_code = error_dict.get("code") if isinstance(error_dict, dict) else None
error_message = error_dict.get("message") if isinstance(error_dict, dict) else str(result.get("error"))
#                                                                                  ^^^^^^^^^^^^^^^^
# BUG: If result.get("error") returns a string, calling .get() on it crashes!
```

**Problem**: When tools return `{"error": "Some string"}` instead of `{"error": {"code": "...", "message": "..."}}`, the code tried to call `.get()` on a string.

**Fix**:
```python
error_data = result.get("error", {})
# Handle both dict and string errors
if isinstance(error_data, dict):
    error_code = error_data.get("code")
    error_message = error_data.get("message", str(error_data))
else:
    # Error is a string directly
    error_code = None
    error_message = str(error_data)
```

### 2. Unhandled KeyboardInterrupt
**Location**: `flux/ui/cli.py`, `execute_tool()` and `continue_after_tools()`

**Before**: KeyboardInterrupt was not caught, causing the entire conversation loop to break.

**Fix**: Added KeyboardInterrupt handling in two places:

#### In `execute_tool()`:
```python
except KeyboardInterrupt:
    # User cancelled during tool execution
    error_msg = "Operation cancelled by user"
    self.llm.add_tool_result(tool_id, {"error": error_msg, "cancelled": True})
    self.console.print(Panel(
        error_msg,
        title="✗ Cancelled",
        border_style="yellow"
    ))
    # Don't re-raise - allow conversation to continue
```

#### In `continue_after_tools()`:
```python
try:
    # ... tool execution ...
except KeyboardInterrupt:
    # User cancelled during continuation
    self.console.print("\n[yellow]Operation cancelled[/yellow]")
    # Don't re-raise - return to main loop
except Exception as e:
    # Log error but don't crash - allow user to continue
    self.console.print(f"\n[red]Error in conversation: {e}[/red]")
    self.console.print("[dim]You can continue chatting - the error has been handled[/dim]")
```

## User Experience

### Before ❌
```
You: Can you build this feature?
Flux: [starts tool execution]
      [shows changes]
Apply changes? [y/n]: n
✗ Changes rejected
Error: 'str' object has no attribute 'get'

You: hello?
[no response - chat is broken]

You: Can you help?
[no response - must restart Flux]
```

### After ✅
```
You: Can you build this feature?
Flux: [starts tool execution]
      [shows changes]
Apply changes? [y/n]: n
✗ Changes rejected

You: Actually, can you modify it differently?
Flux: Sure, let me adjust the approach...
[conversation continues normally]
```

Or with Ctrl+C:
```
You: Can you build this feature?
Flux: [starts tool execution]
^C Operation cancelled

You: Let's try a different approach
Flux: Of course, what would you like to try?
[conversation continues normally]
```

## Error Types Handled

### 1. String Errors
```python
{"error": "Change rejected by user"}
{"error": "File not found"}
{"error": "Invalid path"}
```

### 2. Dict Errors
```python
{"error": {"code": "INVALID_PATH", "message": "Path is invalid"}}
{"error": {"code": "SYNTAX_ERROR", "message": "Syntax error at line 10"}}
```

### 3. Complex Dict Errors
```python
{"error": {"nested": "data", "other": "fields"}}
# Falls back to str(error_data) - won't crash
```

## Testing

Run the test suite:
```bash
python test_error_handling.py
```

Expected output:
```
✅ Dict error parsed correctly
✅ String error parsed correctly  
✅ Nested dict error handled
✅ KeyboardInterrupt caught
✅ Conversation can continue after cancellation
```

## Technical Details

### Error Flow

#### Tool Execution Error:
```
User rejects change
  ↓
Tool returns: {"error": "Change rejected by user"}
  ↓
execute_tool() catches the error
  ↓
Parses error (handles string vs dict)
  ↓
Adds to conversation with llm.add_tool_result()
  ↓
Displays error panel
  ↓
Returns normally (doesn't crash)
  ↓
continue_after_tools() proceeds
  ↓
User can send next message
```

#### KeyboardInterrupt Flow:
```
User presses Ctrl+C
  ↓
KeyboardInterrupt raised
  ↓
Caught in execute_tool() or continue_after_tools()
  ↓
Shows cancellation message
  ↓
Returns normally (doesn't crash)
  ↓
Main REPL loop continues
  ↓
User can send next message
```

## Files Modified

- `flux/ui/cli.py`:
  - Line 613-626: Fixed error parsing for both string and dict errors
  - Line 684-693: Added KeyboardInterrupt handling in `execute_tool()`
  - Line 706-747: Wrapped `continue_after_tools()` in try/except for graceful error handling

## Related Issues

This fix resolves:
1. ✅ Conversation breaking after rejecting changes
2. ✅ Conversation breaking after Ctrl+C
3. ✅ "str has no attribute 'get'" error
4. ✅ Unable to continue chatting after errors
5. ✅ Having to restart Flux after cancellations

## Future Improvements

### 1. Conversation State Recovery
Add explicit state reset command:
```python
/recover - Reset conversation state if stuck
```

### 2. Error Logging
Log all errors to file for debugging:
```python
~/.flux/error.log
```

### 3. Graceful Degradation
If LLM conversation fails, provide manual options:
```
Error in conversation. Options:
  1. Retry last message
  2. Clear conversation history
  3. Start new conversation
  4. Exit Flux
```

### 4. State Persistence
Save conversation state periodically so crashes can be recovered:
```python
~/.flux/conversation_backup.json
```

## Summary

This fix ensures that **Flux conversations are robust and recoverable**:

- ✅ Handles string errors without crashing
- ✅ Handles dict errors as before
- ✅ Catches KeyboardInterrupt gracefully
- ✅ Conversation continues after cancellations
- ✅ User never needs to restart Flux
- ✅ Clear feedback on what happened

**Result**: Users can freely cancel operations, reject changes, and recover from errors without breaking their conversation flow.

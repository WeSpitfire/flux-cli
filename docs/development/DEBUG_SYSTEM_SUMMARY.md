# Flux Debug System - Implementation Summary

## Problem Statement

During testing, Flux exhibited confusing behavior when given multi-line prompts with blank lines:
- Repeatedly asked "Please provide..." despite being given complete requirements
- Overwrote its own work (created file, then replaced tests)
- Got stuck in clarification loops
- No visibility into what was happening internally

## Root Causes Identified

1. **Input Processing**: Multi-line input with blank lines may be parsed incorrectly
2. **Context Loss**: Conversation history not maintaining full task context across tool executions
3. **No Diagnostics**: No way to see what Flux receives, how it interprets inputs, or why it makes decisions
4. **Token Budget Blindness**: Users can't see what's consuming tokens or when they're approaching limits

## Solution: Comprehensive Debug System

### Components Implemented

#### 1. Debug Logger (`flux/core/debug_logger.py`)
A comprehensive logging system that tracks:
- **User inputs**: Raw and processed, with metadata (length, line count, has newlines)
- **System prompts**: Complete prompts sent to LLM with token estimates
- **Context state**: Current tasks, modified files, memory state
- **Tool executions**: Name, inputs, results, success/failure
- **LLM responses**: Text and tool calls
- **Conversation history**: Message counts, roles, estimated tokens

**Features:**
- Logs saved to `~/.flux/debug/debug_<timestamp>.jsonl`
- Disabled by default (zero overhead when not needed)
- Immediate write-to-disk for crash recovery
- Pattern detection for common issues

#### 2. State Inspector (`/inspect` command)
Real-time view of Flux's internal state:
```
/inspect
```

Shows:
- Conversation history stats (message counts by role)
- Recent message exchange (last 5)
- Current context (task, modified files)
- Active failures and retry loops
- Token usage with percentage of limit
- Cost breakdown

#### 3. Debug Commands

**Enable/Disable:**
```
/debug-on    # Enable debug logging
/debug-off   # Disable debug logging
/debug       # Show debug session summary
```

**Analysis:**
```
/debug-analyze "describe issue here"
```
Automatically detects:
- Empty input patterns (parsing issues)
- Tool retry loops
- Multi-line input problems
- Conversation anomalies

#### 4. Integration with Existing Systems

Debug logging integrated at key points:
- `process_query()` - Logs raw user input
- `_build_system_prompt()` - Logs complete prompt
- `execute_tool()` - Logs tool calls and results
- `continue_after_tools()` - Logs LLM responses

Zero performance impact when disabled.

### Usage Examples

#### Diagnosing "Please provide..." Loops

```bash
# Start with debug enabled
/debug-on

# Paste your multi-line task
Create a new Python utility module called 'file_analyzer.py'...
[Flux asks for clarification]

# Analyze what went wrong
/debug-analyze "Flux lost my input"

# Output shows:
⚠️  3 multi-line inputs detected
⚠️  Empty `user:` messages found - possible parsing issue
```

#### Monitoring Complex Tasks

```bash
# Set task context
/task Implement complete file analyzer with tests

# Check state periodically
/inspect

# See exactly where you are:
Conversation History:
  Total messages: 12
  Estimated tokens: ~2,400

Current Context:
  Task: Implement complete file analyzer with tests
  Modified files: 2

Token Usage: 45% of limit
```

#### Debugging Retry Loops

```bash
/inspect

# Shows:
⚠️  Active Failures:
  - edit_file: 3 failures

# Flux automatically blocks after 3 failures
# Manual intervention:
/clear
[provide clearer instructions]
```

## Benefits

### For Users
1. **Transparency**: See exactly what Flux is doing
2. **Control**: Understand token usage and limits
3. **Recovery**: Quick diagnosis when things go wrong
4. **Learning**: Understand how to structure prompts better

### For Developers
1. **Debugging**: Complete audit trail of all operations
2. **Pattern Detection**: Automatically identify common issues
3. **Reproduciblity**: Logs can be shared for issue reports
4. **Performance**: Zero overhead when disabled

## File Changes

### New Files
- `flux/core/debug_logger.py` - Debug logging system
- `docs/DEBUGGING_FLUX.md` - User guide
- `docs/DEBUG_SYSTEM_SUMMARY.md` - This file

### Modified Files
- `flux/ui/cli.py`:
  - Imported `DebugLogger`
  - Added debug logger initialization
  - Added `/debug`, `/debug-on`, `/debug-off`, `/debug-analyze`, `/inspect` commands
  - Integrated logging at key points
  - Added `inspect_state()` method
  - Updated help menu

## How It Solves the Original Problem

### Before
```
User: [pastes multi-line task with blank lines]
Flux: Please provide the details...
User: [confused, pastes again]
Flux: Please specify what you'd like...
User: [frustrated] ???
```

**No visibility into:**
- What Flux actually received
- Why it's asking for clarification
- What context is being lost

### After
```
User: [pastes multi-line task]
Flux: Please provide...
User: /inspect

Shows:
Last 5 Messages:
  1. user: Create a new Python...
  2. assistant: Got it...
  3. tool: {...}
  4. user: [empty]          <-- AHA! Blank line parsed as empty message
  5. assistant: Please provide...

User: /debug-analyze "lost my input"
Analysis shows:
⚠️  Empty inputs detected - possible parsing issue
⚠️  3 multi-line inputs detected

Solution: Avoid blank lines in pasted text
```

## Best Practices for Users

Based on findings:

1. **Multi-line prompts**: Avoid blank lines, use continuous text
2. **Complex tasks**: Set context with `/task` first
3. **Long sessions**: Monitor with `/inspect`, use `/clear` proactively
4. **Debugging**: Enable `/debug-on` when reproducing issues
5. **Reporting**: Include `/inspect` output and debug logs

## Future Enhancements

Potential improvements:
1. **Visual token breakdown**: Graph showing prompt/history/input split
2. **Input sanitization**: Automatically handle multi-line input better
3. **Checkpoint comparison**: Compare state before/after operations
4. **Export debug session**: Bundle logs + context for issue reports
5. **Performance metrics**: Track response times, tool execution times
6. **LLM decision tracing**: Why specific tools were chosen

## Testing Recommendations

To validate the debug system:

1. **Reproduce original issue with debug enabled:**
   ```
   /clear
   /debug-on
   [paste multi-line task with blank lines]
   /debug-analyze "clarification loop"
   ```

2. **Verify inspector shows accurate state:**
   ```
   /inspect
   # Modify a file
   /inspect  # Should show file in modified list
   ```

3. **Confirm logging works:**
   ```
   /debug-on
   [perform various operations]
   cat ~/.flux/debug/debug_*.jsonl | wc -l
   # Should have many log entries
   ```

4. **Pattern detection:**
   ```
   # Trigger a retry loop intentionally
   /debug-analyze "retry loop"
   # Should detect repeated tool calls
   ```

## Conclusion

The debug system provides comprehensive visibility into Flux's internal state and decision-making process. It transforms debugging from guesswork into data-driven analysis, making Flux more transparent, predictable, and easier to use effectively.

Key achievements:
- ✅ Complete input/output tracking
- ✅ Real-time state inspection
- ✅ Automatic pattern detection
- ✅ Zero overhead when disabled
- ✅ User-friendly commands
- ✅ Comprehensive documentation

This makes Flux significantly more reliable and debuggable for both users and developers.

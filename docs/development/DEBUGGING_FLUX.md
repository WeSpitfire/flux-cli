# Debugging Flux Issues

This guide explains how to diagnose and debug issues with Flux using the built-in debugging tools.

## Overview

Flux now includes comprehensive debugging capabilities to help you understand:
- What input Flux receives and how it's processed
- What context and prompts are sent to the LLM
- Why Flux makes certain decisions
- What's consuming your token budget
- Why Flux might be getting confused or stuck in loops

## Quick Diagnosis with `/inspect`

The fastest way to see what's happening is the `/inspect` command:

```
/inspect
```

This shows you:
- **Conversation history** - How many messages, recent exchanges
- **Current context** - Active task, modified files
- **Token usage** - How close you are to limits
- **Active failures** - Any retry loops or errors

### Example Output:
```
🔍 Conversation State Inspector
======================================================================

Conversation History:
  Total messages: 24
  User messages: 8
  Assistant messages: 10
  Tool messages: 6
  Estimated tokens: ~3,450

Last 5 Messages:
  1. user: Create a new Python utility module...
  2. assistant: Got it. To implement a utility module...
     (includes tool calls)
  3. tool: {"success": true, "path": "..."}
  4. user: 
  5. assistant: Please provide the specific functionalities...

Current Context:
  Task: None
  Modified files: 2
    - flux/utils/file_analyzer.py
    - tests/test_file_analyzer.py

Token Usage:
  Input: 12,450
  Output: 3,200
  Total: 15,650
  Cost: $0.0234
```

## Debug Logging

### Enable Debug Mode

```
/debug-on
```

This enables detailed logging of:
- Every user input (raw and processed)
- System prompts sent to LLM
- Conversation history state
- Tool calls and results
- LLM responses

Logs are saved to `~/.flux/debug/debug_<timestamp>.jsonl`

### View Debug Summary

```
/debug
```

Shows event counts and log file location.

### Disable Debug Mode

```
/debug-off
```

## Diagnosing Specific Issues

### Issue: Flux Keeps Asking for Clarification

**Symptoms:**
- You provide a task, but Flux responds with "Please provide..."
- Flux seems to lose context mid-conversation

**Diagnosis:**
```
/debug-on
[paste your task again]
/debug-analyze "Flux loses my input"
```

**What to look for:**
- Check if multi-line input has parsing issues
- Look for empty messages in conversation history
- Check if context is being properly maintained

**Common causes:**
1. **Multi-line input with blank lines** - The conversation parser may split it incorrectly
2. **Token limit reached** - Context is being pruned too aggressively
3. **Missing context preservation** - Task details not carried forward

**Solutions:**
- Try providing the task in a single line without blank lines
- Use `/clear` to reset if close to token limit
- Set a task explicitly with `/task <description>` first

### Issue: Flux Overriding Its Own Work

**Symptoms:**
- Flux completes part of a task, then undoes or overwrites it
- Tool calls seem contradictory

**Diagnosis:**
```
/inspect
```

Look at:
- **Modified files** - Are files being changed multiple times?
- **Active failures** - Is Flux in a retry loop?
- **Recent messages** - Is there confusion in the conversation?

With debug mode:
```
/debug-analyze "Flux overriding previous work"
```

**Common causes:**
1. **Incomplete task specification** - Flux interprets partial progress as errors
2. **Retry loops** - Failed operations causing repeated attempts
3. **Context loss** - Flux "forgets" what it already did

**Solutions:**
- Break large tasks into explicit steps
- Use `/memory` to check what Flux remembers
- Clear history and restart with fresh context if stuck

### Issue: Tool Retry Loops

**Symptoms:**
- Same tool called repeatedly
- Flux can't seem to make progress

**Diagnosis:**
```
/inspect
```

Check "Active Failures" section for:
```
⚠️  Active Failures:
  - edit_file: 3 failures
```

**What Flux does automatically:**
- After 2 failures: Warns and suggests different approach
- After 3 failures: Blocks the tool and forces strategy change

**Manual intervention:**
```
/clear           # Reset conversation
/undo            # Undo problematic changes
[explain issue clearly]
```

### Issue: Token Budget Exhausted

**Symptoms:**
- "Token usage at 90%+" warnings
- Rate limit errors
- Slow responses

**Diagnosis:**
```
/history
/inspect
```

**Solutions:**
```
/clear           # Clear conversation history
--max-history 4000  # Start with lower limit (CLI flag)
```

**Prevention:**
- Use `/clear` proactively when switching tasks
- Break large tasks into smaller sessions
- Avoid pasting huge code blocks repeatedly

## Advanced Debugging

### Reading Debug Logs

Debug logs are JSONL (JSON Lines) format:

```bash
cat ~/.flux/debug/debug_1234567890.jsonl | jq '.event_type'
```

### Analyzing Patterns

```
/debug-analyze "describe the issue"
```

This analyzes recent logs for:
- Empty input patterns
- Tool retry loops
- Multi-line input issues
- Conversation anomalies

## Best Practices

### For Multi-Step Tasks

1. **Enable debug mode first:**
   ```
   /debug-on
   ```

2. **Set the task explicitly:**
   ```
   /task Implement file analyzer with all features
   ```

3. **Provide complete requirements in one message:**
   - Avoid blank lines in pasted text
   - Use bullet points, not numbered lists with spacing
   - Keep formatting simple

4. **Monitor progress:**
   ```
   /inspect     # Check state periodically
   ```

5. **Checkpoint important moments:**
   ```
   /checkpoint Completed file_analyzer.py core functionality
   ```

### For Debugging Session

1. **Reproduce the issue with debug on:**
   ```
   /clear
   /debug-on
   [reproduce issue]
   ```

2. **Analyze immediately:**
   ```
   /debug-analyze "describe what went wrong"
   ```

3. **Inspect state:**
   ```
   /inspect
   ```

4. **Save debug log:**
   The log file path is shown when you enable debug mode. Copy it somewhere safe before disabling.

## Common Patterns & Solutions

| Pattern | Cause | Solution |
|---------|-------|----------|
| Empty `user:` messages | Multi-line input parsing | Avoid blank lines in pasted text |
| Repeated tool calls | Context not updated | Check with `/inspect`, may need `/clear` |
| "Please provide..." loops | Lost task context | Use `/task` to set context explicitly |
| High token usage | Long conversation | Use `/clear` regularly |
| Tool repeatedly fails | Incompatible approach | Explicitly suggest different tool/method |

## Getting Help

When reporting issues, include:

1. **Output of `/inspect`**
2. **Output of `/debug-analyze`** (if debug was enabled)
3. **The debug log file** (`~/.flux/debug/debug_*.jsonl`)
4. **Description of what you expected vs. what happened**

Example:
```
I asked Flux to create a file with multiple functions, but it kept 
asking for clarification. Here's my /inspect output:

[paste /inspect output]

Debug log: ~/.flux/debug/debug_1699123456.jsonl
```

## Summary

- **Quick check:** Use `/inspect` to see current state
- **Deep dive:** Enable `/debug-on` and use `/debug-analyze`
- **Stuck in a loop:** Check for retry patterns, use `/clear` if needed
- **Multi-line input issues:** Avoid blank lines, paste as continuous text
- **Token limits:** Monitor with `/history`, clear proactively with `/clear`

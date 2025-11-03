# Flux Debug Quick Reference

## 🚨 Something's Wrong? Start Here

```bash
/inspect                    # See what's happening right now
```

## 🐛 Common Issues & Quick Fixes

### Flux Keeps Asking "Please provide..."
**Problem:** Context lost, empty messages, or multi-line input issues

**Quick Fix:**
```bash
/inspect                    # Check recent messages
/task [describe task]       # Set context explicitly
[paste task as single paragraph, no blank lines]
```

### Flux Overwriting Its Own Work
**Problem:** Retry loop or task confusion

**Quick Fix:**
```bash
/inspect                    # Check for failures
/clear                      # Reset if stuck
[break task into smaller steps]
```

### "Token limit approaching" Warnings
**Problem:** Running out of context space

**Quick Fix:**
```bash
/clear                      # Clear conversation
/history                    # Check usage first
```

### Same Tool Failing Repeatedly
**Problem:** Retry loop detected

**Quick Fix:**
```bash
/inspect                    # See failure count
/undo                       # Undo if needed
[suggest different approach explicitly]
```

## 📊 Debug Commands

### Quick Inspection
```bash
/inspect                    # Full state inspector
/history                    # Token usage stats
/memory                     # Project memory
/workflow                   # File modification status
```

### Debug Mode
```bash
/debug-on                   # Enable detailed logging
/debug                      # Show debug summary
/debug-off                  # Disable logging
/debug-analyze "issue"      # Analyze recent logs
```

### Context Management
```bash
/task <description>         # Set task context
/checkpoint <message>       # Save progress point
/clear                      # Clear conversation
```

## 🔍 What `/inspect` Shows You

```
Conversation History        → How many messages exchanged
Last 5 Messages            → Recent conversation flow
Current Context            → Active task, modified files
Active Failures            → Retry loops, error patterns
Token Usage                → Budget consumption, cost
```

## 💡 Best Practices

### ✅ DO
- Enable `/debug-on` before reproducing issues
- Use `/inspect` periodically during long tasks
- Set task with `/task` for complex work
- Paste text as continuous paragraphs
- Use `/clear` when switching tasks
- Monitor token usage with `/history`

### ❌ DON'T
- Paste text with blank lines in task descriptions
- Let token usage exceed 80% without clearing
- Continue if Flux is in a retry loop (use `/inspect` to check)
- Paste huge code blocks repeatedly
- Mix multiple unrelated tasks in one session

## 🆘 Debugging Workflow

1. **Notice Issue** → Run `/inspect`
2. **See Pattern** → Check recent messages, failures, token usage
3. **Enable Debug** → `/debug-on` to capture details
4. **Reproduce** → Try the operation again
5. **Analyze** → `/debug-analyze "describe issue"`
6. **Fix** → Apply solution from analysis
7. **Verify** → `/inspect` again to confirm

## 📝 Reporting Issues

When reporting Flux issues, include:

1. Output of `/inspect`
2. Output of `/debug-analyze` (if debug was enabled)
3. Debug log file path (shown by `/debug-on`)
4. What you expected vs. what happened

**Example:**
```
Issue: Flux keeps overwriting tests

/inspect output:
[paste here]

Debug log: ~/.flux/debug/debug_1699123456.jsonl
```

## 🎯 Quick Diagnostics

| Symptom | Check | Likely Cause |
|---------|-------|-------------|
| Empty responses | `/inspect` recent messages | Context loss |
| Repeated tool calls | `/inspect` failures | Retry loop |
| "Please provide..." | `/inspect` last message | Empty input parsed |
| Slow/errors | `/history` | Token limit hit |
| Overwrites work | `/workflow` + `/inspect` | Task confusion |

## 📖 Full Documentation

- **User Guide:** `docs/DEBUGGING_FLUX.md`
- **Implementation:** `docs/DEBUG_SYSTEM_SUMMARY.md`
- **Help Menu:** Type `/help` in Flux

## 🔧 Debug Log Location

```
~/.flux/debug/debug_<timestamp>.jsonl
```

View with:
```bash
cat ~/.flux/debug/*.jsonl | jq '.'
cat ~/.flux/debug/*.jsonl | jq '.event_type'
cat ~/.flux/debug/*.jsonl | jq 'select(.event_type=="tool_call")'
```

---

**Remember:** `/inspect` is your friend. When in doubt, inspect!

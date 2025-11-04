# Multi-Line Input & Paste Mode

## Problem Solved

Previously, when users pasted multi-line tasks with blank lines or entered tasks line-by-line, Flux would:
- Create empty messages in conversation history
- Ask for clarification after each line
- Lose context and get confused
- Fragment the task into many separate queries

**Example of the problem:**
```
User: Create a Python module called 'code_metrics.py'
Flux: Please provide the specific metrics...
User: 1. Analyze a Python file to extract:
Flux: Please provide the specific details...
User: - Total lines of code
Flux: Please provide...
```

Result: 43 messages in conversation for a single task!

## Solution: Paste Mode

Flux now has **intelligent paste mode** that collects multi-line input and sends it as a single coherent message.

### Auto-Detection

Flux automatically enters paste mode when you start typing:
- Numbered lists: `1.`, `2.`, `3.`
- Bullet lists: `-`, `*`
- Task descriptions ending with `:`

**Example:**
```
You: Create a Python module called 'code_metrics.py' that:
Paste mode ON (finish with /end or ```)
You (paste): 1. Analyzes Python files
… composing (1 lines). Type /end to send, /discard to cancel
You (paste): 2. Counts functions and classes
… composing (2 lines). Type /end to send, /discard to cancel
You (paste): 3. Generates reports
… composing (3 lines). Type /end to send, /discard to cancel
You (paste): /end
✓ Sent composed input

Flux: [processes entire task as one message]
```

### Manual Activation

Start paste mode explicitly:

```bash
/paste          # Start paste mode
# or
```           # Use triple backticks
```

Then paste your content and end with:

```bash
/end            # Send the composed message
# or
/send           # Same as /end
# or
```           # Triple backticks again
# or
/discard        # Cancel and throw away
```

## Usage Examples

### Example 1: Large Task with Requirements

```
You: /paste
Paste mode ON (finish with /end or ```)

You (paste): Create a new Python utility module called 'file_analyzer.py' that:
… composing (1 lines)

You (paste): 1. Scans directories for code files
… composing (2 lines)

You (paste): 2. Analyzes each file to count:
… composing (3 lines)

You (paste):    - Lines of code
… composing (4 lines)

You (paste):    - Functions and classes
… composing (5 lines)

You (paste): 3. Generates JSON and Markdown reports
… composing (6 lines)

You (paste): Then create comprehensive tests
… composing (7 lines)

You (paste): /end
✓ Sent composed input

Flux: [Processes complete task, creates file, writes tests, etc.]
```

### Example 2: Auto-Detected Numbered List

```
You: I need you to do the following:
Detected multi-line task. Paste mode ON

You (paste): 1. Fix the bug in authentication.py
… composing (1 lines)

You (paste): 2. Add error handling
… composing (2 lines)

You (paste): 3. Update the tests
… composing (3 lines)

You (paste): /end
✓ Sent composed input
```

### Example 3: Code Snippet

````
You: ```
Paste mode ON

You (paste): def analyze_code(file_path):
… composing (1 lines)

You (paste):     """Analyze Python file"""
… composing (2 lines)

You (paste):     # Implementation here
… composing (3 lines)

You (paste): ```
✓ Sent composed input
````

## Commands

| Command | Action |
|---------|--------|
| `/paste` | Manually start paste mode |
| ` ``` ` | Start/end paste mode (triple backticks) |
| `/end` | Finish composing and send |
| `/send` | Same as `/end` |
| `/discard` | Cancel and discard buffered input |
| `/clear` | Clears conversation AND paste buffer if active |

## Auto-Detection Rules

Flux enters paste mode automatically when you type:

1. **Numbered list**: Lines starting with `1.`, `2.`, etc.
   ```
   1. First item    ← Auto-detected
   2. Second item
   ```

2. **Bullet list**: Lines starting with `-` or `*`
   ```
   - First item     ← Auto-detected
   - Second item
   ```

3. **Task header**: Line ending with `:` and longer than 10 chars
   ```
   Create a module that:    ← Auto-detected
   ```

## Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| `You` | Normal mode - ready for single-line input |
| `You (paste)` | Paste mode active - collecting lines |
| `… composing (N lines)` | N lines collected, waiting for more |
| `✓ Sent composed input` | Successfully sent combined message |
| `✗ Discarded` | Paste mode cancelled |

## Benefits

### Before (Line-by-Line)
- ❌ 43 messages for a single task
- ❌ Empty messages causing confusion
- ❌ Flux asks for clarification repeatedly
- ❌ Context lost between lines
- ❌ Poor user experience

### After (Paste Mode)
- ✅ 1 message for entire task
- ✅ No empty messages
- ✅ Flux processes complete context
- ✅ Natural multi-line task input
- ✅ Great user experience

## Best Practices

### ✅ DO

**For complex tasks:**
```
/paste
[paste entire task description]
/end
```

**For numbered/bulleted lists:**
Just start typing - auto-detection handles it:
```
1. First requirement
2. Second requirement
3. Third requirement
/end
```

**For code snippets:**
````
```
def my_function():
    pass
```
````

### ❌ DON'T

**Don't press enter after single line and expect continuation:**
```
You: Create a module
[Flux processes immediately - no paste mode]
```

**If you want multi-line, start with a trigger:**
```
You: Create a module that:    ← This triggers paste mode
```

## Debug Integration

Paste mode works seamlessly with debug mode:

```bash
/debug-on
/paste
[paste task]
/end
```

The debug logger will show:
- Single `user_input` event with complete combined text
- No empty messages
- Proper `has_newlines` and `line_count` metadata

## Technical Details

### How It Works

1. **Detection**: Regex patterns detect list starts or task headers
2. **Buffer**: Lines accumulated in `_compose_buffer`
3. **Combine**: Lines joined with `\n` when `/end` is sent
4. **Process**: Combined text sent as single query to LLM

### State Management

- `_compose_mode` (bool): Whether paste mode is active
- `_compose_buffer` (list[str]): Accumulated lines
- Both cleared on `/end`, `/discard`, or `/clear`

### Integration Points

- Prompt label changes to show mode
- `/clear` command clears paste buffer
- Debug logger sees combined input as single event
- No modification to downstream processing

## Migration Guide

### Old Way (Problematic)
```
User types: Create a module
User types: 1. Does X
User types: 2. Does Y
User types: Then test it

Result: 4+ separate queries, confusion
```

### New Way (Fixed)
```
User types: Create a module that:  ← Auto-enters paste mode
User types: 1. Does X
User types: 2. Does Y
User types: Then test it
User types: /end  ← Sends as one query

Result: 1 query, perfect understanding
```

## Troubleshooting

### "Detected multi-line task" when I didn't want it

Auto-detection triggered. Just type `/discard` to cancel and retype as single line.

### Paste mode stuck

Type `/discard` to exit, or `/clear` to reset everything.

### Want to paste code without triggering

Use explicit mode:
````
/paste
[your code without list markers]
/end
````

### Forget to use /end

Flux will wait forever showing `You (paste)`. Just type `/end` when ready.

## Summary

The paste mode feature transforms Flux from **frustratingly asking for clarification** to **intelligently understanding multi-line tasks**. It's the fix that makes Flux the great AI editor it should be!

**Key Features:**
- 🎯 Auto-detects multi-line tasks
- 📋 Collects all input before processing
- 🔄 Prevents empty message problems
- ✨ Natural, intuitive workflow
- 🐛 Integrates with debug system
- 📊 Reduces conversation clutter from 43+ to 1 message

Try it out with the original problematic task from the debug logs - it will now work perfectly!

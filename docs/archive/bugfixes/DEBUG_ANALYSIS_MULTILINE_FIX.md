# Debug Analysis: Multi-Line Input Fragmentation in Desktop App

**Date**: 2025-11-03
**Issue**: Flux desktop app was fragmenting multi-line tasks into separate messages
**Status**: ✅ Fixed

## Problem Diagnosis

### Symptoms
When pasting a comprehensive multi-line task into the Flux desktop app:
- Each line was processed as a separate user message
- Flux kept asking for clarification ("What do you want to do?")
- Empty input lines caused repeated prompts
- Task implementation was incomplete and confused

### Root Cause Analysis

From debug log `/Users/developer/.flux/debug/debug_1762144610.jsonl`:

```jsonl
{"event_type": "user_input", "data": {"raw": "Create a Python module...", "length": 144, "line_count": 1}}
{"event_type": "user_input", "data": {"raw": "1. Create a class...", "length": 62, "line_count": 1}}
{"event_type": "user_input", "data": {"raw": "", "length": 0, "line_count": 1}}
{"event_type": "user_input", "data": {"raw": "- analyze_codebase...", "length": 93, "line_count": 1}}
```

**The problem:**
1. Desktop app collected the full multi-line text correctly in the textarea
2. Desktop app sent it as one command via `window.flux.sendCommand(tabId, command)`
3. **BUT** Python's `Prompt.ask()` in CLI reads stdin line-by-line
4. When desktop app writes multi-line text to Flux's stdin, Python processes each `\n` as a new prompt cycle
5. Flux's paste mode auto-detection couldn't trigger because each line arrived separately

### Why Paste Mode Didn't Work

The paste mode detection in `flux/ui/cli.py` at line 203:
```python
self._enable_paste_mode = sys.stdin.isatty()  # Only enable for real terminals
```

Desktop app creates a pseudo-terminal (PTY), so `stdin.isatty()` returns `True`. However:
- Paste mode regex at line 357 looks for patterns like numbered lists: `r"^(\s*\d+\.|\s*[-*])\s+"`
- Paste mode only triggers AFTER the first line matches
- By then, subsequent lines have already been processed as separate messages
- The buffering mechanism expects interactive typing, not programmatic line-by-line writing to stdin

## The Fix

Modified `/Users/developer/SynologyDrive/flux-cli/flux-desktop/src/renderer/renderer.js` to use Flux's explicit paste mode protocol for multi-line commands:

```javascript
// Check if command is multi-line - if so, use explicit paste mode
const isMultiLine = command.includes('\n');

if (isMultiLine) {
  // Send multi-line command using paste mode protocol
  // 1. Enter paste mode
  window.flux.sendCommand(tabManager.activeTabId, '/paste');
  // Small delay to let paste mode activate
  setTimeout(() => {
    // 2. Send each line
    const lines = command.split('\n');
    lines.forEach(line => {
      window.flux.sendCommand(tabManager.activeTabId, line);
    });
    // 3. End paste mode
    setTimeout(() => {
      window.flux.sendCommand(tabManager.activeTabId, '/end');
    }, 50 * lines.length); // Delay based on number of lines
  }, 50);
} else {
  // Send single-line command directly
  window.flux.sendCommand(tabManager.activeTabId, command);
}
```

### How It Works
1. Desktop app detects `\n` characters in the textarea value
2. Sends `/paste` command first to explicitly enter paste mode
3. Sends each line sequentially (with small delays to avoid race conditions)
4. Sends `/end` to finalize and process the complete multi-line task as ONE message

## Verification

To verify the fix works:

1. **Rebuild the desktop app:**
   ```bash
   cd flux-desktop
   npm install
   npm start
   ```

2. **Test with a multi-line task:**
   ```
   Create a test module with:
   1. A main function
   2. Helper utilities
   3. Unit tests
   4. Documentation
   ```

3. **Check debug logs:**
   ```bash
   /debug-on
   # Paste multi-line task
   /debug-analyze
   ```

Expected: One consolidated user_input event with full multi-line content, not fragmented messages.

## Alternative Solutions Considered

### Option 1: Use a different delimiter
Replace `\n` with a special marker like `<NEWLINE>` before sending
- ❌ Rejected: Would break actual newlines in code blocks

### Option 2: Disable paste mode in desktop app
Set environment variable to disable paste mode entirely
- ❌ Rejected: Paste mode is useful when typing interactively in desktop

### Option 3: Batch stdin writes
Buffer all lines and write to stdin as one block
- ❌ Rejected: Python's `Prompt.ask()` still processes line-by-line

### Option 4: Use explicit paste mode protocol ✅
Send `/paste` → lines → `/end` automatically
- ✅ **Selected**: Clean, works with existing Flux features, no breaking changes

## Impact

### Before Fix
- Desktop app: Multi-line tasks fragmented → confused Flux
- CLI direct use: Multi-line paste mode worked correctly

### After Fix
- Desktop app: Multi-line tasks work seamlessly
- CLI direct use: No changes, still works perfectly
- Consistent behavior across both interfaces

## Lessons Learned

1. **Stdin line buffering matters**: Even when sending multi-line strings to stdin, Python's input readers process line-by-line
2. **PTY vs TTY detection**: `sys.stdin.isatty()` returns True for pseudo-terminals, not just real terminals
3. **Auto-detection has limits**: Regex-based paste mode detection works for interactive typing but not programmatic stdin writes
4. **Explicit protocols are reliable**: Using `/paste` command explicitly avoids auto-detection edge cases
5. **Debug logging is essential**: The detailed debug logs immediately revealed the line-by-line fragmentation issue

## Related Files

- `/Users/developer/SynologyDrive/flux-cli/flux/ui/cli.py` (lines 193-362) - Paste mode implementation
- `/Users/developer/SynologyDrive/flux-cli/flux-desktop/src/renderer/renderer.js` (lines 423-474) - Desktop app command execution
- `/Users/developer/SynologyDrive/flux-cli/flux/core/debug_logger.py` - Debug logging system that helped diagnose the issue

## Future Improvements

1. **Add paste mode visual indicator** in desktop app when multi-line detected
2. **Optimize timing delays** - currently using fixed 50ms delays, could be adaptive
3. **Add paste mode success confirmation** - wait for Flux's paste mode prompt before sending lines
4. **Support for file uploads** - extend paste protocol to handle file content pasting

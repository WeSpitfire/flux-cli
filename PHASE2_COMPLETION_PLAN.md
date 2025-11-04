# Phase 2 Completion Plan

## Current Status
**CommandRouter**: ✅ Created (705 lines) and integrated  
**CLI Cleanup**: ❌ INCOMPLETE - old handlers still present

## Problem
The CLI file (2917 lines) still contains ~650 lines of duplicate command handlers that need removal.

## Files Affected
- `flux/ui/cli.py` - lines 373-1043 contain old command handlers
- These ALL need to be deleted (CommandRouter now handles them)

## Precise Removal Strategy

### What to Keep (Lines 1-372, 1044+)
1. **Lines 1-372**: All initialization, imports, dependencies, REPL setup
2. **Lines 373-440ish**: PASTE MODE LOGIC (the real one with `import time`, `/end`, `/send`, `/discard`)
3. **Lines 1044+**: Query processing (`await self.process_query(query)`) and exception handling

### What to DELETE (Lines 441-1043)
These are ALL duplicate handlers now in CommandRouter:
- `/state` handler (~60 lines)
- `/session`, `/workflows`, `/workflow` handlers
- `/watch`, `/status`, `/auto-approve` handlers  
- `/suggest`, `/help`, `/model` handlers
- `/task`, `/memory`, `/checkpoint`, `/project` handlers
- `/undo`, `/undo-history` handlers
- `/workflow`, `/approval` handlers
- `/diff`, `/commit`, `/test` handlers
- `/watch`, `/watch-stop` handlers
- `/index`, `/analyze`, `/related`, `/architecture`, `/preview` handlers
- `/newtask`, `/tasks`, `/summary`, `/stats`, `/performance`, `/metrics` handlers
- `/validate` handler
- `/debug`, `/debug-on`, `/debug-off`, `/debug-analyze`, `/inspect` handlers
- `/autofix*` handlers (7 different commands)
- Duplicate `/help` with long help text

## Correct Paste Mode Section (what should remain)
```python
# Paste mode handling (only if enabled for interactive terminals)
import time
current_time = time.time()

if getattr(self, "_enable_paste_mode", True) and getattr(self, "_compose_mode", False):
    # Check for explicit end commands
    if query.strip() in ('/end', '/send', '```'):
        combined = "\n".join(self._compose_buffer).strip()
        self._compose_mode = False
        self._compose_buffer = []
        if not combined:
            self.console.print("[dim]Nothing to send[/dim]")
            continue
        query = combined
    elif query.strip() == '/discard':
        self._compose_mode = False
        self._compose_buffer = []
        self.console.print("[yellow]Discarded paste buffer[/yellow]")
        continue
    elif not query.strip():
        # Empty line after paste - auto-send if buffer has content
        if self._compose_buffer and (current_time - self._last_input_time) > 0.5:
            combined = "\n".join(self._compose_buffer).strip()
            self._compose_mode = False
            self._compose_buffer = []
            query = combined
        else:
            # Still pasting - skip empty line
            self._last_input_time = current_time
            continue
    else:
        # Accumulate silently
        self._compose_buffer.append(query)
        self._last_input_time = current_time
        continue

# Manual paste mode start
if query.strip() in ('/paste', '```'):
    self._compose_mode = True
    self._compose_buffer = []
    self._last_input_time = current_time
    self.console.print("[dim]Paste mode - press Enter twice when done[/dim]")
    continue

# Skip empty input in normal mode
if not query.strip():
    continue

# Auto-detect paste: if input looks like start of multi-line, enter silent mode
import re
if getattr(self, "_enable_paste_mode", True) and (re.match(r"^(\s*\d+\.|\s*[-*])\s+", query) or (query.rstrip().endswith(':') and len(query) > 10)):
    self._compose_mode = True
    self._compose_buffer = [query]
    self._last_input_time = current_time
    continue

# Process query
await self.process_query(query)
```

## ONE-STEP Solution

Delete lines ~373-1043 and replace with ONLY the paste mode logic above (plus the exception handling that follows).

## Expected Result
- CLI: ~2300 lines (down from 2917)
- Removed: ~617 lines of duplicate handlers
- All commands work via CommandRouter
- Paste mode logic intact
- Query processing preserved

## Test After Cleanup
```bash
python -m py_compile flux/ui/cli.py  # Must pass
flux /help  # Should show help from CommandRouter
flux /test  # Should run tests via CommandRouter
```

## Next Session Actions
1. Read lines 360-1100 from CLI
2. Identify exact start/end of paste mode logic
3. ONE edit: Delete all old handlers, keep paste mode
4. Test syntax
5. Commit Phase 2 COMPLETE

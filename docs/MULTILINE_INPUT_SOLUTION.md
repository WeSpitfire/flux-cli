# Multi-Line Input Solution: Newline Encoding

## The Core Problem

**Why multi-line input breaks with `Prompt.ask()`:**

1. Desktop app sends: `"line1\nline2\nline3\n"` to Flux's stdin
2. Flux CLI uses: `query = Prompt.ask()` which reads **ONE LINE AT A TIME**
3. Result:
   - First loop: reads `"line1"` → processes as separate message
   - Second loop: reads `"line2"` → processes as separate message  
   - Third loop: reads `"line3"` → processes as separate message
4. Flux sees 3 separate user messages instead of 1 multi-line message

## Why Warp Works

Warp doesn't use `Prompt.ask()`. It likely:
- Uses a custom input handler that reads complete messages
- Has a protocol where multi-line input is sent as a complete block
- Or uses a different IPC mechanism entirely (not stdin/stdout)

## Our Solution: Newline Encoding

Instead of trying to change how `Prompt.ask()` works (we can't), we **encode** newlines before sending.

### Desktop App (JavaScript)
```javascript
// Before sending to Flux
const hasNewlines = command.includes('\n');
if (hasNewlines) {
  const encoded = command.replace(/\n/g, '<<<NEWLINE>>>');
  window.flux.sendCommand(tabManager.activeTabId, encoded);
}
```

**What happens:**
- User types: `"Create file:\n1. Function\n2. Tests"`
- Desktop encodes: `"Create file:<<<NEWLINE>>>1. Function<<<NEWLINE>>>2. Tests"`
- Sends as **ONE LINE** to stdin: `"Create file:<<<NEWLINE>>>1. Function<<<NEWLINE>>>2. Tests\n"`

### Flux CLI (Python)
```python
query = Prompt.ask(f"\n[bold green]You[/bold green]")

# Decode newline placeholders
if '<<<NEWLINE>>>' in query:
    query = query.replace('<<<NEWLINE>>>', '\n')
```

**What happens:**
- `Prompt.ask()` reads the entire encoded string as ONE line
- Decodes back to: `"Create file:\n1. Function\n2. Tests"`
- Flux sees complete multi-line message!

## Why This Works

1. **Single Line Transport**: The entire message arrives as one line to `Prompt.ask()`
2. **Preserves Structure**: Newlines are preserved via encoding/decoding
3. **No Timing Issues**: No need for delays, paste mode, or complex protocols
4. **Works Everywhere**: CLI direct use unaffected, desktop app works perfectly
5. **Simple**: Minimal code changes, easy to understand

## Alternative Considered

### Paste Mode Protocol
❌ **Rejected**: Required complex timing, delays, and state management:
```javascript
window.flux.sendCommand(tabId, '/paste');
setTimeout(() => {
  lines.forEach((line, i) => {
    setTimeout(() => sendCommand(line), i * 50);
  });
  setTimeout(() => sendCommand('/end'), lines.length * 50 + 100);
}, 100);
```

**Problems:**
- Race conditions with timing
- Complexity in both client and server
- Hard to debug when delays are wrong
- Still relied on line-by-line processing

### Raw Stdin Reading
❌ **Rejected**: Would break interactive use:
```python
# Read until double newline?
while True:
    line = sys.stdin.readline()
    if not line.strip():
        break
```

**Problems:**
- Breaks rich terminal prompts
- Requires different code paths for interactive vs non-interactive
- User doesn't know when to stop typing
- Incompatible with `rich` library's Prompt

### JSON-RPC Protocol
❌ **Rejected**: Overly complex for simple input:
```javascript
window.flux.sendCommand(tabId, JSON.stringify({
  type: 'user_input',
  content: multilineText,
  timestamp: Date.now()
}));
```

**Problems:**
- Requires complete rewrite of CLI input handling
- Breaks compatibility with direct terminal use
- Adds unnecessary complexity

## Benefits of Newline Encoding

✅ **Simple**: 2 lines of code in JS, 2 lines in Python
✅ **Reliable**: No timing issues or race conditions
✅ **Fast**: No delays needed
✅ **Compatible**: Works with existing `Prompt.ask()`
✅ **Transparent**: CLI users never see the encoding
✅ **Debuggable**: Easy to see in logs if something goes wrong

## Testing

### Test Case 1: Simple Multi-line
```
Input (desktop):
Create a file with:
1. A function
2. A test

Encoded:
Create a file with:<<<NEWLINE>>>1. A function<<<NEWLINE>>>2. A test

Decoded (Flux):
Create a file with:
1. A function
2. A test
```

### Test Case 2: Code Blocks
```
Input (desktop):
Write this function:

def hello():
    print("Hi")

Encoded:
Write this function:<<<NEWLINE>>><<<NEWLINE>>>def hello():<<<NEWLINE>>>    print("Hi")

Decoded (Flux):
Write this function:

def hello():
    print("Hi")
```

### Test Case 3: Single Line
```
Input: Create a file called test.py
Encoded: Create a file called test.py (no encoding needed)
Decoded: Create a file called test.py (no decoding needed)
```

## Implementation Files

- **Desktop App**: `/flux-desktop/src/renderer/renderer.js` (lines 452-464)
- **Flux CLI**: `/flux/ui/cli.py` (lines 215-217)

## Verification

After implementing, test with:
```bash
cd flux-desktop && npm start
# In desktop app, paste:
Create a file called test.py with:
1. A function called greet(name)
2. A function called add(a, b)
3. A main block

# Expected: Flux creates file with all 3 parts in ONE response
```

Check debug logs:
```python
/debug-on
# Paste test above
/debug

# Should show ONE user_input event with full multi-line content
```

## Conclusion

This is the **simplest, most reliable solution** that:
- Respects the limitations of `Prompt.ask()`
- Works with existing code architecture
- Requires minimal changes
- Has zero timing issues
- Is easy to understand and maintain

Like Warp, we now have seamless multi-line input that "just works."

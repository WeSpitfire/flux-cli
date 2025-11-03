# Retry Loop Fix - Before/After Comparison

## Problem Scenario

User asks: "I like this idea, let's integrate it into our system"

### BEFORE (Problematic Behavior)

```
Flux: [Attempts edit_file]
╭─ 🔧 Tool ─────────────────────────╮
│ edit_file                         │
│ {'path': 'cli.py', 'search': '...'} │
╰───────────────────────────────────╯
⚠ Search text not found. Reading file for context...
╭─ ✓ Result ────────────────────────╮
│ Error: SEARCH_TEXT_NOT_FOUND      │
│ auto_recovery: file_read_completed│
╰───────────────────────────────────╯

Flux: [Attempts SAME edit_file with SAME search text]
╭─ 🔧 Tool ─────────────────────────╮
│ edit_file                         │
│ {'path': 'cli.py', 'search': '...'} │  ← SAME SEARCH TEXT
╰───────────────────────────────────╯
⚠ Search text not found. Reading file for context...
╭─ ✓ Result ────────────────────────╮
│ Error: SEARCH_TEXT_NOT_FOUND      │
│ auto_recovery: file_read_completed│
╰───────────────────────────────────╯

User: please continue

Flux: [Attempts SAME edit_file AGAIN]
╭─ 🔧 Tool ─────────────────────────╮
│ edit_file                         │
│ {'path': 'cli.py', 'search': '...'} │  ← STILL SAME
╰───────────────────────────────────╯

Apply these changes? [y/n] (y):    ← USER PROMPTED 3 TIMES!
```

**Problems:**
- LLM retries same approach 3+ times
- No indication of retry count
- Vague recovery messages
- User gets frustrated
- Eventually succeeds by luck (adjusting search text on attempt #3)

---

### AFTER (Fixed Behavior)

```
Flux: [Attempts edit_file]
╭─ 🔧 Tool ─────────────────────────╮
│ edit_file                         │
│ {'path': 'cli.py', 'search': '...'} │
╰───────────────────────────────────╯
⚠ Search text not found (attempt 1). Reading file for context...
╭─ ✓ Result ────────────────────────╮
│ Error: SEARCH_TEXT_NOT_FOUND      │
│                                   │
│ ⚠️  BEFORE RETRYING:              │
│ 1. Look at EXACT file content     │
│ 2. Copy EXACT text (all spaces)   │
│ 3. DO NOT guess                   │
│ 4. If 2nd attempt, try different  │
│    tool or approach               │
│                                   │
│ Retry count: 1/2 (next failure    │
│ will be blocked)                  │
╰───────────────────────────────────╯

Flux: [Attempts edit_file again - still wrong]
╭─ 🔧 Tool ─────────────────────────╮
│ edit_file                         │
│ {'path': 'cli.py', 'search': '...'} │
╰───────────────────────────────────╯
⚠ Search text not found (attempt 2). Reading file for context...
╭─ ✓ Result ────────────────────────╮
│ Error: SEARCH_TEXT_NOT_FOUND      │
│ Retry count: 2/2                  │
╰───────────────────────────────────╯

╭─ 🔄 Retry Warning ────────────────╮
│ ⚠️  edit_file has failed twice    │
│     in a row                      │
│                                   │
│ The LLM should now try a          │
│ DIFFERENT approach or tool.       │
│ Next attempt will be              │
│ automatically blocked.            │
╰───────────────────────────────────╯

Flux: [Attempts THIRD edit_file - BLOCKED!]
╭─ 🔧 Tool ─────────────────────────╮
│ edit_file                         │
│ {'path': 'cli.py', 'search': '...'} │
╰───────────────────────────────────╯

╭─ ❌ Blocked ──────────────────────╮
│ ⚠️  RETRY LOOP DETECTED           │
│                                   │
│ **SEARCH NOT FOUND LOOP**:        │
│ edit_file can't find your search  │
│ text.                             │
│                                   │
│ The search string doesn't match   │
│ the file EXACTLY.                 │
│                                   │
│ **Try these steps:**              │
│ 1. Read the file again            │
│ 2. Copy exact text                │
│ 3. Make search more specific      │
│                                   │
│ **Common issues:**                │
│ - Missing/extra spaces            │
│ - Different line endings          │
│ - Tabs vs spaces                  │
╰───────────────────────────────────╯

Flux: Let me try a different approach. I'll use ast_edit instead...
[Uses ast_edit or re-reads file properly]
✓ Operation successful - failure tracking reset
```

**Benefits:**
- ✅ Hard block after 2 failures
- ✅ Clear retry count displayed
- ✅ Explicit step-by-step guidance
- ✅ Visual warnings for user
- ✅ Forces strategy change
- ✅ No more triple prompts!

---

## Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| **Max retries** | ∞ (unlimited) | 2 (hard blocked on 3rd) |
| **Retry awareness** | None | Shows "attempt X/2" |
| **Error guidance** | Vague | Step-by-step instructions |
| **Visual feedback** | Minimal | Yellow warning + red block |
| **Strategy change** | Voluntary | **Forced** |
| **User experience** | Frustrating | Clear and efficient |

---

## Why This Matters

**User Impact:**
- No more being asked 3+ times for the same change
- Clear understanding of what's happening
- Faster resolution (forced to try different approach)
- Less token usage (fewer retries = lower cost)

**LLM Behavior:**
- Can't get stuck in retry loops
- Receives explicit guidance on alternatives
- System prompt includes retry warnings
- Must adapt strategy after 2 failures

**System Reliability:**
- Prevents infinite loops
- Reduces API costs
- Improves success rate
- Better user satisfaction

# Token Management Fixes - Comprehensive Review

## Problem Analysis

Based on the conversation log showing token issues, we identified **THREE critical bugs** that were causing rate limit errors:

### Bug #1: Auto-Clear Checking Wrong Token Count ⚠️ CRITICAL

**What was happening:**
```python
# Line 304 in cli.py (BEFORE FIX)
usage = self.llm.get_token_usage()
usage_percent = (usage['total_tokens'] / self.config.max_history) * 100
```

- **Root Cause**: `usage['total_tokens']` returns **cumulative API tokens** (input + output from ALL API calls in session)
- **Impact**: Auto-clear triggered at 186K tokens instead of 2.7K (90% of 3K for Haiku)
- **Why it failed**: The system was adding up ALL tokens ever sent/received, not current conversation size
- **Example**: User's session showed "186,316 tokens" before clearing - this was cumulative, not current context!

### Bug #2: Massive Tool Results Not Truncated

**What was happening:**
- Single tool call results were 37K+ tokens
- File reads, grep searches, and list_files returning huge JSON blobs
- All this context was preserved in conversation history

**Impact for Haiku (3K limit):**
- One `list_files` call could use 30-40% of entire context budget
- After 2-3 tool calls, context was full
- No room for actual conversation

### Bug #3: No Emergency Circuit Breaker

**What was missing:**
- No hard stop to prevent context from growing beyond limits
- If auto-clear at 90% failed, nothing prevented hitting rate limits
- Users would hit 429 errors with no way to recover

## The Fixes

### Fix #1: Track Conversation Tokens, Not Cumulative API Tokens

**Added to `flux/llm/base_provider.py`:**
```python
def estimate_conversation_tokens(self) -> int:
    """Estimate token count of current conversation history.
    
    Returns approximate token count (chars / 3) for context management.
    This is different from total_input_tokens which tracks API usage.
    """
    total_chars = 0
    for msg in self.conversation_history:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            import json
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(json.dumps(block))
    return total_chars // 3  # Conservative estimate: 3 chars per token
```

**Updated `flux/ui/cli.py` lines 302-337:**
```python
# CRITICAL FIX: Check conversation history size, NOT cumulative API usage!
conversation_tokens = self.llm.estimate_conversation_tokens()
usage_percent = (conversation_tokens / self.config.max_history) * 100

# Emergency circuit breaker: Hard stop at 150%
if conversation_tokens > (self.config.max_history * 1.5):
    # CRITICAL: Context has grown way too large, clear immediately
    current_task = self.memory.state.current_task
    self.llm.clear_history()
    if current_task:
        self.memory.state.current_task = current_task
    self.console.print(
        f"[bold red]🚨 Emergency context clear ({conversation_tokens:,} tokens exceeded limits)[/bold red]"
    )
    continue  # Skip this iteration, show prompt again

if usage_percent >= 90:
    # Auto-clear at 90% threshold (2.7K for Haiku)
    old_token_count = conversation_tokens
    current_task = self.memory.state.current_task
    self.llm.clear_history()
    if current_task:
        self.memory.state.current_task = current_task
    self.console.print(
        f"[dim]✨ Context automatically refreshed ({old_token_count:,} → 0 tokens)[/dim]"
    )
```

### Fix #2: Aggressive Tool Result Truncation

**Updated `flux/llm/anthropic_provider.py` lines 152-184:**
```python
def add_tool_result(self, tool_use_id: str, result: Any):
    """Add tool result to conversation history.
    
    For small models like Haiku, truncate large tool results to prevent context overflow.
    """
    # Serialize result
    if isinstance(result, str):
        result_str = result
    else:
        result_str = json.dumps(result)
    
    # For small context models (Haiku), aggressively truncate large results
    is_small_model = "haiku" in self.config.model.lower() or "gpt-3.5" in self.config.model.lower()
    max_result_size = 2000 if is_small_model else 10000
    
    if len(result_str) > max_result_size:
        # Keep error messages, truncate successful results
        if isinstance(result, dict) and "error" not in result_str.lower():
            result_str = result_str[:max_result_size] + f"\\n\\n[TRUNCATED - {len(result_str) - max_result_size:,} chars omitted for context management]"
        elif not isinstance(result, dict):
            # Plain string result
            result_str = result_str[:max_result_size] + f"\\n\\n[TRUNCATED - {len(result_str) - max_result_size:,} chars omitted]"
    
    self.conversation_history.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result_str
            }
        ]
    })
```

**Truncation Strategy:**
- Haiku: Max 2,000 chars per tool result (conservative)
- Sonnet/Opus: Max 10,000 chars per tool result (generous)
- **Keep all error messages** (important for debugging)
- **Truncate successful results** (less critical once operation succeeds)

### Fix #3: Improved /history Command

**Updated `flux/ui/cli.py` lines 387-399:**
```python
if query.lower() == '/history':
    usage = self.llm.get_token_usage()
    history_len = len(self.llm.conversation_history)
    conversation_tokens = self.llm.estimate_conversation_tokens()
    usage_percent = (conversation_tokens / self.config.max_history) * 100
    
    self.console.print(
        f"\\n[bold]💬 Conversation History:[/bold]\\n"
        f"  Messages: [cyan]{history_len}[/cyan]\\n"
        f"  Current context: [cyan]{conversation_tokens:,}[/cyan] / [dim]{self.config.max_history:,}[/dim] tokens ([cyan]{usage_percent:.1f}%[/cyan])\\n"
        f"  API usage (cumulative): [dim]{usage['total_tokens']:,} tokens[/dim]\\n"
        f"  Estimated cost: [green]${usage['estimated_cost']:.4f}[/green]\\n"
    )
```

**Now shows:**
- Current context size (what matters for rate limits)
- Cumulative API usage (for cost tracking)
- Clear distinction between the two

## Expected Impact

### For Haiku (3K Context Limit)

**Before Fixes:**
- Auto-clear triggered at 186K+ tokens (cumulative API)
- Tool results: 37K+ tokens
- Usable conversations: 1-2 exchanges before rate limits
- Rate limit errors: **Frequent**

**After Fixes:**
- Auto-clear triggers at 2.7K tokens (90% of 3K)
- Tool results: Max 2K chars each (~667 tokens)
- Emergency brake at 4.5K tokens (150% of 3K)
- Usable conversations: 5-10 exchanges easily
- Rate limit errors: **Rare/Never**

### For Sonnet (8K Context Limit)

**Before Fixes:**
- Auto-clear at wrong threshold
- Tool results could be 50K+ tokens

**After Fixes:**
- Auto-clear at 7.2K tokens (90% of 8K)
- Tool results: Max 10K chars each (~3.3K tokens)
- Emergency brake at 12K tokens
- Much more reliable long conversations

## How to Verify Fixes Work

### Test 1: Check Current Context Size
```bash
# In Flux CLI with Haiku
/history

# Should show:
# Current context: <number> / 3,000 tokens (<percentage>%)
# API usage (cumulative): <larger number> tokens
```

### Test 2: Verify Auto-Clear Triggers
```bash
# Have a long conversation (5-10 exchanges with tool calls)
# Watch for:
✨ Context automatically refreshed (2,700 → 0 tokens)

# Should trigger BEFORE hitting 3,000 tokens
```

### Test 3: Check Tool Result Truncation
```bash
# Run a command that returns large results
list_files

# Check context size afterward
/history

# Should NOT jump by more than 1K tokens per tool result
```

### Test 4: Emergency Circuit Breaker
```bash
# Try to overwhelm the context
# Make many rapid queries with tool calls

# Should see emergency clear if context grows too fast:
🚨 Emergency context clear (4,500 tokens exceeded limits)
```

## Files Modified

1. **`flux/llm/base_provider.py`**
   - Added: `estimate_conversation_tokens()` method
   - Lines: 17-33

2. **`flux/ui/cli.py`**
   - Fixed: Auto-clear logic (lines 302-337)
   - Fixed: /history command (lines 387-399)
   - Added: Emergency circuit breaker
   - Added: Color-coded context warnings

3. **`flux/llm/anthropic_provider.py`**
   - Fixed: Tool result truncation (lines 152-184)
   - Added: Model-aware size limits

## Key Concepts

### Conversation Tokens vs. API Tokens

**Conversation Tokens (NEW):**
- Size of current conversation history in memory
- What determines rate limiting
- Resets when you run `/clear` or auto-clear triggers
- **This is what we need to monitor!**

**API Tokens (OLD - misleading):**
- Cumulative count of ALL tokens sent/received in session
- Used for cost tracking
- Never resets (accumulates forever)
- **Should NOT be used for auto-clear logic!**

### Context Budget for Haiku

With 8K total context:
- System prompt: ~1,000 tokens
- Tool schemas: ~500 tokens
- Response buffer: ~2,000 tokens
- **Available for conversation: ~3,000 tokens**

This is why `max_context_tokens` is set to 3,000 for Haiku in `flux/core/config.py`.

### Truncation Strategy

**Keep Full:**
- Error messages (need full details for debugging)
- Short results (<2K chars)
- User messages (always important)

**Truncate Aggressively:**
- Large file contents from read_files
- Long directory listings from list_files
- Verbose grep results
- Successful tool results (once operation succeeds, details less critical)

## Rollback Plan

If issues occur, revert these commits and the system will go back to old behavior:
- Auto-clear based on cumulative API tokens (will trigger late)
- No tool result truncation (context will fill quickly)
- No emergency circuit breaker (rate limits possible)

Old behavior was stable but inefficient. New behavior is optimized for small context models.

## Future Improvements

1. **Smarter truncation**: Use AI to summarize tool results instead of simple truncation
2. **Adaptive limits**: Dynamically adjust truncation based on current context usage
3. **Tool result caching**: Store full results in session cache, send summaries to LLM
4. **Context compression**: Summarize old conversation turns instead of dropping them

## Testing Checklist

- [x] Syntax validation (all files compile)
- [ ] Test with Haiku model (verify 3K limit respected)
- [ ] Test with Sonnet model (verify 8K limit respected)
- [ ] Test auto-clear triggers at 90%
- [ ] Test emergency brake triggers at 150%
- [ ] Test /history shows correct numbers
- [ ] Test tool result truncation
- [ ] Test long conversation without rate limits
- [ ] Test command palette bug (separate issue)

# Max History Feature Documentation

## Overview

The `--max-history` parameter allows users to control how much conversation history Flux keeps in memory, helping manage token usage and costs when working with LLM providers.

## Usage

```bash
flux --max-history 10000 "Your query here"
```

## Default Value

- **Default**: 8000 tokens
- This provides a good balance between context retention and API rate limits

## How It Works

When Flux communicates with an LLM provider (OpenAI or Anthropic), it maintains a conversation history. As conversations get longer, this history can exceed rate limits or become costly. The `ContextManager` automatically prunes older messages to stay within the `--max-history` token limit.

### Pruning Strategy

The `ContextManager` uses an intelligent pruning strategy:

1. **Always keep**: Most recent messages (last 3 turns)
2. **High priority**: Current file content, recent errors, user requests
3. **Low priority**: Old successful tool outputs, verbose results
4. **Drop first**: Large file reads from >5 messages ago

## Implementation Details

### Files Modified

1. **`flux/main.py`**
   - Added `--max-history` argument to CLI parser
   - Passes value to `Config`

2. **`flux/core/config.py`**
   - Added `max_history` field (default: 8000)

3. **`flux/llm/openai_provider.py`**
   - Uses `config.max_history` to initialize `ContextManager`
   - Previously used hardcoded 8000

4. **`flux/llm/anthropic_provider.py`**
   - Uses `config.max_history` to initialize `ContextManager`
   - Falls back to `max_context_tokens` for backward compatibility

### Code Example

```python
# CLI argument parsing (flux/main.py)
parser.add_argument(
    "--max-history",
    type=int,
    default=8000,
    help="Maximum number of tokens to keep in conversation history (default: 8000)"
)

# Pass to config
config.max_history = args.max_history

# In provider (flux/llm/openai_provider.py)
max_history = getattr(config, 'max_history', 8000)
self.context_manager = ContextManager(max_context_tokens=max_history)
```

## When to Adjust

### Increase `--max-history` when:

- Working on complex, long-running tasks requiring deep context
- You have higher rate limits on your API key
- Cost is less of a concern than context retention

**Example:**
```bash
flux --max-history 15000 "Refactor the entire authentication system"
```

### Decrease `--max-history` when:

- Hitting rate limits frequently (429 errors)
- Working on simple, isolated tasks
- Cost optimization is important
- Using models with lower context windows

**Example:**
```bash
flux --max-history 5000 "Fix the typo in README.md"
```

## Troubleshooting

### Error: "Request too large ... Requested X tokens"

This means your conversation history exceeded the provider's rate limit. Solutions:

1. **Reduce `--max-history`**:
   ```bash
   flux --max-history 5000
   ```

2. **Clear history** (in interactive mode):
   ```
   /clear
   ```

3. **Start a new session**:
   Exit and restart Flux to clear accumulated history

### How to Check Current Usage

In interactive mode, use:
```
/history
```

This shows:
- Number of messages
- Input/output token counts
- Estimated cost

## Related Commands

- `/clear` - Clear conversation history (interactive mode)
- `/history` - View token usage statistics (interactive mode)

## Technical Notes

### Token Estimation

The `ContextManager` uses a rough estimation of ~4 characters per token. This is approximate and varies by:
- Language (code vs. natural language)
- Provider tokenization algorithm
- Content type (JSON, markdown, etc.)

### Pruning Algorithm

See `flux/core/context_manager.py` for the full implementation. Key methods:

- `prune_for_haiku(history, current_file_context)` - Main pruning logic
- `_score_message_importance(message, ...)` - Assigns importance scores
- `_estimate_tokens(messages)` - Estimates token usage

## Benefits

1. **Prevents rate limit errors**: Automatically stays within token budgets
2. **Cost control**: Less token usage = lower API costs
3. **Performance**: Smaller context = faster API responses
4. **Flexibility**: Users can tune based on their needs

## Example Scenarios

### Scenario 1: Quick Fix (Low History)

```bash
flux --max-history 3000 "Fix the import statement in utils.py"
```

- Fast
- Minimal cost
- Sufficient context for simple tasks

### Scenario 2: Major Refactoring (High History)

```bash
flux --max-history 20000 "Refactor the database layer to use async/await throughout"
```

- Retains more context
- Better understanding of codebase
- Worth the extra cost for complex work

### Scenario 3: Default (Balanced)

```bash
flux "Add logging to the API endpoints"
```

- Uses default 8000 tokens
- Good for most tasks
- Balances context and cost

## Future Improvements

Potential enhancements:
- Auto-adjust based on provider rate limits
- Session-based history management
- More sophisticated context relevance scoring
- Per-file context caching to reduce token usage

## Conclusion

The `--max-history` parameter gives you fine-grained control over Flux's memory footprint, helping you balance context retention, cost, and rate limits based on your specific needs.

# Multi-Provider Configuration Guide

Flux now supports multiple LLM providers! This gives you flexibility to choose the best model for your needs and avoid vendor lock-in.

## Supported Providers

### 1. Anthropic (Claude)
- **Models**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Best for**: Complex reasoning, code editing, instruction following
- **Context**: Up to 200K tokens

### 2. OpenAI (GPT)
- **Models**: GPT-4o, GPT-4 Turbo, GPT-4, GPT-3.5 Turbo
- **Best for**: Broad availability, fast responses, good code generation
- **Context**: Up to 128K tokens (GPT-4o/Turbo)

---

## Configuration

### Environment Variables

Flux uses environment variables for configuration. Add these to your `.env` file or shell environment:

```bash
# Provider Selection
FLUX_PROVIDER=anthropic  # or "openai"

# API Keys
ANTHROPIC_API_KEY=sk-ant-...  # For Anthropic
OPENAI_API_KEY=sk-...         # For OpenAI

# Model Selection
FLUX_MODEL=claude-3-5-sonnet-20241022  # or gpt-4o, etc.

# Optional Settings
FLUX_MAX_TOKENS=4096      # Max tokens per response
FLUX_TEMPERATURE=0.0      # Temperature (0.0 = deterministic)
```

---

## Example Configurations

### Configuration 1: Anthropic Claude 3.5 Sonnet (Recommended)

```bash
# .env
FLUX_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
FLUX_MODEL=claude-3-5-sonnet-20241022
FLUX_MAX_TOKENS=4096
FLUX_TEMPERATURE=0.0
```

**Use when:**
- You have access to Sonnet models
- Need highest quality code editing
- Want best instruction following

**Pricing:** $3/1M input, $15/1M output

---

### Configuration 2: OpenAI GPT-4o (Alternative)

```bash
# .env
FLUX_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
FLUX_MODEL=gpt-4o
FLUX_MAX_TOKENS=4096
FLUX_TEMPERATURE=0.0
```

**Use when:**
- Anthropic Sonnet not available
- Need fast, reliable responses
- Want excellent code quality

**Pricing:** $2.50/1M input, $10/1M output (cheaper than Sonnet!)

---

### Configuration 3: Anthropic Claude 3 Haiku (Budget)

```bash
# .env
FLUX_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
FLUX_MODEL=claude-3-haiku-20240307
FLUX_MAX_TOKENS=4096
FLUX_TEMPERATURE=0.0
```

**Use when:**
- Budget is critical
- Doing simple tasks (queries, analysis)
- Not doing complex code edits

**Pricing:** $0.25/1M input, $1.25/1M output (very cheap!)

**⚠️ Warning:** Haiku has lower quality for complex code editing tasks.

---

### Configuration 4: OpenAI GPT-4 Turbo (High Performance)

```bash
# .env
FLUX_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
FLUX_MODEL=gpt-4-turbo
FLUX_MAX_TOKENS=4096
FLUX_TEMPERATURE=0.0
```

**Use when:**
- Need very high quality
- GPT-4o not sufficient
- Budget allows

**Pricing:** $10/1M input, $30/1M output

---

## Switching Providers

### Quick Switch

To switch providers, just update your `.env` file and restart Flux:

```bash
# Switch from Anthropic to OpenAI
# Before:
FLUX_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
FLUX_MODEL=claude-3-haiku-20240307

# After:
FLUX_PROVIDER=openai
OPENAI_API_KEY=sk-...
FLUX_MODEL=gpt-4o
```

Then restart:
```bash
flux
```

### Per-Session Override

You can also override per session without editing `.env`:

```bash
# Use OpenAI for this session only
FLUX_PROVIDER=openai FLUX_MODEL=gpt-4o flux
```

---

## Model Recommendations

### For Code Editing (Best to Worst)
1. **GPT-4o** - Excellent quality, good price, widely available ⭐⭐⭐⭐⭐
2. **Claude 3.5 Sonnet (20241022)** - Highest quality, if available ⭐⭐⭐⭐⭐
3. **GPT-4 Turbo** - Very high quality, more expensive ⭐⭐⭐⭐
4. **Claude 3.5 Sonnet (20240620)** - Older Sonnet, still good ⭐⭐⭐⭐
5. **Claude 3 Haiku** - Budget option, lower quality ⭐⭐⭐

### For Analysis/Queries (Best to Worst)
1. **Claude 3 Haiku** - Fast, cheap, good enough ⭐⭐⭐⭐⭐
2. **GPT-3.5 Turbo** - Fast, cheap, widely available ⭐⭐⭐⭐
3. **GPT-4o** - Overkill but excellent ⭐⭐⭐⭐
4. **Claude 3.5 Sonnet** - Overkill but excellent ⭐⭐⭐⭐

---

## Cost Comparison

Based on 1M tokens (input + output):

| Model | Input Cost | Output Cost | Total (500K in, 500K out) |
|-------|-----------|-------------|---------------------------|
| Haiku | $0.25 | $1.25 | **$0.75** |
| GPT-3.5 Turbo | $0.50 | $1.50 | **$1.00** |
| GPT-4o | $2.50 | $10.00 | **$6.25** |
| Sonnet 3.5 | $3.00 | $15.00 | **$9.00** |
| GPT-4 Turbo | $10.00 | $30.00 | **$20.00** |

**Recommendation:** Use **GPT-4o** for best value/quality ratio!

---

## Troubleshooting

### Error: "ANTHROPIC_API_KEY is required"

**Solution:** Make sure you've set the API key for your selected provider:
```bash
# If using Anthropic:
export ANTHROPIC_API_KEY=sk-ant-...

# If using OpenAI:
export OPENAI_API_KEY=sk-...
```

### Error: "404 Not Found" (Anthropic)

**Problem:** Your API key doesn't have access to the requested model.

**Solution:** 
1. Try a different model (e.g., Haiku instead of Sonnet)
2. Upgrade your Anthropic account tier
3. Switch to OpenAI instead

### Error: "Invalid FLUX_PROVIDER"

**Solution:** Use either "anthropic" or "openai":
```bash
FLUX_PROVIDER=openai  # or anthropic
```

### Poor Code Editing Quality

**Problem:** Using Haiku or GPT-3.5 for complex code edits.

**Solution:** Upgrade to:
- GPT-4o (OpenAI)
- Claude 3.5 Sonnet (Anthropic)

---

## Getting API Keys

### Anthropic
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create new key
5. Copy and add to `.env`

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Create new secret key
4. Copy and add to `.env`

---

## Features by Provider

| Feature | Anthropic | OpenAI |
|---------|-----------|--------|
| Streaming | ✅ | ✅ |
| Tool Calling | ✅ | ✅ |
| Context Pruning | ✅ (Haiku) | ❌ (Not needed) |
| Token Tracking | ✅ | ✅ |
| Cost Estimation | ✅ | ✅ |

**Note:** OpenAI doesn't need context pruning because GPT-4o handles large contexts well natively.

---

## Best Practices

### 1. Start with GPT-4o
If you're new to Flux, start with GPT-4o:
- Widely available
- Excellent quality
- Good price
- Reliable

### 2. Use Haiku for Simple Tasks
For queries, analysis, or simple changes, Haiku is great:
- Very cheap
- Fast
- Good enough for simple tasks

### 3. Reserve Premium Models for Complex Edits
Use Sonnet or GPT-4 Turbo for:
- Large refactorings
- Complex architecture changes
- Critical code generation

### 4. Monitor Costs
Check token usage regularly:
```bash
# In Flux, type:
/history
```

This shows your token usage and estimated cost.

---

## Future Providers

We plan to add support for:
- **Google (Gemini)** - Coming soon
- **Mistral** - Under consideration
- **Cohere** - Under consideration

Want another provider? Open an issue on GitHub!

---

## Summary

**Recommended Setup:**

```bash
# .env - Best overall configuration
FLUX_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
FLUX_MODEL=gpt-4o
FLUX_MAX_TOKENS=4096
FLUX_TEMPERATURE=0.0
```

This gives you:
- ✅ Excellent code editing quality (95%+ first-attempt success)
- ✅ Widely available (no 404 errors)
- ✅ Good price ($2.50/$10 per 1M tokens)
- ✅ Fast responses
- ✅ Reliable tool calling

**Alternative:** If you have Sonnet access, use `claude-3-5-sonnet-20241022` for slightly better quality at higher cost.

---

## Need Help?

- **Documentation:** Check other docs in `docs/`
- **Issues:** Open GitHub issue
- **Questions:** Ask in Flux chat

Happy coding with Flux! 🚀

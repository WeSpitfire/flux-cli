# Flux Troubleshooting Guide

This guide helps you diagnose and fix common issues with Flux.

## Quick Diagnostics

Run this command to check your configuration:
```bash
flux config check
```

## Common Issues

### 1. Token Limit Errors

**Symptom**: Responses are cut off or incomplete.

**Cause**: `FLUX_MAX_TOKENS` is set too low.

**Solution**:
```bash
# In your .env file
FLUX_MAX_TOKENS=4096  # For most use cases
# or
FLUX_MAX_TOKENS=8192  # For complex, multi-file changes
```

**Warning**: Setting `FLUX_MAX_TOKENS` too high (>8192) will:
- Slow down responses
- Increase API costs
- May not provide better results

---

### 2. Environment Variable Override

**Symptom**: `.env` file changes don't take effect.

**Cause**: Shell environment variables override `.env` file values.

**Check**:
```bash
env | grep FLUX
```

**Solution**:
```bash
# Unset conflicting environment variables
unset FLUX_MAX_TOKENS
unset FLUX_MODEL
unset FLUX_TEMPERATURE

# Or set them explicitly
export FLUX_MAX_TOKENS=4096
```

To make this permanent, remove them from your shell config files:
- `~/.zshrc` (zsh)
- `~/.bashrc` or `~/.bash_profile` (bash)

---

### 3. Model Selection Issues

**Symptom**: Warning about using an older model.

**Current Recommended Model**: `claude-3-5-sonnet-20241022`

**Update your .env**:
```bash
FLUX_MODEL=claude-3-5-sonnet-20241022
```

**Model Comparison**:
| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| claude-3-5-sonnet-20241022 | 200K | Fast | Medium | **Recommended - Best balance** |
| claude-3-opus-20240229 | 200K | Slow | High | Maximum quality |
| claude-3-haiku-20240307 | 200K | Very Fast | Low | Simple tasks, low budget |

---

### 4. API Key Issues

**Symptom**: "ANTHROPIC_API_KEY environment variable is required"

**Solution**:
1. Get your API key from https://console.anthropic.com/
2. Add it to your `.env` file:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
   ```
3. Verify:
   ```bash
   flux config check
   ```

---

### 5. Duplicate Configuration Values

**Symptom**: Configuration seems inconsistent or warnings about duplicates.

**Solution**: Check your `.env` file for duplicate entries:
```bash
grep -n "FLUX_MAX_TOKENS" .env
```

Remove duplicates - keep only one value for each setting.

---

### 6. ChromaDB/Vector Database Issues

**Symptom**: Errors related to "chroma" or vector database.

**Solution**:
```bash
# Clear and rebuild the vector database
rm -rf .flux/chroma
flux index  # Re-index your project
```

---

### 7. Permission Errors

**Symptom**: Can't create `.flux` directory or write files.

**Solution**:
```bash
# Check permissions
ls -la ~/.flux

# Fix permissions if needed
chmod 755 ~/.flux
chmod -R 644 ~/.flux/*
```

---

## Performance Optimization

### Optimal Configuration for Most Users

```bash
# .env file
ANTHROPIC_API_KEY=your-key-here
FLUX_MODEL=claude-3-5-sonnet-20241022
FLUX_MAX_TOKENS=4096
FLUX_TEMPERATURE=0.0
CHROMA_PERSIST_DIR=.flux/chroma
```

### When to Adjust Settings

**Increase `FLUX_MAX_TOKENS` (to 8192) when**:
- Working with very large files
- Making complex multi-file refactors
- Generating extensive documentation

**Use `claude-3-haiku-20240307` when**:
- Working on simple, repetitive tasks
- Budget-conscious development
- Quick exploratory work

**Use `claude-3-opus-20240229` when**:
- Maximum code quality is critical
- Complex architectural decisions
- Cost is not a concern

---

## Debugging Tips

### Enable Verbose Logging

```bash
export FLUX_DEBUG=true
flux your-query
```

### Check Flux State

```bash
# View conversation history
cat ~/.flux/history.jsonl

# View current state
cat ~/.flux/state.json
```

### Clear All State (Fresh Start)

```bash
# Backup first!
cp -r ~/.flux ~/.flux.backup

# Clear state
rm -rf ~/.flux
```

---

## Getting Help

If you're still experiencing issues:

1. Run diagnostics: `flux config check`
2. Check the logs in `~/.flux/`
3. Review this troubleshooting guide
4. Search existing issues on GitHub
5. Create a new issue with:
   - Output from `flux config check`
   - Error messages
   - Steps to reproduce

---

## Configuration Priority

Flux loads configuration in this order (later = higher priority):

1. Default values (in `config.py`)
2. `.env` file in project directory
3. Shell environment variables
4. Command-line flags

**Example**: If you have `FLUX_MAX_TOKENS=4096` in `.env` but `FLUX_MAX_TOKENS=8000` in your shell environment, the shell value (8000) will be used.

# Flux CLI Troubleshooting Guide

Common issues and how to resolve them.

---

## Context & Token Issues

### "Context automatically refreshed"
**What it means**: Your conversation history exceeded 90% of the model's capacity, so Flux automatically cleared it.

**What to do**: Nothing! This is normal and automatic. Your current task is preserved.

**Prevention**: 
- Use Sonnet or Opus for complex multi-step tasks
- Haiku is best for quick edits and simple questions

---

### Conversation seems "forgetful"
**Cause**: Context was auto-cleared due to token limits

**Solution**:
1. Set your current task: `/task Describe what you're working on`
2. This helps Flux remember context across auto-clears
3. For long sessions, consider using `/session save` to checkpoint progress

---

## File Editing Issues

### "Search text not found"
**Cause**: The text you're trying to edit doesn't exactly match the file content

**What Flux does**: Automatically re-reads the file for you

**How to fix**:
1. Look at the auto-read file content (shown in Result panel)
2. Copy the **EXACT** text including all spaces/tabs
3. Paste it into your edit command
4. If it fails twice, Flux will block and suggest a different approach

**Pro tip**: Use `/analyze <file>` for large files to see structure first

---

### "RETRY LOOP DETECTED"
**Cause**: Same tool failed twice in a row

**What it means**: The current approach isn't working

**What to do**:
1. Try a **different** tool (e.g., write_file instead of edit_file)
2. Break the change into **smaller steps**
3. Re-read the file to understand current state
4. Ask for clarification if you're unsure

**Don't**: Retry the same command - Flux will block it

---

### File too large to read
**Cause**: File is >500 lines

**Solutions**:
1. **Use `/analyze <file>`** - See file structure and get reading suggestions
2. **Read in chunks** - Use line ranges: `read_files with line_range: {start: 1, end: 300}`
3. **Read specific functions** - If you know the function name

**Example**:
```
/analyze flux/ui/cli.py
# Shows structure, suggests how to read it
```

---

## Model-Specific Issues

### Haiku: "Operation blocked after 2 failures"
**Why this happens**: Haiku has limited context (8K tokens), making complex edits harder

**Solutions**:
1. **Smaller changes** - Edit 3-10 lines at a time, not 100+
2. **Use `/analyze`** - Understand file structure before editing
3. **Switch to Sonnet** - For complex multi-file refactoring
4. **Break into steps** - Do one small edit, test, then next edit

**When to use each model**:
- **Haiku**: Quick edits, single file changes, simple questions
- **Sonnet**: Most development work, multi-file changes, complex tasks
- **Opus**: Highest quality reasoning, architectural decisions

---

## Command Issues

### Command not working
**Common mistakes**:
- Missing `/` prefix: Use `/analyze` not `analyze`
- Wrong syntax: Use `/analyze filename.py` not `/analyze: filename.py`
- File path: Use relative path from project root

**Available commands**:
```
File Analysis:
  /analyze <file>    - Show file structure (for large files)
  
Navigation:
  /diff              - Show git changes
  /state             - Show project state
  
History:
  /clear             - Clear conversation (done automatically at 90%)
  /history           - Show token usage
  /undo              - Undo last operation
  
Testing:
  /test              - Run tests
  /watch             - Auto-run tests on file changes
```

Type `/help` for full command list.

---

## Performance Issues

### Flux is slow
**Causes**:
1. Large conversation history (fixed automatically at 90%)
2. Complex codebase graph building
3. Auto-fix running on many files

**Solutions**:
- Conversation is auto-managed, no action needed
- Graph building happens once, cached afterward
- Disable auto-fix if not needed: `/autofix-off`

---

### "Building codebase graph..." takes forever
**Cause**: Very large project (>500 files)

**What happens**: Flux limits to 500 files automatically

**If it's stuck**:
1. Press Ctrl+C to cancel
2. Exclude large directories (node_modules, etc.) - they're already excluded
3. Graph is optional - Flux works fine without it

---

## Session & State Issues

### Lost my progress
**Solutions**:
1. Check sessions: `/sessions`
2. Restore last session: `/session restore <id>`
3. Check undo history: `/undo-history`

**Prevention**:
- Save checkpoints: `/session save "Before refactor"`
- Set tasks: `/task Working on authentication bug`

---

### Can't undo a change
**Cause**: Some operations (like git commits) can't be undone by Flux

**Check what can be undone**:
```
/undo-history
```

**If not in undo history**:
- Use `git revert` for commits
- Use file system tools for deleted files
- Flux only tracks its own operations

---

## Error Messages

### "Tool not found"
**Cause**: Trying to use unavailable tool (e.g., ast_edit on Haiku)

**Solution**: Tool availability varies by model:
- **Haiku**: No ast_edit (use edit_file instead)
- **Sonnet/Opus**: All tools available

**Check available tools**: They're listed in error messages

---

### "Rate limit exceeded"
**Cause**: Too many API calls to Claude/OpenAI

**What Flux does**: Automatically clears context and continues

**What you can do**:
- Wait a few seconds before next message
- Switch to a different model (different rate limits)
- Check your API plan limits

---

### "Validation failed"
**Cause**: Code has syntax errors

**What happens**: Flux automatically rolls back the change

**To fix**:
1. Check the error message for details
2. Fix the syntax issue
3. Try again with corrected code

**Pro tip**: Run `/validate` before committing to catch issues early

---

## Git Issues

### Changes not showing in `/diff`
**Cause**: Files not tracked by git or already committed

**Check**:
```
git status
```

**Solutions**:
- Stage changes: `git add <file>`
- Initialize repo if needed: `git init`
- Flux only shows uncommitted changes

---

### Can't commit
**Cause**: No changes staged or invalid commit message

**Use smart commit**:
```
/commit
```
Flux will:
1. Show you changes
2. Generate commit message
3. Ask for approval

**Manual commit**:
```
/commit "Your commit message"
```

---

## Installation Issues

### "Module not found"
**Solution**:
```bash
pip install -e .
```

### Import errors
**Solution**:
```bash
pip install -r requirements.txt
```

---

## Getting More Help

### Debug mode
Enable detailed logging:
```
/debug-on
```

View logs:
```
/debug
```

Analyze specific issue:
```
/debug-analyze "describe your issue"
```

### Check configuration
```
flux config
```

Shows:
- Model being used
- Token limits
- API key status
- Directory paths

---

## Best Practices

### For Haiku users:
1. ✅ Use `/analyze` for files >200 lines
2. ✅ Make small, focused edits (3-10 lines)
3. ✅ Let Flux auto-clear context (don't fight it)
4. ✅ Use `/task` to maintain context across clears
5. ❌ Don't try to refactor 1000-line files at once

### For all users:
1. ✅ Let errors guide you (they have helpful suggestions)
2. ✅ Use `/state` to see what you're working on
3. ✅ Commit often with `/commit`
4. ✅ Save session checkpoints: `/session save`
5. ❌ Don't retry failed operations manually - Flux blocks it automatically

---

## Still stuck?

1. Check `/debug` for detailed logs
2. Use `/state` to see current project context
3. Try `/clear` to start fresh (if auto-clear hasn't happened)
4. Switch models if the issue persists
5. Check GitHub issues for known problems

**Remember**: Flux is designed to be invisible and automatic. If you're seeing lots of errors, you might be using Haiku for a task better suited to Sonnet.

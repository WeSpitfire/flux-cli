# Flux Command Reference

Quick reference for all available commands.

---

## Essential Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/clear` | Clear conversation history | `/clear` |
| `/diff` | Show git changes | `/diff` |
| `/commit` | Commit changes | `/commit "Add feature"` |
| `/undo` | Undo last operation | `/undo` |
| `/help` | Show help | `/help` |

---

## File Analysis

| Command | Description | Example |
|---------|-------------|---------|
| `/analyze <file>` | Show file structure for large files | `/analyze flux/ui/cli.py` |
| `/related <file>` | Find related files | `/related auth.py` |
| `/preview <file>` | Preview file impact | `/preview config.py` |

**Pro tip**: Use `/analyze` for files >500 lines before editing.

---

## Navigation & Info

| Command | Description | Example |
|---------|-------------|---------|
| `/state` | Show project state | `/state` |
| `/history` | Show conversation history | `/history` |
| `/stats` | Show project statistics | `/stats` |
| `/architecture` | Show detected architecture | `/architecture` |
| `/metrics` | Show tool reliability metrics | `/metrics` |

---

## Testing

| Command | Description | Example |
|---------|-------------|---------|
| `/test` | Run tests | `/test` |
| `/watch` | Auto-run tests on changes | `/watch` |
| `/watch-stop` | Stop test watching | `/watch-stop` |
| `/validate` | Validate modified files | `/validate` |

---

## Session Management

| Command | Description | Example |
|---------|-------------|---------|
| `/session save <name>` | Save current session | `/session save "Before refactor"` |
| `/session restore <id>` | Restore session | `/session restore abc123` |
| `/session end` | End current session | `/session end` |
| `/sessions` | List all sessions | `/sessions` |

---

## Task Management

| Command | Description | Example |
|---------|-------------|---------|
| `/task <description>` | Set current task | `/task Fix authentication bug` |
| `/newtask <title>` | Create new task | `/newtask Add OAuth support` |
| `/tasks` | List all tasks | `/tasks` |
| `/summary` | Show work summary | `/summary` |

---

## Workflow & Memory

| Command | Description | Example |
|---------|-------------|---------|
| `/workflow` | Show workflow status | `/workflow` |
| `/project` | Show project files | `/project` |
| `/approval` | Show approval stats | `/approval` |
| `/undo-history` | Show undo history | `/undo-history` |

---

## Auto-Fix

| Command | Description | Example |
|---------|-------------|---------|
| `/autofix` | Run auto-fix on project | `/autofix` |
| `/autofix-on` | Enable auto-fix | `/autofix-on` |
| `/autofix-off` | Disable auto-fix | `/autofix-off` |
| `/autofix-undo` | Undo last auto-fix | `/autofix-undo` |
| `/autofix-summary` | Show auto-fix summary | `/autofix-summary` |

---

## Debug & Performance

| Command | Description | Example |
|---------|-------------|---------|
| `/debug` | Show debug info | `/debug` |
| `/debug-on` | Enable debug logging | `/debug-on` |
| `/debug-off` | Disable debug logging | `/debug-off` |
| `/debug-analyze <issue>` | Analyze specific issue | `/debug-analyze "slow response"` |
| `/performance` | Show performance metrics | `/performance` |
| `/perf` | Alias for /performance | `/perf` |

---

## Codebase Intelligence

| Command | Description | Example |
|---------|-------------|---------|
| `/index` | Build codebase graph | `/index` |
| `/suggest` | Show proactive suggestions | `/suggest` |

---

## Special Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/fix` | Auto-fix last error | `/fix` |
| `/inspect` | Show conversation state | `/inspect` |

---

## Natural Language Alternatives

Flux understands natural language! You can use these instead of slash commands:

| Natural Language | Equivalent Command |
|-----------------|-------------------|
| "show me what changed" | `/diff` |
| "undo that" | `/undo` |
| "run the tests" | `/test` |
| "what's the current state" | `/state` |
| "show memory" | `/history` |
| "commit the changes" | `/commit` |

---

## Tips & Tricks

### 1. Context Management (Automatic)
Flux auto-clears context at 90%. You'll see:
```
✨ Context automatically refreshed (15,243 → 0 tokens)
```
**No action needed** - just continue working!

### 2. Large Files
Before editing large files:
```
/analyze flux/ui/cli.py
```
This shows structure and suggests how to read it.

### 3. Multi-Step Tasks
Set a task to maintain context:
```
/task Refactor authentication system
```
Flux remembers this across auto-clears.

### 4. Save Checkpoints
Before major changes:
```
/session save "Before authentication refactor"
```
Can restore if something goes wrong.

### 5. Check Tool Reliability
See which tools work best:
```
/metrics
```

### 6. Quick Fixes
For last error:
```
/fix
```
Flux auto-analyzes and suggests fixes.

---

## Command Patterns

### Editing Workflow
```
1. /analyze large_file.py          # Understand structure
2. Edit the file (via natural language)
3. /validate                        # Check syntax
4. /test                           # Run tests
5. /commit "Description"           # Commit if passing
```

### Debugging Workflow
```
1. /state                          # See what's changed
2. /diff                           # Review changes
3. /fix                            # Auto-fix if error
4. /debug-on                       # Enable detailed logs
5. [Make changes]
6. /debug-off                      # Disable when done
```

### Refactoring Workflow
```
1. /session save "Before refactor"
2. /task Refactor XYZ
3. /related file.py                # Find affected files
4. [Make changes]
5. /validate                       # Check all files
6. /test                           # Run test suite
7. /commit                         # Commit if passing
```

---

## Model-Specific Tips

### Haiku Users
- Use `/analyze` frequently (limited context)
- Let auto-clear happen (it's normal)
- Use `/task` to maintain context
- Keep changes small

### Sonnet/Opus Users
- Batch related changes together
- Use full conversational context
- Less need for `/analyze`
- Can handle complex multi-file refactoring

---

## Keyboard Shortcuts

(In interactive mode)

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel current operation |
| `Ctrl+D` | Exit Flux |
| `↑` | Previous command |
| `↓` | Next command |

---

## Getting Help

### Within Flux
```
/help              # General help
/debug             # Debug current issue
/state             # See current context
```

### External Resources
- **TROUBLESHOOTING.md** - Common issues and solutions
- **MODEL_GUIDE.md** - Choose the right model
- **README.md** - Setup and configuration

---

## Quick Start Examples

### First Time User
```bash
flux
> /help
> What files are in this project?
> /analyze src/main.py
> Fix the bug in main.py line 42
```

### Daily Development
```bash
flux
> /state
> Add error handling to the authentication function
> /test
> /commit "Add error handling"
```

### Code Review
```bash
flux
> /diff
> Review these changes for issues
> /validate
> /commit
```

---

## Command Cheat Sheet

**Most Used:**
- `/clear` - Reset context
- `/diff` - See changes
- `/commit` - Save work
- `/analyze` - Understand large files
- `/test` - Run tests

**Pro Commands:**
- `/metrics` - Tool reliability
- `/session save` - Checkpoint
- `/debug-on` - Detailed logs
- `/fix` - Auto-fix errors
- `/validate` - Check syntax

**Remember**: You don't need to memorize these. Flux understands natural language, so just describe what you want!

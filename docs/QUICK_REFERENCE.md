# Flux CLI - Quick Reference Card

**Your intelligent AI development companion that remembers everything** 🧠⚡

---

## 🚀 Getting Started

```bash
cd /path/to/your/project
source /path/to/flux-cli/venv/bin/activate
python -m flux.main
```

Or if installed globally:
```bash
flux
```

---

## 💬 Basic Usage

### Interactive Mode
```bash
flux
You: what files are in src/?
You: add error handling to api.py
You: /task Building authentication system
```

### Single Query
```bash
flux "find all TODO comments"
flux "add tests for the login function"
```

---

## 🎮 Core Commands

### Session & Memory
| Command | Purpose | Example |
|---------|---------|---------|
| `/task <desc>` | Set what you're working on | `/task Adding JWT auth` |
| `/memory` | View project memory | `/memory` |
| `/checkpoint <msg>` | Save a milestone | `/checkpoint Login complete` |
| `/session` | View current session summary | `/session` |

### Workflows
| Command | Purpose | Example |
|---------|---------|---------|
| `/workflow <name>` | Run a defined workflow | `/workflow deploy-staging` |
| `/workflows` | List available workflows | `/workflows` |

### Monitoring
| Command | Purpose | Example |
|---------|---------|---------|
| `/watch tests` | Start test monitoring | `/watch tests` |
| `/watch lint` | Start lint monitoring | `/watch lint` |
| `/watch stop` | Stop all monitors | `/watch stop` |
| `/status` | View monitor status | `/status` |

### Tools & Help
| Command | Purpose | Example |
|---------|---------|---------|
| `/help` | Show command help | `/help` |
| `/tools` | List available tools | `/tools` |
| `/undo` | Undo last operation | `/undo` |
| `/clear` | Clear conversation | `/clear` |

---

## 🛠️ What Flux Can Do

### Code Operations
- ✅ Add/remove/modify functions (AST-aware!)
- ✅ Read and analyze files
- ✅ Search code patterns
- ✅ Run shell commands
- ✅ Create new files
- ✅ Show diffs before applying
- ✅ Multi-file refactoring
- ✅ Auto-fix formatting

### Intelligence
- ✅ Detect project type automatically
- ✅ Remember everything across sessions
- ✅ Track recent files and changes
- ✅ Understand project structure
- ✅ AI orchestration of multi-step tasks
- ✅ Natural language commands

### Monitoring (NEW!)
- ✅ Proactive test monitoring
- ✅ Build failure detection
- ✅ Lint issue tracking
- ✅ File change tracking
- ✅ Git status monitoring

### Workflows (NEW!)
- ✅ One-command deployments
- ✅ Custom workflow definitions
- ✅ Built-in workflow templates
- ✅ Conditional step execution
- ✅ Parallel step processing

---

## 🌟 Key Features

### Session Persistence (⭐ NEW)
```
$ flux
📂 Resuming session from 2 hours ago
🎯 Last task: Debugging login authentication
📝 Working on: auth.py, login_tests.py
❌ Tests: 3 failing
```

### Proactive Monitoring (⭐ NEW)
```
(You edit auth.py)

============================================================
❌ Tests are now failing!
============================================================

🤖 AI Analysis:
Missing import detected. The validate_token function
was moved but the import wasn't updated.
```

### One-Command Workflows (⭐ NEW)
```
You: /workflow pr-ready
Flux: ✓ Format → ✓ Lint → ✓ Tests → ✓ Commit
      ✓ Ready for PR!
```

### AI Orchestration (⭐ NEW)
```
You: "run the tests"
Flux: [automatically plans and executes]
      ✓ Running pytest...
      ✓ 15 tests passed
```

### AST-Aware Editing
```
You: add a validate_email function to utils.py
Flux: [uses AST to add safely, never breaks code]
```

### Diff Previews
```
Shows exactly what will change before applying
Color-coded: red = removed, green = added
```

---

## 💡 Pro Tips

### Let Flux Use Memory
```
❌ "check the login function in auth.py"
✅ "check the login function"
   (Flux knows auth.py is recent)
```

### Set Tasks for Context
```
/task Refactoring database layer
(Now Flux understands the bigger picture)
```

### Use Checkpoints
```
/checkpoint Completed user authentication
(Marks important milestones)
```

### Trust AST Editing
```
AST editing is safer than text editing
Let Flux use it for Python/JS/TS files
```

---

## 📊 Cost Tracking

Every query shows:
```
Tokens: 4,331 in / 219 out (total: 4,550) | Cost: $0.0014
```

Typical costs (Claude Haiku):
- Simple query: $0.001-0.003
- File edit: $0.002-0.005
- Full session: $0.01-0.05

---

## 🔧 Troubleshooting

### "API key not found"
```bash
# Check .env file has:
ANTHROPIC_API_KEY=sk-ant-...
```

### "Import errors"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Memory not loading"
```bash
# Check memory directory:
ls -la ~/.flux/memory/
```

### "Tool execution fails"
- Verify you're in the right directory
- Check file paths are correct
- Ensure you have necessary permissions

---

## 📁 File Locations

- **Config:** `~/.flux/`
- **Memory:** `~/.flux/memory/<project>.json`
- **Environment:** `flux-cli/.env`
- **Docs:** `flux-cli/*.md`

---

## 🎯 Common Use Cases

### "What am I working on?"
```
You: what was I working on?
Flux: [checks memory, tells you]
```

### "Continue from yesterday"
```
You: continue where we left off
Flux: [loads context automatically]
```

### "Add a new feature"
```
You: add JWT authentication to the API
Flux: [reads files, adds functions, shows diffs]
```

### "Fix a bug"
```
You: fix the login bug
Flux: [checks recent files, finds bug, fixes it]
```

### "Understand code"
```
You: explain how authentication works
Flux: [searches, reads, explains]
```

---

## 🚦 Do's and Don'ts

### ✅ Do
- Set tasks with `/task` for big features
- Trust the AST editor for code
- Check `/memory` when resuming work
- Let Flux track files automatically
- Use checkpoints for milestones

### ❌ Don't
- Specify file names Flux already knows
- Worry about indentation (AST handles it)
- Re-explain context (memory does it)
- Be afraid of diffs (they keep you safe)
- Forget to check token costs

---

## 💪 Flux Advantages

### vs. GitHub Copilot
- ✅ AST-aware editing
- ✅ Persistent memory
- ✅ Full context control

### vs. Cursor
- ✅ Better code safety
- ✅ Cross-session memory
- ✅ Lower cost

### vs. Warp
- ✅ You own it
- ✅ More features
- ✅ Open source

---

## 📚 Learn More

### Getting Started
- **QUICKSTART.md** - 5-minute setup guide
- **USER_GUIDE.md** - Complete user manual
- **TROUBLESHOOTING.md** - Common issues

### Features
- **architecture/TOP_3_FEATURES.md** - Session, Monitoring, Workflows
- **guides/AUTO_FIX_MODE.md** - Auto-fix guide
- **guides/WORKFLOW_ENFORCEMENT.md** - Custom workflows

### Architecture
- **architecture/AST_EDITING.md** - AST system
- **architecture/MEMORY_SYSTEM.md** - Memory system
- **architecture/DESKTOP_APP.md** - Desktop app

---

## 🎉 Remember

**Flux is your intelligent development companion that:**
- 🧠 Remembers everything across sessions
- 🔔 Alerts you proactively when things break
- ⚡ Orchestrates complex workflows automatically
- 🛡️ Never breaks your code structure
- 💸 Costs pennies, not dollars
- 👊 Is completely yours

**Stop manually juggling tools—let Flux orchestrate your workflow!** 🚀

---

*Quick Reference v2.0 - November 2024*

# Project Brief System - Never Forget Again

## 🎯 Problem Solved

**Before**: Flux would "forget" critical context like:
- Your project constraints ("Never use AWS")
- Coding conventions ("Always use TypeScript strict mode")
- Tech stack and architecture decisions
- Current task and progress

After 20-30 messages, these would drop off the context window, forcing you to repeat yourself.

**Now**: ProjectBrief system ensures **critical information is ALWAYS in every prompt**, never forgotten, even after 100+ messages or terminal restarts.

---

## ✨ Features

### 1. **Persistent Structured State**
- Automatically saved to `~/.flux/projects/{project_name}/brief.json`
- Survives terminal restarts, crashes, and context clears
- Auto-detects project info from package.json, README, etc.

### 2. **Always in Prompt**
- Brief is **prepended to every single LLM call**
- High priority formatting (appears at top of system prompt)
- Never gets pruned or dropped, even with long conversations

### 3. **Critical Constraints**
- Add constraints that must NEVER be violated
- Examples:
  - "Never use Amazon products"
  - "All photos must be stored in our database"
  - "Use Resend for email, Digital Ocean for hosting"

### 4. **Coding Style Guidelines**
- Persistent coding conventions
- Examples:
  - "Use TypeScript strict mode"
  - "Follow airbnb style guide"
  - "Always write tests for new features"

### 5. **Project Context**
- Tech stack (languages, frameworks, database)
- Key directories and their purposes
- Architecture notes
- Current task tracking

---

## 📝 Usage

### View Current Brief
```
/brief
```
Shows the current project brief with all constraints, style, and context.

### Add Constraints (CRITICAL)
```
/brief-constraint Never use Amazon products
/brief-constraint All user photos must be stored in our database
/brief-constraint Use Resend for all email sending
```

These will **NEVER** be forgotten - they're in every single prompt.

### Add Coding Style
```
/brief-style Use TypeScript strict mode
/brief-style Follow airbnb eslint config
/brief-style Write tests for all new features
```

### Add Tech Stack Info
```
/brief-add language TypeScript
/brief-add framework Next.js
/brief-add database PostgreSQL
```

### Set Description
```
/brief-add description "Photo sharing app focused on user privacy"
```

### Edit Manually
```
/brief-edit
```
Opens the brief JSON file in your default editor for bulk editing.

---

## 🔄 Automatic Features

### 1. **Auto-Detection**
On first run in a project, Flux automatically detects:
- Project name (from directory or package.json)
- Languages and frameworks (from package.json, pyproject.toml, etc.)
- Project type (web_app, cli_tool, library, etc.)
- Key directories (src/, tests/, docs/)

### 2. **Auto-Save**
Brief is automatically saved after:
- Every query (in case terminal crashes)
- Any brief modification command
- Task completion

### 3. **Cross-Session Persistence**
Brief is loaded on startup:
- Same brief across terminal sessions
- Context survives restarts
- No need to re-explain constraints

---

## 📊 Brief Structure

The brief JSON has the following structure:

```json
{
  "project_name": "my-app",
  "project_type": "web_app",
  "description": "Photo sharing app",
  
  "languages": ["TypeScript"],
  "frameworks": ["Next.js", "React"],
  "database": "PostgreSQL",
  
  "constraints": [
    "Never use Amazon products",
    "Store photos in our database"
  ],
  
  "coding_style": [
    "Use TypeScript strict mode",
    "Follow airbnb style guide"
  ],
  
  "key_directories": {
    "src/": "main source code",
    "tests/": "test files"
  },
  
  "architecture_notes": [
    "Using Clean Architecture pattern"
  ],
  
  "current_task": "Implement photo upload",
  "completed_tasks": [
    "Set up project structure",
    "Create user authentication"
  ],
  "pending_issues": [
    "Photo upload needs compression"
  ],
  
  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T14:30:00"
}
```

---

## 🎨 What Shows Up in AI Prompt

Every single LLM call includes this at the top:

```
============================================================
PROJECT BRIEF (READ FIRST - ALWAYS FOLLOW)
============================================================
Project: my-app
Type: web_app
Description: Photo sharing app focused on user privacy

TECH STACK:
  Languages: TypeScript
  Frameworks: Next.js, React
  Database: PostgreSQL

CRITICAL CONSTRAINTS (NEVER VIOLATE):
  ❌ Never use Amazon products
  ❌ Store all user photos in our database
  ❌ Use Resend for email sending

CODING STYLE (ALWAYS FOLLOW):
  ✓ Use TypeScript strict mode
  ✓ Follow airbnb eslint config
  ✓ Write tests for all new features

KEY DIRECTORIES:
  src/: main source code
  tests/: test files

CURRENT TASK: Implement photo upload with compression

COMPLETED:
  ✓ Set up project structure
  ✓ Create user authentication

PENDING ISSUES:
  ⚠ Photo upload needs compression optimization
============================================================
```

This appears in **EVERY SINGLE PROMPT**, ensuring the AI never forgets.

---

## 🔧 Implementation Details

### Files Created
1. **`flux/core/project_brief.py`** (349 lines)
   - `ProjectBrief` dataclass with all fields
   - `to_prompt()` - converts to AI prompt format
   - `save()` / `load()` - JSON persistence
   - `auto_detect()` - detect from project files
   - Helper methods: `add_constraint()`, `add_coding_style()`, etc.

2. **Modified: `flux/core/conversation_manager.py`**
   - Import ProjectBrief
   - Initialize brief in `__init__`
   - Inject brief into `_build_system_prompt()` (line 542)
   - Auto-save after each query
   - `_load_or_create_project_brief()` method
   - `save_project_brief()` method

3. **Modified: `flux/ui/command_router.py`**
   - Added 5 new commands: `/brief`, `/brief-add`, `/brief-constraint`, `/brief-style`, `/brief-edit`
   - Registered in command router
   - Added to `/help` output

### Storage Location
- `~/.flux/projects/{project_name}/brief.json`
- One brief per project
- Separate from conversation history

### Integration Point
In `conversation_manager.py`, line 542:
```python
# === PROJECT BRIEF (ALWAYS INCLUDED - NEVER FORGOTTEN) ===
brief_prompt = self.project_brief.to_prompt()
if brief_prompt:
    prompt += "\n\n" + brief_prompt
```

This runs on **every LLM call**, ensuring the brief is always present.

---

## 📈 Impact

### Token Efficiency
- Brief is ~500-1000 tokens (small)
- Much smaller than re-explaining constraints in chat
- Only shows non-empty sections (smart formatting)

### Memory Retention
- **Before**: Forgot constraints after ~20 messages
- **After**: Never forgets, even after 100+ messages

### User Experience
- Set constraints once, never repeat yourself
- Terminal restart? No problem, brief loads automatically
- Context clear? Brief stays intact
- New Flux session? All context preserved

---

## 🚀 Next Steps

### Priority 2: Conversation Summarization (Next)
Instead of dropping old messages, summarize them:
- Keep recent messages (last 10)
- Summarize older chunks (messages 11-50)
- Store summaries in brief or separate file
- Include summaries in prompt

### Priority 3: Persistent Conversation State
Save full conversation across restarts:
- Store in `~/.flux/projects/{name}/conversation.json`
- Load on startup if same project
- Optional: "Continue last conversation" prompt

---

## 🧪 Testing

### Manual Test
```bash
cd your-project/

# First run - auto-detect
flux
/brief  # Should show auto-detected info

# Add constraints
/brief-constraint Never use AWS products

# Long conversation (20+ messages)
# Ask about constraints
> "What are my project constraints?"
# Should remember: "Never use AWS products"

# Restart terminal
flux
/brief  # Should show same brief

# Long conversation again (50+ messages)
# Ask about constraints again
> "What cloud provider should I use?"
# Should say: "Not AWS (constraint), use Digital Ocean"
```

### Expected Behavior
- ✅ Brief persists across restarts
- ✅ Constraints never forgotten
- ✅ Auto-detection works on first run
- ✅ Commands modify brief correctly
- ✅ Brief shows in every prompt

---

## 💡 Use Cases

### 1. **Cloud Provider Constraints**
```
/brief-constraint Never use Amazon AWS
/brief-constraint Use Digital Ocean for deployment
```
Now Flux will never suggest AWS, even after 100 messages.

### 2. **Privacy Requirements**
```
/brief-constraint Store all user photos in our database
/brief-constraint Never send user data to third parties
```

### 3. **Email Service**
```
/brief-constraint Use Resend for all email sending
/brief-add description "Email service provider: Resend"
```

### 4. **Coding Conventions**
```
/brief-style Use TypeScript strict mode
/brief-style No any types allowed
/brief-style All functions must have JSDoc
```

### 5. **Architecture Decisions**
```
/brief-add framework "Next.js with App Router"
/brief-add database "PostgreSQL with Prisma ORM"
/brief-style "Use Clean Architecture pattern"
```

---

## 🎓 Best Practices

### Do's
✅ Add constraints at project start
✅ Use brief for "never do X" rules
✅ Add coding style preferences
✅ Keep constraints concise and clear
✅ Review brief with `/brief` occasionally

### Don'ts
❌ Don't add temporary info (use chat instead)
❌ Don't add file-specific details (brief is project-level)
❌ Don't duplicate info already in code
❌ Don't over-constrain (keep it high-level)

---

## 🔍 Troubleshooting

### Brief not loading?
- Check `~/.flux/projects/{name}/brief.json` exists
- Verify JSON is valid (use `/brief-edit` to fix)
- Try restarting Flux

### Brief not in prompt?
- Check `conversation_manager.py` line 542
- Verify `to_prompt()` returns non-empty string
- Enable debug mode: `/debug-on`

### Auto-detection not working?
- Ensure package.json or similar exists
- Check project has recognizable structure
- Manually add info: `/brief-add language Python`

---

## 📚 Related Features

- **Memory System**: Stores files created/modified (different from brief)
- **State Tracker**: Tracks recent activity (different from brief)
- **Smart Context**: Learns code patterns (different from brief)
- **Time Machine**: Snapshots conversation (includes brief in snapshot)

ProjectBrief is the **foundation** - it's always present, while other features are contextual.

---

## 🎉 Summary

ProjectBrief solves the "AI forgetting" problem by:

1. ✅ **Creating persistent structured state** (brief.json)
2. ✅ **Always including it in prompts** (every LLM call)
3. ✅ **Auto-saving after queries** (survives crashes)
4. ✅ **Providing user commands** (/brief-*)
5. ✅ **Auto-detecting project info** (smart defaults)

**Result**: Flux never forgets your constraints, conventions, or context - even after 100+ messages or terminal restarts.

**Next**: Implement conversation summarization to complete the memory system.

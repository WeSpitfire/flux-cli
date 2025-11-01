# Flux User Guide

## Overview

Flux is an AI-powered development assistant with built-in safety features to ensure code quality and give you full control over changes.

## Key Safety Features

### 1. 🛡️ Workflow Enforcement
Flux follows a disciplined workflow before making any changes:

```
UNDERSTAND → PLAN → VALIDATE → EXECUTE
```

**What this means:**
- Flux must read files before editing them
- Cannot blindly modify code without understanding context
- Searches and analyzes before taking action

**Check workflow status:**
```bash
/workflow
```

### 2. 🔍 Auto-Rollback on Syntax Errors
If Flux accidentally introduces a syntax error, it automatically rolls back the change.

**Supported languages:**
- Python (`.py`)
- JavaScript (`.js`, `.jsx`)
- TypeScript (`.ts`, `.tsx`)

**Example:**
```python
# If Flux writes this (broken):
def foo():
    print("missing paren"

# It immediately detects the error and reverts to previous version
```

### 3. ✅ Interactive Approval
Before any file is modified, Flux shows you a beautiful diff and asks for approval.

**What you see:**
- Syntax-highlighted diffs
- Line-by-line changes (+/-)
- File statistics
- Context about the change

**Example output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Proposed edit_file: test.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭─────────── Changes ───────────╮
│ --- test.py (before)          │
│ +++ test.py (after)           │
│ @@ -1,3 +1,4 @@                │
│  def hello():                  │
│ +    """Say hello"""           │
│      print("Hello")            │
╰───────────────────────────────╯

+1 -0

Context:
  changes: +1 -0
  lines: 3 → 4

Apply these changes? [Y/n]:
```

## Usage

### Interactive Mode

Start Flux in interactive mode:
```bash
python flux/main.py
```

Then chat naturally:
```
You: Add error handling to api.py
Flux: [reads file, shows plan, requests approval]
```

### Single Command Mode

Execute a single command:
```bash
python flux/main.py "Add a docstring to the hello function"
```

### Auto-Approve Mode

Skip approval prompts (useful for batch operations or CI):
```bash
python flux/main.py --yes "Fix all typos"
# or
python flux/main.py -y "Refactor the code"
```

## Commands

### Memory & Context
- `/task <description>` - Set current task
- `/memory` - Show project memory
- `/checkpoint <msg>` - Save a checkpoint
- `/project` - Show files created in this session

### Undo & Recovery
- `/undo` - Undo last file operation
- `/undo-history` - Show undo history

### Workflow & Safety
- `/workflow` - Show current workflow stage
- `/approval` - Show approval statistics

### Help
- `/help` - Show all commands

## Examples

### Example 1: Safe Refactoring

```bash
You: Refactor the getUserData function to use async/await

# Flux workflow:
# 1. UNDERSTAND - Reads the file
# 2. PLAN - "I'll convert the callback pattern to async/await"
# 3. VALIDATE - Checks syntax will be valid
# 4. EXECUTE - Shows diff and asks for approval

Apply these changes? [Y/n]: y
✓ Changes approved
```

### Example 2: Preventing Errors

```bash
You: Remove the closing brace from function

# Flux:
# - Tries to make the change
# - Detects syntax error
# - Automatically rolls back
# - Reports error to you

Error: Syntax error introduced - changes rolled back
Syntax error: SyntaxError at line 5: unexpected EOF
```

### Example 3: Batch Operations

```bash
# Auto-approve all changes
python flux/main.py --yes "Add JSDoc comments to all functions in src/"

# Flux will:
# - Read all files
# - Make changes
# - Show diffs
# - Apply without prompting (because of --yes)
```

## Configuration

### Environment Variables

Set in `.env` file:

```bash
# API Key (required)
ANTHROPIC_API_KEY=your_key_here

# Model selection
FLUX_MODEL=claude-3-5-sonnet-20241022

# Disable approval prompts by default
FLUX_REQUIRE_APPROVAL=false

# Token limits
FLUX_MAX_TOKENS=4096
```

### CLI Flags

```bash
--yes, -y          Auto-approve all changes
--no-approval      Same as --yes
```

## Best Practices

### 1. Review Changes Carefully
Even with auto-rollback, always review the diffs before approving.

### 2. Use Checkpoints
Create checkpoints before major refactoring:
```
/checkpoint "Before refactoring auth system"
```

### 3. Start Small
For complex changes, break them into smaller pieces:
```
You: First, add the new parameter to the function signature
[Review and approve]

You: Now, update all callers to pass the parameter
[Review and approve]
```

### 4. Test After Changes
After Flux makes changes, run your tests:
```
You: Add error handling to api.py
[Approve changes]

You: Run the tests for api.py
```

### 5. Use Auto-Approve Wisely
Only use `--yes` when:
- Changes are low-risk
- You're doing repetitive tasks
- You trust the operation completely

## Troubleshooting

### Approval prompt not showing?
Check if auto-approve is enabled:
```bash
# Disable auto-approve
unset FLUX_REQUIRE_APPROVAL
# or set it to true
export FLUX_REQUIRE_APPROVAL=true
```

### Workflow blocking changes?
Use `/workflow` to see what stage you're in. Flux may need more context:
```
You: Edit the file
Flux: Cannot modify files in UNDERSTAND stage
Suggestions:
  - Read the file first
  - List directory contents
```

### Syntax checker too strict?
The syntax checker only validates Python and JS/TS files. Other files are not checked.

### Changes keep getting rolled back?
Check the syntax error message. The new code may have valid-looking syntax that's actually invalid in context.

## Advanced Features

### Workflow Stages

Monitor Flux's thought process:

```bash
You: /workflow

Stage: understand
Files read: 2
Searches: 1
Plan: ✗
Validations: 0
Modifications: 0
```

### Approval Statistics

Track how many changes you've approved:

```bash
You: /approval

Total requests: 5
Approved: 4
Rejected: 1
Approval rate: 80.0%
```

### Undo Operations

Flux tracks all file operations for easy rollback:

```bash
You: /undo-history

[0] [2024-10-31 10:30] write: Created test.py
[1] [2024-10-31 10:32] edit: Edited api.py
[2] [2024-10-31 10:35] edit: Edited utils.py

You: /undo
✓ Undone: Edited utils.py
```

## Safety Guarantees

Flux provides these safety guarantees:

1. **No Blind Modifications** - Must understand code first
2. **Syntax Validation** - Auto-rollback on syntax errors
3. **User Approval** - You control what gets changed
4. **Undo Support** - All operations can be reversed
5. **Workflow Visibility** - See what Flux is thinking

## Getting Help

- `/help` - Show all commands
- Check `WORKFLOW_ENFORCEMENT.md` for technical details
- Check `IMPROVEMENTS_PROGRESS.md` for feature status

## Summary

Flux is designed to be:
- **Safe** - Multiple layers of protection
- **Transparent** - You see everything it does
- **Controllable** - You approve all changes
- **Recoverable** - Easy to undo mistakes

Use it confidently knowing that your code is protected!

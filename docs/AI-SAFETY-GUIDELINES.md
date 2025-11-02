# AI Agent Safety Guidelines

## Critical: Preventing Data Loss

This document outlines mandatory safety protocols that AI agents MUST follow when operating in Flux to prevent catastrophic data loss.

## 🚨 NEVER Run These Commands Without Explicit User Approval

### Git Operations (CRITICAL)
- ❌ `git checkout <file>` - Discards uncommitted changes permanently
- ❌ `git reset --hard` - Destroys all uncommitted work
- ❌ `git clean -fd` - Deletes untracked files permanently
- ❌ `git reset HEAD~` - Can lose commits if not careful

### File System Operations
- ❌ `rm -rf` - Permanent deletion (except in clearly temporary directories)
- ❌ `mv` - Moving files without backup
- ❌ Overwriting files without checking if they have uncommitted changes

## ✅ ALWAYS Do This Before Destructive Operations

### 1. Check for Uncommitted Work
```bash
# Run safety check script
./scripts/git-safety-check.sh

# Or manually check:
git status
git diff --stat
```

### 2. Show User What Will Be Lost
```bash
# Show number of lines and files affected
echo "Files modified: $(git diff --name-only | wc -l)"
echo "Lines added: $(git diff --numstat | awk '{s+=$1} END {print s}')"
echo "Lines deleted: $(git diff --numstat | awk '{s+=$2} END {print s}')"
```

### 3. Offer Safe Alternatives
- **Stash:** `git stash push -m "description"`
- **Backup commit:** `git add -A && git commit -m "WIP: backup"`
- **Create branch:** `git checkout -b backup-branch`

### 4. Require Explicit Confirmation
```
User: "Are you sure you want to discard X files with Y lines of uncommitted changes?"
AI: Wait for clear "yes" or "confirm" before proceeding
```

## Required Pre-Flight Checks

Before ANY potentially destructive operation, the AI MUST:

1. ✅ Run `git status` to check for uncommitted work
2. ✅ Calculate and display impact (files/lines affected)
3. ✅ Show list of files that will be affected
4. ✅ Ask user for explicit approval with clear warning
5. ✅ Offer to create backup (stash/commit/branch)
6. ✅ Wait for confirmation
7. ✅ Log the operation for audit trail

## Safe Workflow Pattern

```bash
# 1. Check status
if git diff-index --quiet HEAD --; then
    echo "✅ Safe to proceed"
else
    echo "⚠️  Uncommitted changes detected!"
    
    # 2. Show impact
    git diff --stat
    
    # 3. Create backup
    git stash push -m "Auto-backup before operation"
    
    # 4. Proceed
    # ... perform operation ...
    
    # 5. Restore if needed
    git stash pop
fi
```

## Automatic Safety Features to Implement

### 1. Git Hook: Pre-Destructive-Operation
Create `.git/hooks/pre-destructive` that:
- Detects dangerous commands
- Forces interactive confirmation
- Auto-creates stash backup
- Logs all operations

### 2. Automatic Stashing
Before any checkout/reset/clean:
```bash
git stash push -m "Auto-stash $(date +%Y%m%d-%H%M%S)"
```

### 3. Commit History Backup
Periodically backup to a separate branch:
```bash
git branch backup/auto-$(date +%Y%m%d-%H%M%S)
```

### 4. Work-In-Progress Auto-Commits
Every N minutes, auto-commit to WIP branch:
```bash
git checkout -b wip/session-$(date +%Y%m%d)
git add -A
git commit -m "Auto-save: $(date)"
```

## User Confirmation Patterns

### ❌ Bad (What NOT to do)
```
AI: "Let me fix that by checking out the file"
[Runs git checkout without asking]
[3000+ lines of work lost]
```

### ✅ Good (What TO do)
```
AI: "I notice you have uncommitted changes:
     • 5 files modified
     • 3,247 lines added
     
     Would you like me to:
     1. Stash your changes (recommended)
     2. Create a backup commit
     3. Show me what's changed first
     4. Cancel this operation
     
     What would you prefer?"

User: "1"

AI: [Creates stash]
AI: "✅ Changes safely stashed. Proceeding with operation..."
```

## Red Flags - When to STOP

If the AI observes:
- `git status` shows modified files
- `git diff` shows any output
- User mentions "uncommitted work"
- User mentions "haven't committed yet"
- User mentions "working on X"

Then the AI MUST:
1. 🛑 STOP immediately
2. Alert user to uncommitted work
3. Offer backup options
4. Wait for explicit go-ahead

## Recovery Procedures

### If Data Was Already Lost

1. Check for editor backups:
```bash
find . -name "*.swp" -o -name "*~" -o -name ".*.sw?"
```

2. Check git reflog:
```bash
git reflog
git fsck --unreachable
```

3. Check IDE/editor auto-save:
```bash
# VS Code
~/Library/Application Support/Code/Backups/

# Cursor
~/Library/Application Support/Cursor/Backups/
```

4. Check Time Machine (macOS):
```bash
tmutil listbackups
```

5. Apologize profusely and help user recreate work

## Audit Trail

All destructive operations should be logged:
```bash
echo "$(date): git checkout src/main.js - 127 lines discarded" >> ~/.flux/audit.log
```

## Testing Safety Features

Create test scenarios:
1. Simulate uncommitted work (create temp files)
2. Try to run destructive command
3. Verify safety check blocks it
4. Verify backup is created
5. Verify work can be restored

## Principle: Better Safe Than Sorry

**When in doubt, ALWAYS:**
- ❌ DON'T proceed
- ✅ DO ask the user
- ✅ DO create a backup
- ✅ DO show what will be affected
- ✅ DO wait for confirmation

## The Golden Rule

> **No AI operation should EVER result in permanent data loss of uncommitted work.**

If an operation could potentially lose data:
1. It requires a safety check
2. It requires user confirmation
3. It requires a backup
4. It requires clear documentation of impact

## Implementation Checklist

- [x] Create git-safety-check.sh script
- [ ] Add pre-commit hooks
- [ ] Integrate safety check into Flux CLI
- [ ] Add automatic stashing before destructive ops
- [ ] Create WIP auto-commit feature
- [ ] Add operation logging
- [ ] Create recovery tools
- [ ] Add user prompts with clear warnings
- [ ] Test all safety features
- [ ] Document in user guide

## For AI Agents

**If you are an AI agent reading this:**

1. You have the power to help users OR destroy hours of their work
2. ALWAYS assume uncommitted work is precious
3. ALWAYS check `git status` before ANY git operation
4. ALWAYS ask before discarding changes
5. NEVER run `git checkout <file>` without explicit approval
6. When in doubt, create a backup
7. If you make a mistake, own it immediately and help recover

**Remember:** User's time and work are irreplaceable. Code can be rewritten, but trust is harder to rebuild.

---

**Last Updated:** 2025-11-02  
**Triggered By:** Catastrophic data loss incident - 3000+ lines of uncommitted work lost  
**Severity:** CRITICAL  
**Status:** Active - Must be enforced by all AI agents

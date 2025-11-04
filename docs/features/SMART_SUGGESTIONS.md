# Smart Command Suggestions

**Status**: ✅ Complete  
**Type**: Context-Aware Intelligence (No ML)  
**Added**: December 2024

## Overview

Smart Command Suggestions provides context-aware command recommendations based on your current project state, workflow patterns, and recent activity. Unlike traditional ML-based systems, this uses intelligent rules to suggest the most relevant next actions.

## How It Works

The system analyzes multiple context signals:

### 1. **Test State**
- Recent test runs and results
- Test failures and successes
- Time since last test run

### 2. **Git State**
- Uncommitted changes
- Staged files
- Number of modified files

### 3. **File Activity**
- Recently modified files
- Number of active files
- Edit patterns

### 4. **Session Patterns**
- Common workflows (edit→test→commit)
- Fix cycles (test failure→edit→retest)
- Workflow usage patterns

### 5. **Monitor State**
- Active monitors
- Recent failures
- Monitor events

### 6. **Workflow History**
- Last executed workflow
- Workflow chains
- Next logical steps

## Usage

### Manual Suggestions

Type `/suggest` anytime to see top 5 contextual suggestions:

```
You> /suggest

💡 Suggested Commands:
  1. 🧪 /test - 3 files modified - run tests
  2. ✅ /commit - Tests passing - ready to commit
  3. 🚀 /workflow pr-ready - Multiple files changed - prepare PR
  4. 📝 /diff - 5 files changed - review changes
  5. 🔍 /validate - Test failures detected - validate modified files
```

### Automatic Suggestions

High-confidence suggestions (≥80%) appear automatically every 3-5 commands:

```
💡 Suggestions:
  🔧 /fix - Last test run failed - auto-fix available
  🧪 /test - Re-run tests after fixes
Type /suggest for more suggestions

You> _
```

## Suggestion Categories

### 🧪 Test Actions
- Run tests after file modifications
- Re-run tests after fixes
- Fix failing tests

**Triggers:**
- Files modified without test run
- Test failures detected
- No recent test activity

### ✅ Git Actions
- Commit with passing tests
- Review uncommitted changes
- Commit staged files

**Triggers:**
- Tests passing + changes exist
- Many uncommitted changes
- Files staged for commit

### 🚀 Workflow Actions
- Execute common workflows
- Follow detected patterns
- Complete workflow chains

**Triggers:**
- Pattern detection (edit→test→commit)
- Last workflow completion
- Multiple file changes

### 🔧 Fix Actions
- Auto-fix formatting issues
- Validate modified files
- Run diagnostics

**Triggers:**
- Test failures exist
- Recent file modifications
- Error detection

### 👀 Monitor Actions
- Start test monitoring
- Check monitor status
- Review recent events

**Triggers:**
- Test failures without monitors
- Monitor failures detected
- Long development sessions

### 🧠 Validation Actions
- Review project state
- Check recent activity
- Analyze changes

**Triggers:**
- Many file modifications
- Complex changes
- Long sessions

## Confidence Scoring

Each suggestion has a confidence score (0.0-1.0):

- **0.90-1.00**: Critical actions (failing tests, ready to commit)
- **0.80-0.89**: High-priority actions (run tests, review changes)
- **0.70-0.79**: Recommended actions (workflows, monitoring)
- **0.60-0.69**: Optional actions (validation, state review)
- **0.50-0.59**: Low-priority actions (general improvements)

Only suggestions ≥0.80 show automatically.

## Pattern Detection

The system learns from your behavior:

### Edit-Test-Commit Pattern
Detects when you consistently:
1. Edit files
2. Run tests
3. Commit changes

**Suggestion**: After commit, suggests deployment workflows

### Fix Cycle Pattern
Detects when you:
1. Run tests (fail)
2. Edit files
3. Re-run tests

**Suggestion**: Offers `/fix` for auto-fixing common issues

### Workflow User Pattern
Detects frequent workflow usage

**Suggestion**: Suggests related workflows in sequence

## Examples

### Scenario 1: Development Cycle

```
# You edit 3 files
[After 3-5 commands]
💡 Suggestions:
  🧪 /test - 3 files modified - run tests

# Tests pass
💡 Suggestions:
  ✅ /commit - Tests passing - ready to commit

# After commit
💡 Suggestions:
  🚀 /workflow deploy-staging - Following your pattern
```

### Scenario 2: Bug Fixing

```
# Tests fail
💡 Suggestions:
  🔧 /fix - Last test run failed - auto-fix available
  🧪 /test - Re-run tests after fixes

# You run /fix and edit files
💡 Suggestions:
  🧪 /test - Re-run tests after fixes
  🔍 /validate - Validate modified files
```

### Scenario 3: Pull Request

```
# Multiple files changed, tests passing
💡 Suggestions:
  📋 /workflow pr-ready - Multiple files changed - prepare PR

# After pr-ready workflow
💡 Suggestions:
  🚀 /workflow deploy-staging - PR ready - deploy to staging
```

## Rate Limiting

To avoid overwhelming you with suggestions:

- **Auto-display**: Only every 3-5 commands (random interval)
- **Confidence filter**: Auto-display only high-confidence (≥0.80)
- **Deduplication**: Same command won't appear twice
- **Manual override**: `/suggest` always shows all suggestions

## Integration

### SessionManager Integration
- Tracks all events (edits, tests, commands, workflows)
- Detects patterns in behavior
- Remembers last workflow executed

### StateTracker Integration
- Provides recent file activity
- Test run history
- Command history

### Git Integration
- Monitors uncommitted changes
- Tracks staged files
- Branch status

### ProactiveMonitor Integration
- Monitor status and events
- Failure detection
- Real-time notifications

### WorkflowManager Integration
- Available workflows
- Workflow patterns
- Execution history

## Technical Details

### Architecture

```
CommandSuggestionEngine
├── Context Analyzer
│   ├── Git State
│   ├── Test State
│   ├── File State
│   ├── Session Patterns
│   ├── Monitor State
│   └── Workflow History
├── Rule Engine
│   ├── Test Actions
│   ├── Git Actions
│   ├── Workflow Actions
│   ├── Fix Actions
│   ├── Monitor Actions
│   └── Validation Actions
└── Suggestion Scorer
    ├── Confidence Calculation
    ├── Deduplication
    └── Priority Sorting
```

### No ML Required

This system uses **zero machine learning**:
- ✅ Rule-based logic
- ✅ Pattern matching
- ✅ Context analysis
- ✅ Confidence scoring
- ❌ No training data
- ❌ No model inference
- ❌ No data collection

### Performance

- **Fast**: < 1ms to generate suggestions
- **Lightweight**: No model loading or inference
- **Deterministic**: Same context = same suggestions
- **Explainable**: Every suggestion has a clear reason

## Future Enhancements

Potential improvements (without ML):

1. **Time-based patterns**: Detect time-of-day workflows
2. **File-type patterns**: Suggest based on file extensions
3. **Team patterns**: Learn from team workflow templates
4. **Project-specific rules**: Custom suggestion rules per project
5. **Integration with CI/CD**: Suggest based on pipeline status

## Commands

- `/suggest` - Show top 5 contextual suggestions
- `/help` - See all available commands

## Configuration

No configuration needed! The system works out of the box.

## Troubleshooting

**Q: Suggestions not showing?**  
A: They show every 3-5 commands. Use `/suggest` to see them anytime.

**Q: Too many suggestions?**  
A: Only high-confidence ones show automatically. Use `/suggest` for full list.

**Q: Wrong suggestions?**  
A: The system learns from your patterns. Keep using Flux naturally.

**Q: Want to disable?**  
A: Auto-suggestions only show in interactive terminal mode (not in desktop app).

## See Also

- [Session Persistence](../architecture/TOP_3_FEATURES.md#1-session-persistence--context-memory)
- [Proactive Monitoring](../architecture/TOP_3_FEATURES.md#2-proactive-monitoring)
- [Workflows](../architecture/TOP_3_FEATURES.md#3-one-command-workflows)
- [Quick Reference](../QUICK_REFERENCE.md)

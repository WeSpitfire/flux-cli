# Workflow Enforcement System

## Problem

Flux was blindly making file changes without understanding the codebase first. This led to:
- Modifying files without reading them
- Creating files in wrong locations
- Breaking existing code structure
- Not following project conventions
- Acting like an "overly eager developer running into a wall"

## Solution

A **workflow enforcement system** that requires Flux to follow a disciplined process before making any changes.

## Workflow Stages

```
UNDERSTAND → PLAN → VALIDATE → EXECUTE → VERIFY
```

### 1. UNDERSTAND (Required First Step)
Flux **must** gather information before attempting modifications:
- Read files it wants to modify
- List directory contents to understand structure
- Search for related code patterns
- Understand existing conventions

**Blocked actions:** Cannot write or edit files in this stage

### 2. PLAN
After understanding, Flux must articulate its plan:
- Describe what changes will be made
- Explain why they make sense
- Consider edge cases and dependencies

### 3. VALIDATE
Check the plan against reality:
- Verify file structure supports changes
- Check for conflicts
- Ensure dependencies are correct

### 4. EXECUTE
Now file modifications are allowed:
- Use `write_file` or `edit_file`
- Make changes confidently with context

### 5. VERIFY
After changes, verify they work:
- Run tests
- Check for errors
- Validate the outcome

## How It Works

### System Prompt
The LLM receives explicit instructions about the required workflow in `prompts.py`:

```
**NEVER jump straight to editing without understanding the file first.**
You are NOT allowed to modify files you haven't read yet.
```

### Runtime Enforcement
The `WorkflowEnforcer` class tracks:
- Which stage we're in
- Files that have been read
- Searches performed
- Plan status
- Validations done

### Tool Integration
File operation tools check with the enforcer before allowing modifications:

```python
# In WriteFileTool and EditFileTool
check = self.workflow.check_modification_allowed(file_path, operation)
if not check["allowed"]:
    return {
        "error": check["reason"],
        "suggestions": check.get("suggestions", []),
        "workflow_blocked": True
    }
```

### Automatic Tracking
- `read_files` → Records files read
- `grep_search` → Records searches performed
- `write_file`/`edit_file` → Checks workflow state before executing

## Usage

### For Users
Check workflow status:
```
/workflow
```

Output:
```
Stage: understand
Files read: 3
Searches: 2
Plan: ✗
Validations: 0
Modifications: 0
```

### For Developers
The workflow is initialized automatically for each query:

```python
# In CLI.process_query()
self.workflow.start_workflow()  # Fresh workflow for each query
```

## Example Workflow

**User asks:** "Add error handling to api.py"

**Bad (old) behavior:**
1. ❌ Immediately calls `edit_file` on api.py
2. ❌ Makes changes without context
3. ❌ Breaks existing code structure

**Good (new) behavior:**
1. ✅ Calls `read_files` on api.py → Moves to UNDERSTAND stage
2. ✅ Examines error handling patterns → Searches codebase
3. ✅ Describes the changes → Moves to PLAN stage
4. ✅ Validates structure → Moves to VALIDATE stage
5. ✅ Makes targeted edit → Executes in EXECUTE stage

## Error Messages

When Flux tries to skip steps, it gets blocked with helpful feedback:

```json
{
  "error": "Cannot modify files in UNDERSTAND stage. Need to analyze first.",
  "suggestions": [
    "Read api.py first to understand its current content",
    "List files in the directory to understand project structure",
    "Search for similar patterns in the codebase"
  ],
  "workflow_blocked": true
}
```

## Configuration

Strict mode can be disabled for testing:

```python
workflow = WorkflowEnforcer(cwd)
workflow.strict_mode = False  # Disable enforcement
```

## Benefits

1. **Forces understanding** - Can't change what you haven't read
2. **Prevents blind changes** - Must analyze before acting  
3. **Better code quality** - Changes respect existing patterns
4. **Self-documenting** - Plan stage creates natural documentation
5. **Debuggable** - Can check workflow status at any time
6. **Educational** - Teaches proper development workflow

## Implementation Files

- `flux/core/workflow.py` - Main enforcer logic
- `flux/tools/file_ops.py` - Integration into file tools
- `flux/tools/search.py` - Search tracking
- `flux/ui/cli.py` - CLI integration and commands
- `flux/llm/prompts.py` - System prompt instructions

## Future Enhancements

- [ ] Automatic plan generation from understanding phase
- [ ] Validation rules specific to file types
- [ ] Workflow templates for common tasks
- [ ] Persistent workflow context across sessions
- [ ] Visual workflow diagram in UI
- [ ] Metrics on workflow adherence

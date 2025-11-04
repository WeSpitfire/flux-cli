# Critical Issues with Flux - User Feedback

## Date: 2025-10-31

## Issue: Blind Code Changes

### Observation
User noted: *"flux doesn't seem to even look at the file structure before making edits - it's akin to a person just running up against a wall or an overly eager developer that just wants to make changes but doesn't actually understand what they are doing"*

### Specific Problems

1. **Not Reading Before Writing**
   - Flux makes changes without reading existing file content
   - Overwrites entire files instead of making targeted edits
   - Doesn't understand what code already exists

2. **Wrong Directory Placement**
   - Created files in `src/renderer/` instead of `flux-desktop/src/renderer/`
   - Doesn't respect `target_dir` parameter consistently
   - Ignores project structure

3. **No Context Awareness**
   - Doesn't check if functions already exist before adding them
   - Doesn't verify imports before using modules
   - Doesn't validate that referenced IDs/classes exist

4. **Overwrites Instead of Merges**
   - Replaced entire CSS file instead of appending
   - Lost all previous styling when adding new features
   - Destructive rather than additive

### Why This Happens

**Current Flux Workflow:**
```
User Request → Generate Code → Write File
```

**Missing Steps:**
- ✗ Read existing files
- ✗ Understand project structure  
- ✗ Validate against existing code
- ✗ Merge changes intelligently

### What Should Happen

**Proper Workflow:**
```
User Request 
  → Read relevant files
  → Understand existing structure
  → Generate compatible code
  → Validate changes
  → Apply targeted edits
  → Verify result
```

## Impact

### What Works
- ✅ Generating new files from scratch
- ✅ Simple text replacements with `edit_file`
- ✅ AST operations on single functions (Python/JS)

### What Fails
- ❌ Multi-file features requiring coordination
- ❌ Adding to existing files without destroying content
- ❌ Respecting project structure
- ❌ Understanding context before changes

## Root Causes

1. **LLM doesn't automatically read files**
   - Must explicitly call `read_files` tool
   - Often skips this step
   - Makes assumptions instead

2. **No pre-flight checks**
   - No validation before writing
   - No "does this make sense?" step
   - Trusts its own output blindly

3. **Tool design encourages overwriting**
   - `write_file` is easier than `edit_file`
   - No `append_to_file` or `merge_code` tools
   - AST tool only works for Python/JS

4. **No memory of project structure**
   - Doesn't remember what files exist
   - No project map in memory
   - Each request starts from zero context

## Solutions Needed

### Immediate (High Priority)

1. **Force Read-Before-Write**
   ```python
   class WriteFileTool:
       async def execute(self, path, content):
           # ALWAYS read existing file first
           if Path(path).exists():
               old_content = Path(path).read_text()
               # Show LLM the existing content
               # Confirm it wants to overwrite
   ```

2. **Add Merge Tool**
   ```python
   class MergeCodeTool:
       """Intelligently merge new code into existing file"""
       # Appends, doesn't replace
       # Preserves existing content
       # Smart insertion points
   ```

3. **Pre-Execution Validation**
   ```python
   def validate_before_execution(tool_name, params):
       if tool_name == "write_file":
           # Check if file exists
           # Show diff of changes
           # Confirm with user
   ```

4. **Project Structure in Memory**
   ```python
   class MemoryStore:
       def scan_project_structure(self):
           # Build file tree
           # Store in memory
           # Use for context
   ```

### Medium Priority

5. **Smarter Tool Selection**
   - Prompt engineering: "Read existing files first"
   - System prompt: "Never overwrite without reading"
   - Tool descriptions: "Use edit_file, not write_file"

6. **Diff Preview Required**
   - All file changes show diff before execution
   - User confirmation for destructive operations
   - Undo is automatic

7. **Context Injection**
   - Automatically inject file list in prompts
   - Include project structure in system prompt
   - Show related files before operations

### Low Priority

8. **Learning from Mistakes**
   - Track failed operations
   - Learn patterns of errors
   - Suggest better approaches

9. **Project Templates**
   - Understand common structures (React, Python, etc.)
   - Apply framework-specific patterns
   - Respect conventions

## Test Cases That Expose Issues

### Test 1: Add Feature to Existing File
```
Task: "Add a status bar to the existing Electron app"
Expected: Read HTML, add element, preserve existing
Actual: Overwrites entire HTML file
Result: ❌ FAIL
```

### Test 2: Append CSS Styles
```
Task: "Add file explorer styles to CSS"
Expected: Append to existing styles
Actual: Replaces entire CSS file
Result: ❌ FAIL
```

### Test 3: Multi-File Coordination
```
Task: "Add file explorer with JS, HTML, CSS changes"
Expected: Coordinate changes across files
Actual: Creates files in wrong directory, overwrites
Result: ❌ FAIL
```

## Immediate Action Items

1. ✅ Document this issue (this file)
2. ⬜ Add "read-first" rule to system prompt
3. ⬜ Create MergeCodeTool
4. ⬜ Add validation layer before file writes
5. ⬜ Test with same Electron app scenario
6. ⬜ Measure improvement

## Metrics to Track

- **Read-before-write rate**: Currently ~30%, should be 100%
- **Overwrite vs Edit ratio**: Currently 70/30, should be 20/80
- **Files created in correct location**: Currently ~60%, should be 100%
- **User manual fixes required**: Currently ~40% of changes, should be <10%

## Conclusion

**Flux needs to be more thoughtful, not just fast.**

The core issue isn't the LLM capability - it's the workflow and tooling that encourages blind changes. By forcing read-before-write, adding merge capabilities, and validating before execution, we can make Flux much more reliable.

This is exactly the kind of self-improvement Flux was designed for - using feedback from real usage to get better!

---

**Priority**: CRITICAL  
**Affects**: Multi-file projects, existing codebases  
**Fix Difficulty**: Medium (requires tool changes + prompt engineering)  
**User Impact**: HIGH - Currently causes frustration and manual fixes

# Flux Editing Strategy Guidelines

## Core Philosophy
**Read → Understand → Plan → Execute → Verify**

The LLM should follow a disciplined workflow for file modifications, treating code editing as a careful, methodical process rather than a trial-and-error approach.

---

## 1. Context Gathering (MANDATORY)

### Before ANY File Edit:
```
✅ DO: Read the target file FIRST
✅ DO: Read surrounding context (±50 lines from edit location)
✅ DO: Identify existing patterns in the code
✅ DO: Check if functionality already exists

❌ DON'T: Edit files you haven't read
❌ DON'T: Assume file structure without verification
❌ DON'T: Skip reading "because you remember" from previous context
```

### Reading Strategy:
- **Small files (<200 lines)**: Read entire file
- **Medium files (200-1000 lines)**: Read target function/class + surrounding context
- **Large files (>1000 lines)**: 
  1. Use `grep_search` to find target location
  2. Read lines around target (±100 lines)
  3. For modifications, read related functions too

---

## 2. Tool Selection

### Decision Tree:

```
Are you editing Python?
├─ YES → Is it adding/removing a complete function?
│         ├─ YES, clean location → ast_edit (add_function/remove_function)
│         └─ NO, modifying code → edit_file (PREFERRED)
└─ NO → edit_file (ONLY option for JS/TS/CSS/HTML/JSON)
```

### Tool Preferences (in order):

1. **edit_file** - MOST RELIABLE
   - Use for: Most code modifications
   - Pros: Exact text matching, undo support, works with all languages
   - Cons: Requires exact whitespace match
   
2. **ast_edit** - SPECIALIZED
   - Use for: Adding complete new Python functions/classes in clean locations
   - Pros: Understands code structure
   - Cons: Python only, fragile for modifications, poor error recovery
   
3. **write_file** - LAST RESORT
   - Use for: Creating new files or complete rewrites
   - Cons: No surgical edits, overwrites entire file

### When ast_edit Fails:
If `ast_edit` fails **even once**, immediately pivot to `edit_file`. Do NOT retry `ast_edit` with different parameters.

---

## 3. Execution Best Practices

### For edit_file:

#### ✅ CORRECT Approach:
```python
# Step 1: Read file
read_files(['file.py'])

# Step 2: Copy EXACT text including whitespace
search = """                if query.lower() == '/summary':
                    await self.show_work_summary()
                    continue
                
                if query.lower() == '/help':"""

# Step 3: Provide precise replacement
replace = """                if query.lower() == '/summary':
                    await self.show_work_summary()
                    continue
                
                if query.lower() == '/stats':
                    await self.show_project_stats()
                    continue
                
                if query.lower() == '/help':"""

# Step 4: Execute
edit_file(path='file.py', search=search, replace=replace)
```

#### ❌ INCORRECT Approach:
```python
# DON'T: Edit without reading
edit_file(path='file.py', search='...', replace='...')

# DON'T: Guess at the content
search = "if query == '/help':"  # Wrong! Actual code uses .lower()

# DON'T: Ignore indentation
search = "if query.lower() == '/help':"  # Missing leading spaces!
```

### For ast_edit:

#### ✅ When to use:
- Adding a NEW function to a class/module
- Target location exists and is verified
- Function is COMPLETE and self-contained

#### ❌ When NOT to use:
- Modifying existing functions (use edit_file)
- Inserting code into middle of functions (use edit_file)
- After first failure (pivot to edit_file)

---

## 4. Error Recovery Strategy

### Intelligent Retry Logic:

```
Attempt 1: Use selected tool
   ├─ SUCCESS → Done ✓
   └─ FAIL → Read error message carefully

Attempt 2: Follow error suggestion OR pivot strategy
   ├─ SUCCESS → Done ✓
   └─ FAIL → Same error pattern?
             ├─ YES → Pivot to different tool
             └─ NO → Try error suggestion

Attempt 3: Use edit_file (fallback)
   ├─ SUCCESS → Done ✓
   └─ FAIL → Read file again, re-examine approach

MAX 3 attempts per operation
```

### Common Error Patterns & Responses:

| Error | Response |
|-------|----------|
| "Function already exists" | Use `modify_function` OR better: use `edit_file` |
| "Search text not found" | Re-read file, copy EXACT text with line numbers |
| "Syntax error at line X" | Read lines around X, check indentation/structure |
| "File not found" | Use `find_files` to search by pattern |
| Same error twice | **STOP current approach, pivot completely** |

---

## 5. Verification (MANDATORY)

### After Every Edit:

1. **Automatic** (built into tools):
   - Syntax validation
   - Auto-rollback on syntax errors

2. **Manual** (LLM should do):
   ```python
   # For Python files:
   run_command("python -m py_compile path/to/file.py")
   
   # For any file - verify it exists and has expected content:
   read_files(['path/to/file.py'])  # Spot check changes
   ```

3. **Context check**:
   - Did I add the command handler?
   - Did I update the help text?
   - Are there related files that need updates (tests, docs)?

---

## 6. Multi-Step Modifications

### Pattern for Complex Changes:

```
Task: Add /stats command to CLI

Step 1: Understand structure
├─ read_files(['cli.py'])
├─ Identify command handler pattern (lines 310-320)
└─ Identify help text location (line 350)

Step 2: Plan minimal changes
├─ Add command handler (3 lines)
├─ Update help text (1 line)
└─ Ensure method exists (may need separate addition)

Step 3: Execute in order
├─ Edit 1: Add method to class (if needed)
├─ Edit 2: Add command handler  
└─ Edit 3: Update help text

Step 4: Verify
└─ Syntax check + spot-check reads
```

### Batching vs Sequential:

- **Sequential** (preferred): One logical change per edit
- **Batching**: Only if changes are in different files or very distant in same file

---

## 7. Specific Guidance by Language

### Python:
- Indentation: Use spaces, match existing file (usually 4 spaces)
- Always verify imports are at top
- Check for existing functionality before adding

### JavaScript/TypeScript:
- Use `edit_file` ONLY (no AST support in current version)
- Watch for semicolons (match file style)
- Preserve JSDoc comments

### JSON:
- Use `edit_file` only
- Verify valid JSON after edit
- Watch for trailing commas

---

## 8. Anti-Patterns to Avoid

### 🚫 The "Repeat Same Failure" Pattern:
```
ast_edit → syntax error
ast_edit → syntax error  ← WRONG! Pivot instead
ast_edit → syntax error  ← VERY WRONG!
```

### 🚫 The "Blind Edit" Pattern:
```
# User: "Add X to file.py"
edit_file(...)  ← WRONG! Read first
```

### 🚫 The "Overconfident Guess" Pattern:
```
# "I remember the file structure from earlier"
edit_file(search="def process_query(self, query: str):")  ← WRONG! Could be changed
```

### 🚫 The "Whole Function Rewrite" Pattern:
```
# Don't replace entire functions when you only need to change 3 lines
# Use targeted edits instead
```

---

## 9. Success Metrics

After following these guidelines, success rate should be:

- ✅ 95%+ of edits succeed on first attempt
- ✅ 100% of edits succeed within 2 attempts
- ✅ 0% of edits make more than 3 attempts
- ✅ 100% of files are read before modification
- ✅ 90%+ of edits use `edit_file` over `ast_edit`

---

## 10. Examples

### Example 1: Adding a CLI Command (CORRECT)

```python
# Step 1: Read and understand
await read_files(['flux/ui/cli.py'])
# Observe: Commands handled around line 315, help at line 350

# Step 2: Make precise edit for handler
await edit_file(
    path='flux/ui/cli.py',
    search='''                if query.lower() == '/summary':
                    await self.show_work_summary()
                    continue
                
                if query.lower() == '/help':''',
    replace='''                if query.lower() == '/summary':
                    await self.show_work_summary()
                    continue
                
                if query.lower() == '/stats':
                    await self.show_project_stats()
                    continue
                
                if query.lower() == '/help':'''
)

# Step 3: Update help text
await edit_file(
    path='flux/ui/cli.py',
    search='''                        "  /summary - Show work summary for today\\n"
                        "\\n[bold]General:[/bold]\\n"''',
    replace='''                        "  /summary - Show work summary for today\\n"
                        "  /stats - Show project statistics\\n"
                        "\\n[bold]General:[/bold]\\n"'''
)

# Step 4: Verify
await run_command('python -m py_compile flux/ui/cli.py')
```

### Example 2: Recovering from Failure (CORRECT)

```python
# Attempt 1: Try ast_edit
result = await ast_edit(path='cli.py', operation='add_function', ...)
# Result: ERROR - "Function already exists"

# Attempt 2: Pivot immediately to edit_file
await read_files(['cli.py'])  # Re-read to understand current state
await edit_file(path='cli.py', search='...', replace='...')  # Targeted edit
# Result: SUCCESS ✓
```

---

## Summary

**The Golden Rules:**
1. Always read before editing
2. Prefer `edit_file` for most changes
3. Make minimal, targeted edits
4. Pivot strategy after failures
5. Verify every change

These guidelines turn Flux from a "trial-and-error" tool into a disciplined, reliable code editor.

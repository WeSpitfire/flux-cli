# Flux Code Editing Improvements Plan

**Date**: November 1, 2025  
**Problem**: Flux (even with GPT-4o) struggles with indentation-sensitive edits  
**Root Cause**: Text-based search/replace is fragile for Python's whitespace sensitivity

---

## Problem Analysis

### Issue 1: Indentation Errors
**Example**: `/model` command implementation
- Flux made 3 attempts, all failed with indentation errors
- Even GPT-4o couldn't get whitespace exactly right
- Text-based `edit_file` requires perfect character-by-character matching

### Issue 2: No Error Recovery
- Flux repeated same approach 3 times
- Didn't pivot to alternative strategies
- No learning from failed attempts

### Issue 3: Context Loss
- Truncated file reads lose indentation context
- LLM can't see the exact whitespace structure
- Guesses at indentation level

---

## Proposed Solutions

### Priority 1: Smart Indentation Detection (High Impact)

**Goal**: Automatically detect and apply correct indentation

**Implementation**:
```python
# flux/tools/smart_edit.py

class SmartEditTool(Tool):
    """Edit files with automatic indentation detection."""
    
    def detect_indentation(self, file_content: str, line_number: int) -> str:
        """Detect indentation at a specific line."""
        lines = file_content.split('\n')
        if line_number >= len(lines):
            return ""
        
        line = lines[line_number]
        # Count leading whitespace
        indent = len(line) - len(line.lstrip())
        return line[:indent]
    
    def normalize_indentation(self, 
                             text: str, 
                             target_indent: str) -> str:
        """Normalize multi-line text to target indentation."""
        lines = text.split('\n')
        normalized = []
        
        # Detect original indentation
        if lines:
            first_line_indent = len(lines[0]) - len(lines[0].lstrip())
        else:
            first_line_indent = 0
        
        for line in lines:
            if line.strip():  # Non-empty line
                # Remove original indent, add target indent
                stripped = line.lstrip()
                line_indent = len(line) - len(stripped)
                relative_indent = line_indent - first_line_indent
                new_line = target_indent + (" " * max(0, relative_indent)) + stripped
                normalized.append(new_line)
            else:
                normalized.append(line)
        
        return '\n'.join(normalized)
```

**Benefits**:
- ✅ LLM doesn't need to guess indentation
- ✅ Auto-corrects whitespace issues
- ✅ Works with any indentation style

**Effort**: 2-3 hours

---

### Priority 2: Line-Based Insertion (High Impact)

**Goal**: Insert code at line number without search/replace

**Implementation**:
```python
class LineInsertTool(Tool):
    """Insert code at specific line numbers."""
    
    async def execute(self, 
                     path: str, 
                     line_number: int, 
                     code: str,
                     mode: str = "insert") -> Dict[str, Any]:
        """
        Insert code at line number.
        
        Args:
            path: File path
            line_number: Where to insert (1-indexed)
            code: Code to insert
            mode: "insert" (keep existing), "replace" (replace line), 
                  "after" (insert after line)
        """
        file_path = self.cwd / path
        
        # Read file
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Detect indentation at target line
        if line_number <= len(lines):
            target_indent = self.detect_indentation(
                ''.join(lines), 
                line_number - 1
            )
        else:
            target_indent = ""
        
        # Normalize code indentation
        normalized_code = self.normalize_indentation(code, target_indent)
        
        # Insert based on mode
        if mode == "insert":
            lines.insert(line_number - 1, normalized_code + '\n')
        elif mode == "replace":
            lines[line_number - 1] = normalized_code + '\n'
        elif mode == "after":
            lines.insert(line_number, normalized_code + '\n')
        
        # Write back
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        return {"success": True, "lines_added": len(normalized_code.split('\n'))}
```

**Benefits**:
- ✅ No search/replace fragility
- ✅ Simple for LLM: just specify line number
- ✅ Auto-handles indentation

**Effort**: 2-3 hours

---

### Priority 3: Visual Diff Preview (Medium Impact)

**Goal**: Show LLM what the change will look like before applying

**Implementation**:
```python
class DiffPreviewTool(Tool):
    """Preview changes before applying."""
    
    async def execute(self,
                     path: str,
                     search: str,
                     replace: str) -> Dict[str, Any]:
        """Show diff preview without applying changes."""
        
        file_path = self.cwd / path
        with open(file_path, 'r') as f:
            original = f.read()
        
        # Generate modified content
        modified = original.replace(search, replace)
        
        # Generate unified diff
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
            lineterm=''
        )
        
        diff_text = ''.join(diff)
        
        return {
            "preview": diff_text,
            "changes_found": search in original,
            "warning": "Use edit_file to apply" if search in original else "Search text not found"
        }
```

**Benefits**:
- ✅ LLM can verify before applying
- ✅ Catches indentation issues early
- ✅ Reduces failed attempts

**Effort**: 1-2 hours

---

### Priority 4: Better Error Messages (High Impact)

**Goal**: Give LLM actionable feedback on what went wrong

**Current Error**:
```
Syntax error: SyntaxError at line 208: unexpected indent
```

**Improved Error**:
```
Indentation Error at line 208:
  Expected: 16 spaces (to match line 207)
  Got: 20 spaces

Context:
  207|                if query.lower() == '/history':
  208|                    if query.lower() == '/model':  ❌ Too much indent
  
Suggestion: Your replacement has inconsistent indentation. 
The block should align with the 'if' statement on line 195.
Try reading lines 190-210 to see the exact indentation pattern.
```

**Implementation**:
```python
def enhanced_syntax_error(error: SyntaxError, 
                         original: str, 
                         modified: str) -> Dict[str, Any]:
    """Generate helpful error message with context."""
    
    # Detect indentation mismatch
    orig_lines = original.split('\n')
    mod_lines = modified.split('\n')
    
    error_line = error.lineno - 1
    
    # Show context around error
    context_start = max(0, error_line - 2)
    context_end = min(len(mod_lines), error_line + 3)
    
    context = []
    for i in range(context_start, context_end):
        if i < len(mod_lines):
            marker = " ❌" if i == error_line else ""
            context.append(f"  {i+1:3d}|{mod_lines[i]}{marker}")
    
    # Analyze indentation
    if error_line < len(mod_lines):
        line = mod_lines[error_line]
        indent = len(line) - len(line.lstrip())
        
        # Find expected indentation
        expected_indent = None
        for i in range(error_line - 1, -1, -1):
            if i < len(orig_lines) and orig_lines[i].strip():
                expected_indent = len(orig_lines[i]) - len(orig_lines[i].lstrip())
                break
    
    return {
        "error": str(error),
        "line": error_line + 1,
        "context": '\n'.join(context),
        "indent_expected": expected_indent,
        "indent_got": indent,
        "suggestion": (
            f"Indentation mismatch. Expected {expected_indent} spaces "
            f"(to match previous lines), got {indent} spaces. "
            f"Try reading lines {context_start}-{context_end} to see "
            f"the correct indentation pattern."
        )
    }
```

**Benefits**:
- ✅ LLM understands exactly what went wrong
- ✅ Actionable suggestions
- ✅ Context for fixing

**Effort**: 2-3 hours

---

### Priority 5: Retry with Strategy Change (Medium Impact)

**Goal**: After failure, try different approach

**Implementation**:
```python
# In LLM prompt after failed edit:

EDIT_FAILURE_PROMPT = """
The previous edit attempt failed with: {error}

IMPORTANT: The text-based edit_file tool failed. Try one of these alternatives:

1. READ MORE CONTEXT: Use read_files to see lines {context_range} 
   to understand the exact indentation pattern

2. USE LINE INSERTION: Instead of search/replace, use line_insert_tool
   to insert at line {insert_line} with automatic indentation

3. BREAK INTO STEPS: Make smaller changes one at a time
   - First add just the if statement
   - Then add the content
   - Then add the continue

4. USE AST EDITING: For Python files, use ast_edit_tool which handles
   indentation automatically

Which approach would work best for this change?
"""
```

**Benefits**:
- ✅ Forces LLM to pivot strategy
- ✅ Suggests concrete alternatives
- ✅ Breaks infinite retry loops

**Effort**: 1-2 hours

---

### Priority 6: AST-Based Python Editing (High Impact, Long-term)

**Goal**: Edit Python using AST instead of text

**Implementation**:
```python
class ASTInsertTool(Tool):
    """Insert Python code using AST."""
    
    async def execute(self,
                     path: str,
                     target_function: str,
                     insert_before: str,
                     code: str) -> Dict[str, Any]:
        """
        Insert code into function using AST.
        
        Args:
            target_function: Function name to modify
            insert_before: Statement to insert before (or "end" for end of function)
            code: Code to insert (will be parsed as AST)
        """
        import ast
        
        # Read and parse file
        with open(self.cwd / path, 'r') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        # Find target function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == target_function:
                # Parse code to insert
                insert_tree = ast.parse(code)
                
                # Find insertion point
                for i, stmt in enumerate(node.body):
                    # Logic to find insertion point
                    pass
                
                # Insert statements
                node.body.insert(insertion_index, *insert_tree.body)
                
                # Regenerate source with proper indentation
                new_source = ast.unparse(tree)
                
                # Write back
                with open(self.cwd / path, 'w') as f:
                    f.write(new_source)
                
                return {"success": True}
```

**Benefits**:
- ✅ Perfect indentation always
- ✅ Syntax-aware editing
- ✅ Can't break code structure

**Drawbacks**:
- ⚠️ Python-only
- ⚠️ Complex implementation
- ⚠️ May change formatting

**Effort**: 4-6 hours

---

## Implementation Roadmap

### Phase 1: Quick Wins (4-6 hours)
1. **Better error messages** (Priority 4) - 2-3 hours
2. **Retry with strategy change** (Priority 5) - 1-2 hours
3. **Diff preview tool** (Priority 3) - 1-2 hours

**Impact**: Immediate improvement in error recovery

### Phase 2: Core Improvements (4-6 hours)
1. **Smart indentation detection** (Priority 1) - 2-3 hours
2. **Line-based insertion tool** (Priority 2) - 2-3 hours

**Impact**: 80%+ reduction in indentation failures

### Phase 3: Long-term (Optional, 4-6 hours)
1. **AST-based editing** (Priority 6) - 4-6 hours

**Impact**: Perfect Python editing, but complex

---

## Recommendation

**Start with Phase 1 (Quick Wins):**

1. Improve error messages (2-3 hours)
   - Show indentation mismatches clearly
   - Provide actionable suggestions
   - Show context around error

2. Add retry strategy guidance (1-2 hours)
   - Detect repeated failures
   - Suggest alternative approaches
   - Break out of infinite loops

**Then move to Phase 2 if needed:**

3. Smart indentation tool (2-3 hours)
   - Handles most indentation issues
   - Works with existing edit_file tool
   - Minimal disruption

---

## Testing Plan

After each improvement, test with:

1. **Simple insertion** (like `/model` command)
   - Should succeed first try
   - Correct indentation

2. **Nested block insertion**
   - Inside if/while/for
   - Multiple indentation levels

3. **Function modification**
   - Add statements to existing function
   - Maintain structure

4. **Error recovery**
   - Intentionally break something
   - Check error message quality
   - Verify LLM tries different approach

---

## Expected Results

### Before
- ❌ 30% first-attempt success (even with GPT-4o)
- ❌ Infinite retry loops on indentation
- ❌ Cryptic error messages

### After Phase 1
- ✅ 60% first-attempt success
- ✅ Clear error messages
- ✅ Strategic pivoting on failure

### After Phase 2
- ✅ 90%+ first-attempt success
- ✅ Auto-corrects indentation
- ✅ Minimal manual intervention

---

## Next Steps

**Which phase should we start with?**

**Option A: Quick Wins (Recommended)**
- 4-6 hours total
- Immediate visible improvement
- Easy to test

**Option B: Go straight to Phase 2**
- More work upfront (4-6 hours)
- Solves root cause immediately
- Higher impact but more complex

**Option C: Implement all**
- 12-18 hours total
- Complete solution
- Best long-term investment

What do you think? Should we start with Phase 1 (quick wins) or go straight to Phase 2 (core improvements)?

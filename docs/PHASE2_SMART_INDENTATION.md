# Phase 2: Smart Indentation & Line-Based Insertion

## Overview

Phase 2 introduces intelligent indentation handling and a line-based insertion tool to eliminate the most common source of code editing failures: whitespace mismatches.

## Components

### 1. IndentationHelper (`flux/core/indentation.py`)

A utility class providing static methods for indentation detection and normalization.

#### Key Methods

**`detect_indentation(content: str, line_number: int) -> Tuple[str, int]`**
- Detects the indentation string and count for a specific line
- Returns: `(indent_string, indent_count)`
  - `indent_string`: The actual whitespace characters (e.g., `'    '` for 4 spaces)
  - `indent_count`: Number of spaces/tabs used

**`detect_indentation_from_context(content: str, line_number: int, look_back: int = 10) -> Tuple[str, int]`**
- Detects expected indentation by analyzing surrounding context
- Looks at nearby non-empty lines to infer indentation
- Smart fallback: uses previous/next line if target line is empty
- Returns: `(indent_string, indent_count)`

**`normalize_indentation(code: str, target_indent: str, target_count: int) -> str`**
- Normalizes multiline code to match target indentation
- Preserves relative indentation between lines
- Handles edge cases like empty lines and mixed indentation

**`count_indent(line: str) -> int`**
- Counts leading whitespace characters
- Handles both spaces and tabs

**`detect_indent_style(content: str) -> str`**
- Detects indentation style: `'spaces'`, `'tabs'`, or `'mixed'`
- Scans file to determine predominant style

**`get_indent_unit(content: str) -> str`**
- Returns the base indentation unit for a file
- E.g., `'    '` for 4 spaces, `'\t'` for tabs

#### Usage Examples

```python
from flux.core.indentation import IndentationHelper

# Example 1: Detect indentation at a specific line
content = """def foo():
    if True:
        pass"""

indent_str, indent_count = IndentationHelper.detect_indentation(content, 2)
# Result: ('    ', 4)

# Example 2: Normalize code to match context
code = """if condition:
    print('hello')
    print('world')"""

# Normalize from 4 spaces to 8 spaces
normalized = IndentationHelper.normalize_indentation(code, '        ', 8)
# Result:
#         if condition:
#             print('hello')
#             print('world')

# Example 3: Detect indentation from context (smart)
content = """def bar():
    x = 1
    # INSERT HERE
    y = 2"""

indent_str, indent_count = IndentationHelper.detect_indentation_from_context(content, 3)
# Result: ('    ', 4) - detected from surrounding lines
```

### 2. InsertAtLineTool (`flux/tools/line_insert.py`)

A line-based code insertion tool that automatically handles indentation.

#### Features

- **Automatic indentation detection**: Analyzes surrounding context
- **Three insertion modes**: `before`, `after`, `replace`
- **Syntax validation**: Validates Python syntax before writing
- **Undo support**: Creates snapshots for rollback
- **User approval**: Optional approval workflow integration

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | File path (absolute or relative) |
| `line_number` | number | Yes | Line number to insert at (1-indexed) |
| `code` | string | Yes | Code to insert (indentation auto-corrected) |
| `mode` | string | No | Insert mode: `'before'`, `'after'` (default), or `'replace'` |

#### Return Values

**Success:**
```python
{
    "success": True,
    "path": "/path/to/file.py",
    "line_number": 42,
    "mode": "after",
    "lines_added": 3,
    "indentation_applied": "8 spaces",
    "total_lines": 150
}
```

**Error:**
```python
{
    "error": "Invalid line number: 999. File has 100 lines."
}
```

#### Usage Examples

**Example 1: Insert after a line**
```python
from flux.tools.line_insert import InsertAtLineTool
from pathlib import Path

tool = InsertAtLineTool(cwd=Path.cwd())

result = await tool.execute(
    path="src/calculator.py",
    line_number=10,
    code='print("Operation complete")',
    mode="after"
)
# Inserts the print statement after line 10 with correct indentation
```

**Example 2: Insert before a line**
```python
result = await tool.execute(
    path="src/calculator.py",
    line_number=5,
    code='# Starting calculation',
    mode="before"
)
# Inserts comment before line 5
```

**Example 3: Replace a line**
```python
result = await tool.execute(
    path="src/calculator.py",
    line_number=1,
    code='def calculate(x: int, y: int) -> int:',
    mode="replace"
)
# Replaces line 1 with new function signature
```

**Example 4: Insert multiline code**
```python
multiline_code = """self.history = []
self.max_size = 100
self.current_index = 0"""

result = await tool.execute(
    path="src/calculator.py",
    line_number=3,
    code=multiline_code,
    mode="after"
)
# All three lines are inserted with correct indentation
```

## When to Use Each Tool

### Use `insert_at_line` when:
- ✅ You know the exact line number to insert at
- ✅ You're adding new code (not modifying existing)
- ✅ You want automatic indentation handling
- ✅ The file structure is complex or deeply nested

### Use `edit_file` when:
- ✅ You need to modify existing code via search/replace
- ✅ The change spans multiple non-contiguous sections
- ✅ You have unique search strings to target specific code

## How It Works

### Insertion Flow

1. **Read file**: Load current file content
2. **Validate line number**: Ensure line number is within bounds
3. **Detect context indentation**: Analyze surrounding lines
4. **Normalize code**: Adjust provided code to match context
5. **Insert/Replace**: Apply changes based on mode
6. **Validate syntax**: Check for syntax errors (Python files)
7. **Request approval**: If approval manager is configured
8. **Write file**: Save changes
9. **Create snapshot**: Record for undo capability

### Indentation Detection Strategy

The tool uses a smart context-aware strategy:

1. **Target line detection**:
   - `before` mode: Uses the target line itself
   - `after` mode: Uses the line after target
   - `replace` mode: Uses the target line

2. **Context analysis** (looks back up to 10 lines):
   - Finds nearest non-empty line
   - Extracts its indentation
   - Uses as the baseline

3. **Normalization**:
   - Detects relative indentation in provided code
   - Re-applies same relative indentation using context baseline
   - Preserves code structure

### Example: Deep Nesting

**Original file:**
```python
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, n):
        if n > 0:
            self.result += n  # Line 7
            return True
        return False
```

**Insert after line 7:**
```python
await tool.execute(
    path="calculator.py",
    line_number=7,
    code='print(f"Added {n}")',
    mode="after"
)
```

**Result:**
```python
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, n):
        if n > 0:
            self.result += n
            print(f"Added {n}")  # ← Correct 12-space indent!
            return True
        return False
```

## Benefits

### 1. Eliminates Indentation Errors
- No more "IndentationError" or whitespace mismatch failures
- LLM doesn't need to count spaces manually
- Works correctly with tabs, spaces, or mixed indentation

### 2. Simpler Mental Model
- Think in line numbers, not search/replace patterns
- No need to worry about whitespace in search strings
- Clear and predictable behavior

### 3. Safer Operations
- Syntax validation before writing
- Undo snapshot creation
- Optional user approval

### 4. Better Error Messages
- Clear feedback on what went wrong
- Actionable suggestions
- Detailed metadata in responses

## Testing

### Test Coverage

All components have been tested with:
- ✅ Basic indentation detection (spaces and tabs)
- ✅ Indentation normalization (increasing/decreasing)
- ✅ Context-based detection (smart fallback)
- ✅ Line insertion (before/after/replace modes)
- ✅ Multiline code insertion
- ✅ Deep nesting scenarios
- ✅ Edge cases (empty lines, mixed indentation)

### Running Tests

```bash
# Test indentation helper
python -c "from flux.core.indentation import IndentationHelper; ..."

# Test line insertion tool
python -c "from flux.tools.line_insert import InsertAtLineTool; ..."
```

See test examples in the implementation files for detailed test cases.

## Integration

### CLI Integration

The `insert_at_line` tool is registered in the CLI's tool registry:

```python
# In flux/cli/main.py or equivalent
from flux.tools.line_insert import InsertAtLineTool

# Initialize tool
insert_tool = InsertAtLineTool(
    cwd=current_working_directory,
    undo_manager=undo_mgr,
    workflow_enforcer=workflow,
    approval_manager=approval
)

# Register with Anthropic client
tools.append(insert_tool.to_anthropic_tool())
```

### LLM Guidance

The tool description includes clear guidance for LLMs:

```
BEST FOR: Adding new code when you know the exact line number.
NO NEED to worry about indentation - it's automatically detected and applied!

ADVANTAGES over edit_file:
- No search/replace text matching required
- Indentation handled automatically
- Can't fail due to whitespace issues
- Perfect for adding new blocks of code

USAGE:
1. Read the file to see line numbers
2. Find where to insert (e.g., after line 207)
3. Provide the code WITHOUT worrying about exact indentation
4. Tool automatically matches surrounding indentation
```

## Future Enhancements

Potential improvements for Phase 3:
- AST-based editing for even more robust Python modifications
- Support for other languages (JavaScript, TypeScript, etc.)
- Visual diff preview before applying changes
- Bulk line insertions (insert at multiple line numbers in one call)

## Troubleshooting

### Common Issues

**Issue: "Invalid line number"**
- Solution: Read the file first to see how many lines it has
- Line numbers are 1-indexed (first line is 1, not 0)

**Issue: Indentation looks wrong**
- Solution: Check if file uses mixed tabs/spaces (use `detect_indent_style`)
- Tool preserves relative indentation from provided code

**Issue: Syntax error after insertion**
- Solution: The tool prevents writing if syntax is invalid
- Check the error message for details about what's wrong

### Debug Tips

1. **Check indentation detection**:
   ```python
   from flux.core.indentation import IndentationHelper
   content = open('file.py').read()
   style = IndentationHelper.detect_indent_style(content)
   unit = IndentationHelper.get_indent_unit(content)
   print(f"Style: {style}, Unit: {repr(unit)}")
   ```

2. **Preview normalization**:
   ```python
   normalized = IndentationHelper.normalize_indentation(
       your_code,
       target_indent='    ',
       target_count=8
   )
   print(normalized)
   ```

3. **Test in isolation**:
   - Use temporary files to test insertions
   - Verify behavior before applying to real code

## Summary

Phase 2 provides the foundation for reliable code editing by:
1. **IndentationHelper**: Smart indentation detection and normalization
2. **InsertAtLineTool**: Line-based insertion with automatic indentation

Together, these eliminate the primary source of edit failures (whitespace mismatches) and provide a clearer, more predictable editing experience for both LLMs and users.

**Next Steps**: Phase 3 will build on this foundation with AST-based Python editing for even more sophisticated modifications.

# Flux Automatic Validation System

## Overview
Flux has built-in automatic validation that prevents broken code from being saved. This happens transparently in the background for all file modification tools.

## How It Works

### 1. Syntax Checking
Every time a file is modified using `edit_file`, `write_file`, or `ast_edit`, Flux automatically:

1. **Validates the new content** against language-specific syntax rules
2. **Compares with old content** to ensure the change doesn't break syntax
3. **Auto-rolls back** if syntax errors are introduced

### 2. Supported Languages

| Language | Validation Method | Auto-Rollback |
|----------|------------------|---------------|
| Python (.py) | AST parsing with `ast.parse()` | ✅ Yes |
| JavaScript (.js, .jsx) | Node.js syntax check | ✅ Yes |
| TypeScript (.ts, .tsx) | Node.js syntax check | ✅ Yes |
| Others | No validation | ❌ No |

### 3. Implementation

The validation is implemented in `flux/core/syntax_checker.py`:

```python
def validate_modification(file_path, old_content, new_content):
    """
    Validates that a modification doesn't break syntax.
    Returns should_rollback=True if new content breaks syntax.
    """
```

This is called automatically in:
- `flux/tools/file_ops.py` - `EditFileTool.execute()`
- `flux/tools/file_ops.py` - `WriteFileTool.execute()`
- `flux/tools/ast_edit.py` - `ASTEditTool.execute()`

## Example Flow

```
1. User: "Add /stats command"
2. Flux: Uses edit_file to modify cli.py
3. edit_file internally:
   ├─ a. Read old content
   ├─ b. Generate new content
   ├─ c. Call SyntaxChecker.validate_modification()
   ├─ d. If validation fails:
   │     ├─ Rollback to old content
   │     └─ Return error to LLM
   └─ e. If validation passes:
         ├─ Write new content
         └─ Return success
```

## Error Response Format

When validation fails, tools return:

```json
{
  "error": "Syntax error introduced - changes rolled back",
  "syntax_error": "SyntaxError at line 374: expected an indented block...",
  "rolled_back": true,
  "path": "/path/to/file.py"
}
```

This tells the LLM:
- What went wrong
- That changes were already rolled back (file is safe)
- Where the error occurred (for debugging)

## Benefits

### 1. Safety
- Users can never end up with broken code
- All syntax errors caught before writing to disk
- Automatic rollback means no manual cleanup needed

### 2. Feedback Loop
- LLM receives immediate feedback on syntax errors
- Error messages guide LLM to fix the issue
- Encourages better code generation

### 3. Confidence
- Users can trust that Flux won't break their code
- Reduces fear of using AI code modification
- Makes experimentation safer

## Limitations

### 1. Semantic Errors Not Caught
The validation only checks **syntax**, not **logic**:

```python
# This will PASS validation (syntactically correct)
def add(a, b):
    return a - b  # But logically wrong!
```

### 2. Import Errors Not Caught
```python
# This will PASS validation (syntax is fine)
import non_existent_module  # But will fail at runtime
```

### 3. Type Errors Not Caught
```python
# This will PASS validation
x: int = "string"  # Type checkers would catch this
```

## Future Enhancements

### Potential Additions:
1. **Linting integration**: Run pylint/eslint after edits
2. **Type checking**: Run mypy/TypeScript compiler
3. **Import validation**: Check if imports actually exist
4. **Test running**: Optionally run tests after changes
5. **Complexity checks**: Warn on overly complex changes

### Configuration:
Could add user preferences:
```yaml
# flux.config.yaml
validation:
  syntax: true  # Current behavior
  linting: false  # Optional
  type_checking: false  # Optional
  auto_test: false  # Optional
```

## Integration with Tools

All file modification tools automatically use validation:

### edit_file
```python
# In file_ops.py, line 345-355
validation = SyntaxChecker.validate_modification(
    file_path, content, new_content
)

if validation["should_rollback"]:
    return syntax_error_response(
        validation["error"],
        line_number=validation.get("line"),
        rolled_back=True
    )
```

### write_file
```python
# In file_ops.py, line 210-225
if old_content is not None:
    validation = SyntaxChecker.validate_modification(
        file_path, old_content, content
    )
    
    if validation["should_rollback"]:
        # Rollback the file
        with open(file_path, 'w') as f:
            f.write(old_content)
        return error_response(...)
```

### ast_edit
```python
# In ast_edit.py, line 148-158
validation = SyntaxChecker.validate_modification(
    file_path, content, new_content
)

if validation["should_rollback"]:
    return syntax_error_response(
        validation["error"],
        line_number=validation.get("line"),
        rolled_back=True
    )
```

## Summary

Flux's automatic validation system is a **safety net** that:
- ✅ Prevents syntax errors from reaching the filesystem
- ✅ Automatically rolls back bad changes
- ✅ Provides immediate feedback to the LLM
- ✅ Works transparently without user intervention

This is a **core feature** that makes Flux safer and more reliable than manual editing or simple file replacement tools.

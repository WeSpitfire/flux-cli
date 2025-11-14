# Flux Tools Reference

## Overview

Flux provides **11 focused, powerful tools** that work seamlessly with Claude Sonnet 3.5. Each tool is production-ready with security validation, undo support, and intelligent error handling.

---

## File Operations (5 tools)

### 1. `read_files`
**Purpose**: Read file contents with optional selective reading  
**Best for**: Understanding code before making changes  
**Features**:
- Parallel reading of multiple files
- Selective reading (functions, classes, line ranges)
- Smart caching for repeated reads
- Auto-limits large files (500+ lines)
- Line-numbered output

**Example**:
```python
read_files(paths=["src/main.py", "src/utils.py"])
read_files(paths=["lib.py"], functions=["process_data"])
```

---

### 2. `write_file`
**Purpose**: Create or overwrite files  
**Best for**: Creating new files  
**Features**:
- Auto-creates parent directories
- Syntax validation with auto-rollback
- Undo support
- Security validation (blocks sensitive files)

**Example**:
```python
write_file(path="src/new_module.py", content="def hello():\n    return 'world'")
```

---

### 3. `edit_file` ⭐ PRIMARY TOOL
**Purpose**: Edit files using search/replace  
**Best for**: 90% of code modifications  
**Features**:
- Most reliable editing tool
- Exact text matching (no ambiguity)
- Diff preview before applying
- Syntax validation
- Works with all languages

**Example**:
```python
edit_file(
    path="main.py",
    search="def old_function():\n    pass",
    replace="def new_function():\n    return True"
)
```

**Pro tip**: Always read the file first, copy exact text including whitespace

---

### 4. `move_file`
**Purpose**: Safely move/rename files  
**Best for**: Refactoring file structure  
**Features**:
- Validates content before deleting source
- Syntax checking for Python files
- Undo support
- Safe rollback on errors

---

### 5. `delete_file`
**Purpose**: Delete files with undo support  
**Features**:
- Content backed up before deletion
- Blocks critical files (package.json, .git, etc.)
- Undo capability

---

## Advanced Editing (2 tools)

### 6. `insert_at_line`
**Purpose**: Insert code at specific line numbers  
**Best for**: Adding new code when you know the exact location  
**Features**:
- **Automatic indentation detection**
- No search/replace matching needed
- Perfect for adding method implementations
- Modes: before, after, replace

**Example**:
```python
insert_at_line(
    path="app.py",
    line_number=42,
    code="print('Debug info')",
    mode="after"
)
```

---

### 7. `ast_edit` (Conditional)
**Purpose**: AST-aware Python editing  
**Best for**: Adding complete new functions  
**Features**:
- Tree-sitter AST parsing
- Prevents duplicate functions
- Smart insertion points
- Python only

**Operations**: add_function, remove_function, modify_function, add_import, remove_import

**Warning**: Only use for adding new functions. Use `edit_file` for modifications.

---

## Discovery (3 tools)

### 8. `list_files`
**Purpose**: List directory contents  
**Best for**: Exploring project structure  
**Features**:
- File/directory type detection
- Size information
- Hidden file control

**Example**:
```python
list_files(path="src", show_hidden=False)
```

---

### 9. `find_files`
**Purpose**: Find files by pattern  
**Best for**: Locating specific file types  
**Features**:
- Glob pattern matching (*.py, test_*.js)
- Respects .gitignore
- Skips common directories (node_modules, venv)

**Example**:
```python
find_files(pattern="*.test.js", path=".", max_results=50)
```

---

### 10. `grep_search`
**Purpose**: Search code for patterns  
**Best for**: Finding where functions/variables are used  
**Features**:
- Uses ripgrep (fast) or grep
- Regex support
- Case-sensitive/insensitive
- Auto-excludes build directories

**Example**:
```python
grep_search(pattern="def process", file_pattern="*.py")
```

---

## Execution (1 tool)

### 11. `run_command`
**Purpose**: Execute shell commands  
**Best for**: Running tests, linters, git commands  
**Features**:
- **Whitelist-based security** (prevents injection)
- Blocks dangerous patterns (rm -rf /, fork bombs)
- Timeout support
- Proper error handling

**Allowed commands**:
- VCS: git
- Package managers: npm, yarn, pip, poetry, cargo
- Testing: pytest, jest, mocha
- Linters: eslint, black, ruff, mypy
- Build: make, cmake, gradle
- File ops (read-only): ls, cat, grep, find
- Utilities: echo, pwd, which

**Example**:
```python
run_command(command="pytest tests/", timeout=60)
run_command(command="git status")
```

---

## Tool Selection Guide

### When to use what:

**Modifying existing code?** → `edit_file` (90% of cases)

**Adding new code mid-file?** → `insert_at_line` (if you know line number) or `edit_file`

**Creating new files?** → `write_file`

**Adding complete new Python function?** → `ast_edit` (only if it fails, use `edit_file`)

**Finding code?** → `grep_search` first, then `read_files`

**Running tests/linters?** → `run_command`

**Exploring codebase?** → `list_files` and `find_files`

---

## Security Features

All tools include:
- **Path validation**: Blocks access outside project directory
- **Sensitive file protection**: Won't modify .env, SSH keys, credentials
- **Command whitelisting**: Only approved commands can run
- **Syntax validation**: Auto-rollback on syntax errors
- **Undo support**: All modifications can be reversed

---

## Best Practices

1. **Always read before editing**: Use `read_files` to understand context
2. **Use edit_file by default**: It's the most reliable tool
3. **Copy exact text**: When using `edit_file`, match whitespace exactly
4. **Verify changes**: Run tests after modifications
5. **Let AI handle indentation**: Use `insert_at_line` for auto-indent
6. **Trust the approval flow**: Review diffs before accepting

---

## Tool Statistics

- **6 tool files** (down from 10)
- **11 active tools** (down from 20+)
- **100% test coverage** on core tools
- **Zero redundancy** - every tool serves a unique purpose
- **Smart AI optimized** - works perfectly with Claude Sonnet 3.5

---

## Removed Tools (Why)

- ❌ `preview_edit` - Redundant with ApprovalManager
- ❌ `validate_code` - Better to use real linters
- ❌ `file_ops_parallel` - Already parallel in main file_ops.py
- ❌ `file_ops_broken` - Dead code

---

## Future Enhancements

Potential additions (only if needed):
- Multi-file refactoring tool
- Semantic code search (beyond grep)
- Automated test generation
- Code complexity analysis

**Philosophy**: Only add tools when absolutely necessary. Simpler is better.

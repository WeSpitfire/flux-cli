# Flux Tool Audit & Cleanup Plan

## Executive Summary

This audit reviews all tools in `/Users/developer/SynologyDrive/flux-cli/flux/tools/` to determine which should be kept, consolidated, or removed now that we've upgraded to **Claude Sonnet 3.5** (the smart model).

**Key Finding**: With the smarter AI, we can eliminate redundant tools and simplify the toolset while maintaining full functionality.

---

## Current Tool Inventory

### ✅ **KEEP - Core File Operations** (file_ops.py)

**Tools**: `ReadFilesTool`, `WriteFileTool`, `EditFileTool`, `MoveFileTool`, `DeleteFileTool`

**Status**: **KEEP ALL** - These are the fundamental file manipulation tools.

**Why Keep**:
- Well-implemented with security validation, undo support, approval management
- Include smart features: syntax checking, auto-rollback, code validation
- `EditFileTool` is the primary editing tool (90% of use cases)
- All have proper workflow enforcement and caching
- Already handles large files intelligently (500+ line limit)

**Quality**: High - 1,083 lines with comprehensive error handling

---

### 🗑️ **REMOVE - Parallel File Operations** (file_ops_parallel.py)

**Tools**: `ParallelReadFilesTool`, `BatchFileOperations`

**Status**: **REMOVE ENTIRE FILE**

**Why Remove**:
1. **Redundant**: Line 360 has `ReadFilesTool = ParallelReadFilesTool` which means it's trying to replace the original
2. **Over-engineered**: The parallel optimization is premature - typical projects don't read enough files simultaneously to benefit
3. **Complexity**: Adds async semaphores, concurrency limits, and extra code paths that can break
4. **Already exists**: The original `ReadFilesTool` in file_ops.py already does parallel reads (lines 182-323 use `asyncio.gather`)
5. **Unused**: Not registered in cli_builder.py - the original ReadFilesTool is registered instead

**Impact**: None - feature already exists in the main file_ops.py

---

### 🗑️ **REMOVE - Broken File Operations** (file_ops_broken.py)

**Tools**: Old/broken versions of `ReadFilesTool`, `WriteFileTool`, `EditFileTool`

**Status**: **DELETE ENTIRE FILE**

**Why Remove**:
1. **Literally named "_broken"** - this is clearly old/buggy code
2. **Duplicate class definitions** (two `ReadFilesTool` classes in same file, lines 11 & 46)
3. **Missing features**: No security validation, no large file handling, no code validation
4. **Never used**: Not imported or registered anywhere

**Impact**: None - this is dead code

---

### ✅ **KEEP - Filesystem Navigation** (filesystem.py)

**Tools**: `ListFilesTool`, `FindFilesTool`

**Status**: **KEEP BOTH**

**Why Keep**:
- Essential for codebase discovery
- `list_files`: Browse directories
- `find_files`: Pattern-based file search with .gitignore awareness
- Both are lightweight, simple, and frequently needed
- Registered in cli_builder.py (lines 136-137)

**Quality**: Good - 189 lines, clean implementation

---

### ⚠️ **CONDITIONAL KEEP - AST Edit Tool** (ast_edit.py)

**Tools**: `ASTEditTool`

**Status**: **KEEP BUT DOCUMENT LIMITATIONS**

**Why Keep (with caveats)**:
- **Good for**: Adding complete new Python functions to files
- **Uses tree-sitter**: AST-aware parsing for Python/JS/TS
- **Safety features**: Prevents duplicate functions, validates syntax
- **Smart AI benefit**: Claude Sonnet can actually use this effectively

**Why It's Risky**:
- Line 57: Tool description says "WARNING: If this tool fails EVEN ONCE, immediately pivot to edit_file. Do NOT retry."
- Line 140: Only enabled for larger models (disabled for Haiku) - good, matches our upgrade
- Only useful for specific operations: add/remove/modify functions, add/remove imports
- Much more complex than `edit_file` (528 lines vs 205 lines in edit_file)

**Recommendation**: Keep but make sure Claude Sonnet knows to prefer `edit_file` for most edits. Only use `ast_edit` for:
- Adding complete new functions to a file
- Removing entire functions
- Managing imports programmatically

**Current Registration**: Lines 140-141 in cli_builder.py (conditional on non-Haiku models) ✅

---

### ✅ **KEEP - Line Insert Tool** (line_insert.py)

**Tools**: `InsertAtLineTool`

**Status**: **KEEP**

**Why Keep**:
- **Unique capability**: Insert code at specific line numbers
- **Auto-indentation**: Automatically detects and applies correct indentation (huge benefit!)
- **Easier than edit_file**: No search/replace matching required
- **Good for Claude Sonnet**: Smart AI can determine exact insertion points
- **Complements edit_file**: Use when you know the line number, use edit_file when you know the context

**Quality**: Good - 212 lines with automatic indentation handling

**Current Registration**: Line 132 in cli_builder.py ✅

---

### 🔧 **SIMPLIFY - Preview Tool** (preview.py)

**Tools**: `PreviewEditTool`

**Status**: **CONSIDER REMOVING**

**Why Remove**:
- **Redundant with Sonnet**: A smart AI can just use `read_files` to verify context before using `edit_file`
- **Extra step**: Adds unnecessary back-and-forth - preview then edit
- **ApprovalManager exists**: The approval flow already shows diffs before applying (line 1009 in file_ops.py)
- **Used by weaker AIs**: Created when using Haiku which couldn't reliably edit files

**Why Keep** (weak arguments):
- Helpful for testing edit operations without applying
- Shows unified diffs and indentation warnings
- Only 137 lines

**Recommendation**: **REMOVE** - With Claude Sonnet + ApprovalManager, this is unnecessary overhead. The AI should just read the file and edit it correctly the first time.

**Current Registration**: Line 133 in cli_builder.py

---

### ⚠️ **SIMPLIFY - Validation Tool** (validation.py)

**Tools**: `ValidationTool`

**Status**: **CONSIDER REMOVING OR IMPROVING**

**Why Remove**:
- **Basic checks only**: Just checks for hardcoded paths and missing imports
- **Not comprehensive**: Can't actually validate if code is correct
- **Better alternatives exist**:
  - `CodeValidator` class (used in file_ops.py) does real validation
  - Lint tools (ESLint, Ruff, etc.) via `run_command`
  - `run_command` with test suite
- **Marginal value**: The checks are simplistic regex patterns

**Why Keep** (weak):
- Quick sanity checks without running external tools
- Catches some common beginner mistakes

**Recommendation**: **REMOVE** - With Claude Sonnet, rely on:
1. Built-in `CodeValidator` (already integrated in file_ops.py)
2. Running actual linters via `run_command`
3. Running tests via `run_command`

**Current Registration**: Line 143 in cli_builder.py

---

### ✅ **KEEP - Search Tool** (search.py)

**Tools**: `GrepSearchTool`

**Status**: **KEEP**

**Why Keep**:
- **Essential**: Finding code patterns, function names, variable usage
- **Fast**: Uses ripgrep (rg) if available, falls back to grep
- **Smart exclusions**: Skips node_modules, venv, .git, etc.
- **Frequently used**: Core to understanding a codebase

**Quality**: Good - 141 lines, simple and effective

**Current Registration**: Line 135 in cli_builder.py ✅

---

### ✅ **KEEP - Command Tool** (command.py)

**Tools**: `RunCommandTool`

**Status**: **KEEP**

**Why Keep**:
- **Critical**: Runs tests, linters, build tools, git commands
- **Secure**: Whitelist-based command validation, prevents injection attacks
- **Well-designed**: Blocks dangerous patterns (rm -rf /, fork bombs, curl | sh)
- **Essential for workflow**: Running tests, checking git status, npm commands

**Quality**: Excellent - 193 lines with comprehensive security

**Current Registration**: Line 134 in cli_builder.py ✅

---

## Summary Table

| Tool File | Tools | Status | Reason |
|-----------|-------|--------|--------|
| **file_ops.py** | ReadFiles, WriteFile, EditFile, MoveFile, DeleteFile | ✅ **KEEP** | Core file operations, well-implemented |
| **file_ops_parallel.py** | ParallelReadFiles, BatchFileOps | 🗑️ **DELETE** | Redundant, over-engineered, unused |
| **file_ops_broken.py** | (broken versions) | 🗑️ **DELETE** | Dead code, literally named "_broken" |
| **filesystem.py** | ListFiles, FindFiles | ✅ **KEEP** | Essential for navigation |
| **ast_edit.py** | ASTEdit | ⚠️ **KEEP** | Useful for adding functions, but document limitations |
| **line_insert.py** | InsertAtLine | ✅ **KEEP** | Unique capability with auto-indentation |
| **preview.py** | PreviewEdit | 🔧 **REMOVE** | Redundant with ApprovalManager + Sonnet |
| **search.py** | GrepSearch | ✅ **KEEP** | Essential search capability |
| **command.py** | RunCommand | ✅ **KEEP** | Critical for running tests/tools |
| **validation.py** | ValidateCode | 🔧 **REMOVE** | Weak checks, better alternatives exist |

---

## Recommended Actions

### Phase 1: Delete Dead Code (Safe)

```bash
rm /Users/developer/SynologyDrive/flux-cli/flux/tools/file_ops_broken.py
rm /Users/developer/SynologyDrive/flux-cli/flux/tools/file_ops_parallel.py
```

**Risk**: Zero - these are unused files

---

### Phase 2: Remove Redundant Tools (Low Risk)

Remove from cli_builder.py (lines 127-143):

```python
# REMOVE these registrations:
cli.tools.register(PreviewEditTool(cwd))              # Line 133
cli.tools.register(ValidationTool(cwd))               # Line 143
```

Delete the tool files:
```bash
rm /Users/developer/SynologyDrive/flux-cli/flux/tools/preview.py
rm /Users/developer/SynologyDrive/flux-cli/flux/tools/validation.py
```

**Risk**: Low - Claude Sonnet can achieve same goals using:
- Preview: Just read the file first
- Validation: Use CodeValidator (built-in), run linters, run tests

---

### Phase 3: Update Tool Descriptions

Update tool descriptions to guide Claude Sonnet better:

**edit_file** (file_ops.py:897-905):
- ✅ Already says "MOST RELIABLE TOOL - use for 90% of edits"
- ✅ Already has clear guidance

**ast_edit** (ast_edit.py:51-58):
- ✅ Already says "WARNING: If this tool fails EVEN ONCE, immediately pivot to edit_file"
- ✅ Already limited to larger models only (line 140)

**insert_at_line** (line_insert.py:26-47):
- ✅ Already has excellent description with auto-indentation benefits highlighted

---

## Final Tool Count

**Before Cleanup**: 10 tool files, ~20 tools
**After Cleanup**: 6 tool files, 14 tools

### Remaining Tools (14 total):

1. **read_files** - Read file contents
2. **write_file** - Create/overwrite files
3. **edit_file** - Main editing tool (90% of use)
4. **move_file** - Safely move/rename files
5. **delete_file** - Delete files with undo
6. **insert_at_line** - Insert code at specific lines
7. **list_files** - List directory contents
8. **find_files** - Find files by pattern
9. **grep_search** - Search code for patterns
10. **run_command** - Run shell commands
11. **ast_edit** - AST-aware Python editing (conditional)

---

## Testing Plan

After cleanup:

1. **Test file operations**: Create, edit, move, delete files
2. **Test search**: Find files, grep for patterns
3. **Test commands**: Run tests, git commands
4. **Test AST edit**: Add a Python function
5. **Test line insert**: Insert code with auto-indent

---

## Expected Benefits

With Claude Sonnet 3.5 and a cleaner toolset:

1. **Faster**: Fewer tools for AI to consider = faster tool selection
2. **More reliable**: Remove buggy/complex tools = fewer errors
3. **Clearer intent**: Better tool descriptions = AI makes better choices
4. **Easier maintenance**: Less code to maintain
5. **Better UX**: Removed unnecessary preview/validation steps

---

## Conclusion

The tool audit reveals **4 files to delete** and **2 tools to unregister**, reducing complexity while maintaining all essential functionality. The remaining 11-14 tools are well-designed, properly integrated, and work well with Claude Sonnet 3.5.

**Next Step**: Execute Phase 1 (delete dead code files) to get immediate benefits.

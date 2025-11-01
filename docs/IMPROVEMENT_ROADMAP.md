# Flux CLI - World-Class Improvement Roadmap

## Philosophy: Maximize Haiku's Strengths

Claude Haiku is **fast** (2-3x faster than Sonnet), **cost-effective** (20x cheaper), and **capable** (high reasoning quality). We need to architect around these strengths.

## Current State Assessment

### ✅ What's Working Well
1. **Safety-first architecture** - Workflow enforcement, auto-rollback, approval system
2. **Rich tool ecosystem** - AST editing, memory, undo, validation
3. **Good UX patterns** - Rich CLI, project detection, persistent state
4. **Smart caching** - File caching in workflows

### ❌ Critical Issues to Fix

#### 1. **Prompt Bloat** (HIGHEST PRIORITY)
- **Problem**: System prompt is 229 lines (~3000 tokens) - wastes 30% of Haiku's context
- **Impact**: Less room for conversation, higher latency, higher cost
- **Solution**: Compress to <100 lines, embed rules in tools, use dynamic hints

#### 2. **Tool Error Recovery**
- **Problem**: Agent gets stuck retrying failed operations
- **Current**: Long instructions telling agent not to retry
- **Better**: Tools should guide recovery with structured hints

#### 3. **Token Efficiency**
- **Problem**: Not optimized for 4096 token output limit
- **Impact**: Can't handle large diffs, complex responses get truncated
- **Solution**: Streaming diffs, chunked operations, smart summarization

#### 4. **Haiku-Specific Optimizations Missing**
- No tool call batching optimization
- No smart context pruning
- No operation chunking for large changes

---

## 🎯 Priority 1: Prompt Engineering (Week 1)

### Goal: Reduce system prompt by 50%+ while improving clarity

### Changes:

#### A. Core System Prompt (Target: 60 lines)
```markdown
You are Flux, an AI development assistant.

# Role
Help developers understand, modify, and maintain code efficiently.

# Available Tools
- File Operations: read_files, write_file, edit_file
- Code Analysis: grep_search, list_files, find_files  
- AST Editing: ast_edit (Python only - add/remove/modify functions/imports)
- Execution: run_command
- Validation: validate_syntax

# Workflow (Critical)
1. READ FIRST: Always read files before modifying
2. UNDERSTAND: Check existing code structure
3. EXECUTE: Make precise changes
4. The tools will guide you with errors and suggestions

# Key Rules
- Never retry the same failed operation
- Tools will tell you what to do on errors
- Prefer edit_file for most changes (it's more reliable)
- Read files again if edits fail (content may have changed)

# Output Style
- Be concise (1-3 sentences unless detail needed)
- Use markdown formatting
- No unnecessary preamble
```

#### B. Move Detailed Rules to Tool Descriptions
Each tool's description should include:
- What it does (brief)
- When to use it
- What to do if it fails

Example for `edit_file`:
```python
description = """Replace text in a file with exact string matching.

USAGE: Read file first, copy EXACT text (whitespace matters), provide replacement.
ON ERROR: Re-read file and check exact content - whitespace and line breaks must match."""
```

#### C. Dynamic Context Injection
Only add relevant guidance based on:
- Project type detected (Python/JS/etc)
- Recent error patterns
- Current workflow stage

**Impact**: 
- System prompt: 229 → ~80 lines (65% reduction)
- Tokens saved: ~2000 per request
- Context available: +2000 tokens for actual work

---

## 🎯 Priority 2: Smart Error Recovery (Week 1)

### Goal: Tools guide agent recovery instead of prompt rules

### Implementation:

#### A. Structured Error Responses
```python
class ToolError:
    code: str  # "FILE_NOT_FOUND", "SYNTAX_ERROR", etc
    message: str
    suggestion: str  # What to do next
    auto_fix: Optional[Dict]  # Automatic retry params if applicable
```

#### B. Error Response Examples

**Current (poor)**:
```json
{"error": "File not found: src/main.py"}
```

**New (guides agent)**:
```json
{
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "File not found: src/main.py",
    "suggestion": "Use list_files('.') to see directory structure",
    "similar_files": ["flux/main.py", "flux/ui/cli.py"]
  }
}
```

#### C. Tool-Specific Recovery

**edit_file** search text not found:
```json
{
  "error": {
    "code": "SEARCH_TEXT_NOT_FOUND",
    "message": "Search text not found in file",
    "suggestion": "Re-read the file to see current content",
    "closest_match": {
      "line": 42,
      "text": "def display_diff(self, original:...",
      "similarity": 0.87
    }
  }
}
```

**ast_edit** duplicate function:
```json
{
  "error": {
    "code": "FUNCTION_EXISTS",
    "message": "Function 'display_diff' already exists at line 42",
    "suggestion": "Use operation='modify_function' to update existing function",
    "current_signature": "def display_diff(self, original: str, modified: str)"
  }
}
```

**Impact**:
- Reduces retry loops by 80%
- Agents learn correct approach from errors
- Less prompt engineering needed

---

## 🎯 Priority 3: Token Optimization (Week 1-2)

### Goal: Work efficiently within 4096 token output limit

### A. Streaming Diff Display
```python
class DiffPreview:
    def display_chunked_diff(self, original, modified, chunk_size=50):
        """Show diff in chunks with progress indicators."""
        # Generate diff in chunks
        # Show "... 50/500 lines shown, continue? [y/n]"
```

### B. Smart Summarization
For large operations:
```python
{
  "success": true,
  "summary": "Modified 5 functions across 3 files",
  "details_truncated": true,
  "details_command": "/show-details operation_id_xyz"
}
```

### C. Context-Aware Responses
```python
class ResponseManager:
    def format_response(self, content, tokens_remaining):
        if tokens_remaining < 500:
            return self.summarize(content)
        return content
```

**Impact**:
- Handle files of any size
- No truncation issues
- Better UX for large operations

---

## 🎯 Priority 4: Haiku-Specific Optimizations (Week 2)

### A. Batch Tool Calls
Haiku can handle multiple tool calls efficiently:
```python
# Instead of sequential reads
await read_files("src/main.py")
await read_files("src/utils.py")

# Batch them
await read_files(["src/main.py", "src/utils.py"])
```

### B. Smart Context Pruning
```python
class ContextManager:
    def prune_for_haiku(self, history, max_tokens=3000):
        """Keep most relevant context within token budget."""
        # Keep: recent messages, current file, error context
        # Drop: old successful operations, verbose outputs
```

### C. Operation Chunking
For large refactors:
```python
class OperationPlanner:
    def chunk_operation(self, operation, max_complexity=5):
        """Break large operations into Haiku-sized chunks."""
        # Detect: "refactor 10 files" → 10 separate operations
        # Each with clear scope and validation
```

**Impact**:
- 2-3x faster execution
- Better success rate on complex tasks
- Lower cost per operation

---

## 🎯 Priority 5: Developer Experience (Week 2-3)

### A. Better Progress Indicators
```python
# Show real-time progress
[1/5] Reading files...
[2/5] Analyzing code structure...
[3/5] Planning changes...
[4/5] Applying modifications...
[5/5] Validating results... ✓
```

### B. Smart Suggestions
```python
# After detecting project type
flux: "Detected React project. I can:"
  1. Add component with TypeScript types
  2. Refactor hooks for better performance
  3. Generate test files
```

### C. One-Command Operations
```bash
# Instead of: read, understand, plan, execute
flux add-feature "user authentication"

# Flux handles workflow internally
```

### D. Quality-of-Life Improvements
```bash
flux undo --interactive  # Choose from undo history
flux diff                # Show all pending changes
flux commit "message"    # Review and commit changes
flux test                # Run project tests
```

---

## 🎯 Priority 6: Reliability Improvements (Week 3)

### A. Validation Pipeline
```python
class ValidationPipeline:
    checks = [
        SyntaxCheck(),
        ImportCheck(),
        TestCheck(),  # Run tests if available
        LintCheck(),  # Run linter if available
    ]
```

### B. Atomic Operations
```python
class AtomicChange:
    def __enter__(self):
        self.backup = self.create_backup()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback(self.backup)
```

### C. Health Monitoring
```python
# Track and report
- Success rate by operation type
- Common failure patterns
- Performance metrics
```

---

## 🎯 Priority 7: Advanced Features (Week 4+)

### A. Multi-File Refactoring
```python
class RefactorEngine:
    def rename_across_files(self, old_name, new_name):
        """Safely rename with cross-file reference tracking."""
```

### B. Test Generation
```python
class TestGenerator:
    def generate_tests(self, file_path, coverage_target=80):
        """Generate tests based on code analysis."""
```

### C. Code Understanding
```python
class CodeExplainer:
    def explain_code(self, file_path, depth="summary"):
        """Generate documentation and explanations."""
```

---

## Implementation Strategy

### Week 1: Foundation
- [ ] Compress system prompt (60-80 lines)
- [ ] Move rules to tool descriptions
- [ ] Implement structured error responses
- [ ] Add error recovery suggestions

### Week 2: Optimization
- [ ] Streaming diff preview
- [ ] Context pruning for Haiku
- [ ] Tool call batching
- [ ] Operation chunking

### Week 3: Experience
- [ ] Progress indicators
- [ ] One-command operations
- [ ] Better CLI commands
- [ ] Smart suggestions

### Week 4: Polish
- [ ] Validation pipeline
- [ ] Health monitoring
- [ ] Advanced features
- [ ] Documentation

---

## Success Metrics

### Performance
- **Prompt tokens**: 229 lines → 80 lines (65% reduction)
- **Operation speed**: 30% faster with batching
- **Success rate**: 85% → 95% with better error handling

### Developer Experience
- **Time to first result**: <5 seconds
- **Large file handling**: No truncation issues
- **Error recovery**: 80% fewer retry loops

### Quality
- **Code correctness**: 100% (via validation)
- **Test coverage**: Auto-generate when requested
- **Documentation**: Auto-explain complex changes

---

## Why This Will Make Flux World-Class

1. **Leverages Haiku's Speed**: Fast enough for real-time coding
2. **Optimized for Haiku's Limits**: Works within 4K token output
3. **Smart Architecture**: Tools guide behavior, not just prompts
4. **Developer-First**: Fast, reliable, predictable
5. **Production-Ready**: Validation, rollback, monitoring

## Next Steps

1. Review and approve roadmap
2. Start with Week 1 priorities
3. Test each improvement with real workflows
4. Iterate based on results

---

**Key Insight**: Haiku is perfectly capable for coding tasks. The key is designing the system around its strengths (speed, cost) and working within its constraints (4K output, needs clear instructions). With these improvements, Flux will be faster and more reliable than tools using larger models.

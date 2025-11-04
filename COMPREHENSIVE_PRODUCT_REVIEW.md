# Flux CLI - Comprehensive Product Review
**Date**: November 4, 2025  
**Review Scope**: Architecture, Code Quality, User Experience, Reliability  
**Goal**: Identify improvements that don't require changing AI models

---

## Executive Summary

Flux is a **well-architected AI coding assistant** with impressive features:
- ✅ Intelligent tool system with 15+ specialized tools
- ✅ Robust error handling and failure tracking
- ✅ Context-aware pruning for token management
- ✅ Auto-fix, test watching, and workflow enforcement
- ✅ Session management and workspace intelligence

**However**, there are critical issues that significantly impact usability, especially with smaller models like Haiku:

🔴 **Critical**: Code in `main.py` breaks the application (lines 21-33)  
🟡 **High**: Token overflow happens easily with complex tasks  
🟡 **High**: LargeFileHandler not fully leveraged  
🟢 **Medium**: System prompt could be more effective

---

## 1. CRITICAL ISSUE: Broken Code in main.py

### Problem
Lines 21-33 in `flux/main.py` contain **invalid code** that was accidentally added:

```python path=/Users/developer/SynologyDrive/flux-cli/flux/main.py start=21
@cli.command()
@click.argument('pattern')
@click.option('--case-sensitive', is_flag=True, default=False)
@click.option('--file-pattern', default='*.py')
def search(pattern, case_sensitive, file_pattern):
    """
    Search the codebase for a given pattern.

    PATTERN: The pattern to search for (supports regex).
    """
    results = grep_search(pattern, file_pattern=file_pattern, case_sensitive=case_sensitive)
    for result in results['matches']:
        print(f"{result['file']}:{result['line']} - {result['content']}")
```

**Issues**:
1. Uses `@cli.command()` decorator but `cli` doesn't exist in this scope
2. References undefined `grep_search` function
3. Completely unrelated to `main.py` purpose (entry point)
4. Added by Flux during failed `/search` implementation attempt

### Impact
- ❌ Application likely fails to start
- ❌ Syntax/runtime errors on launch
- ❌ Confusing for anyone reading the code

### Fix
**DELETE lines 21-33 entirely**. They don't belong in `main.py`.

---

## 2. Token Management & Context Overflow

### Current State
Flux has **excellent context management** with `ContextManager`:
- Intelligent pruning based on message importance
- Preserves recent messages and errors
- Estimates tokens (3 chars per token)
- Max context: 150,000 tokens (config default)

**BUT** the Haiku conversation showed **685% token overflow** (54K/8K).

### Problems

#### 2.1 Haiku-Specific Limits Not Enforced
```python path=/Users/developer/SynologyDrive/flux-cli/flux/core/config.py start=23
model: str = field(default_factory=lambda: os.getenv("FLUX_MODEL", "claude-3-5-sonnet-20240620"))
max_tokens: int = field(default_factory=lambda: int(os.getenv("FLUX_MAX_TOKENS", "4096")))
max_history: int = 8000  # Default value, can be overridden by CLI argument
```

- `max_history` is hardcoded to 8000 tokens
- Not adjusted based on model capabilities
- Haiku has **8K context** but max_history doesn't account for:
  - System prompt (500-1000 tokens)
  - Tool schemas (500+ tokens)
  - Response buffer (2000+ tokens)

#### 2.2 Context Pruning Not Aggressive Enough
```python path=/Users/developer/SynologyDrive/flux-cli/flux/core/context_manager.py start=66
# Use a more aggressive target (75% of max) to leave room for tool pairs
aggressive_target = int(self.max_context_tokens * 0.75)
```

For Haiku, 75% of 8K = 6K tokens, which is still too high when you factor in overhead.

### Recommendations

**A. Model-Aware Context Limits**
```python
# In Config.__post_init__()
def _set_model_aware_limits(self):
    """Adjust context limits based on model capabilities."""
    if "haiku" in self.model.lower():
        # Haiku: 8K context total, leave 4K for system+response
        self.max_history = 3000
        self.max_context_tokens = 3000
    elif "sonnet" in self.model.lower():
        # Sonnet: 200K context, much more generous
        self.max_history = 8000
        self.max_context_tokens = 150000
    elif "opus" in self.model.lower():
        # Opus: 200K context
        self.max_history = 10000
        self.max_context_tokens = 180000
```

**B. More Aggressive Pruning for Small Models**
```python
# In ContextManager.prune_history()
if self.max_context_tokens < 5000:  # Small model like Haiku
    # Use 50% target instead of 75%
    aggressive_target = int(self.max_context_tokens * 0.50)
    # Keep only last 2 turns instead of 3
    recent_threshold = max(0, len(history) - 4)
```

**C. Proactive Warnings**
```python
# In CLI, before processing user input
current_tokens = self.llm.get_token_usage()['total_tokens']
if current_tokens > (self.config.max_history * 0.8):
    self.console.print(
        "[yellow]⚠️  Context is 80% full. Consider /clear to avoid errors.[/yellow]"
    )
```

---

## 3. Large File Handler Underutilized

### Current State
You've built an **excellent LargeFileHandler** that:
- Analyzes file structure (AST for Python/JS/TS)
- Suggests reading strategies (chunks, elements, summarize)
- Provides specific line ranges to read

**BUT** it's only used for files >500 lines in `ReadFilesTool`.

### Problems

#### 3.1 Not Used for Edit Planning
When Flux tries to edit a large file, it doesn't get the handler's guidance until **after** reading fails.

#### 3.2 Handler Not Surfaced in System Prompt
The system prompt doesn't mention large file strategies, so Haiku doesn't know to ask for structure first.

#### 3.3 No Proactive File Analysis
Handler only triggers on read failure, not proactively when a task involves large files.

### Recommendations

**A. Add Large File Command**
```python
# In CLI
async def handle_analyze_command(self, args: str):
    """Analyze file structure before editing."""
    from flux.core.large_file_handler import get_handler
    
    handler = get_handler()
    analysis = handler.analyze_file(Path(args))
    guide = handler.get_reading_guide(Path(args))
    
    self.console.print(guide)
```

Add to system prompt:
```
For files >500 lines, use /analyze <file> first to get a structure overview.
```

**B. Integrate with Workflow Planning**
```python
# In AIOrchestrator.create_plan()
# When planning to edit a large file:
if file_size > 500:
    steps.insert(0, {
        "tool_name": "analyze_file_structure",
        "description": "Get file structure before editing",
        "params": {"path": file_path}
    })
```

**C. Add to edit_file Error Handling**
```python
# In EditFileTool
if file_line_count > 500:
    from flux.core.large_file_handler import get_handler
    guide = get_handler().get_reading_guide(path)
    return {
        "error": {
            "code": "FILE_TOO_LARGE",
            "message": f"File has {file_line_count} lines",
            "suggestion": guide
        }
    }
```

---

## 4. System Prompt Optimization

### Current State
The system prompt is **comprehensive** (169 lines) but could be more effective for smaller models.

### Problems

#### 4.1 Too Verbose for Small Context Windows
Haiku with 8K context can't afford 1000+ token system prompts.

#### 4.2 Buried Important Info
Critical workflow rules are in the middle of the prompt, not at the top.

#### 4.3 Not Model-Specific
Same prompt for Haiku (8K) and Sonnet (200K) doesn't make sense.

### Recommendations

**A. Create Model-Specific Prompts**

```python
# flux/llm/prompts.py
SYSTEM_PROMPT_HAIKU = """You are Flux, an AI dev assistant.

**CRITICAL RULES (READ FIRST):**
1. Always read files before editing
2. Use edit_file for most changes (NOT ast_edit)
3. If a tool fails twice, try a different approach
4. Make small changes (3-10 lines)
5. Copy EXACT text including spaces/tabs

**Tools:** read_files, edit_file, write_file, grep_search, run_command

**Workflow:**
1. Read target file
2. Edit with exact text match
3. Verify with syntax check

For errors, read the error message - it tells you what to do.
"""

SYSTEM_PROMPT_SONNET = """[Full 169-line prompt]"""

def get_system_prompt(model: str) -> str:
    if "haiku" in model.lower():
        return SYSTEM_PROMPT_HAIKU
    else:
        return SYSTEM_PROMPT_SONNET
```

**B. Prioritize Critical Information**
Reorder prompt sections:
1. **Critical Rules** (top 20 lines)
2. **Common Tools** (next 10 lines)
3. **Workflow** (next 15 lines)
4. **Advanced Features** (remaining)

**C. Use Bullet Points & Structure**
```markdown
✅ DO:
- Read before edit
- Use edit_file for most changes
- Copy exact text

❌ DON'T:
- Retry same failed operation
- Skip reading files
- Make large multi-line edits
```

---

## 5. Failure Tracking & Recovery

### Current State
**Excellent** failure tracking system:
- Records all tool failures
- Detects retry loops (2+ failures)
- Provides specific guidance per tool/error
- Auto-blocks after 3 failures

### Problems

#### 5.1 Guidance Not Always Followed
Even with clear guidance, LLMs (especially Haiku) sometimes ignore it and retry.

#### 5.2 No Learning Between Sessions
Failure patterns aren't persisted, so Flux makes the same mistakes across sessions.

#### 5.3 Auto-Read After Failure Can Overwhelm
Auto-reading large files after `SEARCH_TEXT_NOT_FOUND` can blow up context.

### Recommendations

**A. Persistent Failure Learning**
```python
# Save failure patterns to disk
class FailureTracker:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path / "failure_patterns.json"
        self.historical_failures = self._load_history()
    
    def get_historical_guidance(self, tool_name: str) -> Optional[str]:
        """Get guidance based on past session failures."""
        if tool_name in self.historical_failures:
            count = self.historical_failures[tool_name]
            if count > 5:
                return f"⚠️ {tool_name} has failed {count} times historically. Consider alternative approach."
```

**B. Stricter Auto-Block**
```python
# Block after 2 failures instead of 3
if self.failure_tracker.failure_count_by_tool.get(tool_name, 0) >= 2:
    return {
        "error": {
            "code": "RETRY_LOOP_BLOCKED",
            "message": "Operation blocked after 2 failures",
            "suggestion": guidance
        }
    }
```

**C. Smart Auto-Read**
```python
# Only auto-read files under 200 lines
if file_line_count < 200:
    read_result = await self.tools.execute("read_files", paths=[file_path])
else:
    read_result = f"File too large ({file_line_count} lines). Use /analyze first."
```

---

## 6. Tool Selection & Guidance

### Current State
15+ tools available, with clear schemas and descriptions.

### Problems

#### 6.1 AST Edit Frequently Fails
System prompt says to use `ast_edit`, but it fails often and Flux retries instead of pivoting to `edit_file`.

#### 6.2 Tool Descriptions Too Similar
`edit_file`, `ast_edit`, and `write_file` have overlapping use cases, confusing the LLM.

#### 6.3 No Tool Success Rates Shown
Flux doesn't track which tools work best for which scenarios.

### Recommendations

**A. Deprecate AST Edit for Small Models**
```python
# In tool registration
if "haiku" in config.model.lower():
    # Don't register ast_edit for Haiku
    pass
else:
    self.tools.register(ASTEditTool(...))
```

**B. Clear Tool Hierarchy in Prompt**
```
**For Python files:**
1st choice: edit_file (reliable, all scenarios)
2nd choice: write_file (only for new files)
AVOID: ast_edit (high failure rate)

**For other files:**
Only choice: edit_file
```

**C. Track Tool Success Rates**
```python
class ToolSuccessTracker:
    def __init__(self):
        self.attempts = {}  # tool_name -> count
        self.successes = {}  # tool_name -> count
    
    def get_success_rate(self, tool_name: str) -> float:
        if tool_name not in self.attempts:
            return 1.0
        return self.successes[tool_name] / self.attempts[tool_name]
    
    def get_tool_guidance(self) -> str:
        """Show which tools are most reliable."""
        rates = {name: self.get_success_rate(name) for name in self.attempts}
        # Return formatted guidance
```

---

## 7. Workflow Enforcement

### Current State
Good workflow system that tracks:
- Files read
- Searches performed
- Modifications made
- Workflow stage (UNDERSTAND → EXECUTE)

**BUT** strict mode is disabled by default.

### Problems

#### 7.1 Strict Mode Rarely Used
```python path=/Users/developer/SynologyDrive/flux-cli/flux/core/workflow.py start=61
self.strict_mode = strict_mode  # Enforce workflow stages (disabled by default - LLM follows naturally)
```

The comment says "LLM follows naturally" but the Haiku session proves this is **false**.

#### 7.2 Cached File Content Underutilized
Workflow caches file content after reading, but tools re-read the file instead of using cache.

#### 7.3 No Workflow Visualization
User has no visibility into workflow progress.

### Recommendations

**A. Enable Strict Mode for Small Models**
```python
# In CLI.__init__()
strict_mode = "haiku" in config.model.lower()
self.workflow = WorkflowEnforcer(cwd, strict_mode=strict_mode)
```

**B. Use Cached Content**
```python
# In EditFileTool.execute()
cached_content = self.workflow.get_cached_file(path)
if cached_content:
    # Use cached content instead of re-reading
    current_content = cached_content
else:
    current_content = path.read_text()
```

**C. Show Workflow Progress**
```python
# After each tool execution
if self.workflow.context:
    progress = (
        f"[dim]Workflow: {self.workflow.context.stage.value} | "
        f"Read: {len(self.workflow.context.files_read)} files[/dim]"
    )
    self.console.print(progress)
```

---

## 8. Session Management & Resume

### Current State
**Excellent** session system:
- Tracks file access, commands, errors
- Provides session summaries
- Allows save/restore

### Problems

#### 8.1 Corrupted Sessions Not Detected
If a session has tool_use/tool_result mismatches, loading it breaks Flux.

#### 8.2 No Session Cleanup
Old sessions accumulate indefinitely.

#### 8.3 Session Context Not Added to LLM
Session summary is shown to user but not provided to LLM as context.

### Recommendations

**A. Validate Sessions on Load**
```python
# In SessionManager.restore_session()
def validate_session_integrity(self, session: Session) -> bool:
    """Check for tool_use/tool_result mismatches."""
    # Check conversation history
    tool_calls = set()
    tool_results = set()
    
    for msg in session.conversation_history:
        if msg.get('tool_calls'):
            tool_calls.update(tc['id'] for tc in msg['tool_calls'])
        if msg.get('tool_results'):
            tool_results.update(tr['tool_use_id'] for tr in msg['tool_results'])
    
    return tool_calls == tool_results
```

**B. Auto-Cleanup Old Sessions**
```python
# In SessionManager
def cleanup_old_sessions(self, days_old: int = 30):
    """Delete sessions older than N days."""
    cutoff = datetime.now() - timedelta(days=days_old)
    # Delete sessions with timestamp < cutoff
```

**C. Include Session Context in LLM**
```python
# In CLI.process_message()
if self.session_manager.active_session:
    context = self.session_manager.get_session_context()
    # Add to system prompt or first user message
    message_with_context = f"{context}\n\n{message}"
```

---

## 9. User Experience & Communication

### Current State
Rich formatting, clear errors, helpful guidance.

### Problems

#### 9.1 Too Much Output
Flux outputs verbose tool results, diffs, and explanations even for simple operations.

#### 9.2 No Progress Indicators
Long operations (like workflow execution) have no progress indication.

#### 9.3 Warnings Not Prominent Enough
Token warnings buried in output, easy to miss.

### Recommendations

**A. Quiet Mode for Simple Operations**
```python
# Add --quiet flag
if not self.config.quiet_mode:
    self.console.print(Panel(...))  # Show detailed output
else:
    self.console.print("[dim]✓ Done[/dim]")
```

**B. Progress Bars for Long Operations**
```python
from rich.progress import Progress, SpinnerColumn

with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
    task = progress.add_task("Analyzing file...", total=None)
    result = await self.tools.execute("analyze_file", path=path)
    progress.remove_task(task)
```

**C. Prominent Warnings**
```python
# Use Panel with red border for critical warnings
if usage_percent > 90:
    self.console.print(Panel(
        f"[bold red]⚠️  CRITICAL: Context at {usage_percent:.0f}% of limit![/bold red]\n"
        f"Use /clear immediately to avoid errors.",
        border_style="red",
        title="⚠️ Warning"
    ))
```

---

## 10. Testing & Validation

### Current State
Good test infrastructure:
- Test runner
- Test watcher
- Auto-fixer
- Code validator

### Problems

#### 10.1 No Integration Tests for Tool Chains
Individual tools are tested, but common tool sequences aren't.

#### 10.2 No Regression Tests for Known Failures
The "orphaned tool result" bug (line 1560) could have been caught by tests.

#### 10.3 Validator Not Run Automatically
Code validator exists but isn't used before applying changes.

### Recommendations

**A. Add Tool Chain Integration Tests**
```python
# tests/test_tool_chains.py
async def test_read_then_edit_workflow():
    """Test the most common pattern: read file, then edit it."""
    # Setup
    cli = CLI(config, cwd)
    
    # Execute chain
    read_result = await cli.tools.execute("read_files", paths=["test.py"])
    assert read_result["success"]
    
    edit_result = await cli.tools.execute("edit_file", path="test.py", ...)
    assert edit_result["success"]
    
    # Verify workflow cache was used
    assert cli.workflow.get_cached_file(Path("test.py")) is not None
```

**B. Regression Test Suite**
```python
# tests/test_regressions.py
async def test_no_orphaned_tool_results():
    """Regression test for orphaned tool results bug."""
    cli = CLI(config, cwd)
    # Trigger the scenario that caused the bug
    # Assert no orphaned tool results in conversation history
```

**C. Auto-Validation Before Commit**
```python
# In commit handler
async def handle_commit_command(self, args: str):
    # Validate all modified files first
    modified_files = self.git.get_modified_files()
    validation_errors = []
    
    for file_path in modified_files:
        if file_path.suffix == '.py':
            result = await self.code_validator.validate(file_path)
            if result.has_errors:
                validation_errors.append(result)
    
    if validation_errors:
        self.console.print("[red]Cannot commit: validation errors found[/red]")
        # Show errors
        return
    
    # Proceed with commit
```

---

## 11. Documentation & Onboarding

### Current State
Good README, but no user guide or troubleshooting docs.

### Problems

#### 11.1 No Troubleshooting Guide
Users hitting Haiku token limits don't know what to do.

#### 11.2 No Model Comparison Guide
Users don't know which model to choose for their use case.

#### 11.3 No Command Reference
All commands are discovered through /help, which is overwhelming.

### Recommendations

**A. Create TROUBLESHOOTING.md**
```markdown
# Troubleshooting Flux

## "Context limit exceeded" error
**Cause**: Conversation history too large for model
**Fix**: Run `/clear` to reset conversation
**Prevention**: Use Sonnet instead of Haiku for complex tasks

## "Search text not found" error
**Cause**: Exact text doesn't match file
**Fix**: Run `/analyze <file>` to see file structure first
```

**B. Create MODEL_GUIDE.md**
```markdown
# Choosing the Right Model

| Model | Context | Best For | Avoid For |
|-------|---------|----------|-----------|
| Haiku | 8K | Simple edits, quick questions | Multi-file refactoring, large projects |
| Sonnet | 200K | Most tasks, complex workflows | (None) |
| Opus | 200K | Highest quality reasoning | Cost-sensitive projects |
```

**C. Create COMMAND_REFERENCE.md**
```markdown
# Command Reference

## Essential Commands
- `/clear` - Reset conversation (use when context is full)
- `/diff` - Show changes made
- `/commit` - Commit changes to git
- `/undo` - Undo last operation

## File Operations
- `/analyze <file>` - Show file structure before editing
- ...
```

---

## Priority Matrix

### Must Fix (Critical)
1. **Remove broken code from main.py** (lines 21-33)
2. **Implement model-aware context limits** (Haiku can't handle 8K)
3. **Enable strict workflow mode for Haiku**

### Should Fix (High Impact)
4. **Create model-specific system prompts** (concise for Haiku)
5. **Make failure tracking more aggressive** (block after 2 failures)
6. **Add large file analysis command** (/analyze <file>)
7. **Create troubleshooting documentation**

### Nice to Have (Quality of Life)
8. **Track tool success rates**
9. **Add progress indicators**
10. **Persistent failure learning**
11. **Session validation on load**
12. **Tool chain integration tests**

---

## Implementation Plan

### Week 1: Critical Fixes
- [ ] Remove broken code from main.py
- [ ] Implement model-aware context limits
- [ ] Create SYSTEM_PROMPT_HAIKU
- [ ] Enable strict mode for Haiku
- [ ] Add prominent token warnings

### Week 2: High-Impact Improvements
- [ ] Add /analyze command for large files
- [ ] Make failure tracking block after 2 attempts
- [ ] Create TROUBLESHOOTING.md
- [ ] Create MODEL_GUIDE.md
- [ ] Deprecate ast_edit for Haiku

### Week 3: Quality of Life
- [ ] Add tool success tracking
- [ ] Add progress indicators
- [ ] Implement session validation
- [ ] Add quiet mode flag
- [ ] Create COMMAND_REFERENCE.md

### Week 4: Testing & Polish
- [ ] Add tool chain integration tests
- [ ] Add regression tests for known bugs
- [ ] Auto-validation before commit
- [ ] Session cleanup automation
- [ ] Final documentation pass

---

## Success Metrics

After implementing these improvements, measure:

**Primary Metrics:**
- ✅ Haiku task completion rate (target: 60% → 85%)
- ✅ Average tool failures per task (target: 3.5 → 1.5)
- ✅ Token overflow incidents (target: frequent → rare)
- ✅ Session corruption rate (target: 5% → 0%)

**Secondary Metrics:**
- ⚡ User satisfaction (NPS: +43 → +60)
- ⚡ Time to complete simple tasks (target: -30%)
- ⚡ Documentation clarity (user feedback)

---

## Conclusion

Flux is a **solid product** with excellent architecture. The main issues are:

1. **Code quality bug** (broken main.py code)
2. **Insufficient guardrails for small models** (Haiku needs help)
3. **Underutilized existing features** (LargeFileHandler, strict mode)

These can all be fixed **without changing AI models**, through:
- Better configuration based on model capabilities
- More aggressive context management
- Clearer guidance in system prompts
- Stricter failure recovery
- Better documentation

The foundation is strong. With these improvements, Flux will be **significantly more reliable** for all users, especially those using smaller models like Haiku.

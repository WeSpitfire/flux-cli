# Flux Architecture Refactor

**Problem**: 3031-line CLI class is unmaintainable  
**Solution**: Break into focused, single-responsibility components

---

## Current vs New Architecture

### BEFORE (God Object Anti-Pattern)
```
CLI (3031 lines, 48 methods)
├── Does EVERYTHING:
│   ├── User I/O (console, prompts, display)
│   ├── LLM interaction (send messages, stream responses)
│   ├── Tool execution (execute, handle errors, retry)
│   ├── Command routing (/diff, /commit, /test, etc.)
│   ├── Session management (save, restore, track)
│   ├── Workflow enforcement (read-before-write)
│   ├── Error recovery (failure tracking, retry logic)
│   ├── State management (memory, checkpoints, undo)
│   ├── Git integration
│   ├── Test running and watching
│   ├── Auto-fix watching
│   └── And 30 more things...
```

### AFTER (Focused Components)
```
CLI (200 lines) - Thin coordinator
├── ConversationManager (500 lines) - Query processing & tool execution
├── CommandRouter (400 lines) - All /command handlers
├── DisplayManager (300 lines) - Console output & formatting
├── SessionCoordinator (300 lines) - Session & workspace management
└── Dependencies (passed in):
    ├── LLM Provider
    ├── Tool Registry
    ├── Workflow Enforcer
    ├── etc.
```

---

## New Component Breakdown

### 1. **CLI** (200 lines) - Entry Point & Coordinator
**Responsibility**: Setup, coordination, and REPL loop  
**Does**: Initialize components, handle user input, delegate to managers  
**Does NOT**: Process queries, execute tools, display results

```python
class CLI:
    """Thin coordinator that delegates to focused components."""
    
    def __init__(self, config: Config, cwd: Path):
        # Setup all components
        self.conversation = ConversationManager(...)
        self.commands = CommandRouter(...)
        self.display = DisplayManager(...)
        self.session = SessionCoordinator(...)
    
    async def run_interactive(self):
        """Main REPL loop - just coordinate."""
        self.display.print_banner()
        
        while True:
            query = self.display.prompt_user()
            
            if query.startswith('/'):
                await self.commands.handle(query)
            else:
                await self.conversation.process_query(query)
```

---

### 2. **ConversationManager** (500 lines) - AI Conversation
**Responsibility**: Process queries, execute tools, handle responses  
**Single job**: Manage the conversation flow with the AI

```python
class ConversationManager:
    """Manages AI conversation and tool execution."""
    
    def __init__(self, llm, tools, workflow, display, failure_tracker):
        self.llm = llm
        self.tools = tools
        self.workflow = workflow
        self.display = display
        self.failure_tracker = failure_tracker
    
    async def process_query(self, query: str):
        """Process user query and execute tools."""
        # Build system prompt
        # Send to LLM
        # Stream response
        # Execute tools
        # Continue if needed
    
    async def execute_tool(self, tool_use: dict):
        """Execute a single tool with error handling."""
        # Check retry loops
        # Execute tool
        # Handle auto-recovery
        # Display results
    
    async def continue_after_tools(self):
        """Continue conversation after tool execution."""
        # Send tool results to LLM
        # Handle response
        # Recursively execute more tools if needed
```

---

### 3. **CommandRouter** (400 lines) - Slash Commands
**Responsibility**: Handle all /command operations  
**Single job**: Route commands to appropriate handlers

```python
class CommandRouter:
    """Routes /commands to appropriate handlers."""
    
    def __init__(self, cli_context):
        self.ctx = cli_context
        self.handlers = self._register_handlers()
    
    def _register_handlers(self) -> Dict[str, Callable]:
        """Register all command handlers."""
        return {
            '/clear': self.handle_clear,
            '/history': self.handle_history,
            '/diff': self.handle_diff,
            '/commit': self.handle_commit,
            '/test': self.handle_test,
            '/watch': self.handle_watch,
            '/analyze': self.handle_analyze,
            '/metrics': self.handle_metrics,
            # ... etc
        }
    
    async def handle(self, command: str):
        """Route command to handler."""
        cmd, *args = command.split(maxsplit=1)
        handler = self.handlers.get(cmd)
        
        if handler:
            await handler(args[0] if args else None)
        else:
            self.ctx.display.error(f"Unknown command: {cmd}")
    
    async def handle_diff(self, args: str):
        """Handle /diff command."""
        # Git diff logic
    
    async def handle_test(self, args: str):
        """Handle /test command."""
        # Test running logic
    
    # ... 20+ more handlers
```

---

### 4. **DisplayManager** (300 lines) - Console Output
**Responsibility**: All console display logic  
**Single job**: Format and display information to user

```python
class DisplayManager:
    """Handles all console display logic."""
    
    def __init__(self):
        self.console = Console()
    
    def print_banner(self):
        """Print startup banner."""
    
    def prompt_user(self) -> str:
        """Get user input."""
        return Prompt.ask("\n[bold green]You[/bold green]")
    
    def show_tool_execution(self, tool_name: str, tool_input: dict):
        """Display tool execution panel."""
    
    def show_tool_result(self, result: dict):
        """Display tool result panel."""
    
    def show_error(self, error: dict):
        """Display error with recovery suggestions."""
    
    def show_token_usage(self, conversation_tokens: int, max_tokens: int, cost: float):
        """Display token usage with color coding."""
    
    def show_test_results(self, results: List[TestResult]):
        """Display test results."""
    
    # ... etc
```

---

### 5. **SessionCoordinator** (300 lines) - Session Management
**Responsibility**: Session, workspace, and state management  
**Single job**: Coordinate persistent state

```python
class SessionCoordinator:
    """Coordinates session and workspace state."""
    
    def __init__(self, session_manager, workspace, memory, state_tracker):
        self.session_manager = session_manager
        self.workspace = workspace
        self.memory = memory
        self.state_tracker = state_tracker
    
    def load_or_create_session(self):
        """Load last session or create new one."""
    
    def save_current_state(self):
        """Save current session state."""
    
    def record_event(self, event_type: str, data: dict):
        """Record session event."""
    
    def get_context_for_ai(self) -> dict:
        """Get session context for AI prompt."""
    
    def get_work_summary(self) -> dict:
        """Get daily work summary."""
```

---

## Migration Strategy

### Phase 1: Extract DisplayManager (2 hours)
1. Create `flux/ui/display_manager.py`
2. Move all `console.print()` calls into display methods
3. Update CLI to use `self.display.method()` instead of direct console calls
4. Test that output looks the same

### Phase 2: Extract CommandRouter (3 hours)
1. Create `flux/ui/command_router.py`
2. Move all command handlers (methods that handle /commands)
3. Update CLI to delegate to `self.commands.handle()`
4. Test all commands work

### Phase 3: Extract ConversationManager (4 hours)
1. Create `flux/core/conversation_manager.py`
2. Move query processing, tool execution, and continuation logic
3. Update CLI to delegate to `self.conversation.process_query()`
4. Test full conversation flow works

### Phase 4: Extract SessionCoordinator (2 hours)
1. Create `flux/core/session_coordinator.py`
2. Move session, workspace, and state management
3. Update CLI to delegate to `self.session.*`
4. Test session persistence works

### Phase 5: Slim Down CLI (1 hour)
1. Remove all extracted logic from CLI
2. CLI becomes thin coordinator (~200 lines)
3. Update tests
4. Celebrate

**Total Time**: ~12 hours for complete refactor

---

## Benefits

### Before
- ❌ 3031 lines in one file
- ❌ 48 methods doing everything
- ❌ Impossible to test in isolation
- ❌ High coupling between concerns
- ❌ Can't reuse components
- ❌ Merge conflicts guaranteed

### After
- ✅ 5 focused files (200-500 lines each)
- ✅ Single responsibility per class
- ✅ Easy to test each component
- ✅ Clear boundaries and interfaces
- ✅ Components reusable
- ✅ Parallel development possible

---

## Rules Going Forward

### NEVER again:
1. **No file over 500 lines** - If it hits 500, split it
2. **No class over 300 lines** - If it hits 300, extract
3. **Max 15 public methods per class** - If more, you're doing too much
4. **Single Responsibility Principle** - Each class does ONE thing well

### Code Review Checklist:
- [ ] No class over 300 lines?
- [ ] No file over 500 lines?
- [ ] Single responsibility?
- [ ] Clear, descriptive class name?
- [ ] Can be tested in isolation?

---

## Next Steps

1. **Start with Phase 1** (DisplayManager) - lowest risk
2. **Commit after each phase** - rollback if needed
3. **Test thoroughly** - ensure no regressions
4. **Update docs** - keep ARCHITECTURE.md current

Ready to start?

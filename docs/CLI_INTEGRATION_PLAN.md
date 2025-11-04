# CLI Integration Plan

## Current State
- ✅ AIOrchestrator - Already initialized and working
- ❌ SessionManager - Built but not integrated
- ❌ ProactiveMonitor - Built but not integrated
- ❌ WorkflowManager - Built but not integrated

## Integration Points

### 1. `__init__` - Initialize New Systems
```python
# Add to flux/ui/cli.py __init__ (after line 144):

# Initialize Session Manager
from flux.core.session_manager import SessionManager, EventType
self.session_manager = SessionManager(cwd)

# Initialize Proactive Monitor
from flux.core.proactive_monitor import ProactiveMonitor, MonitorType
self.proactive_monitor = ProactiveMonitor(cwd, self.llm)
self.proactive_monitor.add_notification_callback(self._print_monitor_notification)

# Initialize Workflow Manager
from flux.core.workflows import WorkflowManager, WorkflowExecutor
self.workflow_manager = WorkflowManager(cwd)
self.workflow_executor = WorkflowExecutor(self.orchestrator)
```

### 2. `print_banner` - Load/Display Session
```python
# Replace memory display with session display (lines 218-223):

# Load last session
last_session = self.session_manager.load_last_session()
if last_session:
    # Display session summary
    summary = self.session_manager.get_session_summary(last_session)
    self.console.print(summary)
else:
    # Start new session
    self.session_manager.start_new_session()
```

### 3. Event Recording - Throughout CLI
```python
# In process_query_normal (after line 1056):
self.session_manager.record_event(EventType.MESSAGE, {
    'role': 'user',
    'content': query
})

# After tool execution (in execute_tool, after line 1135):
if tool_name in ['write_file', 'edit_file']:
    self.session_manager.record_event(Event Type.FILE_EDIT, {
        'file': tool_input.get('path') or tool_input.get('file_path'),
        'tool': tool_name
    })

# After test execution:
self.session_manager.update_test_status({
    'total': result.total,
    'passed': result.passed,
    'failed': result.failed
})

# After errors:
self.session_manager.record_error({
    'message': str(error),
    'context': context
})
```

### 4. New Commands

#### Session Commands
```python
if query.lower() == '/session':
    if self.session_manager.current_session:
        summary = self.session_manager.get_session_summary(
            self.session_manager.current_session
        )
        self.console.print(Panel(summary, title="📂 Current Session"))
    continue

# Update /task to use SessionManager:
if query.lower().startswith('/task '):
    task = query[6:].strip()
    self.session_manager.set_current_task(task)
    self.memory.set_current_task(task)  # Keep old system too for now
    self.console.print(f"[green]Task set:[/green] {task}")
    continue
```

#### Workflow Commands
```python
if query.lower().startswith('/workflow '):
    workflow_name = query[10:].strip()
    workflow = self.workflow_manager.get_workflow(workflow_name)
    
    if not workflow:
        self.console.print(f"[red]Workflow '{workflow_name}' not found[/red]")
        self.console.print(f"[dim]Available: {', '.join(self.workflow_manager.list_workflows())}[/dim]")
        continue
    
    self.console.print(f"[bold cyan]🔄 Executing workflow: {workflow_name}[/bold cyan]")
    
    def on_progress(progress):
        if progress['status'] == 'running':
            self.console.print(
                f"[dim][{progress['current_step']}/{progress['total_steps']}] "
                f"{progress['step_name']}...[/dim]"
            )
    
    self.workflow_executor.add_progress_callback(on_progress)
    result = await self.workflow_executor.execute(workflow)
    
    if result['success']:
        self.console.print(f"[green]✓ Workflow completed in {result['elapsed']:.1f}s[/green]")
    else:
        self.console.print(f"[yellow]⚠ Workflow failed: {result.get('error')}[/yellow]")
    
    continue

if query.lower() == '/workflows':
    workflows = self.workflow_manager.list_workflows()
    self.console.print("[bold]Available Workflows:[/bold]")
    for name in workflows:
        workflow = self.workflow_manager.get_workflow(name)
        self.console.print(f"  • [cyan]{name}[/cyan]: {workflow.description}")
    continue
```

#### Monitoring Commands
```python
if query.lower().startswith('/watch '):
    monitor_type = query[7:].strip().lower()
    
    if monitor_type == 'stop':
        self.proactive_monitor.stop()
        self.console.print("[yellow]Stopped all monitors[/yellow]")
        continue
    
    # Map command to monitor type
    monitor_map = {
        'tests': MonitorType.TESTS,
        'lint': MonitorType.LINT,
        'build': MonitorType.BUILD,
        'files': MonitorType.FILE_CHANGES,
        'git': MonitorType.GIT,
        'all': None  # Enable all
    }
    
    if monitor_type == 'all':
        for mtype in [MonitorType.TESTS, MonitorType.LINT, MonitorType.FILE_CHANGES]:
            self.proactive_monitor.enable_monitor(mtype)
        self.console.print("[green]✓ Enabled all monitors[/green]")
    elif monitor_type in monitor_map:
        mtype = monitor_map[monitor_type]
        self.proactive_monitor.enable_monitor(mtype)
        self.console.print(f"[green]✓ Monitoring {monitor_type}[/green]")
    else:
        self.console.print(f"[red]Unknown monitor: {monitor_type}[/red]")
        self.console.print("[dim]Available: tests, lint, build, files, git, all, stop[/dim]")
    
    # Start monitoring in background
    if not self.proactive_monitor.running:
        import asyncio
        asyncio.create_task(self.proactive_monitor.start())
    
    continue

if query.lower() == '/status':
    status = self.proactive_monitor.get_status()
    
    self.console.print("[bold]Monitor Status:[/bold]")
    if status['running']:
        self.console.print(f"  Running: [green]✓[/green]")
        self.console.print(f"  Active monitors: {', '.join(status['monitors'])}")
        self.console.print(f"  Total events: {status['total_events']}")
        
        if status['recent_events']:
            self.console.print("\\n[bold]Recent Events:[/bold]")
            for event in status['recent_events'][-5:]:
                self.console.print(f"  • {event['monitor_type']}: {event['message']}")
    else:
        self.console.print(f"  Running: [dim]Not started[/dim]")
        self.console.print("[dim]Use /watch <type> to start monitoring[/dim]")
    
    continue
```

### 5. Helper Methods

```python
def _print_monitor_notification(self, message: str):
    """Callback for proactive monitor notifications."""
    # Print with visual separator
    self.console.print(message)

async def _record_session_event(self, event_type: EventType, data: dict):
    """Helper to record session events."""
    self.session_manager.record_event(event_type, data)
```

### 6. Context Injection for LLM

```python
# In _build_system_prompt (around line 1400):

# Add session context
session_context = self.session_manager.get_context_for_ai()
if session_context:
    context_str = f"""

SESSION CONTEXT:
Current task: {session_context.get('current_task', 'None')}
Active files: {', '.join(session_context.get('active_files', [])[:5])}
Test status: {session_context.get('test_status', {})}
Recent errors: {len(session_context.get('recent_errors', []))} errors

Recent activity:
{chr(10).join(f"- {a['summary']}" for a in session_context.get('recent_activity', [])[-5:])}
"""
    system_prompt += context_str
```

## Implementation Order

1. ✅ Add imports and initialize in __init__
2. ✅ Add session loading in print_banner
3. ✅ Add /session, /workflow, /workflows, /watch, /status commands
4. ✅ Add event recording throughout
5. ✅ Add session context to LLM prompts
6. ✅ Update /help with new commands
7. ✅ Test everything

## Testing Checklist

- [ ] Session persists across CLI restarts
- [ ] /session shows current session
- [ ] /workflow executes workflows
- [ ] /workflows lists available workflows
- [ ] /watch tests starts test monitoring
- [ ] Monitor notifications appear when tests break
- [ ] Session events are recorded
- [ ] LLM receives session context
- [ ] Desktop app gets all features automatically

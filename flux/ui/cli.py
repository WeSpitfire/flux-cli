"""CLI interface for Flux."""

import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from flux.core.config import Config
from flux.core.project import ProjectDetector, ProjectInfo
from flux.core.memory import MemoryStore
from flux.core.undo import UndoManager
from flux.core.workflow import WorkflowEnforcer
from flux.core.approval import ApprovalManager
from flux.core.git_utils import GitIntegration
from flux.core.codebase_intelligence import CodebaseGraph
from flux.core.impact_analyzer import ImpactAnalyzer
from flux.core.suggestions import SuggestionsEngine, Priority
from flux.core.workspace import Workspace, TaskPriority, TaskStatus
from flux.core.failure_tracker import FailureTracker
from flux.core.background_processor import SmartBackgroundProcessor
from flux.core.code_validator import CodeValidator
from flux.core.debug_logger import DebugLogger
from flux.core.state_tracker import ProjectStateTracker
from flux.core.error_parser import ErrorParser
from flux.core.test_runner import TestRunner, TestResult
from flux.core.test_watcher import TestWatcher
from flux.core.auto_fixer import AutoFixer
from flux.core.auto_fix_watcher import AutoFixWatcher, AutoFixEvent
from flux.core.orchestrator import AIOrchestrator
from flux.core.orchestrator_tools import register_all_tools
from flux.core.auto_init import auto_initialize
from flux.ui.nl_commands import get_parser
from flux.llm.provider_factory import create_provider
from flux.llm.prompts import SYSTEM_PROMPT
from flux.tools.base import ToolRegistry
from flux.tools.file_ops import ReadFilesTool, WriteFileTool, EditFileTool, MoveFileTool, DeleteFileTool
from flux.tools.command import RunCommandTool
from flux.tools.search import GrepSearchTool
from flux.tools.filesystem import ListFilesTool, FindFilesTool
from flux.tools.ast_edit import ASTEditTool
from flux.tools.validation import ValidationTool
from flux.tools.preview import PreviewEditTool
from flux.tools.line_insert import InsertAtLineTool


class CLI:
    """Main CLI interface for Flux."""

    def __init__(self, config: Config, cwd: Path):
        """Initialize CLI."""
        self.config = config
        self.cwd = cwd
        # Force UTF-8 encoding for console to handle emojis in piped stdout
        import sys
        self.console = Console(file=sys.stdout, force_terminal=False)
        self.llm = create_provider(config)

        # Detect project
        self.project_info = ProjectDetector(cwd).detect()

        # Initialize memory store
        self.memory = MemoryStore(config.flux_dir, cwd)

        # Initialize undo manager
        self.undo = UndoManager(config.flux_dir, cwd)

        # Initialize workflow enforcer
        self.workflow = WorkflowEnforcer(cwd)

        # Initialize approval manager
        self.approval = ApprovalManager(auto_approve=config.auto_approve)

        # Initialize git integration
        self.git = GitIntegration(cwd)

        # Initialize codebase intelligence (lazy loading)
        self.codebase_graph: Optional[CodebaseGraph] = None
        self._graph_building = False
        self._project_readme: Optional[str] = None

        # Initialize impact analyzer (lazy loading)
        self.impact_analyzer: Optional[ImpactAnalyzer] = None

        # Initialize suggestions engine (lazy loading)
        self.suggestions_engine: Optional[SuggestionsEngine] = None

        # Initialize workspace manager
        workspace_dir = config.flux_dir / "workspace"
        self.workspace: Workspace = Workspace(workspace_dir, cwd)

        # Initialize failure tracker
        self.failure_tracker = FailureTracker()

        # Initialize smart background processor
        self.bg_processor = SmartBackgroundProcessor(cwd)

        # Initialize code validator for self-checking
        self.code_validator = CodeValidator(cwd)

        # Initialize debug logger (disabled by default)
        self.debug_logger = DebugLogger(config.flux_dir, enabled=False)

        # Initialize project state tracker for contextual awareness
        self.state_tracker = ProjectStateTracker(cwd)

        # Initialize natural language command parser
        self.nl_parser = get_parser()

        # Initialize error parser for smart error detection
        self.error_parser = ErrorParser(cwd)

        # Initialize test runner and watcher
        self.test_runner = TestRunner(cwd)
        self.test_watcher: Optional[TestWatcher] = None

        # Initialize auto-fixer (enabled by default)
        self.auto_fixer = AutoFixer(cwd, enabled=True)
        self.auto_fix_watcher: Optional[AutoFixWatcher] = None

        # Initialize tool registry
        self.tools = ToolRegistry()
        self.tools.register(ReadFilesTool(cwd, workflow_enforcer=self.workflow, background_processor=self.bg_processor))
        self.tools.register(WriteFileTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval, code_validator=self.code_validator))
        self.tools.register(EditFileTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval, code_validator=self.code_validator))
        self.tools.register(MoveFileTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(DeleteFileTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(InsertAtLineTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(PreviewEditTool(cwd))
        self.tools.register(RunCommandTool(cwd))
        self.tools.register(GrepSearchTool(cwd, workflow_enforcer=self.workflow))
        self.tools.register(ListFilesTool(cwd))
        self.tools.register(FindFilesTool(cwd))
        self.tools.register(ASTEditTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(ValidationTool(cwd))

        # Initialize AI Orchestrator
        self.orchestrator = AIOrchestrator(self.llm, cwd)
        # Register all tools with orchestrator
        register_all_tools(self.orchestrator, self)

        # Initialize Session Manager
        from flux.core.session_manager import SessionManager, EventType
        self.session_manager = SessionManager(cwd)
        self.EventType = EventType  # Store for easy access

        # Initialize Proactive Monitor
        from flux.core.proactive_monitor import ProactiveMonitor, MonitorType
        self.proactive_monitor = ProactiveMonitor(cwd, self.llm)
        self.proactive_monitor.add_notification_callback(self._print_monitor_notification)
        self.MonitorType = MonitorType  # Store for easy access

        # Initialize Workflow Manager and Executor
        from flux.core.workflows import WorkflowManager, WorkflowExecutor
        self.workflow_manager = WorkflowManager(cwd)
        self.workflow_executor = WorkflowExecutor(self.orchestrator)
        self.workflow_executor.add_notification_callback(self._print_monitor_notification)

    async def build_codebase_graph(self) -> None:
        """Build the codebase semantic graph (runs in background)."""
        if self._graph_building or self.codebase_graph:
            return

        self._graph_building = True
        try:
            self.console.print("[dim]Building codebase graph...[/dim]")
            self.codebase_graph = CodebaseGraph(self.cwd)
            self.codebase_graph.build_graph(max_files=500)  # Limit for performance

            # Show architecture detection results
            patterns = self.codebase_graph.detect_architecture_patterns()
            if patterns.get('framework'):
                self.console.print(f"[dim]Detected: {patterns['framework']} ({patterns['structure']} structure)[/dim]")

            # Auto-read README for project understanding
            self._project_readme = await self._load_readme()

            # Initialize impact analyzer with graph
            self.impact_analyzer = ImpactAnalyzer(self.cwd, self.codebase_graph)

            # Initialize suggestions engine with graph
            self.suggestions_engine = SuggestionsEngine(self.cwd, self.codebase_graph)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not build code graph: {e}[/yellow]")
        finally:
            self._graph_building = False

    async def _load_readme(self) -> Optional[str]:
        """Load README file for project understanding."""
        readme_files = ['README.md', 'README.txt', 'README.rst', 'README']
        for readme_name in readme_files:
            readme_path = self.cwd / readme_name
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Limit to first 5000 chars to avoid token bloat
                        return content[:5000] if len(content) > 5000 else content
                except Exception:
                    pass
        return None

    def get_intelligent_context(self, query: str) -> List[str]:
        """Get intelligent file suggestions based on query."""
        if not self.codebase_graph:
            return []

        suggested_files = self.codebase_graph.suggest_context_files(query, max_files=3)
        return suggested_files

    def print_banner(self):
        """Print Flux banner."""
        banner = Text()
        banner.append("╔═══════════════════════════════╗\n", style="bold blue")
        banner.append("║   ", style="bold blue")
        banner.append("FLUX", style="bold cyan")
        banner.append(" - AI Dev Assistant   ║\n", style="bold blue")
        banner.append("╚═══════════════════════════════╝", style="bold blue")
        self.console.print(banner)
        self.console.print(f"Working directory: [cyan]{self.cwd}[/cyan]")
        self.console.print(f"Provider: [cyan]{self.config.provider}[/cyan]")
        self.console.print(f"Model: [cyan]{self.config.model}[/cyan]")

        # Show project info if detected
        if self.project_info:
            self.console.print(f"Project: [green]{self.project_info.name}[/green] ([cyan]{self.project_info.project_type}[/cyan])")
            if self.project_info.frameworks:
                self.console.print(f"Tech: [dim]{', '.join(self.project_info.frameworks)}[/dim]")

        # Load/resume session
        last_session = self.session_manager.load_last_session()
        if last_session:
            # Display session summary
            summary = self.session_manager.get_session_summary(last_session)
            self.console.print("\n" + summary)
        else:
            # Start new session
            self.session_manager.start_new_session()

        # Show memory/resume info (keep for backward compatibility)
        if self.memory.state.current_task and not last_session:
            self.console.print(f"Task: [yellow]{self.memory.state.current_task}[/yellow]")

        self.console.print()

    async def run_interactive(self):
        """Run interactive REPL mode."""
        self.print_banner()

        # Smart auto-initialization based on project context
        await auto_initialize(self)

        # Multi-line compose state (disabled if not truly interactive)
        import sys
        self._enable_paste_mode = sys.stdin.isatty()  # Only enable for real terminals
        self._compose_mode = False
        self._compose_buffer = []  # type: list[str]
        self._last_input_time = 0.0  # Track timing for paste detection

        self.console.print("[dim]Type 'exit' or 'quit' to exit[/dim]\n")

        while True:
            try:
                # Get user input (show prompt only in real terminal, not when piped from desktop app)
                if self._enable_paste_mode:
                    # Real terminal - show fancy prompt
                    query = Prompt.ask(f"\n[bold green]You[/bold green]")
                else:
                    # Piped/desktop mode - just read from stdin without showing prompt
                    query = input()

                # Decode newline placeholders from desktop app
                if '<<<NEWLINE>>>' in query:
                    query = query.replace('<<<NEWLINE>>>', '\n')

                # Try to parse natural language commands
                nl_result = self.nl_parser.parse(query)
                if nl_result:
                    command, args = nl_result
                    # Show what we interpreted
                    self.console.print(f"[dim]→ Interpreted as: {command} {args or ''}[/dim]")
                    # Rewrite query as the slash command
                    if args:
                        query = f"{command} {args}"
                    else:
                        query = command

                if query.lower() in ['exit', 'quit', 'q']:
                    self.console.print("\n[cyan]Goodbye![/cyan]")
                    break

                if query.lower() == '/clear':
                    self.llm.clear_history()
                    self.console.print("[green]✓ Conversation history cleared[/green]")
                    # Clear compose buffer too
                    if getattr(self, "_compose_mode", False):
                        self._compose_mode = False
                        self._compose_buffer = []
                        self.console.print("[dim]Paste mode cancelled[/dim]")
                    continue

                if query.lower() == '/history':
                    usage = self.llm.get_token_usage()
                    history_len = len(self.llm.conversation_history)
                    self.console.print(
                        f"\n[bold]💬 Conversation History:[/bold]\n"
                        f"  Messages: [cyan]{history_len}[/cyan]\n"
                        f"  Input tokens: [cyan]{usage['input_tokens']:,}[/cyan]\n"
                        f"  Output tokens: [cyan]{usage['output_tokens']:,}[/cyan]\n"
                        f"  Total tokens: [cyan]{usage['total_tokens']:,}[/cyan]\n"
                        f"  Estimated cost: [green]${usage['estimated_cost']:.4f}[/green]\n"
                    )
                    continue

                if query.lower() == '/fix':
                    # Check if there are any recent errors
                    recent_commands = [c for c in self.state_tracker.command_history[-5:] if c.exit_code != 0]

                    if not recent_commands:
                        self.console.print("[yellow]No recent failed commands to fix.[/yellow]")
                        continue

                    # Get the most recent failed command
                    last_failed = recent_commands[-1]

                    # Parse errors
                    parsed_errors = self.error_parser.parse_output(last_failed.output or "", last_failed.command)

                    if not parsed_errors:
                        self.console.print(f"[yellow]No parseable errors found in: {last_failed.command}[/yellow]")
                        continue

                    # Show errors
                    self.console.print(f"\n[bold]🛠️  Analyzing Errors from:[/bold] [cyan]{last_failed.command}[/cyan]\n")

                    for i, error in enumerate(parsed_errors[:3], 1):
                        self.console.print(f"{i}. {self.error_parser.format_error(error)}\n")

                    # Get fix context for first error
                    first_error = parsed_errors[0]
                    fix_context = self.error_parser.get_fix_context(first_error)

                    if fix_context:
                        # Automatically ask Flux to fix it
                        fix_query = (
                            f"Fix this error:\n\n"
                            f"Error: {first_error.error_type}: {first_error.message}\n"
                            f"File: {fix_context['file_path']}:{fix_context['line_number']}\n\n"
                            f"Code context (lines {fix_context['start_line']}-{fix_context['end_line']}):\n"
                            f"```\n{fix_context['code_context']}```\n\n"
                            f"Please fix this error."
                        )

                        self.console.print("[dim]→ Asking Flux to fix the error...[/dim]\n")

                        # Process as a query
                        query = fix_query
                        # Let it continue to the main processing logic
                    else:
                        self.console.print(f"[yellow]Could not get fix context for {first_error.file_path}[/yellow]")
                        continue

                if query.lower() == '/state':
                    summary = self.state_tracker.get_context_summary(max_age_minutes=30)
                    suggestions = self.state_tracker.get_proactive_suggestions()

                    self.console.print("\n[bold]🧠 Project State (Last 30 minutes):[/bold]\n")

                    # Files
                    if summary['files']['recently_modified']:
                        self.console.print(f"[bold cyan]Recent Files:[/bold cyan]")
                        for f in summary['files']['recently_modified'][:5]:
                            self.console.print(f"  • {f}")
                        self.console.print()

                    if summary['files']['most_active']:
                        self.console.print(f"[bold cyan]Hot Files:[/bold cyan]")
                        for f, count in summary['files']['most_active']:
                            self.console.print(f"  • {f} ({count} modifications)")
                        self.console.print()

                    # Git
                    if summary['git']['is_repo']:
                        self.console.print(f"[bold cyan]Git:[/bold cyan]")
                        self.console.print(f"  Branch: {summary['git']['branch']}")
                        if summary['git']['has_changes']:
                            self.console.print(f"  Changes: {summary['git']['total_changes']} files (" +
                                             f"{summary['git']['staged_files']} staged, " +
                                             f"{summary['git']['modified_files']} modified, " +
                                             f"{summary['git']['untracked_files']} untracked)")
                        else:
                            self.console.print("  Clean working directory")
                        self.console.print()

                    # Tests
                    if summary['tests']['recent_count'] > 0:
                        self.console.print(f"[bold cyan]Tests:[/bold cyan]")
                        if summary['tests']['last_passed'] is not None:
                            status = "[green]✓ Passed[/green]" if summary['tests']['last_passed'] else "[red]✗ Failed[/red]"
                            self.console.print(f"  Last run: {status}")
                        if summary['tests']['recent_failures']:
                            self.console.print(f"  Failures:")
                            for failure in summary['tests']['recent_failures'][:3]:
                                self.console.print(f"    • {failure}")
                        self.console.print()

                    # Commands
                    if summary['commands']['recent_count'] > 0:
                        self.console.print(f"[bold cyan]Commands:[/bold cyan]")
                        self.console.print(f"  Recent: {summary['commands']['recent_count']}")
                        if summary['commands']['last_command']:
                            self.console.print(f"  Last: {summary['commands']['last_command']}")
                        if summary['commands']['failed_commands']:
                            self.console.print(f"  Failed: {len(summary['commands']['failed_commands'])}")
                        self.console.print()

                    # Suggestions
                    if suggestions:
                        self.console.print(f"[bold yellow]💡 Suggestions:[/bold yellow]")
                        for suggestion in suggestions:
                            self.console.print(f"  {suggestion}")
                        self.console.print()
                    else:
                        self.console.print("[dim]No suggestions - you're doing great! 🚀[/dim]\n")

                    continue

                # -- Session commands --
                if query.lower() == '/session':
                    # Show current session summary
                    current = self.session_manager.get_current_session()
                    if current:
                        summary = self.session_manager.get_session_summary(current)
                        self.console.print("\n" + summary)
                    else:
                        self.console.print("[yellow]No active session[/yellow]")
                    continue

                # -- Workflow commands --
                if query.lower() == '/workflows':
                    # List available workflows
                    workflows = self.workflow_manager.list_workflows()
                    if not workflows:
                        self.console.print("[yellow]No workflows defined. Create `.flux/workflows.yaml` to add workflows.[/yellow]")
                    else:
                        self.console.print("\n[bold]Available Workflows:[/bold]")
                        for wf in workflows:
                            workflow = self.workflow_manager.get_workflow(wf)
                            desc = workflow.get('description', 'No description')
                            self.console.print(f"  [cyan]{wf}[/cyan] - {desc}")
                        self.console.print("\nUse `/workflow <name>` to execute a workflow.")
                    continue

                if query.lower().startswith('/workflow '):
                    # Execute a workflow
                    workflow_name = query[10:].strip()
                    if not workflow_name:
                        self.console.print("[red]Usage: /workflow <name>[/red]")
                        continue

                    try:
                        workflow = self.workflow_manager.get_workflow(workflow_name)
                        self.console.print(f"\n[bold]Executing workflow: {workflow_name}[/bold]\n")

                        # Execute workflow asynchronously
                        import asyncio
                        result = asyncio.run(self.workflow_executor.execute(workflow))

                        if result.get('success'):
                            self.console.print(f"\n[green]✓ Workflow '{workflow_name}' completed successfully[/green]")
                        else:
                            error = result.get('error', 'Unknown error')
                            self.console.print(f"\n[red]✗ Workflow '{workflow_name}' failed: {error}[/red]")

                        # Record workflow execution
                        self.session_manager.record_event(
                            self.EventType.WORKFLOW_EXECUTED,
                            {'workflow': workflow_name, 'success': result.get('success', False)}
                        )
                    except Exception as e:
                        self.console.print(f"[red]Error executing workflow: {e}[/red]")
                    continue

                # -- Monitoring commands --
                if query.lower().startswith('/watch'):
                    parts = query.split()
                    if len(parts) < 2:
                        self.console.print("[yellow]Usage: /watch <type> or /watch stop[/yellow]")
                        self.console.print("Types: tests, lint, build, files, git, all")
                        continue

                    action = parts[1].lower()

                    if action == 'stop':
                        self.proactive_monitor.stop()
                        self.console.print("[yellow]All monitors stopped[/yellow]")
                    elif action == 'all':
                        import asyncio
                        for monitor_type in self.MonitorType:
                            self.proactive_monitor.enable_monitor(monitor_type)
                        asyncio.create_task(self.proactive_monitor.start())
                        self.console.print("[green]All monitors started[/green]")
                    else:
                        try:
                            # Map string to MonitorType
                            type_map = {
                                'tests': self.MonitorType.TESTS,
                                'lint': self.MonitorType.LINT,
                                'build': self.MonitorType.BUILD,
                                'files': self.MonitorType.FILE_CHANGES,
                                'git': self.MonitorType.GIT_CHANGES
                            }
                            monitor_type = type_map.get(action)
                            if not monitor_type:
                                self.console.print(f"[red]Unknown monitor type: {action}[/red]")
                                continue

                            import asyncio
                            self.proactive_monitor.enable_monitor(monitor_type)
                            asyncio.create_task(self.proactive_monitor.start())
                            self.console.print(f"[green]Started {action} monitor[/green]")
                        except Exception as e:
                            self.console.print(f"[red]Error starting monitor: {e}[/red]")
                    continue

                if query.lower() == '/status':
                    # Show monitor status
                    status = self.proactive_monitor.get_status()
                    self.console.print("\n[bold]Monitor Status:[/bold]")
                    self.console.print(f"  Running: {'Yes' if status['running'] else 'No'}")
                    self.console.print(f"  Active monitors: {len(status['active_monitors'])}")
                    if status['active_monitors']:
                        for monitor in status['active_monitors']:
                            self.console.print(f"    - {monitor}")
                    if status['last_events']:
                        self.console.print("\n[bold]Recent Events:[/bold]")
                        for event in status['last_events'][-5:]:  # Show last 5
                            self.console.print(f"  [{event['timestamp']}] {event['type']}: {event.get('message', 'N/A')}")
                    continue

                if query.lower() == '/help':
                    help_text = (
                        "[bold]Available Commands:[/bold]\n"
                        "\n[bold magenta]✨ Natural Language:[/bold magenta]\n"
                        "  Just ask naturally! Examples:\n"
                        "  [dim]• 'show me what changed' → /diff[/dim]\n"
                        "  [dim]• 'run the tests' → /test[/dim]\n"
                        "  [dim]• 'undo that' → /undo[/dim]\n"
                        "  [dim]• 'what's happening' → /state[/dim]\n"
                        "\n[bold cyan]General:[/bold cyan]\n"
                        "  [green]/help[/green] - Show this help message\n"
                        "  [green]/model[/green] - Show current provider and model\n"
                        "  [green]/history[/green] - Show conversation history summary\n"
                        "  [green]/clear[/green] - Clear conversation history\n"
                        "\n[bold cyan]Multi-line & Paste Mode:[/bold cyan]\n"
                        "  [green]/paste[/green] or [green]```[/green] - Start paste mode\n"
                        "  [green]/end[/green] or [green]/send[/green] or [green]```[/green] - Finish and send\n"
                        "  [green]/discard[/green] - Cancel paste mode and discard\n"
                        "  Tip: Paste large tasks as a single block; Flux auto-detects lists and will enter paste mode.\n"
                        "\n[bold cyan]Session & Context:[/bold cyan]\n"
                        "  [green]/session[/green] - Show current session summary\n"
                        "  [green]/task <description>[/green] - Set current task\n"
                        "  [green]/memory[/green] - Show project memory\n"
                        "  [green]/checkpoint <msg>[/green] - Save a checkpoint\n"
                        "  [green]/project[/green] - Show files created in this session\n"
                        "\n[bold cyan]Workflows & Automation:[/bold cyan]\n"
                        "  [green]/workflows[/green] - List available workflows\n"
                        "  [green]/workflow <name>[/green] - Execute a workflow\n"
                        "  [green]/watch <type>[/green] - Start monitoring (tests/lint/build/files/git/all)\n"
                        "  [green]/watch stop[/green] - Stop all monitors\n"
                        "  [green]/status[/green] - Show monitor status\n"
                        "\n[bold cyan]Undo Commands:[/bold cyan]\n"
                        "  [green]/undo[/green] - Undo last file operation\n"
                        "  [green]/undo-history[/green] - Show undo history\n"
                        "\n[bold cyan]Git & Testing:[/bold cyan]\n"
                        "  [green]/diff[/green] - Show git diff of changes\n"
                        "  [green]/commit[/green] - Smart commit with generated message\n"
                        "  [green]/test[/green] - Run project tests\n"
                        "  [green]/watch[/green] - Start test watch mode (auto-run on file changes)\n"
                        "  [green]/watch-stop[/green] - Stop test watch mode\n"
                        "\n[bold cyan]Workflow & Approval:[/bold cyan]\n"
                        "  [green]/workflow[/green] - Show workflow status\n"
                        "  [green]/approval[/green] - Show approval statistics\n"
                        "\n[bold cyan]Codebase Intelligence:[/bold cyan]\n"
                        "  [green]/index[/green] - Build semantic codebase graph\n"
                        "  [green]/related <file|query>[/green] - Find related files\n"
                        "  [green]/architecture[/green] - Show detected architecture\n"
                        "  [green]/preview <file>[/green] - Preview impact of modifying a file\n"
                        "  [green]/suggest[/green] - Get proactive AI suggestions\n"
                        "\n[bold cyan]Workspace Intelligence:[/bold cyan]\n"
                        "  [green]/session save <n>[/green] - Save current work session\n"
                        "  [green]/session restore <id>[/green] - Restore a saved session\n"
                        "  [green]/sessions[/green] - List all sessions\n"
                        "  [green]/newtask <title>[/green] - Create a new task\n"
                        "  [green]/tasks[/green] - List all tasks\n"
                        "  [green]/summary[/green] - Show work summary for today\n"
                        "  [green]/stats[/green] - Show project statistics\n"
                        "  [green]/performance[/green] (or [green]/perf[/green]) - Show background processing stats\n"
                        "\n[bold cyan]Code Quality:[/bold cyan]\n"
                        "  [green]/validate[/green] - Validate modified files for errors\n"
                        "  [green]/fix[/green] - Auto-detect and fix recent errors\n"
                        "\n[bold cyan]Debug & Diagnostics:[/bold cyan]\n"
                        "  [green]/debug-on[/green] - Enable debug logging\n"
                        "  [green]/debug-off[/green] - Disable debug logging\n"
                        "  [green]/debug[/green] - Show debug session summary\n"
                        "  [green]/debug-analyze <issue>[/green] - Analyze logs for an issue\n"
                        "  [green]/inspect[/green] - Inspect current conversation state\n"
                    )
                    # Use plain text title to avoid Unicode issues in piped output
                    self.console.print(Panel(help_text, title="Help", border_style="blue"))
                    continue


                if query.lower() == '/model':
                    self.console.print(
                        f"\n[bold]🤖 Current Model:[/bold]\n"
                        f"  Provider: [cyan]{self.config.provider}[/cyan]\n"
                        f"  Model: [cyan]{self.config.model}[/cyan]\n"
                    )
                    continue

                # Paste mode handling (only if enabled for interactive terminals)
                import time
                current_time = time.time()

                if getattr(self, "_enable_paste_mode", True) and getattr(self, "_compose_mode", False):
                    # Check for explicit end commands
                    if query.strip() in ('/end', '/send', '```'):
                        combined = "\n".join(self._compose_buffer).strip()
                        self._compose_mode = False
                        self._compose_buffer = []
                        if not combined:
                            self.console.print("[dim]Nothing to send[/dim]")
                            continue
                        query = combined
                    elif query.strip() == '/discard':
                        self._compose_mode = False
                        self._compose_buffer = []
                        self.console.print("[yellow]Discarded paste buffer[/yellow]")
                        continue
                    elif not query.strip():
                        # Empty line after paste - auto-send if buffer has content
                        if self._compose_buffer and (current_time - self._last_input_time) > 0.5:
                            combined = "\n".join(self._compose_buffer).strip()
                            self._compose_mode = False
                            self._compose_buffer = []
                            query = combined
                        else:
                            # Still pasting - skip empty line
                            self._last_input_time = current_time
                            continue
                    else:
                        # Accumulate silently
                        self._compose_buffer.append(query)
                        self._last_input_time = current_time
                        continue

                # Manual paste mode start
                if query.strip() in ('/paste', '```'):
                    self._compose_mode = True
                    self._compose_buffer = []
                    self._last_input_time = current_time
                    self.console.print("[dim]Paste mode - press Enter twice when done[/dim]")
                    continue

                # Skip empty input in normal mode
                if not query.strip():
                    continue

                # Auto-detect paste: if input looks like start of multi-line, enter silent mode
                # Only enable if running in interactive terminal (not piped/desktop app)
                import re
                if getattr(self, "_enable_paste_mode", True) and (re.match(r"^(\s*\d+\.|\s*[-*])\s+", query) or (query.rstrip().endswith(':') and len(query) > 10)):
                    self._compose_mode = True
                    self._compose_buffer = [query]
                    self._last_input_time = current_time
                    continue

                # Handle special memory commands
                if query.lower().startswith('/task '):
                    task = query[6:].strip()
                    self.memory.set_current_task(task)
                    self.console.print(f"[green]Task set:[/green] {task}")
                    continue

                if query.lower() == '/memory':
                    mem_str = self.memory.to_context_string(max_items=10)
                    self.console.print(Panel(mem_str, title="\ud83d\udcda Memory", border_style="blue"))
                    continue

                if query.lower() == '/checkpoint':
                    msg = query[12:].strip() if len(query) > 12 else "Manual checkpoint"
                    self.memory.add_checkpoint(msg)
                    self.console.print(f"[green]Checkpoint saved:[/green] {msg}")
                    continue

                if query.lower() == '/undo':
                    result = self.undo.undo_last()
                    if result.get("error"):
                        self.console.print(f"[red]{result['error']}[/red]")
                    else:
                        self.console.print(
                            f"[green]\u2713 Undone:[/green] {result['description']}\n"
                            f"  File: {result['file']}\n"
                            f"  Action: {result['action']}\n"
                            f"  Time: {result['timestamp']}"
                        )
                    continue

                if query.lower() == '/undo-history':
                    history = self.undo.get_history()
                    if not history:
                        self.console.print("[dim]No undo history[/dim]")
                    else:
                        lines = ["[bold]Undo History:[/bold]"]
                        for entry in history:
                            lines.append(
                                f"  [{entry['index']}] [{entry['timestamp']}] "
                                f"{entry['operation']}: {entry['description']}"
                            )
                        self.console.print("\n".join(lines))
                    continue

                if query.lower() == '/project':
                    summary = self.memory.get_project_summary()
                    self.console.print(Panel(summary, title="\ud83d\udce6 Project Files", border_style="blue"))
                    continue

                if query.lower() == '/workflow':
                    summary = self.workflow.get_summary()
                    self.console.print(Panel(summary, title="\ud83d\udd04 Workflow Status", border_style="blue"))
                    continue

                if query.lower() == '/approval':
                    stats = self.approval.get_approval_stats()
                    summary = (
                        f"Total requests: {stats['total']}\n"
                        f"Approved: [green]{stats['approved']}[/green]\n"
                        f"Rejected: [red]{stats['rejected']}[/red]\n"
                        f"Approval rate: {stats['rate']:.1%}"
                    )
                    self.console.print(Panel(summary, title="\u2705 Approval Stats", border_style="blue"))
                    continue

                # Git commands
                if query.lower() == '/diff':
                    await self.show_diff()
                    continue

                if query.lower().startswith('/commit'):
                    await self.smart_commit(query)
                    continue

                if query.lower() == '/test':
                    await self.run_tests()
                    continue

                if query.lower() == '/watch':
                    await self.start_watch_mode()
                    continue

                if query.lower() == '/watch-stop':
                    self.stop_watch_mode()
                    continue

                # Codebase intelligence commands
                if query.lower() == '/index':
                    await self.build_codebase_graph()
                    continue

                if query.lower().startswith('/related '):
                    file_or_query = query[9:].strip()
                    await self.show_related_files(file_or_query)
                    continue

                if query.lower() == '/architecture':
                    await self.show_architecture()
                    continue

                if query.lower().startswith('/preview '):
                    file_path = query[9:].strip()
                    await self.show_file_preview(file_path)
                    continue

                # Proactive suggestions
                if query.lower() == '/suggest':
                    await self.show_suggestions()
                    continue

                # Workspace commands
                if query.lower().startswith('/session '):
                    args = query[9:].strip()
                    await self.handle_session_command(args)
                    continue

                if query.lower() == '/sessions':
                    await self.list_sessions()
                    continue

                if query.lower().startswith('/newtask '):
                    task_title = query[9:].strip()
                    await self.create_task(task_title)
                    continue

                if query.lower() == '/tasks':
                    await self.list_tasks()
                    continue

                if query.lower() == '/summary':
                    await self.show_work_summary()
                    continue

                if query.lower() == '/stats':
                    await self.show_project_stats()
                    continue

                if query.lower() == '/performance' or query.lower() == '/perf':
                    metrics = self.bg_processor.get_metrics()
                    summary = (
                        f"Files preloaded: [cyan]{metrics.files_preloaded}[/cyan]\n"
                        f"Cache hits: [green]{metrics.cache_hits}[/green]\n"
                        f"Cache misses: [yellow]{metrics.cache_misses}[/yellow]\n"
                        f"Hit rate: [cyan]{metrics.hit_rate():.1%}[/cyan]\n"
                        f"Time saved: [green]{metrics.time_saved_ms}ms[/green]\n"
                        f"Predictions: {metrics.predictions_made}"
                    )
                    self.console.print(Panel(summary, title="⚡ Background Processing", border_style="blue"))
                    continue

                if query.lower() == '/validate':
                    # Validate modified files in this session
                    modified_files = self.workflow.get_modified_files()
                    if not modified_files:
                        self.console.print("[dim]No modified files to validate[/dim]")
                        continue

                    self.console.print(f"\n[bold]Validating {len(modified_files)} files...[/bold]")
                    result = self.code_validator.validate_before_completion(modified_files)
                    report = self.code_validator.get_validation_report(result)
                    self.console.print(report)
                    continue

                # Debug commands
                if query.lower() == '/debug':
                    if self.debug_logger.enabled:
                        summary = self.debug_logger.get_summary()
                        self.console.print(Panel(summary, title="🐛 Debug Info", border_style="yellow"))
                    else:
                        self.console.print("[yellow]Debug mode is disabled. Enable with /debug-on[/yellow]")
                    continue

                if query.lower() == '/debug-on':
                    self.debug_logger.enable()
                    self.console.print("[green]✓ Debug logging enabled[/green]")
                    self.console.print(f"[dim]Logs will be saved to: {self.debug_logger.log_file}[/dim]")
                    continue

                if query.lower() == '/debug-off':
                    self.debug_logger.disable()
                    self.console.print("[green]✓ Debug logging disabled[/green]")
                    continue

                if query.lower().startswith('/debug-analyze '):
                    issue = query[15:].strip()
                    if not issue:
                        self.console.print("[red]Please provide an issue description[/red]")
                        continue
                    analysis = self.debug_logger.analyze_issue(issue)
                    self.console.print(Panel(analysis, title="🔍 Analysis", border_style="cyan"))
                    continue

                if query.lower() == '/inspect':
                    # Show current conversation state
                    await self.inspect_state()
                    continue

                # Auto-fix commands
                if query.lower() == '/autofix':
                    # Run auto-fix on current directory
                    await self.run_autofix()
                    continue

                if query.lower() == '/autofix-on':
                    self.auto_fixer.enabled = True
                    self.console.print("[green]✓ Auto-fix enabled[/green]")
                    self.console.print("[dim]Flux will automatically fix safe issues in the background[/dim]")
                    continue

                if query.lower() == '/autofix-off':
                    self.auto_fixer.enabled = False
                    self.console.print("[yellow]Auto-fix disabled[/yellow]")
                    continue

                if query.lower() == '/autofix-undo':
                    fix = self.auto_fixer.undo_last_fix()
                    if fix:
                        self.console.print(f"[green]✓ Undone:[/green] {fix.description}")
                        self.console.print(f"  File: {fix.file_path}")
                    else:
                        self.console.print("[yellow]No auto-fixes to undo[/yellow]")
                    continue

                if query.lower() == '/autofix-summary':
                    summary = self.auto_fixer.get_fix_summary()
                    if summary:
                        total = sum(summary.values())
                        summary_text = f"Total fixes applied: [cyan]{total}[/cyan]\n\n"
                        for fix_type, count in summary.items():
                            summary_text += f"  {fix_type}: {count}\n"
                        self.console.print(Panel(summary_text, title="🔧 Auto-Fix Summary", border_style="blue"))
                    else:
                        self.console.print("[dim]No auto-fixes applied yet[/dim]")
                    continue

                if query.lower() == '/autofix-watch':
                    # Start auto-fix watching
                    await self.start_autofix_watch()
                    continue

                if query.lower() == '/autofix-watch-stop':
                    # Stop auto-fix watching
                    self.stop_autofix_watch()
                    continue

                if query.lower() == '/autofix-stats':
                    # Show auto-fix watch statistics
                    if self.auto_fix_watcher:
                        stats = self.auto_fix_watcher.get_stats()
                        stats_text = (
                            f"Running: [{'green' if stats['running'] else 'yellow'}]{stats['running']}[/{'green' if stats['running'] else 'yellow'}]\n"
                            f"Total fixes: [cyan]{stats['total_fixes']}[/cyan]\n"
                            f"Files fixed: [cyan]{stats['files_fixed']}[/cyan]\n"
                        )
                        if stats['fix_types']:
                            stats_text += f"\nFix types: {', '.join(stats['fix_types'])}\n"

                        if stats.get('recent_events'):
                            stats_text += f"\n[bold]Recent fixes:[/bold]\n"
                            for event in stats['recent_events'][-5:]:
                                rel_path = event.file_path.relative_to(self.cwd) if event.file_path.is_relative_to(self.cwd) else event.file_path
                                stats_text += f"  • {rel_path} - {event.fixes_applied} fix(es)\n"

                        self.console.print(Panel(stats_text, title="📊 Auto-Fix Watch Stats", border_style="blue"))
                    else:
                        self.console.print("[yellow]Auto-fix watch not started. Use /autofix-watch to start.[/yellow]")
                    continue

                if query.lower() == '/help':
                    self.console.print(
                        "[bold]Memory Commands:[/bold]\n"
                        "  /task <description> - Set current task\n"
                        "  /memory - Show project memory\n"
                        "  /checkpoint <msg> - Save a checkpoint\n"
                        "  /project - Show files created in this session\n"
                        "\n[bold]Undo Commands:[/bold]\n"
                        "  /undo - Undo last file operation\n"
                        "  /undo-history - Show undo history\n"
                        "\n[bold]Git Commands:[/bold]\n"
                        "  /diff - Show git diff of changes\n"
                        "  /commit - Smart commit with generated message\n"
                        "  /test - Run project tests\n"
                        "\n[bold]Workflow & Approval:[/bold]\n"
                        "  /workflow - Show workflow status\n"
                        "  /approval - Show approval statistics\n"
                        "\n[bold]Codebase Intelligence:[/bold]\n"
                        "  /index - Build semantic codebase graph\n"
                        "  /related <file|query> - Find related files\n"
                        "  /architecture - Show detected architecture\n"
                        "  /preview <file> - Preview impact of modifying a file\n"
                        "  /suggest - Get proactive AI suggestions\n"
                        "\n[bold]Workspace Intelligence:[/bold]\n"
                        "  /session save <n> - Save current work session\n"
                        "  /session restore <id> - Restore a saved session\n"
                        "  /sessions - List all sessions\n"
                        "  /newtask <title> - Create a new task\n"
                        "  /tasks - List all tasks\n"
                        "  /summary - Show work summary for today\n"
                        "  /stats - Show project statistics\n"
                        "  /performance (/perf) - Show background processing stats\n"
                        "\n[bold]Auto-Fix (Invisible Mode):[/bold]\n"
                        "  /autofix - Run auto-fix on project files\n"
                        "  /autofix-on - Enable auto-fix mode\n"
                        "  /autofix-off - Disable auto-fix mode\n"
                        "  /autofix-watch - Start watching files (auto-fix on save)\n"
                        "  /autofix-watch-stop - Stop watching files\n"
                        "  /autofix-stats - Show watch mode statistics\n"
                        "  /autofix-undo - Undo last auto-fix\n"
                        "  /autofix-summary - Show auto-fix statistics\n"
                        "\n[bold]General:[/bold]\n"
                        "  /help - Show this help\n"
                        "  /model - Show current provider and model\n"
                        "  /history - Show conversation history summary\n"
                        "  /clear - Clear conversation history\n"
                    )
                    continue

                # Process query
                await self.process_query(query)

            except KeyboardInterrupt:
                self.console.print("\n[cyan]Goodbye![/cyan]")
                break
            except Exception as e:
                self.console.print(f"\n[red]Error: {e}[/red]")

    async def run_single_query(self, query: str):
        """Run a single query and exit."""
        # Build graph before processing (don't wait)
        import asyncio
        asyncio.create_task(self.build_codebase_graph())

        await self.process_query(query)

        # Show token usage
        self._show_token_usage()

    async def process_with_orchestrator(self, query: str):
        """Process a query using the AI orchestrator.

        Args:
            query: User's natural language goal
        """
        try:
            # Show that we're planning
            self.console.print("\n[bold cyan]🎯 Planning workflow...[/bold cyan]")

            # Execute goal through orchestrator
            result = await self.orchestrator.execute_goal(
                goal=query,
                auto_approve=self.config.auto_approve
            )

            # Display plan
            plan = result['plan']

            # Check if plan has parse error (fallback scenario)
            if len(plan['steps']) == 1 and plan['steps'][0].get('tool_name') == '_parse_error':
                self.console.print("[yellow]Could not create workflow plan, using normal conversation mode[/yellow]")
                await self.process_query_normal(query)
                return

            self.console.print(f"\n[bold]Goal:[/bold] {plan['goal']}")
            self.console.print(f"[dim]Steps: {len(plan['steps'])}[/dim]\n")

            # Show plan to user
            if plan['requires_approval'] and not self.config.auto_approve:
                self.console.print("[bold]Execution Plan:[/bold]")
                for i, step in enumerate(plan['steps'], 1):
                    tool_name = step['tool_name']
                    desc = step['description']
                    self.console.print(f"  {i}. [{tool_name}] {desc}")

                # Ask for approval
                self.console.print()
                approve = Prompt.ask(
                    "[bold yellow]Proceed with execution?[/bold yellow]",
                    choices=["y", "n"],
                    default="y"
                )

                if approve.lower() != 'y':
                    self.console.print("[yellow]Cancelled[/yellow]")
                    return

            # Execute (plan already executed, just show results)
            self.console.print("\n[bold cyan]📋 Execution Summary:[/bold cyan]\n")
            self.console.print(result['summary'])

            # Show success/failure
            if result['success']:
                self.console.print("\n[bold green]✓ Workflow completed successfully[/bold green]")
            else:
                self.console.print("\n[bold yellow]⚠ Workflow completed with some errors[/bold yellow]")

        except Exception as e:
            self.console.print(f"\n[red]Orchestration error: {e}[/red]")
            self.console.print("[dim]Falling back to normal conversation mode...[/dim]")
            # Fall back to normal processing
            await self.process_query_normal(query)

    def should_use_orchestrator(self, query: str) -> bool:
        """Determine if query should be handled by orchestrator.

        Queries that benefit from orchestration:
        - Build/create features ("add login page")
        - Multi-step workflows ("fix failing tests")
        - Testing workflows ("run tests and fix failures")
        - Code changes with validation ("refactor X and test")

        Queries that should use normal flow:
        - Simple questions ("what does this do?")
        - Explanations ("explain this code")
        - Direct slash commands already handled
        """
        query_lower = query.lower()

        # Orchestration triggers
        orchestration_patterns = [
            # Build/create
            r'(build|create|add|make|generate).*?(page|feature|component|function|class|api|endpoint)',
            # Testing
            r'(run|execute).*?tests?',
            r'fix.*?(test|failing)',
            # Workflows
            r'(refactor|optimize|improve).*?(and|then)',
            r'.*?(test|check|validate).*?(after|and)',
            # Commit
            r'(commit|save).*?(changes|work)',
        ]

        import re
        for pattern in orchestration_patterns:
            if re.search(pattern, query_lower):
                return True

        # Avoid orchestration for questions and reviews
        question_patterns = [
            r'^(what|why|how|when|where|who)',
            r'(explain|describe|tell me|show me)',
            r'^(review|look|check|examine|see)',
            r'(please|just|simply)\s+(review|look|check)'
        ]

        for pattern in question_patterns:
            if re.search(pattern, query_lower):
                return False

        # Default: use orchestrator for longer queries (likely tasks)
        # But not for very simple queries
        return len(query.split()) > 4 and len(query.split()) < 20

    async def process_query(self, query: str):
        """Process a user query."""
        # Log the raw input
        self.debug_logger.log_user_input(query, query)  # No processing currently

        # Check if this should be orchestrated
        use_orchestrator = self.should_use_orchestrator(query)

        if use_orchestrator:
            # Route through orchestrator for workflow execution
            await self.process_with_orchestrator(query)
            return

        # Otherwise use normal LLM conversation flow
        await self.process_query_normal(query)

    async def process_query_normal(self, query: str):
        """Process query through normal LLM conversation (non-orchestrated).

        Args:
            query: User's query or question
        """
        # Check token usage and warn if approaching limits
        usage = self.llm.get_token_usage()
        max_tokens = getattr(self.config, 'max_history', 8000)
        usage_percent = (usage['total_tokens'] / max_tokens) * 100 if max_tokens > 0 else 0

        # Always show compact token status
        if usage['total_tokens'] > 0:
            color = "red" if usage_percent > 90 else "yellow" if usage_percent > 80 else "dim cyan"
            self.console.print(
                f"[{color}]📊 Context: {usage['total_tokens']:,}/{max_tokens:,} tokens ({usage_percent:.0f}%) | "
                f"Cost: ${usage['estimated_cost']:.4f}[/{color}]"
            )

        if usage_percent > 90:
            self.console.print("[bold red]⚠ WARNING: Conversation is at 90%+ of token limit![/bold red]")
            self.console.print("[yellow]Strongly recommend using /clear to avoid rate limit errors[/yellow]\n")
        elif usage_percent > 80:
            self.console.print(f"[yellow]⚠ Token usage at {usage_percent:.0f}% - consider using /clear soon[/yellow]\n")

        # Start new workflow for each query
        self.workflow.start_workflow()

        # Show thinking indicator (only in real terminal, not in desktop/piped mode)
        if sys.stdin.isatty():
            self.console.print("\n[bold cyan]Flux[/bold cyan]:", end=" ")

        response_text = ""
        tool_uses = []

        # Build system prompt with project context, intelligent suggestions, and state
        system_prompt = self._build_system_prompt(query=query)

        # Add contextual state to prompt
        state_context = self.state_tracker.get_contextual_prompt_addon()
        if state_context:
            system_prompt += state_context

        # Log system prompt and context
        self.debug_logger.log_system_prompt(system_prompt)
        self.debug_logger.log_conversation_history(self.llm.conversation_history)

        # Get LLM response
        async for event in self.llm.send_message(
            message=query,
            system_prompt=system_prompt,
            tools=self.tools.get_all_schemas()
        ):
            if event["type"] == "text":
                # Stream text to console
                content = event["content"]
                response_text += content
                self.console.print(content, end="")

                # SMART BACKGROUND PROCESSING:
                # While user reads the streaming text, analyze it and
                # pre-load files that are likely to be needed next
                tasks = self.bg_processor.analyze_chunk(content)
                if tasks:
                    await self.bg_processor.schedule_and_run(tasks)

            elif event["type"] == "tool_use":
                tool_uses.append(event)

        # Log LLM response
        self.debug_logger.log_llm_response(response_text, tool_uses)

        # Track conversation in state tracker
        files_mentioned = []
        for tool_use in tool_uses:
            if 'path' in tool_use['input']:
                files_mentioned.append(tool_use['input']['path'])
            elif 'file_path' in tool_use['input']:
                files_mentioned.append(tool_use['input']['file_path'])
            elif 'paths' in tool_use['input']:
                files_mentioned.extend(tool_use['input']['paths'])
        tools_used = [t['name'] for t in tool_uses]
        self.state_tracker.track_conversation(query, response_text, files_mentioned, tools_used)

        # Record message event in session
        self.session_manager.record_event(
            self.EventType.MESSAGE,
            {
                'query': query,
                'response': response_text[:200],  # First 200 chars
                'tools_used': tools_used,
                'files_mentioned': files_mentioned
            }
        )

        # If there was text, add newline
        if response_text:
            self.console.print()

        # Execute tools
        if tool_uses:
            self.console.print()
            for tool_use in tool_uses:
                await self.execute_tool(tool_use)

            # Continue conversation with tool results
            await self.continue_after_tools()

    async def execute_tool(self, tool_use: dict):
        """Execute a tool and display results."""
        tool_name = tool_use["name"]
        tool_id = tool_use["id"]
        tool_input = tool_use["input"]

        # Display tool execution
        self.console.print(Panel(
            f"[bold]{tool_name}[/bold]\n[dim]{tool_input}[/dim]",
            title="🔧 Tool",
            border_style="blue"
        ))

        # CHECK FOR RETRY LOOP BEFORE EXECUTING
        if self.failure_tracker.is_retry_loop(tool_name, threshold=2):
            guidance = self.failure_tracker.get_retry_guidance(tool_name)
            if guidance:
                # BLOCK execution - force strategy change
                result = {
                    "error": {
                        "code": "RETRY_LOOP_DETECTED",
                        "message": f"Too many consecutive failures for {tool_name}. You MUST try a different approach.",
                    },
                    "retry_guidance": guidance,
                    "retry_blocked": True,
                    "previous_failures": self.failure_tracker.failure_count_by_tool.get(tool_name, 0)
                }

                # Add result and display blocking message
                self.llm.add_tool_result(tool_id, result)
                self.console.print(Panel(
                    f"[bold red]⚠️  RETRY LOOP DETECTED[/bold red]\n\n{guidance}",
                    title="❌ Blocked",
                    border_style="red"
                ))
                return  # Don't execute the tool

        # Execute tool
        try:
            result = await self.tools.execute(tool_name, **tool_input)
            success = not (isinstance(result, dict) and "error" in result)

            # Log tool execution
            self.debug_logger.log_tool_call(tool_name, tool_input, result, success)

            # SMART RETRY: If edit_file fails with SEARCH_TEXT_NOT_FOUND, auto-read and provide context
            if (tool_name == "edit_file" and
                isinstance(result, dict) and
                result.get("error", {}).get("code") == "SEARCH_TEXT_NOT_FOUND"):

                file_path = tool_input.get("path")
                if file_path:
                    retry_count = self.failure_tracker.failure_count_by_tool.get(tool_name, 0)
                    self.console.print(f"[yellow]⚠ Search text not found (attempt {retry_count + 1}). Reading file for context...[/yellow]")

                    # Read the file to get current content
                    try:
                        read_result = await self.tools.execute("read_files", paths=[file_path])

                        # Add helpful context to the error with stronger guidance
                        result["auto_recovery"] = {
                            "action": "file_read_completed",
                            "message": (
                                "⚠️  SEARCH TEXT NOT FOUND - File has been auto-read for you.\n\n"
                                "BEFORE RETRYING:\n"
                                "1. Look at the EXACT file content in the Result panel below\n"
                                "2. Copy the EXACT text you want to change (including ALL spaces/tabs)\n"
                                "3. DO NOT guess or try to remember - use the exact content shown\n"
                                "4. If this is your 2nd attempt, consider using a different tool or approach\n\n"
                                f"Retry count: {retry_count + 1}/2 (next failure will be blocked)"
                            ),
                            "file_content_available": True,
                            "retry_count": retry_count + 1
                        }

                        # Show the file content to user
                        self.console.print(Panel(
                            f"[dim]Auto-read {file_path} to help with retry[/dim]",
                            border_style="yellow"
                        ))

                        # Add the file read result to conversation immediately
                        # This allows the LLM to see the current file state
                        import uuid
                        read_tool_id = str(uuid.uuid4())
                        self.llm.add_tool_result(read_tool_id, read_result)

                    except Exception as read_error:
                        result["auto_recovery"] = {
                            "action": "file_read_failed",
                            "message": f"Failed to auto-read file: {str(read_error)}"
                        }

            # Check if result is an error
            is_error = isinstance(result, dict) and "error" in result

            if is_error:
                # Record failure
                error_data = result.get("error", {})
                # Handle both dict and string errors
                if isinstance(error_data, dict):
                    error_code = error_data.get("code")
                    error_message = error_data.get("message", str(error_data))
                else:
                    # Error is a string directly
                    error_code = None
                    error_message = str(error_data)

                self.failure_tracker.record_failure(
                    tool_name=tool_name,
                    error_code=error_code,
                    error_message=error_message,
                    input_params=tool_input
                )

                # Get failure count and show visual warning
                failure_count = self.failure_tracker.failure_count_by_tool.get(tool_name, 0)
                if failure_count == 2:
                    self.console.print(Panel(
                        f"[bold yellow]⚠️  {tool_name} has failed twice in a row[/bold yellow]\n\n"
                        f"The LLM should now try a DIFFERENT approach or tool.\n"
                        f"Next attempt will be automatically blocked.",
                        title="🔄 Retry Warning",
                        border_style="yellow"
                    ))

                # Check for retry loop and inject guidance
                if self.failure_tracker.is_retry_loop(tool_name):
                    guidance = self.failure_tracker.get_retry_guidance(tool_name)
                    if guidance:
                        # Inject guidance into the result for LLM to see
                        result["retry_guidance"] = guidance
            else:
                # Success - clear ALL failures (fresh start)
                if self.failure_tracker.failures:
                    self.console.print("[dim]✓ Operation successful - failure tracking reset[/dim]")
                self.failure_tracker.reset()

            # Record in memory
            self.memory.record_tool_use(tool_name, tool_input, result)

            # Record file edit events in session
            if tool_name == "edit_file" and success:
                file_path = tool_input.get("path")
                if file_path:
                    self.session_manager.record_event(
                        self.EventType.FILE_EDIT,
                        {'file': str(file_path)}
                    )

            # Record errors in session
            if is_error:
                error_data = result.get("error", {})
                if isinstance(error_data, dict):
                    error_message = error_data.get("message", str(error_data))
                else:
                    error_message = str(error_data)

                self.session_manager.record_error({
                    'message': error_message,
                    'tool': tool_name,
                    'file': tool_input.get('path') or tool_input.get('file_path')
                })

            # Update suggestions engine context
            if self.suggestions_engine:
                # Track file access
                if tool_name in ['read_files', 'write_file', 'edit_file', 'ast_edit']:
                    file_path = tool_input.get('file_path') or tool_input.get('path')
                    if file_path:
                        self.suggestions_engine.update_context(current_file=file_path)

                # Track commands
                elif tool_name == 'run_command':
                    command = tool_input.get('command', '')
                    self.suggestions_engine.update_context(recent_command=command)

            # Update workspace tracking
            if tool_name in ['read_files', 'write_file', 'edit_file', 'ast_edit']:
                file_path = tool_input.get('file_path') or tool_input.get('path')
                if file_path:
                    self.workspace.track_file_access(file_path)

                    # Track in state tracker too
                    if tool_name in ['write_file', 'edit_file', 'ast_edit']:
                        operation = 'write' if tool_name == 'write_file' else 'edit'
                        self.state_tracker.track_file_modification(file_path, operation)
            elif tool_name == 'run_command':
                command = tool_input.get('command', '')
                self.workspace.track_command(command)

                # Track command execution in state tracker
                exit_code = result.get('exit_code', 0) if isinstance(result, dict) else 0
                output_str = result.get('output', '') if isinstance(result, dict) else str(result)
                self.state_tracker.track_command(command, exit_code, output_str)

                # Parse errors from command output automatically
                if exit_code != 0 and isinstance(result, dict) and 'output' in result:
                    parsed_errors = self.error_parser.parse_output(output_str, command)
                    if parsed_errors:
                        # Add parsed errors to result for LLM context
                        result['parsed_errors'] = [e.to_dict() for e in parsed_errors]

                        # Show parsed errors to user
                        self.console.print("\n[bold yellow]🔍 Detected Errors:[/bold yellow]")
                        for i, error in enumerate(parsed_errors[:3], 1):  # Show top 3
                            self.console.print(f"\n{i}. {self.error_parser.format_error(error)}")

                        if len(parsed_errors) > 3:
                            self.console.print(f"\n[dim]... and {len(parsed_errors) - 3} more errors[/dim]")

                        self.console.print()  # Add spacing

                # Detect test commands and track results
                test_keywords = ['pytest', 'test', 'npm test', 'jest', 'mocha', 'cargo test', 'go test']
                if any(kw in command.lower() for kw in test_keywords):
                    passed = exit_code == 0
                    # Extract failures from output (simplified)
                    failures = []
                    if not passed and isinstance(result, dict) and 'output' in result:
                        # Try to extract test names from output
                        for line in result['output'].split('\n'):
                            if 'FAILED' in line or 'failed' in line.lower():
                                failures.append(line.strip()[:100])
                    self.state_tracker.track_test_result(command, passed, failures[:5])

            # Add result to conversation
            self.llm.add_tool_result(tool_id, result)

            # Display result (truncated if too long)
            result_str = str(result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."

            self.console.print(Panel(
                result_str,
                title="✓ Result",
                border_style="green"
            ))

        except KeyboardInterrupt:
            # User cancelled during tool execution
            error_msg = "Operation cancelled by user"
            self.llm.add_tool_result(tool_id, {"error": error_msg, "cancelled": True})
            self.console.print(Panel(
                error_msg,
                title="✗ Cancelled",
                border_style="yellow"
            ))
            # Don't re-raise - allow conversation to continue
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.llm.add_tool_result(tool_id, {"error": error_msg})

            self.console.print(Panel(
                error_msg,
                title="✗ Error",
                border_style="red"
            ))

    async def continue_after_tools(self):
        """Continue conversation after tool execution."""
        try:
            # Show thinking indicator (only in real terminal, not in desktop/piped mode)
            if sys.stdin.isatty():
                self.console.print("\n[bold cyan]Flux[/bold cyan]:", end=" ")

            response_text = ""
            tool_uses = []

            # Build system prompt with project context and retry warnings
            system_prompt = self._build_system_prompt()

            # Add retry context if there are failures
            retry_context = self._get_retry_context()
            if retry_context:
                system_prompt += retry_context

            # Send empty message to get LLM's response to tool results
            async for event in self.llm.send_message(
                message="",
                system_prompt=system_prompt,
                tools=self.tools.get_all_schemas()
            ):
                if event["type"] == "text":
                    content = event["content"]
                    response_text += content
                    self.console.print(content, end="")

                elif event["type"] == "tool_use":
                    tool_uses.append(event)

            if response_text:
                self.console.print()

            # Execute more tools if needed (recursive)
            if tool_uses:
                self.console.print()
                for tool_use in tool_uses:
                    await self.execute_tool(tool_use)

                await self.continue_after_tools()

        except KeyboardInterrupt:
            # User cancelled during continuation
            self.console.print("\n[yellow]Operation cancelled[/yellow]")
            # Don't re-raise - return to main loop
        except Exception as e:
            # Log error but don't crash - allow user to continue
            self.console.print(f"\n[red]Error in conversation: {e}[/red]")
            self.console.print("[dim]You can continue chatting - the error has been handled[/dim]")

    def _get_retry_context(self) -> str:
        """Get retry context warning for system prompt."""
        if not self.failure_tracker.failures:
            return ""

        # Check for tools that have failed multiple times
        warnings = []
        for tool_name, count in self.failure_tracker.failure_count_by_tool.items():
            if count >= 2:
                warnings.append(
                    f"⚠️  CRITICAL: {tool_name} has failed {count} times. "
                    f"DO NOT retry the same approach. Try:\n"
                    f"  - Re-read files and copy EXACT text\n"
                    f"  - Use a different tool (e.g., ast_edit for Python)\n"
                    f"  - Break the change into smaller steps\n"
                    f"  - Ask for clarification if unclear"
                )

        if warnings:
            return "\n\n" + "\n\n".join(warnings) + "\n"
        return ""

    def _build_system_prompt(self, query: Optional[str] = None) -> str:
        """Build system prompt with project context and intelligence."""
        prompt = SYSTEM_PROMPT

        # Add minimal project context
        if self.project_info:
            # Condensed version - just essentials
            prompt += f"\n\nProject: {self.project_info.name} ({self.project_info.project_type})"
            if self.project_info.frameworks:
                prompt += f" | {', '.join(self.project_info.frameworks[:2])}"

        # Add README only on first query, keep it very brief
        if self._project_readme and query and len(self.llm.conversation_history) < 2:
            # Limit to 500 chars to save tokens (reduced from 1000)
            readme_snippet = self._project_readme[:500]
            prompt += f"\n\nREADME: {readme_snippet}"

        # Minimal codebase intelligence - only when relevant
        if self.codebase_graph and query:
            # Only add file suggestions if they exist (limit to 2)
            suggested_files = self.get_intelligent_context(query)
            if suggested_files:
                prompt += f"\n\nRelevant: {', '.join(suggested_files[:2])}"

        # Only add memory context if there's an active task
        if self.memory.state.current_task:
            prompt += f"\n\nCurrent task: {self.memory.state.current_task}"

        # Add session context for AI
        session_context = self.session_manager.get_context_for_ai()
        if session_context.get('recent_events'):
            prompt += "\n\nRecent session activity:"
            for event in session_context['recent_events'][:3]:  # Last 3 events
                prompt += f"\n- {event['type']}: {event.get('summary', 'N/A')}"

        if session_context.get('current_task'):
            prompt += f"\n\nActive task: {session_context['current_task']}"

        return prompt

    def _print_monitor_notification(self, message: str):
        """Callback for proactive monitor notifications."""
        self.console.print(message)

    def _show_token_usage(self):
        """Display token usage statistics."""
        usage = self.llm.get_token_usage()

        if usage["total_tokens"] > 0:
            self.console.print()
            self.console.print(
                f"[dim]Tokens: {usage['input_tokens']:,} in / {usage['output_tokens']:,} out "
                f"(total: {usage['total_tokens']:,}) | "
                f"Cost: ${usage['estimated_cost']:.4f}[/dim]"
            )

    async def show_diff(self):
        """Show git diff using visual diff viewer."""
        from flux.ui.diff_viewer import create_diff_viewer_from_git

        status = self.git.get_status()

        if not status.is_repo:
            self.console.print("[red]Not in a git repository[/red]")
            return

        if not status.has_changes:
            self.console.print("[green]No changes to show[/green]")
            return

        # Show branch info
        self.console.print(f"\n[bold]Branch:[/bold] {status.branch}")

        # Create and populate diff viewer
        viewer = create_diff_viewer_from_git(self.console, self.git, self.cwd)

        # Display the visual diff
        viewer.display_summary()

    async def smart_commit(self, query: str):
        """Create a smart commit."""
        status = self.git.get_status()

        if not status.is_repo:
            self.console.print("[red]Not in a git repository[/red]")
            return

        if not status.has_changes:
            self.console.print("[yellow]No changes to commit[/yellow]")
            return

        # Check if message provided
        message = None
        if len(query.strip()) > 7:  # More than just "/commit"
            message = query[7:].strip()

        # Generate message if not provided
        if not message:
            all_files = status.staged_files + status.modified_files + status.untracked_files
            message = self.git.create_smart_commit_message(all_files)
            self.console.print(f"\n[bold]Generated commit message:[/bold]")
            self.console.print(f"  {message}\n")

            # Ask for confirmation
            from rich.prompt import Confirm
            if not Confirm.ask("Use this message?"):
                self.console.print("[yellow]Commit cancelled[/yellow]")
                return

        # Stage all changed files
        files_to_commit = status.modified_files + status.untracked_files
        if files_to_commit:
            success, msg = self.git.stage_files(files_to_commit)
            if not success:
                self.console.print(f"[red]Failed to stage files: {msg}[/red]")
                return

        # Create commit
        success, msg = self.git.commit(message)
        if success:
            self.console.print(f"[green]✓ {msg}[/green]")
            self.memory.add_checkpoint(f"Committed: {message}")
        else:
            self.console.print(f"[red]✗ {msg}[/red]")

    async def run_tests(self, file_filter: Optional[str] = None):
        """Run project tests using the smart test runner."""
        self.console.print(f"\n[bold]Running tests...[/bold] (Framework: {self.test_runner.framework.value})\n")

        # Run tests
        import asyncio
        result = await asyncio.to_thread(self.test_runner.run_tests, file_filter)

        # Display results
        self._display_test_result(result)

        # Update state tracker
        if result.status.value == "failed":
            self.state_tracker.record_test_failure([
                {"name": f.test_name, "error": f.error_message}
                for f in result.failures
            ])
        else:
            self.state_tracker.record_test_success()

        # Update session with test status
        self.session_manager.update_test_status({
            'total': result.total_tests,
            'passed': result.passed,
            'failed': result.failed,
            'skipped': result.skipped,
            'duration': result.duration
        })

    def _display_test_result(self, result: TestResult):
        """Display test results in a beautiful format."""
        # Summary panel
        status_icon = "✓" if result.success else "✗"
        status_color = "green" if result.success else "red"

        summary = (
            f"[bold]{result.framework.value.upper()} Test Results[/bold]\n\n"
            f"Tests: [{status_color}]{result.total_tests}[/{status_color}]\n"
            f"Passed: [green]{result.passed}[/green]\n"
            f"Failed: [red]{result.failed}[/red]\n"
        )

        if result.skipped > 0:
            summary += f"Skipped: [yellow]{result.skipped}[/yellow]\n"

        if result.duration > 0:
            summary += f"Duration: [cyan]{result.duration:.2f}s[/cyan]\n"

        if result.total_tests > 0:
            summary += f"Pass Rate: [cyan]{result.pass_rate:.1f}%[/cyan]"

        self.console.print(Panel(
            summary,
            title=f"{status_icon} Test Results",
            border_style=status_color
        ))

        # Show failures if any
        if result.failures:
            self.console.print("\n[bold red]Failures:[/bold red]\n")
            for failure in result.failures:
                self.console.print(f"  ❌ {failure.test_name}")
                if failure.file_path:
                    self.console.print(f"     File: [cyan]{failure.file_path}[/cyan]")
                if failure.error_message:
                    # Truncate long error messages
                    error = failure.error_message[:200]
                    if len(failure.error_message) > 200:
                        error += "..."
                    self.console.print(f"     Error: [dim]{error}[/dim]")
                self.console.print()

    async def start_watch_mode(self):
        """Start test watch mode."""
        if self.test_watcher and self.test_watcher.is_running:
            self.console.print("[yellow]Watch mode already running[/yellow]")
            return

        self.console.print("\n[bold cyan]Starting test watch mode...[/bold cyan]")
        self.console.print(f"Framework: [green]{self.test_runner.framework.value}[/green]")
        self.console.print(f"Watching: [cyan]{self.cwd}[/cyan]")
        self.console.print("\n[dim]Tests will run automatically when files change[/dim]")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        # Create watcher with callback
        self.test_watcher = TestWatcher(
            self.test_runner,
            on_test_complete=self._on_watch_test_complete
        )

        await self.test_watcher.start()

        # Run tests once on start
        self.console.print("[dim]Running initial test suite...[/dim]\n")
        result = await asyncio.to_thread(self.test_runner.run_tests)
        self._display_test_result(result)

        try:
            # Keep running until interrupted
            while self.test_watcher.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Stopping watch mode...[/yellow]")
            self.stop_watch_mode()

    def stop_watch_mode(self):
        """Stop test watch mode."""
        if self.test_watcher:
            self.test_watcher.stop()
            self.test_watcher = None
            self.console.print("[green]✓ Watch mode stopped[/green]")

    def _on_watch_test_complete(self, result: TestResult):
        """Callback when watch mode tests complete."""
        self.console.print("\n" + "─" * 80 + "\n")
        self.console.print("[bold]Tests completed[/bold]")
        self._display_test_result(result)

    async def show_related_files(self, file_or_query: str):
        """Show files related to a file or query."""
        # Build graph if not built
        if not self.codebase_graph:
            await self.build_codebase_graph()

        if not self.codebase_graph:
            self.console.print("[red]Could not build codebase graph[/red]")
            return

        # Find related files
        related = self.codebase_graph.find_related_files(file_or_query, limit=10)

        if not related:
            self.console.print(f"[yellow]No related files found for '{file_or_query}'[/yellow]")
            return

        self.console.print(f"\n[bold]Related files for '{file_or_query}':[/bold]\n")
        for file_path, score in related:
            # Show file with score indicator
            score_indicator = "🔥" if score > 10 else "🔹" if score > 5 else "🔸"
            self.console.print(f"  {score_indicator} [cyan]{file_path}[/cyan] [dim](score: {score:.1f})[/dim]")

            # Show file context
            context = self.codebase_graph.get_file_context(file_path)
            if context.get('entities'):
                entities = context['entities'][:3]  # Show first 3
                for ent in entities:
                    self.console.print(f"     - {ent['type']}: {ent['name']}")

        self.console.print()

    async def show_file_preview(self, file_path: str):
        """Show preview of what would happen if file is modified."""
        if not self.impact_analyzer:
            self.console.print("[yellow]Impact analyzer not available. Run /index first.[/yellow]")
            return

        # Read current file
        full_path = self.cwd / file_path
        if not full_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            with open(full_path, 'r') as f:
                current_content = f.read()
        except Exception as e:
            self.console.print(f"[red]Error reading file: {e}[/red]")
            return

        # Show current file info
        self.console.print(f"\n[bold]Preview for:[/bold] [cyan]{file_path}[/cyan]\n")

        # Get file context from codebase graph
        if self.codebase_graph and file_path in self.codebase_graph.files:
            context = self.codebase_graph.get_file_context(file_path)

            self.console.print(f"[bold]Current State:[/bold]")
            self.console.print(f"  Language: {context.get('language', 'unknown')}")
            self.console.print(f"  Entities: {len(context.get('entities', []))}")

            if context.get('entities'):
                self.console.print(f"\n[bold]Defined in this file:[/bold]")
                for entity in context['entities'][:5]:
                    self.console.print(f"  - {entity['type']}: {entity['name']} (line {entity['line']})")

            if context.get('dependencies'):
                self.console.print(f"\n[bold]Dependencies:[/bold]")
                for dep in context['dependencies'][:3]:
                    self.console.print(f"  → {dep}")

            if context.get('dependents'):
                self.console.print(f"\n[bold]Files that depend on this:[/bold]")
                for dep in context['dependents'][:3]:
                    self.console.print(f"  ← {dep}")
                if len(context['dependents']) > 3:
                    self.console.print(f"  ... and {len(context['dependents']) - 3} more")

        self.console.print(f"\n[dim]To see impact of specific changes, modify the file and Flux will show the analysis.[/dim]")
        self.console.print()

    def show_impact_analysis(self, impact, show_diff: bool = False):
        """Display impact analysis in a beautiful format."""
        from flux.core.impact_analyzer import ImpactLevel

        # Impact level badge
        level_colors = {
            ImpactLevel.LOW: "green",
            ImpactLevel.MEDIUM: "yellow",
            ImpactLevel.HIGH: "red",
            ImpactLevel.CRITICAL: "bold red"
        }
        level_emoji = {
            ImpactLevel.LOW: "🟢",
            ImpactLevel.MEDIUM: "🟡",
            ImpactLevel.HIGH: "🔴",
            ImpactLevel.CRITICAL: "⚫"
        }

        color = level_colors.get(impact.impact_level, "white")
        emoji = level_emoji.get(impact.impact_level, "○")

        self.console.print(f"\n[bold]📊 Impact Analysis[/bold]")
        self.console.print("=" * 50)

        # Summary
        self.console.print(f"\n[{color}]{emoji} {impact.impact_level.value.upper()}[/{color}] - {impact.change_type.value}")
        self.console.print(f"Confidence: [{self._get_confidence_color(impact.confidence_score)}]{impact.confidence_score * 100:.0f}%[/]")

        # What's affected
        if impact.functions_affected:
            self.console.print(f"\n[bold]Functions:[/bold] {', '.join(impact.functions_affected[:5])}")
            if len(impact.functions_affected) > 5:
                self.console.print(f"  ... and {len(impact.functions_affected) - 5} more")

        if impact.classes_affected:
            self.console.print(f"[bold]Classes:[/bold] {', '.join(impact.classes_affected)}")

        if impact.dependencies_affected:
            self.console.print(f"\n[bold]Dependencies affected:[/bold]")
            for dep in impact.dependencies_affected:
                self.console.print(f"  ← {dep}")

        # Dependency Impact Tree
        if impact.dependency_tree:
            self._show_dependency_tree(impact)

        # Warnings
        if impact.warnings:
            self.console.print(f"\n[bold yellow]Warnings:[/bold yellow]")
            for warning in impact.warnings:
                self.console.print(f"  {warning}")

        # Suggestions
        if impact.suggestions:
            self.console.print(f"\n[bold cyan]Suggestions:[/bold cyan]")
            for suggestion in impact.suggestions:
                self.console.print(f"  {suggestion}")

        # Risk flags
        if impact.breaks_existing_code:
            self.console.print(f"\n[bold red]⚠️  May break existing code![/bold red]")
        if impact.requires_migration:
            self.console.print(f"[bold yellow]⚠️  May require data migration[/bold yellow]")
        if impact.affects_public_api:
            self.console.print(f"[bold yellow]⚠️  Affects public API[/bold yellow]")

        self.console.print("=" * 50)

    def _get_confidence_color(self, confidence: float) -> str:
        """Get color for confidence score."""
        if confidence >= 0.95:
            return "green"
        elif confidence >= 0.80:
            return "cyan"
        elif confidence >= 0.60:
            return "yellow"
        else:
            return "red"

    def _show_dependency_tree(self, impact):
        """Display visual dependency impact tree."""

        self.console.print(f"\n[bold]🌳 Dependency Impact Tree:[/bold]")
        self.console.print(f"[dim]Propagation depth: {impact.propagation_depth} layer(s)[/dim]\n")

        # Group by impact type
        direct_deps = {k: v for k, v in impact.dependency_tree.items() if v.impact_type == "direct"}
        indirect_deps = {k: v for k, v in impact.dependency_tree.items() if v.impact_type == "indirect"}
        test_deps = {k: v for k, v in impact.dependency_tree.items() if v.impact_type == "test"}

        # Show direct dependencies
        if direct_deps:
            self.console.print(f"[bold cyan]Direct Impact:[/bold cyan]")
            for file_path, dep_impact in list(direct_deps.items())[:8]:  # Limit display
                self._show_dependency_node(file_path, dep_impact, prefix="  ")

        # Show test dependencies
        if test_deps:
            self.console.print(f"\n[bold yellow]Test Files:[/bold yellow]")
            for file_path, dep_impact in list(test_deps.items())[:5]:
                self._show_dependency_node(file_path, dep_impact, prefix="  ")

        # Show indirect dependencies
        if indirect_deps:
            self.console.print(f"\n[bold magenta]Indirect Impact:[/bold magenta]")
            for file_path, dep_impact in list(indirect_deps.items())[:5]:
                self._show_dependency_node(file_path, dep_impact, prefix="  ", show_details=False)

        # Summary
        total_deps = len(impact.dependency_tree)
        if total_deps > 18:  # If we didn't show all
            self.console.print(f"\n[dim]... and {total_deps - 18} more files affected[/dim]")

    def _show_dependency_node(self, file_path: str, dep_impact, prefix: str = "", show_details: bool = True):
        """Display a single dependency node."""
        # Risk emoji and color
        risk_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }
        risk_color = {
            "high": "red",
            "medium": "yellow",
            "low": "green"
        }

        emoji = risk_emoji.get(dep_impact.break_risk, "○")
        color = risk_color.get(dep_impact.break_risk, "white")

        # File path with risk indicator
        self.console.print(f"{prefix}├─ {emoji} [{color}]{file_path}[/{color}]")

        if show_details:
            # Show what functions/classes are used
            if dep_impact.functions_used:
                funcs = ", ".join(dep_impact.functions_used[:3])
                if len(dep_impact.functions_used) > 3:
                    funcs += f" +{len(dep_impact.functions_used) - 3}"
                self.console.print(f"{prefix}│  [dim]→ uses functions: {funcs}[/dim]")

            if dep_impact.classes_used:
                classes = ", ".join(dep_impact.classes_used[:3])
                if len(dep_impact.classes_used) > 3:
                    classes += f" +{len(dep_impact.classes_used) - 3}"
                self.console.print(f"{prefix}│  [dim]→ uses classes: {classes}[/dim]")

            # Show break risk if not low
            if dep_impact.break_risk != "low":
                self.console.print(f"{prefix}│  [{color}]⚠ {dep_impact.break_risk} risk of breaking[/{color}]")

    async def show_architecture(self):
        """Show detected architecture patterns."""
        # Build graph if not built
        if not self.codebase_graph:
            await self.build_codebase_graph()

        if not self.codebase_graph:
            self.console.print("[red]Could not build codebase graph[/red]")
            return

        patterns = self.codebase_graph.detect_architecture_patterns()

        self.console.print("\n[bold]Project Architecture:[/bold]\n")
        self.console.print(f"  Framework: [cyan]{patterns.get('framework', 'Unknown')}[/cyan]")
        self.console.print(f"  Structure: [cyan]{patterns.get('structure', 'Unknown')}[/cyan]")
        self.console.print(f"  Testing: [cyan]{patterns.get('testing', 'None detected')}[/cyan]")
        self.console.print(f"  Has tests: [{'green' if patterns.get('has_tests') else 'red'}]{patterns.get('has_tests')}[/]")
        self.console.print(f"  Has docs: [{'green' if patterns.get('has_docs') else 'red'}]{patterns.get('has_docs')}[/]")

        # Show file/entity statistics
        self.console.print(f"\n[bold]Statistics:[/bold]")
        self.console.print(f"  Total files: [cyan]{len(self.codebase_graph.files)}[/cyan]")
        self.console.print(f"  Total entities: [cyan]{len(self.codebase_graph.entities)}[/cyan]")

        # Show most connected files
        most_connected = sorted(
            self.codebase_graph.files.items(),
            key=lambda x: len(x[1].dependencies) + len(x[1].dependents),
            reverse=True
        )[:5]

        if most_connected:
            self.console.print(f"\n[bold]Most Connected Files:[/bold]")
            for file_path, file_node in most_connected:
                connections = len(file_node.dependencies) + len(file_node.dependents)
                self.console.print(f"  [cyan]{file_path}[/cyan] [dim]({connections} connections)[/dim]")

        self.console.print()

    async def show_suggestions(self):
        """Show proactive AI suggestions."""
        # Build graph and initialize suggestions engine if needed
        if not self.suggestions_engine:
            await self.build_codebase_graph()

        if not self.suggestions_engine:
            self.console.print("[red]Suggestions engine not available[/red]")
            return

        # Get suggestions
        suggestions = self.suggestions_engine.get_suggestions(max_suggestions=10, min_priority=Priority.LOW)

        if not suggestions:
            self.console.print("\n[green]✓ No suggestions - everything looks good![/green]\n")
            return

        # Display suggestions
        self.console.print("\n[bold]💡 Proactive Suggestions:[/bold]")
        self.console.print("=" * 60)

        # Group by priority
        by_priority = {}
        for s in suggestions:
            if s.priority not in by_priority:
                by_priority[s.priority] = []
            by_priority[s.priority].append(s)

        priority_order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]

        for priority in priority_order:
            if priority not in by_priority:
                continue

            priority_suggestions = by_priority[priority]

            # Priority header
            priority_emoji = {
                Priority.CRITICAL: "🔴",
                Priority.HIGH: "🟠",
                Priority.MEDIUM: "🟡",
                Priority.LOW: "🟢"
            }
            priority_color = {
                Priority.CRITICAL: "red",
                Priority.HIGH: "yellow",
                Priority.MEDIUM: "cyan",
                Priority.LOW: "green"
            }

            emoji = priority_emoji.get(priority, "○")
            color = priority_color.get(priority, "white")

            self.console.print(f"\n[{color}]{emoji} {priority.value.upper()}[/{color}]")

            # Show suggestions
            for i, suggestion in enumerate(priority_suggestions, 1):
                self._show_suggestion(suggestion, index=i)

        self.console.print("\n" + "=" * 60)
        self.console.print("[dim]Tip: Ask Flux to implement any of these suggestions![/dim]\n")

    def _show_suggestion(self, suggestion, index: int):
        """Display a single suggestion."""
        # Type icon
        type_icons = {
            "next_action": "▶️",
            "code_quality": "✨",
            "security": "🔒",
            "performance": "⚡",
            "testing": "🧪",
            "documentation": "📝",
            "refactoring": "♻️"
        }
        icon = type_icons.get(suggestion.type.value, "•")

        # Title
        self.console.print(f"\n  {index}. {icon} [bold]{suggestion.title}[/bold]")

        # Description
        self.console.print(f"     [dim]{suggestion.description}[/dim]")

        # File and line
        if suggestion.file_path:
            location = f"{suggestion.file_path}"
            if suggestion.line_number:
                location += f":{suggestion.line_number}"
            self.console.print(f"     📍 {location}")

        # Action (what Flux can do)
        if suggestion.action:
            self.console.print(f"     💡 [cyan]{suggestion.action}[/cyan]")

        # Confidence
        confidence_color = self._get_confidence_color(suggestion.confidence)
        self.console.print(f"     Confidence: [{confidence_color}]{suggestion.confidence * 100:.0f}%[/{confidence_color}]")

        # Reasoning
        if suggestion.reasoning:
            self.console.print(f"     [dim italic]Why: {suggestion.reasoning}[/dim italic]")

    # Workspace Intelligence Commands

    async def handle_session_command(self, args: str):
        """Handle session sub-commands."""
        parts = args.split(maxsplit=1)
        if not parts:
            self.console.print("[red]Usage: /session save <name> | /session restore <id>[/red]")
            return

        command = parts[0].lower()

        if command == "save":
            name = parts[1] if len(parts) > 1 else "Work Session"
            session = self.workspace.save_session(name)
            self.console.print(f"[green]✓ Session saved:[/green] {session.name}")
            self.console.print(f"   ID: [cyan]{session.id}[/cyan]")
            self.console.print(f"   Files: {len(session.files_modified)}")
            self.console.print(f"   Time: {session.time_spent_seconds / 60:.1f} minutes")

        elif command == "restore":
            if len(parts) < 2:
                self.console.print("[red]Please provide session ID[/red]")
                return

            session_id = parts[1]
            session = self.workspace.restore_session(session_id)

            if session:
                self.console.print(f"[green]✓ Restored session:[/green] {session.name}")
                self.console.print(f"   Files: {len(session.open_files)}")
                if session.current_task_id:
                    task = self.workspace.get_task(session.current_task_id)
                    if task:
                        self.console.print(f"   Task: [yellow]{task.title}[/yellow]")
            else:
                self.console.print(f"[red]✗ Session not found: {session_id}[/red]")

        elif command == "end":
            summary = self.workspace.end_session()
            if summary:
                self.console.print(f"[green]✓ Session ended:[/green] {summary.session_name}")
                self.console.print(f"\n{summary.summary_text}")

                if summary.key_achievements:
                    self.console.print(f"\n[bold]Key Achievements:[/bold]")
                    for achievement in summary.key_achievements:
                        self.console.print(f"  {achievement}")
            else:
                self.console.print("[yellow]No active session[/yellow]")

        else:
            self.console.print(f"[red]Unknown session command: {command}[/red]")

    async def list_sessions(self):
        """List all sessions."""
        sessions = self.workspace.list_sessions(limit=10)

        if not sessions:
            self.console.print("\n[yellow]No sessions found[/yellow]\n")
            return

        self.console.print("\n[bold]📋 Work Sessions:[/bold]")
        self.console.print("=" * 60)

        for i, session in enumerate(sessions, 1):
            # Time info
            from datetime import datetime
            updated = datetime.fromtimestamp(session.updated_at).strftime("%Y-%m-%d %H:%M")
            duration = session.time_spent_seconds / 60

            # Status indicator
            is_active = self.workspace.active_session and self.workspace.active_session.id == session.id
            status = "▶️ [green]ACTIVE[/green]" if is_active else "  "

            self.console.print(f"\n{status} {i}. [bold]{session.name}[/bold]")
            self.console.print(f"     ID: [dim]{session.id}[/dim]")
            self.console.print(f"     Updated: {updated}")
            self.console.print(f"     Duration: {duration:.1f} minutes")
            self.console.print(f"     Files: {len(session.files_modified)}")

            if session.description:
                self.console.print(f"     [dim]{session.description}[/dim]")

        self.console.print("\n" + "=" * 60)
        self.console.print("[dim]Use /session restore <id> to restore a session[/dim]\n")

    async def create_task(self, title: str):
        """Create a new task."""
        if not title:
            self.console.print("[red]Please provide a task title[/red]")
            return

        task = self.workspace.create_task(title)
        self.console.print(f"[green]✓ Task created:[/green] {task.title}")
        self.console.print(f"   ID: [cyan]{task.id}[/cyan]")
        self.console.print(f"   Priority: {task.priority.value}")
        self.console.print(f"   Status: {task.status.value}")

    async def list_tasks(self):
        """List all tasks."""
        tasks = self.workspace.list_tasks(limit=20)

        if not tasks:
            self.console.print("\n[yellow]No tasks found[/yellow]")
            self.console.print("[dim]Create one with: /newtask <title>[/dim]\n")
            return

        self.console.print("\n[bold]✅ Tasks:[/bold]")
        self.console.print("=" * 60)

        # Group by status
        by_status = {}
        for task in tasks:
            if task.status not in by_status:
                by_status[task.status] = []
            by_status[task.status].append(task)

        # Status emoji and colors
        status_emoji = {
            TaskStatus.TODO: "○",
            TaskStatus.IN_PROGRESS: "▶️",
            TaskStatus.BLOCKED: "⛔",
            TaskStatus.DONE: "✅",
            TaskStatus.CANCELLED: "❌"
        }

        status_color = {
            TaskStatus.TODO: "white",
            TaskStatus.IN_PROGRESS: "cyan",
            TaskStatus.BLOCKED: "yellow",
            TaskStatus.DONE: "green",
            TaskStatus.CANCELLED: "red"
        }

        # Priority emoji
        priority_emoji = {
            TaskPriority.URGENT: "🔴",
            TaskPriority.HIGH: "🟠",
            TaskPriority.MEDIUM: "🟡",
            TaskPriority.LOW: "🟢",
            TaskPriority.BACKLOG: "⬜"
        }

        # Show tasks by status
        for status in [TaskStatus.IN_PROGRESS, TaskStatus.TODO, TaskStatus.BLOCKED, TaskStatus.DONE]:
            if status not in by_status:
                continue

            status_tasks = by_status[status]
            emoji = status_emoji.get(status, "○")
            color = status_color.get(status, "white")

            self.console.print(f"\n[{color}]{emoji} {status.value.upper().replace('_', ' ')}[/{color}]")

            for task in status_tasks[:10]:  # Limit per status
                priority_icon = priority_emoji.get(task.priority, "")

                # Show current task indicator
                current = "🎯 " if (self.workspace.active_session and
                                         self.workspace.active_session.current_task_id == task.id) else "   "

                self.console.print(f"{current}{priority_icon} [bold]{task.title}[/bold]")
                self.console.print(f"       [dim]ID: {task.id} | Priority: {task.priority.value}[/dim]")

                if task.description:
                    desc = task.description[:60] + "..." if len(task.description) > 60 else task.description
                    self.console.print(f"       [dim]{desc}[/dim]")

        # Suggest next task
        next_task = self.workspace.suggest_next_task()
        if next_task:
            self.console.print(f"\n[bold cyan]💡 Suggested Next Task:[/bold cyan]")
            self.console.print(f"   {next_task.title}")
            self.console.print(f"   [dim]Priority: {next_task.priority.value} | ID: {next_task.id}[/dim]")

        self.console.print("\n" + "=" * 60 + "\n")

    async def show_work_summary(self):
        """Show work summary for today."""
        summary = self.workspace.get_daily_summary()

        self.console.print("\n[bold]📊 Today's Work Summary:[/bold]")
        self.console.print("=" * 60)

        self.console.print(f"\n🕒 Time: {summary['total_minutes']:.1f} minutes")
        if summary['total_minutes'] >= 60:
            hours = summary['total_minutes'] / 60
            self.console.print(f"      ({hours:.1f} hours)")

        self.console.print(f"\n📋 Sessions: {summary['sessions']}")
        self.console.print(f"📄 Files Modified: {summary['files_modified']}")
        self.console.print(f"✅ Tasks Completed: {summary['tasks_completed']}")

        if summary['completed_task_titles']:
            self.console.print(f"\n[bold]Completed Tasks:[/bold]")
            for task_title in summary['completed_task_titles']:
                self.console.print(f"  ✓ {task_title}")

        # Show active session info
        if self.workspace.active_session:
            session = self.workspace.active_session
            self.console.print(f"\n[bold cyan]Active Session:[/bold cyan] {session.name}")
            self.console.print(f"  Duration: {session.time_spent_seconds / 60:.1f} minutes")
            self.console.print(f"  Files: {len(session.files_modified)}")

            if session.current_task_id:
                task = self.workspace.get_task(session.current_task_id)
                if task:
                    self.console.print(f"  Current Task: [yellow]{task.title}[/yellow]")

        self.console.print("\n" + "=" * 60 + "\n")

    async def inspect_state(self):
        """Inspect current conversation and context state."""
        self.console.print("\n[bold]🔍 Conversation State Inspector[/bold]")
        self.console.print("=" * 70)

        # Conversation history stats
        history = self.llm.conversation_history
        self.console.print(f"\n[bold cyan]Conversation History:[/bold cyan]")
        self.console.print(f"  Total messages: [cyan]{len(history)}[/cyan]")

        # Count by role
        user_msgs = sum(1 for m in history if m.get('role') == 'user')
        assistant_msgs = sum(1 for m in history if m.get('role') == 'assistant')
        tool_msgs = sum(1 for m in history if m.get('role') == 'tool')

        self.console.print(f"  User messages: [green]{user_msgs}[/green]")
        self.console.print(f"  Assistant messages: [yellow]{assistant_msgs}[/yellow]")
        self.console.print(f"  Tool messages: [blue]{tool_msgs}[/blue]")

        # Estimate token usage
        total_chars = sum(len(str(m.get('content', ''))) for m in history)
        est_tokens = total_chars // 4
        self.console.print(f"  Estimated tokens: [cyan]~{est_tokens:,}[/cyan]")

        # Recent messages
        self.console.print(f"\n[bold cyan]Last 5 Messages:[/bold cyan]")
        for i, msg in enumerate(history[-5:], 1):
            role = msg.get('role', 'unknown')
            content = str(msg.get('content', ''))[:100]
            has_tools = 'tool_calls' in msg

            role_color = {'user': 'green', 'assistant': 'yellow', 'tool': 'blue'}.get(role, 'white')
            self.console.print(f"  {i}. [{role_color}]{role}[/{role_color}]: {content}{'...' if len(str(msg.get('content', ''))) > 100 else ''}")
            if has_tools:
                self.console.print(f"     [dim](includes tool calls)[/dim]")

        # Current context
        self.console.print(f"\n[bold cyan]Current Context:[/bold cyan]")
        if self.memory.state.current_task:
            self.console.print(f"  Task: [yellow]{self.memory.state.current_task}[/yellow]")
        else:
            self.console.print(f"  Task: [dim]None[/dim]")

        # Modified files
        modified = self.workflow.get_modified_files()
        self.console.print(f"  Modified files: [cyan]{len(modified)}[/cyan]")
        if modified:
            for f in modified[:5]:
                self.console.print(f"    - {f}")
            if len(modified) > 5:
                self.console.print(f"    ... and {len(modified) - 5} more")

        # Failure tracker state
        if self.failure_tracker.failures:
            self.console.print(f"\n[bold yellow]⚠️  Active Failures:[/bold yellow]")
            for tool_name, count in self.failure_tracker.failure_count_by_tool.items():
                self.console.print(f"  - {tool_name}: {count} failures")

        # Token usage from LLM
        usage = self.llm.get_token_usage()
        self.console.print(f"\n[bold cyan]Token Usage:[/bold cyan]")
        self.console.print(f"  Input: [cyan]{usage['input_tokens']:,}[/cyan]")
        self.console.print(f"  Output: [cyan]{usage['output_tokens']:,}[/cyan]")
        self.console.print(f"  Total: [cyan]{usage['total_tokens']:,}[/cyan]")
        self.console.print(f"  Cost: [green]${usage['estimated_cost']:.4f}[/green]")

        max_history = getattr(self.config, 'max_history', 8000)
        usage_percent = (usage['total_tokens'] / max_history) * 100 if max_history > 0 else 0

        if usage_percent > 80:
            self.console.print(f"  [yellow]⚠️  At {usage_percent:.0f}% of limit[/yellow]")

        self.console.print("\n" + "=" * 70 + "\n")

    async def show_project_stats(self):
        """Show project-level statistics."""
        if not self.codebase_graph:
            await self.build_codebase_graph()

        if not self.codebase_graph:
            self.console.print("[red]Could not build codebase graph[/red]")
            return

        total_files = len(self.codebase_graph.files)
        total_entities = len(self.codebase_graph.entities)

        self.console.print("\n[bold]📊 Project Statistics:[/bold]")
        self.console.print("=" * 60)

        self.console.print(f"\n📂 Total Files: [cyan]{total_files}[/cyan]")
        self.console.print(f"📚 Total Entities: [cyan]{total_entities}[/cyan]")

        if self.project_info:
            self.console.print(f"\n📈 Project: [green]{self.project_info.name}[/green] ({self.project_info.project_type})")
            if self.project_info.frameworks:
                self.console.print(f"💻 Tech: [dim]{', '.join(self.project_info.frameworks)}[/dim]")

        self.console.print("\n" + "=" * 60 + "\n")

    async def run_autofix(self):
        """Run auto-fix on all project files."""
        if not self.auto_fixer.enabled:
            self.console.print("[yellow]Auto-fix is disabled. Enable with /autofix-on[/yellow]")
            return

        self.console.print("\n[bold cyan]🔧 Running Auto-Fix...[/bold cyan]\n")

        # Find all supported files
        supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yaml', '.yml'}
        files_to_check = []

        for ext in supported_extensions:
            files_to_check.extend(self.cwd.rglob(f'*{ext}'))

        # Filter out node_modules, venv, etc.
        ignore_dirs = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build'}
        files_to_check = [
            f for f in files_to_check
            if not any(part in f.parts for part in ignore_dirs)
        ]

        if not files_to_check:
            self.console.print("[yellow]No files found to auto-fix[/yellow]")
            return

        self.console.print(f"Found {len(files_to_check)} files to analyze...")

        total_fixes = 0
        files_fixed = 0

        # Process files
        import asyncio
        for i, file_path in enumerate(files_to_check, 1):
            if i % 10 == 0:
                self.console.print(f"[dim]Analyzing... {i}/{len(files_to_check)}[/dim]")

            # Analyze and apply fixes
            fixes = await asyncio.to_thread(self.auto_fixer.analyze_file, file_path)
            if fixes:
                success, count = await asyncio.to_thread(self.auto_fixer.apply_fixes, file_path, fixes)
                if success and count > 0:
                    total_fixes += count
                    files_fixed += 1
                    rel_path = file_path.relative_to(self.cwd)
                    self.console.print(f"  ✓ [green]{rel_path}[/green] - {count} fix(es)")

        # Show summary
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"  Files analyzed: [cyan]{len(files_to_check)}[/cyan]")
        self.console.print(f"  Files fixed: [green]{files_fixed}[/green]")
        self.console.print(f"  Total fixes: [green]{total_fixes}[/green]")

        if total_fixes > 0:
            self.console.print("\n[dim]Use /autofix-undo to undo last fix[/dim]")
            self.console.print("[dim]Use /autofix-summary to see detailed statistics[/dim]")

    async def start_autofix_watch(self, silent: bool = False):
        """Start auto-fix watch mode.

        Args:
            silent: If True, suppress startup messages (for auto-init)
        """
        if self.auto_fix_watcher and self.auto_fix_watcher.is_running:
            if not silent:
                self.console.print("[yellow]Auto-fix watch already running[/yellow]")
            return

        if not self.auto_fixer.enabled:
            if not silent:
                self.console.print("[yellow]Auto-fix is disabled. Enable with /autofix-on first.[/yellow]")
            return

        if not silent:
            self.console.print("\n[bold cyan]👁️ Starting Auto-Fix Watch Mode...[/bold cyan]")
            self.console.print(f"Watching: [cyan]{self.cwd}[/cyan]")
            self.console.print("[dim]Files will be auto-fixed when you save them[/dim]")
            self.console.print("[dim]Use /autofix-watch-stop to stop[/dim]\n")

        # Create watcher with callback
        def on_fix_applied(event: AutoFixEvent):
            """Show subtle notification when fix is applied."""
            rel_path = event.file_path.relative_to(self.cwd) if event.file_path.is_relative_to(self.cwd) else event.file_path
            fix_desc = ", ".join(event.fix_types)
            # Subtle single-line notification
            self.console.print(f"[dim]✨ Auto-fixed {rel_path} ({event.fixes_applied} fix: {fix_desc})[/dim]")

        self.auto_fix_watcher = AutoFixWatcher(
            self.auto_fixer,
            on_fix_applied=on_fix_applied
        )

        await self.auto_fix_watcher.start()
        self.console.print("[green]✓ Auto-fix watch started[/green]")

    def stop_autofix_watch(self):
        """Stop auto-fix watch mode."""
        if not self.auto_fix_watcher:
            self.console.print("[yellow]Auto-fix watch not running[/yellow]")
            return

        if not self.auto_fix_watcher.is_running:
            self.console.print("[yellow]Auto-fix watch not running[/yellow]")
            return

        # Show final stats
        stats = self.auto_fix_watcher.get_stats()

        self.auto_fix_watcher.stop()
        self.console.print("\n[green]✓ Auto-fix watch stopped[/green]")

        if stats['total_fixes'] > 0:
            self.console.print(f"  Fixed [cyan]{stats['files_fixed']}[/cyan] files with [cyan]{stats['total_fixes']}[/cyan] total fixes")

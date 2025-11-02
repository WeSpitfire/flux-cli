"""CLI interface for Flux."""

import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
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
from flux.llm.provider_factory import create_provider
from flux.llm.prompts import SYSTEM_PROMPT
from flux.tools.base import ToolRegistry
from flux.tools.file_ops import ReadFilesTool, WriteFileTool, EditFileTool
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
        self.console = Console()
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
        
        # Initialize tool registry
        self.tools = ToolRegistry()
        self.tools.register(ReadFilesTool(cwd, workflow_enforcer=self.workflow, background_processor=self.bg_processor))
        self.tools.register(WriteFileTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(EditFileTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(InsertAtLineTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(PreviewEditTool(cwd))
        self.tools.register(RunCommandTool(cwd))
        self.tools.register(GrepSearchTool(cwd, workflow_enforcer=self.workflow))
        self.tools.register(ListFilesTool(cwd))
        self.tools.register(FindFilesTool(cwd))
        self.tools.register(ASTEditTool(cwd, undo_manager=self.undo, workflow_enforcer=self.workflow, approval_manager=self.approval))
        self.tools.register(ValidationTool(cwd))
    
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
        
        # Show memory/resume info
        if self.memory.state.current_task:
            self.console.print(f"Task: [yellow]{self.memory.state.current_task}[/yellow]")
        last_cp = self.memory.last_checkpoint()
        if last_cp:
            from flux.core.memory import _human_ts
            self.console.print(f"Last activity: [dim]{_human_ts(last_cp.ts)} - {last_cp.message}[/dim]")
        
        self.console.print()
    
    async def run_interactive(self):
        """Run interactive REPL mode."""
        self.print_banner()

        # Auto-build codebase graph in background
        import asyncio
        asyncio.create_task(self.build_codebase_graph())

        self.console.print("[dim]Type 'exit' or 'quit' to exit[/dim]\n")

        while True:
            try:
                # Get user input
                query = Prompt.ask("\n[bold green]You[/bold green]")

                if query.lower() in ['exit', 'quit', 'q']:
                    self.console.print("\n[cyan]Goodbye![/cyan]")
                    break

                if query.lower() == '/clear':
                    self.llm.clear_history()
                    self.console.print("[green]✓ Conversation history cleared[/green]")
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
                
                if query.lower() == '/help':
                    help_text = (
                        "[bold]Available Commands:[/bold]\n"
                        "\n[bold cyan]General:[/bold cyan]\n"
                        "  [green]/help[/green] - Show this help message\n"
                        "  [green]/model[/green] - Show current provider and model\n"
                        "  [green]/history[/green] - Show conversation history summary\n"
                        "  [green]/clear[/green] - Clear conversation history\n"
                        "\n[bold cyan]Memory Commands:[/bold cyan]\n"
                        "  [green]/task <description>[/green] - Set current task\n"
                        "  [green]/memory[/green] - Show project memory\n"
                        "  [green]/checkpoint <msg>[/green] - Save a checkpoint\n"
                        "  [green]/project[/green] - Show files created in this session\n"
                        "\n[bold cyan]Undo Commands:[/bold cyan]\n"
                        "  [green]/undo[/green] - Undo last file operation\n"
                        "  [green]/undo-history[/green] - Show undo history\n"
                        "\n[bold cyan]Git Commands:[/bold cyan]\n"
                        "  [green]/diff[/green] - Show git diff of changes\n"
                        "  [green]/commit[/green] - Smart commit with generated message\n"
                        "  [green]/test[/green] - Run project tests\n"
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
                        "  [green]/performance[/green] (or [green]/perf[/green]) - Show background processing stats"
                    )
                    self.console.print(Panel(help_text, title="📖 Help", border_style="blue"))
                    continue

                
                if query.lower() == '/model':
                    self.console.print(
                        f"\n[bold]🤖 Current Model:[/bold]\n"
                        f"  Provider: [cyan]{self.config.provider}[/cyan]\n"
                        f"  Model: [cyan]{self.config.model}[/cyan]\n"
                    )
                    continue
                
                if not query.strip():
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
    
    async def process_query(self, query: str):
        """Process a user query."""
        # Check token usage and warn if approaching limits
        usage = self.llm.get_token_usage()
        max_tokens = getattr(self.config, 'max_history', 8000)
        usage_percent = (usage['total_tokens'] / max_tokens) * 100 if max_tokens > 0 else 0
        
        if usage_percent > 90:
            self.console.print("[bold red]⚠ WARNING: Conversation is at 90%+ of token limit![/bold red]")
            self.console.print("[yellow]Strongly recommend using /clear to avoid rate limit errors[/yellow]\n")
        elif usage_percent > 80:
            self.console.print(f"[yellow]⚠ Token usage at {usage_percent:.0f}% - consider using /clear soon[/yellow]\n")
        
        # Start new workflow for each query
        self.workflow.start_workflow()
        
        # Show thinking indicator
        self.console.print("\n[bold cyan]Flux[/bold cyan]:", end=" ")
        
        response_text = ""
        tool_uses = []
        
        # Build system prompt with project context and intelligent suggestions
        system_prompt = self._build_system_prompt(query=query)
        
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
        
        # Execute tool
        try:
            result = await self.tools.execute(tool_name, **tool_input)
            
            # SMART RETRY: If edit_file fails with SEARCH_TEXT_NOT_FOUND, auto-read and provide context
            if (tool_name == "edit_file" and 
                isinstance(result, dict) and 
                result.get("error", {}).get("code") == "SEARCH_TEXT_NOT_FOUND"):
                
                file_path = tool_input.get("path")
                if file_path:
                    self.console.print("[yellow]⚠ Search text not found. Reading file for context...[/yellow]")
                    
                    # Read the file to get current content
                    try:
                        read_result = await self.tools.execute("read_files", paths=[file_path])
                        
                        # Add helpful context to the error
                        result["auto_recovery"] = {
                            "action": "file_read_completed",
                            "message": "The file has been read automatically. Please review the current content and retry your edit with the correct search text.",
                            "file_content_available": True
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
                error_dict = result.get("error", {})
                error_code = error_dict.get("code") if isinstance(error_dict, dict) else None
                error_message = error_dict.get("message") if isinstance(error_dict, dict) else str(result.get("error"))
                
                self.failure_tracker.record_failure(
                    tool_name=tool_name,
                    error_code=error_code,
                    error_message=error_message,
                    input_params=tool_input
                )
                
                # Check for retry loop and inject guidance
                if self.failure_tracker.is_retry_loop(tool_name):
                    guidance = self.failure_tracker.get_retry_guidance(tool_name)
                    if guidance:
                        # Inject guidance into the result for LLM to see
                        result["retry_guidance"] = guidance
            else:
                # Success - clear failures for this tool
                self.failure_tracker.clear_tool_failures(tool_name)
            
            # Record in memory
            self.memory.record_tool_use(tool_name, tool_input, result)
            
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
            elif tool_name == 'run_command':
                command = tool_input.get('command', '')
                self.workspace.track_command(command)
            
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
        self.console.print("\n[bold cyan]Flux[/bold cyan]:", end=" ")
        
        response_text = ""
        tool_uses = []
        
        # Build system prompt with project context
        system_prompt = self._build_system_prompt()
        
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
    
    def _build_system_prompt(self, query: Optional[str] = None) -> str:
        """Build system prompt with project context and intelligence."""
        prompt = SYSTEM_PROMPT
        
        # Add minimal project context
        if self.project_info:
            # Condensed version - just essentials
            prompt += f"\n\nProject: {self.project_info.name} ({self.project_info.project_type})"
            if self.project_info.frameworks:
                prompt += f" | {', '.join(self.project_info.frameworks[:2])}"
        
        # Add README only on first query, keep it brief
        if self._project_readme and query and len(self.llm.conversation_history) < 2:
            # Limit to 1000 chars to save tokens
            readme_snippet = self._project_readme[:1000]
            prompt += f"\n\nREADME: {readme_snippet}"
        
        # Minimal codebase intelligence - only when relevant
        if self.codebase_graph and query:
            # Only add file suggestions if they exist
            suggested_files = self.get_intelligent_context(query)
            if suggested_files:
                prompt += f"\n\nRelevant files: {', '.join(suggested_files)}"
        
        # Only add memory context if there's an active task
        if self.memory.state.current_task:
            prompt += f"\n\nCurrent task: {self.memory.state.current_task}"
        
        return prompt
    
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
        """Show git diff of current changes."""
        status = self.git.get_status()
        
        if not status.is_repo:
            self.console.print("[red]Not in a git repository[/red]")
            return
        
        if not status.has_changes:
            self.console.print("[green]No changes to show[/green]")
            return
        
        # Show status summary
        self.console.print(f"\n[bold]Branch:[/bold] {status.branch}")
        self.console.print(f"[bold]Changes:[/bold] {status.total_changes} files\n")
        
        if status.staged_files:
            self.console.print(f"[green]Staged ({len(status.staged_files)}):[/green]")
            for f in status.staged_files[:10]:
                self.console.print(f"  + {f}")
            if len(status.staged_files) > 10:
                self.console.print(f"  ... and {len(status.staged_files) - 10} more")
            self.console.print()
        
        if status.modified_files:
            self.console.print(f"[yellow]Modified ({len(status.modified_files)}):[/yellow]")
            for f in status.modified_files[:10]:
                self.console.print(f"  M {f}")
            if len(status.modified_files) > 10:
                self.console.print(f"  ... and {len(status.modified_files) - 10} more")
            self.console.print()
        
        if status.untracked_files:
            self.console.print(f"[dim]Untracked ({len(status.untracked_files)}):[/dim]")
            for f in status.untracked_files[:10]:
                self.console.print(f"  ? {f}")
            if len(status.untracked_files) > 10:
                self.console.print(f"  ... and {len(status.untracked_files) - 10} more")
            self.console.print()
        
        # Show diff
        self.console.print("[bold]Diff:[/bold]")
        diff = self.git.get_diff()
        if diff:
            # Limit diff output
            lines = diff.split('\n')
            if len(lines) > 50:
                self.console.print("\n".join(lines[:50]))
                self.console.print(f"\n[dim]... {len(lines) - 50} more lines ...[/dim]")
            else:
                self.console.print(diff)
        else:
            self.console.print("[dim]No unstaged changes[/dim]")
    
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
    
    async def run_tests(self):
        """Run project tests."""
        # Detect test command based on project type
        test_cmd = None
        
        if self.project_info:
            if self.project_info.project_type == "python":
                # Check for pytest, unittest
                if (self.cwd / "pytest.ini").exists() or "pytest" in str(self.project_info.dependencies):
                    test_cmd = "pytest"
                else:
                    test_cmd = "python -m unittest discover"
            
            elif self.project_info.project_type in ["node", "javascript", "typescript"]:
                # Check package.json for test script
                import json
                package_json = self.cwd / "package.json"
                if package_json.exists():
                    try:
                        with open(package_json) as f:
                            pkg = json.load(f)
                            if "scripts" in pkg and "test" in pkg["scripts"]:
                                test_cmd = "npm test"
                    except:
                        pass
        
        if not test_cmd:
            self.console.print("[yellow]No test command detected. Common options:[/yellow]")
            self.console.print("  - pytest")
            self.console.print("  - npm test")
            self.console.print("  - python -m unittest")
            return
        
        self.console.print(f"[bold]Running:[/bold] {test_cmd}\n")
        
        # Run the command
        import subprocess
        try:
            result = subprocess.run(
                test_cmd,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Show output
            if result.stdout:
                self.console.print(result.stdout)
            if result.stderr:
                self.console.print(f"[red]{result.stderr}[/red]")
            
            if result.returncode == 0:
                self.console.print(f"\n[green]✓ Tests passed[/green]")
            else:
                self.console.print(f"\n[red]✗ Tests failed (exit code: {result.returncode})[/red]")
                
        except subprocess.TimeoutExpired:
            self.console.print("[red]✗ Tests timed out (60s limit)[/red]")
        except Exception as e:
            self.console.print(f"[red]✗ Error running tests: {e}[/red]")
    
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
        from flux.core.impact_analyzer import DependencyImpact
        
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

"""CLI interface for Flux."""

import sys
from pathlib import Path
from typing import Optional, List

from flux.core.config import Config
from flux.core.project import ProjectDetector, ProjectInfo
from flux.core.codebase_intelligence import CodebaseGraph
from flux.core.impact_analyzer import ImpactAnalyzer
from flux.core.suggestions import SuggestionsEngine, Priority
from flux.core.workspace import Workspace, TaskPriority, TaskStatus
from flux.core.test_runner import TestRunner, TestResult
from flux.core.auto_fix_watcher import AutoFixWatcher, AutoFixEvent
from flux.core.auto_init import auto_initialize
from flux.core.task_planner import TaskPlanner
from flux.tools.file_ops import ReadFilesTool, WriteFileTool, EditFileTool, MoveFileTool, DeleteFileTool
from flux.tools.filesystem import ListFilesTool, FindFilesTool


class CLI:
    """Main CLI interface for Flux."""

    def __init__(self, config: Config, cwd: Path):
        """Initialize CLI - delegates to CLIBuilder for dependency injection."""
        from flux.ui.cli_builder import CLIBuilder
        initialized = CLIBuilder.build(config, cwd)
        self.__dict__.update(initialized.__dict__)

    async def build_codebase_graph(self) -> None:
        """Build the codebase semantic graph (runs in background)."""
        if self._graph_building or self.codebase_graph:
            return

        self._graph_building = True
        try:
            # Build graph silently in background - no UI spam
            self.codebase_graph = CodebaseGraph(self.cwd)
            self.codebase_graph.build_graph(max_files=500)  # Limit for performance

            # Skip architecture announcement - not needed on every startup
            # patterns = self.codebase_graph.detect_architecture_patterns()

            # Auto-read README for project understanding
            self._project_readme = await self._load_readme()

            # Initialize impact analyzer with graph
            self.impact_analyzer = ImpactAnalyzer(self.cwd, self.codebase_graph)

            # Initialize suggestions engine with graph
            self.suggestions_engine = SuggestionsEngine(self.cwd, self.codebase_graph)

            # Initialize task planner with graph
            self.task_planner = TaskPlanner(self.llm, self.codebase_graph)
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
    
    async def _maybe_restore_conversation(self):
        """Check if we should restore previous conversation and prompt user."""
        state_manager = self.conversation_manager.state_manager
        
        # Check if we should prompt
        if not state_manager.should_prompt_restore():
            return
        
        # Get prompt message
        prompt_msg = state_manager.get_restore_prompt_message()
        
        from rich.panel import Panel
        from rich.prompt import Confirm
        
        # Show prompt
        self.console.print(Panel(
            prompt_msg,
            title="\u23f1\ufe0f  Previous Conversation Found",
            border_style="cyan"
        ))
        
        # Ask user
        try:
            should_restore = Confirm.ask(
                "[cyan]Continue where you left off?[/cyan]",
                default=True
            )
            
            if should_restore:
                # Restore
                restored = self.conversation_manager.restore_conversation_state()
                if restored:
                    stats = state_manager.get_stats()
                    self.console.print(
                        f"[green]\u2713 Restored {stats['message_count']} messages[/green]"
                    )
                    if stats['summaries_count'] > 0:
                        self.console.print(
                            f"[dim]  {stats['summaries_count']} summaries loaded[/dim]"
                        )
                    
                    # Add context message to help AI understand the restoration
                    await self._add_restoration_context(state_manager.state)
                else:
                    self.console.print("[yellow]\u26a0 Failed to restore conversation[/yellow]")
            else:
                # User chose to start fresh
                state_manager.clear_state()
                self.console.print("[dim]Starting fresh conversation[/dim]")
            
            self.console.print()  # Empty line for spacing
        except KeyboardInterrupt:
            # User cancelled with Ctrl+C - start fresh
            state_manager.clear_state()
            self.console.print("\n[dim]Starting fresh conversation[/dim]\n")
    
    async def _add_restoration_context(self, state):
        """Add a context message and re-read important files to help AI understand the restored conversation.
        
        Args:
            state: ConversationState that was restored
        """
        if not state:
            return
        
        # Collect all files mentioned in the conversation
        all_files = set()
        
        # Get files from summaries
        if state.summaries:
            for summary in state.summaries:
                all_files.update(summary.get('files_discussed', []))
        
        # Get files from recent conversation history
        import re
        for msg in state.conversation_history[-10:]:  # Last 10 messages
            content = msg.get('content', '')
            if isinstance(content, str):
                # Extract file paths (simple heuristic)
                # Match common file patterns: path/to/file.ext
                file_patterns = re.findall(r'[\w/.-]+\.(py|js|ts|jsx|tsx|go|rs|java|cpp|c|h|rb|php|swift|kt|md|json|yaml|yml|toml|txt)', content)
                all_files.update(file_patterns)
        
        # Filter to existing files and prioritize by importance
        existing_files = []
        for file_path in all_files:
            full_path = self.cwd / file_path
            if full_path.exists() and full_path.is_file():
                existing_files.append(file_path)
        
        # Limit to top 5 most recently discussed files
        files_to_read = existing_files[:5]
        
        # Re-read the important files
        if files_to_read:
            self.console.print(f"[dim]📖 Re-reading {len(files_to_read)} key files from previous session...[/dim]")
            
            try:
                # Use the read_files tool to get file contents
                file_contents = await self.tools.execute('read_files', paths=files_to_read)
                
                if not file_contents.get('error'):
                    # Add file contents to conversation as context
                    files_summary = []
                    for file_info in file_contents.get('files', []):
                        path = file_info.get('path', '')
                        lines = file_info.get('total_lines', 0)
                        files_summary.append(f"{path} ({lines} lines)")
                    
                    if files_summary:
                        self.console.print(f"[dim]✓ Loaded: {', '.join(files_summary)}[/dim]")
            except Exception as e:
                # If reading fails, just continue without file context
                self.console.print(f"[dim]⚠ Could not re-read files: {e}[/dim]")
        
        # Build a context summary
        context_parts = []
        
        # Add project brief context if available
        if state.project_brief:
            brief_summary = []
            if state.project_brief.get('project_name'):
                brief_summary.append(f"Project: {state.project_brief['project_name']}")
            if state.project_brief.get('constraints'):
                constraints = state.project_brief.get('constraints', [])
                brief_summary.append(f"Constraints: {', '.join(constraints[:2])}")
            if brief_summary:
                context_parts.append(", ".join(brief_summary))
        
        # Add summary information
        if state.summaries:
            all_decisions = []
            for summary in state.summaries:
                all_decisions.extend(summary.get('decisions_made', []))
            
            if all_decisions:
                context_parts.append(f"Previous decisions: {len(all_decisions)} recorded")
        
        # Add files re-read info
        if files_to_read:
            context_parts.append(f"Key files re-loaded: {', '.join(files_to_read[:3])}")
        
        # Add this as a system message in the conversation
        if context_parts:
            context_msg = (
                "[SYSTEM: Conversation restored from previous session. "
                f"Context: {'. '.join(context_parts)}. "
                "The key files have been re-read for you. Review the conversation history to understand what was discussed.]"
            )
            
            # Add as a user message (lightweight reminder)
            self.llm.conversation_history.append({
                "role": "user",
                "content": context_msg
            })
            
            # Add assistant acknowledgment (so it knows it received the context)
            self.llm.conversation_history.append({
                "role": "assistant",
                "content": "I understand. I've reviewed the restored conversation history and the key files. I'm ready to continue from where we left off."
            })

    def print_banner(self):
        """Print Flux banner."""
        # Load/resume session
        last_session = self.session_manager.load_last_session()
        session_summary = None
        if last_session:
            session_summary = self.session_manager.get_session_summary(last_session)
        else:
            self.session_manager.start_new_session()

        # Get current task for legacy support
        current_task = None
        if self.memory.state.current_task and not last_session:
            current_task = self.memory.state.current_task

        # Delegate to display manager
        self.display.print_banner(
            cwd=self.cwd,
            config=self.config,
            project_info=self.project_info,
            session_summary=session_summary,
            current_task=current_task
        )

    async def run_interactive(self):
        """Run interactive REPL mode."""
        self.print_banner()
        
        # === CONVERSATION STATE RESTORE ===
        # Check if we should restore previous conversation
        await self._maybe_restore_conversation()

        # Skip auto-initialization - user can trigger manually if needed
        # await auto_initialize(self)
        
        # Disable noisy background features on startup
        # import asyncio
        # asyncio.create_task(self.copilot.start_monitoring())  # Disabled - too noisy
        
        # Enable auto-snapshot (will create snapshots every 5 minutes)
        self.time_machine.auto_snapshot_enabled = True

        # Multi-line compose state (disabled if not truly interactive)
        import sys
        self._enable_paste_mode = sys.stdin.isatty()  # Only enable for real terminals
        self._compose_mode = False
        self._compose_buffer = []  # type: list[str]
        self._last_input_time = 0.0  # Track timing for paste detection

        self.display.print_help_text()

        while True:
            try:
                # Disable suggestion spam - let user focus on work
                # if self._enable_paste_mode:
                #     self._maybe_show_suggestions()

                # Auto-clear context when it gets too full (invisible to user)
                # CRITICAL FIX: Check conversation history size, NOT cumulative API usage!
                conversation_tokens = self.llm.estimate_conversation_tokens()
                usage_percent = (conversation_tokens / self.config.max_history) * 100 if self.config.max_history > 0 else 0

                # Emergency circuit breaker: Hard stop at 150% to prevent rate limit errors
                if conversation_tokens > (self.config.max_history * 1.5):
                    # CRITICAL: Context has grown way too large, clear immediately
                    current_task = self.memory.state.current_task
                    self.llm.clear_history()
                    if current_task:
                        self.memory.state.current_task = current_task
                    self.display.print_emergency_context_clear(conversation_tokens)
                    continue  # Skip this iteration, show prompt again

                if usage_percent >= 90:
                    # Auto-clear to prevent errors - but preserve important context
                    old_token_count = conversation_tokens

                    # Save current task before clearing
                    current_task = self.memory.state.current_task

                    # Clear conversation history
                    self.llm.clear_history()

                    # Restore task context in a fresh message if there was one
                    if current_task:
                        # Add it back as system context (not as a user message)
                        self.memory.state.current_task = current_task

                    self.display.print_context_cleared(old_token_count)

                # BLOCK INPUT if LLM is processing
                if self._llm_processing:
                    self.display.print_processing_blocker()
                    # Show a persistent indicator until processing completes
                    import asyncio
                    while self._llm_processing:
                        await asyncio.sleep(0.1)
                    # After processing completes, show prompt again
                    self.display.print_processing_ready()

                # Get user input
                query = self.display.prompt_user(enable_paste_mode=self._enable_paste_mode)

                # Decode newline placeholders from desktop app
                if '<<<NEWLINE>>>' in query:
                    query = query.replace('<<<NEWLINE>>>', '\n')

                # Try to parse natural language commands
                nl_result = self.nl_parser.parse(query)
                if nl_result:
                    command, args = nl_result
                    # Show what we interpreted
                    self.display.print_nl_command_interpretation(command, args)
                    # Rewrite query as the slash command
                    if args:
                        query = f"{command} {args}"
                    else:
                        query = command

                if query.lower() in ['exit', 'quit', 'q']:
                    self.display.print_goodbye()
                    break

                # Handle slash commands via CommandRouter
                if query.startswith('/'):
                    handled = await self.commands.handle(query)
                    if handled:
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

                # Process query
                await self.process_query(query)

            except KeyboardInterrupt:
                # If we're processing, cancel it. Otherwise, exit.
                if self._llm_processing:
                    self._processing_cancelled = True
                    self._llm_processing = False
                    self.console.print("\n[yellow]⏹️  Operation cancelled[/yellow]")
                    # Clear any partial state
                    continue
                else:
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

    async def process_with_task_planner(self, query: str):
        """Process query using task planner - delegates to WorkflowCoordinator."""
        await self.workflow_coord.process_with_task_planner(query)

    async def process_with_orchestrator(self, query: str):
        """Process query using orchestrator - delegates to WorkflowCoordinator."""
        await self.workflow_coord.process_with_orchestrator(query)

    def should_use_orchestrator(self, query: str) -> bool:
        """Determine if orchestrator should be used - delegates to WorkflowCoordinator."""
        return self.workflow_coord.should_use_orchestrator(query)

    async def process_query(self, query: str):
        """Process a user query - delegates to ConversationManager."""
        await self.conversation_manager.process_query(query)

    async def process_query_normal(self, query: str):
        """Process query through normal LLM conversation - delegates to ConversationManager."""
        await self.conversation_manager.process_query_normal(query)

    async def _process_query_normal_impl(self, query: str):
        """Internal implementation - delegates to ConversationManager."""
        await self.conversation_manager._process_query_normal_impl(query)

    async def execute_tool(self, tool_use: dict):
        """Execute a tool - delegates to ConversationManager."""
        await self.conversation_manager.execute_tool(tool_use)

    async def continue_after_tools(self):
        """Continue conversation after tools - delegates to ConversationManager."""
        await self.conversation_manager.continue_after_tools()

    def _get_retry_context(self) -> str:
        """Get retry context warning - delegates to ConversationManager."""
        return self.conversation_manager._get_retry_context()

    def _build_system_prompt(self, query: Optional[str] = None) -> str:
        """Build system prompt - delegates to ConversationManager."""
        return self.conversation_manager._build_system_prompt(query)


    def _print_monitor_notification(self, notification: dict):
        """Callback for proactive monitor notifications."""
        # Handle both string and dict notification formats
        if isinstance(notification, str):
            # Legacy string format - convert to dict
            notification = {'message': notification, 'type': 'info', 'title': '💡 Notification'}
        self.display.print_monitor_notification(notification)
    
    def _print_copilot_suggestion(self, suggestion):
        """Callback for Copilot suggestions."""
        from rich.panel import Panel
        
        priority_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(suggestion.priority.value, '⚪')
        
        message = f"{priority_emoji} [bold]{suggestion.title}[/bold]\n"
        message += f"{suggestion.description}\n\n"
        message += f"[dim]→ {suggestion.action_prompt}[/dim]"
        if suggestion.auto_fixable:
            message += "\n[green]✓ Auto-fixable[/green]"
        
        self.console.print(Panel(
            message,
            title="🤖 Flux Copilot",
            border_style="magenta",
            width=80
        ))
        
        self.console.print(f"[dim]Use /copilot to see all suggestions, /copilot-dismiss {suggestion.id[:8]} to dismiss[/dim]")

    def _maybe_show_suggestions(self):
        """Show smart suggestions if there are any relevant ones.

        Only shows suggestions occasionally to avoid spam:
        - After every 3-5 commands
        - When high-confidence suggestions exist (> 0.8)
        """
        # Rate limiting - don't show too often
        if not hasattr(self, '_suggestion_counter'):
            self._suggestion_counter = 0

        self._suggestion_counter += 1

        # Only check every 3-5 commands (with some randomness)
        import random
        check_interval = random.randint(3, 5)

        if self._suggestion_counter < check_interval:
            return

        # Reset counter
        self._suggestion_counter = 0

        # Get suggestions
        try:
            suggestions = self.command_suggester.get_suggestions(max_suggestions=2)

            # Only show high-confidence suggestions automatically
            high_conf_suggestions = [s for s in suggestions if s.confidence >= 0.80]

            if high_conf_suggestions:
                self.console.print("\n[dim]💡 Suggestions:[/dim]")
                for sug in high_conf_suggestions:
                    self.console.print(f"  [dim]{sug.format()}[/dim]")
                self.console.print("[dim]Type /suggest for more suggestions[/dim]")
        except Exception:
            # Silently fail - suggestions are not critical
            pass

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
        """Show git diff - delegates to GitTestManager."""
        await self.git_test.show_diff()

    async def smart_commit(self, query: str):
        """Create smart commit - delegates to GitTestManager."""
        await self.git_test.smart_commit(query)

    async def run_tests(self, file_filter: Optional[str] = None):
        """Run tests - delegates to GitTestManager."""
        await self.git_test.run_tests(file_filter)

    def _display_test_result(self, result):
        """Display test results - delegates to GitTestManager."""
        self.git_test.display_test_result(result)

    async def start_watch_mode(self):
        """Start test watch mode - delegates to GitTestManager."""
        await self.git_test.start_watch_mode()

    def stop_watch_mode(self):
        """Stop test watch mode - delegates to GitTestManager."""
        self.git_test.stop_watch_mode()

    def _on_watch_test_complete(self, result):
        """Watch mode callback - delegates to GitTestManager."""
        self.git_test._on_watch_test_complete(result)

    async def show_related_files(self, file_or_query: str):
        """Show related files - delegates to CodebaseAnalyzer."""
        await self.codebase_analyzer.show_related_files(file_or_query)

    async def show_file_preview(self, file_path: str):
        """Show file preview - delegates to CodebaseAnalyzer."""
        await self.codebase_analyzer.show_file_preview(file_path)

    def show_impact_analysis(self, impact, show_diff: bool = False):
        """Show impact analysis - delegates to CodebaseAnalyzer."""
        self.codebase_analyzer.show_impact_analysis(impact, show_diff)

    async def show_architecture(self):
        """Show architecture - delegates to CodebaseAnalyzer."""
        await self.codebase_analyzer.show_architecture()

    async def analyze_file_structure(self, file_path: str):
        """Analyze file structure - delegates to CodebaseAnalyzer."""
        await self.codebase_analyzer.analyze_file_structure(file_path)

    async def show_suggestions(self):
        """Show suggestions - delegates to CodebaseAnalyzer."""
        await self.codebase_analyzer.show_suggestions()

    async def handle_session_command(self, args: str):
        """Handle session commands - delegates to SessionTaskManager."""
        await self.session_task_mgr.handle_session_command(args)

    async def list_sessions(self):
        """List sessions - delegates to SessionTaskManager."""
        await self.session_task_mgr.list_sessions()

    async def create_task(self, title: str):
        """Create task - delegates to SessionTaskManager."""
        await self.session_task_mgr.create_task(title)

    async def list_tasks(self):
        """List tasks - delegates to SessionTaskManager."""
        await self.session_task_mgr.list_tasks()

    async def show_work_summary(self):
        """Show work summary - delegates to SessionTaskManager."""
        await self.session_task_mgr.show_work_summary()

    async def inspect_state(self):
        """Inspect state - delegates to SessionTaskManager."""
        await self.session_task_mgr.inspect_state()

    async def show_project_stats(self):
        """Show project stats - delegates to SessionTaskManager."""
        await self.session_task_mgr.show_project_stats()

    async def run_autofix(self):
        """Run autofix - delegates to AutoFixManager."""
        await self.autofix_mgr.run_autofix()

    async def start_autofix_watch(self, silent: bool = False):
        """Start autofix watch - delegates to AutoFixManager."""
        await self.autofix_mgr.start_autofix_watch(silent)

    def stop_autofix_watch(self):
        """Stop autofix watch - delegates to AutoFixManager."""
        self.autofix_mgr.stop_autofix_watch()

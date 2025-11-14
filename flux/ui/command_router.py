"""Command router - handles all slash command routing and execution."""

from typing import Dict, Callable, Optional, Any


class CommandRouter:
    """Routes /commands to appropriate handlers."""

    def __init__(self, cli):
        """Initialize command router with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli
        self.handlers = self._register_handlers()

    def _register_handlers(self) -> Dict[str, Callable]:
        """Register all command handlers.

        Returns:
            Dictionary mapping command names to handler methods
        """
        return {
            # Core commands
            '/clear': self.handle_clear,
            '/history': self.handle_history,
            '/help': self.handle_help,
            '/model': self.handle_model,

            # State & context
            '/fix': self.handle_fix,
            '/state': self.handle_state,
            '/inspect': self.handle_inspect,

            # Session management
            '/session': self.handle_session,
            '/sessions': self.handle_sessions,

            # Workflow & monitoring
            '/workflows': self.handle_workflows,
            '/workflow': self.handle_workflow,
            '/watch': self.handle_watch,
            '/status': self.handle_status,
            '/suggest': self.handle_suggest,

            # Approval
            '/auto-approve': self.handle_auto_approve,

            # Memory & tasks
            '/task': self.handle_task,
            '/memory': self.handle_memory,
            '/checkpoint': self.handle_checkpoint,
            '/project': self.handle_project,

            # Undo
            '/undo': self.handle_undo,
            '/undo-history': self.handle_undo_history,

            # Workflow & approval stats
            '/workflow-status': self.handle_workflow_status,
            '/approval': self.handle_approval,

            # Git
            '/diff': self.handle_diff,
            '/commit': self.handle_commit,

            # Testing
            '/test': self.handle_test,
            '/watch-tests': self.handle_watch_tests,
            '/watch-stop': self.handle_watch_stop,

            # Codebase intelligence
            '/index': self.handle_index,
            '/analyze': self.handle_analyze,
            '/related': self.handle_related,
            '/architecture': self.handle_architecture,
            '/preview': self.handle_preview,
            '/suggest-ai': self.handle_suggest_ai,

            # Workspace
            '/newtask': self.handle_newtask,
            '/tasks': self.handle_tasks,
            '/summary': self.handle_summary,
            '/stats': self.handle_stats,
            '/performance': self.handle_performance,
            '/perf': self.handle_performance,
            '/metrics': self.handle_metrics,

            # Validation
            '/validate': self.handle_validate,

            # Debug
            '/debug': self.handle_debug,
            '/debug-on': self.handle_debug_on,
            '/debug-off': self.handle_debug_off,
            '/debug-analyze': self.handle_debug_analyze,

            # Auto-fix
            '/autofix': self.handle_autofix,
            '/autofix-on': self.handle_autofix_on,
            '/autofix-off': self.handle_autofix_off,
            '/autofix-undo': self.handle_autofix_undo,
            '/autofix-summary': self.handle_autofix_summary,
            '/autofix-watch': self.handle_autofix_watch,
            '/autofix-watch-stop': self.handle_autofix_watch_stop,
            '/autofix-stats': self.handle_autofix_stats,
            
            # UX Differentiators
            # Copilot Mode
            '/copilot': self.handle_copilot,
            '/copilot-status': self.handle_copilot_status,
            '/copilot-dismiss': self.handle_copilot_dismiss,
            '/copilot-on': self.handle_copilot_on,
            '/copilot-off': self.handle_copilot_off,
            
            # Time Machine
            '/snapshot': self.handle_snapshot,
            '/snapshots': self.handle_snapshots,
            '/restore': self.handle_restore,
            '/compare': self.handle_compare,
            '/timeline': self.handle_timeline,
            
            # Smart Context
            '/learn': self.handle_learn,
            '/context': self.handle_context,
            '/knowledge': self.handle_knowledge,
            '/patterns': self.handle_patterns,
            
            # Onboarding
            '/guide': self.handle_guide,
        }

    async def handle(self, query: str) -> bool:
        """Route command to handler.

        Args:
            query: The full query string (including command)

        Returns:
            True if command was handled, False if not a command or unknown
        """
        if not query.startswith('/'):
            return False

        # Extract command and args
        parts = query.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None

        # Check for exact handler
        handler = self.handlers.get(command)
        if handler:
            await handler(args)
            return True

        # Check for startswith handlers (e.g., /workflow <name>)
        for cmd_prefix in ['/workflow ', '/watch ', '/session ', '/analyze ',
                          '/related ', '/preview ', '/task ', '/newtask ',
                          '/commit', '/debug-analyze ', '/checkpoint']:
            if query.lower().startswith(cmd_prefix):
                # Find the handler for base command
                base_cmd = cmd_prefix.strip()
                handler = self.handlers.get(base_cmd)
                if handler:
                    # Pass everything after the command as args
                    args_text = query[len(cmd_prefix):].strip() if len(query) > len(cmd_prefix) else None
                    await handler(args_text)
                    return True

        # Unknown command
        self.cli.display.print_error(f"Unknown command: {command}")
        self.cli.display.print_dim("Type /help for available commands")
        return True

    # ============================================
    # COMMAND HANDLERS
    # ============================================

    async def handle_clear(self, args: Optional[str]):
        """Handle /clear command."""
        self.cli.llm.clear_history()
        self.cli.display.print_success("✓ Conversation history cleared")

        # Clear compose buffer too
        if getattr(self.cli, "_compose_mode", False):
            self.cli._compose_mode = False
            self.cli._compose_buffer = []
            self.cli.display.print_dim("Paste mode cancelled")

    async def handle_history(self, args: Optional[str]):
        """Handle /history command."""
        usage = self.cli.llm.get_token_usage()
        history_len = len(self.cli.llm.conversation_history)
        conversation_tokens = self.cli.llm.estimate_conversation_tokens()
        max_tokens = self.cli.config.max_history

        self.cli.display.print_history_stats(
            history_len=history_len,
            conversation_tokens=conversation_tokens,
            max_tokens=max_tokens,
            cumulative_tokens=usage['total_tokens'],
            estimated_cost=usage['estimated_cost']
        )

    async def handle_help(self, args: Optional[str]):
        """Handle /help command."""
        from rich.panel import Panel

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
            "  [green]/guide[/green] - Interactive walkthrough for new users\n"
            "  [green]/model[/green] - Show current provider and model\n"
            "  [green]/history[/green] - Show conversation history summary\n"
            "  [green]/clear[/green] - Clear conversation history\n"
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
            "  [green]/suggest[/green] - Get smart command suggestions\n"
            "\n[bold cyan]Undo Commands:[/bold cyan]\n"
            "  [green]/undo[/green] - Undo last file operation\n"
            "  [green]/undo-history[/green] - Show undo history\n"
            "\n[bold cyan]Git & Testing:[/bold cyan]\n"
            "  [green]/diff[/green] - Show git diff of changes\n"
            "  [green]/commit[/green] - Smart commit with generated message\n"
            "  [green]/test[/green] - Run project tests\n"
            "  [green]/watch[/green] - Start test watch mode\n"
            "  [green]/watch-stop[/green] - Stop test watch mode\n"
            "\n[bold cyan]Codebase Intelligence:[/bold cyan]\n"
            "  [green]/index[/green] - Build semantic codebase graph\n"
            "  [green]/related <file|query>[/green] - Find related files\n"
            "  [green]/architecture[/green] - Show detected architecture\n"
            "  [green]/preview <file>[/green] - Preview impact of modifying a file\n"
            "\n[bold cyan]Workspace:[/bold cyan]\n"
            "  [green]/sessions[/green] - List all sessions\n"
            "  [green]/newtask <title>[/green] - Create a new task\n"
            "  [green]/tasks[/green] - List all tasks\n"
            "  [green]/summary[/green] - Show work summary for today\n"
            "  [green]/stats[/green] - Show project statistics\n"
            "  [green]/performance[/green] (or [green]/perf[/green]) - Show performance stats\n"
            "\n[bold cyan]Code Quality:[/bold cyan]\n"
            "  [green]/validate[/green] - Validate modified files\n"
            "  [green]/fix[/green] - Auto-detect and fix recent errors\n"
            "  [green]/auto-approve[/green] - Toggle auto-approve mode\n"
            "\n[bold cyan]Debug & Diagnostics:[/bold cyan]\n"
            "  [green]/debug-on[/green] - Enable debug logging\n"
            "  [green]/debug-off[/green] - Disable debug logging\n"
            "  [green]/debug[/green] - Show debug session summary\n"
            "  [green]/inspect[/green] - Inspect conversation state\n"
            "\n[bold magenta]✨ UX Differentiators:[/bold magenta]\n"
            "  [green]/copilot[/green] - Show proactive suggestions\n"
            "  [green]/copilot-status[/green] - Show Copilot monitoring status\n"
            "  [green]/snapshot[/green] - Create manual snapshot\n"
            "  [green]/snapshots[/green] - List all snapshots\n"
            "  [green]/restore <id>[/green] - Restore from snapshot\n"
            "  [green]/timeline[/green] - Show Time Machine status\n"
            "  [green]/knowledge[/green] - Show knowledge graph stats\n"
            "  [green]/context <query>[/green] - Get relevant context\n"
        )

        self.cli.console.print(Panel(help_text, title="Help", border_style="blue"))

    async def handle_model(self, args: Optional[str]):
        """Handle /model command."""
        self.cli.console.print(
            f"\n[bold]🤖 Current Model:[/bold]\n"
            f"  Provider: [cyan]{self.cli.config.provider}[/cyan]\n"
            f"  Model: [cyan]{self.cli.config.model}[/cyan]\n"
        )

    async def handle_fix(self, args: Optional[str]):
        """Handle /fix command - auto-detect and fix recent errors."""
        recent_commands = [c for c in self.cli.state_tracker.command_history[-5:] if c.exit_code != 0]

        if not recent_commands:
            self.cli.display.print_warning("No recent failed commands to fix.")
            return

        last_failed = recent_commands[-1]
        parsed_errors = self.cli.error_parser.parse_output(last_failed.output or "", last_failed.command)

        if not parsed_errors:
            self.cli.display.print_warning(f"No parseable errors found in: {last_failed.command}")
            return

        # Show errors
        self.cli.console.print(f"\n[bold]🛠️  Analyzing Errors from:[/bold] [cyan]{last_failed.command}[/cyan]\n")
        for i, error in enumerate(parsed_errors[:3], 1):
            self.cli.console.print(f"{i}. {self.cli.error_parser.format_error(error)}\n")

        # Get fix context and process
        first_error = parsed_errors[0]
        fix_context = self.cli.error_parser.get_fix_context(first_error)

        if fix_context:
            fix_query = (
                f"Fix this error:\n\n"
                f"Error: {first_error.error_type}: {first_error.message}\n"
                f"File: {fix_context['file_path']}:{fix_context['line_number']}\n\n"
                f"Code context (lines {fix_context['start_line']}-{fix_context['end_line']}):\n"
                f"```\n{fix_context['code_context']}```\n\n"
                f"Please fix this error."
            )
            self.cli.console.print("[dim]→ Asking Flux to fix the error...[/dim]\n")
            # Process as normal query
            await self.cli.process_query(fix_query)
        else:
            self.cli.display.print_warning(f"Could not get fix context for {first_error.file_path}")

    async def handle_state(self, args: Optional[str]):
        """Handle /state command - show project state."""
        summary = self.cli.state_tracker.get_context_summary(max_age_minutes=30)
        suggestions = self.cli.state_tracker.get_proactive_suggestions()

        self.cli.console.print("\n[bold]🧠 Project State (Last 30 minutes):[/bold]\n")

        # Files
        if summary['files']['recently_modified']:
            self.cli.console.print(f"[bold cyan]Recent Files:[/bold cyan]")
            for f in summary['files']['recently_modified'][:5]:
                self.cli.console.print(f"  • {f}")
            self.cli.console.print()

        if summary['files']['most_active']:
            self.cli.console.print(f"[bold cyan]Hot Files:[/bold cyan]")
            for f, count in summary['files']['most_active']:
                self.cli.console.print(f"  • {f} ({count} modifications)")
            self.cli.console.print()

        # Git (similar pattern for git, tests, commands...)
        # ... rest of state display logic from CLI ...

        if suggestions:
            self.cli.console.print(f"[bold yellow]💡 Suggestions:[/bold yellow]")
            for suggestion in suggestions:
                self.cli.console.print(f"  {suggestion}")
            self.cli.console.print()
        else:
            self.cli.console.print("[dim]No suggestions - you're doing great! 🚀[/dim]\n")

    async def handle_inspect(self, args: Optional[str]):
        """Handle /inspect command."""
        await self.cli.inspect_state()

    async def handle_session(self, args: Optional[str]):
        """Handle /session command."""
        if args:
            await self.cli.handle_session_command(args)
        else:
            current = self.cli.session_manager.get_current_session()
            if current:
                summary = self.cli.session_manager.get_session_summary(current)
                self.cli.console.print("\n" + summary)
            else:
                self.cli.display.print_warning("No active session")

    async def handle_sessions(self, args: Optional[str]):
        """Handle /sessions command."""
        await self.cli.list_sessions()

    async def handle_workflows(self, args: Optional[str]):
        """Handle /workflows command."""
        workflows = self.cli.workflow_manager.list_workflows()
        if not workflows:
            self.cli.display.print_warning("No workflows defined. Create `.flux/workflows.yaml` to add workflows.")
        else:
            self.cli.console.print("\n[bold]Available Workflows:[/bold]")
            for wf in workflows:
                workflow = self.cli.workflow_manager.get_workflow(wf)
                desc = workflow.get('description', 'No description')
                self.cli.console.print(f"  [cyan]{wf}[/cyan] - {desc}")
            self.cli.console.print("\nUse `/workflow <name>` to execute a workflow.")

    async def handle_workflow(self, args: Optional[str]):
        """Handle /workflow <name> command."""
        if not args:
            # Show workflow status if no args
            summary = self.cli.workflow.get_summary()
            from rich.panel import Panel
            self.cli.console.print(Panel(summary, title="🔄 Workflow Status", border_style="blue"))
            return

        workflow_name = args.strip()
        try:
            workflow = self.cli.workflow_manager.get_workflow(workflow_name)
            self.cli.console.print(f"\n[bold]Executing workflow: {workflow_name}[/bold]\n")

            result = await self.cli.workflow_executor.execute(workflow)

            if result.get('success'):
                self.cli.display.print_success(f"✓ Workflow '{workflow_name}' completed successfully")
            else:
                error = result.get('error', 'Unknown error')
                self.cli.display.print_error(f"✗ Workflow '{workflow_name}' failed: {error}")

            self.cli.session_manager.record_event(
                self.cli.EventType.WORKFLOW_EXECUTED,
                {'workflow': workflow_name, 'success': result.get('success', False)}
            )
        except Exception as e:
            self.cli.display.print_error(f"Error executing workflow: {e}")

    async def handle_watch(self, args: Optional[str]):
        """Handle /watch command."""
        # Implementation matches CLI logic...
        if not args or args == 'tests':
            await self.cli.start_watch_mode()
        else:
            # Handle other watch types...
            pass

    async def handle_status(self, args: Optional[str]):
        """Handle /status command."""
        status = self.cli.proactive_monitor.get_status()
        self.cli.console.print("\n[bold]Monitor Status:[/bold]")
        self.cli.console.print(f"  Running: {'Yes' if status['running'] else 'No'}")
        # ... rest of status display ...

    async def handle_suggest(self, args: Optional[str]):
        """Handle /suggest command."""
        suggestions = self.cli.command_suggester.get_suggestions(max_suggestions=5)
        if suggestions:
            self.cli.console.print("\n[bold]💡 Suggested Commands:[/bold]")
            for i, sug in enumerate(suggestions, 1):
                self.cli.console.print(f"  {i}. {sug.format()}")
            self.cli.console.print()
        else:
            self.cli.console.print("\n[dim]No suggestions at the moment - you're doing great! 🚀[/dim]\n")

    async def handle_auto_approve(self, args: Optional[str]):
        """Handle /auto-approve command."""
        self.cli.approval.auto_approve = not self.cli.approval.auto_approve
        status = "enabled" if self.cli.approval.auto_approve else "disabled"
        if self.cli.approval.auto_approve:
            self.cli.display.print_success(f"Auto-approve {status}")
            self.cli.display.print_dim("All file changes will be applied automatically without prompts")
        else:
            self.cli.display.print_warning(f"Auto-approve {status}")
            self.cli.display.print_dim("You'll be prompted to approve each file change")

    # Memory commands
    async def handle_task(self, args: Optional[str]):
        """Handle /task command."""
        if not args:
            self.cli.display.print_error("Usage: /task <description>")
            return
        self.cli.memory.set_current_task(args)
        self.cli.display.print_success(f"Task set: {args}")

    async def handle_memory(self, args: Optional[str]):
        """Handle /memory command."""
        from rich.panel import Panel
        mem_str = self.cli.memory.to_context_string(max_items=10)
        self.cli.console.print(Panel(mem_str, title="📚 Memory", border_style="blue"))

    async def handle_checkpoint(self, args: Optional[str]):
        """Handle /checkpoint command."""
        msg = args if args else "Manual checkpoint"
        self.cli.memory.add_checkpoint(msg)
        self.cli.display.print_success(f"Checkpoint saved: {msg}")

    async def handle_project(self, args: Optional[str]):
        """Handle /project command."""
        from rich.panel import Panel
        summary = self.cli.memory.get_project_summary()
        self.cli.console.print(Panel(summary, title="📦 Project Files", border_style="blue"))

    # Undo commands
    async def handle_undo(self, args: Optional[str]):
        """Handle /undo command."""
        result = self.cli.undo.undo_last()
        if result.get("error"):
            self.cli.display.print_error(result['error'])
        else:
            self.cli.console.print(
                f"[green]✓ Undone:[/green] {result['description']}\n"
                f"  File: {result['file']}\n"
                f"  Action: {result['action']}\n"
                f"  Time: {result['timestamp']}"
            )

    async def handle_undo_history(self, args: Optional[str]):
        """Handle /undo-history command."""
        history = self.cli.undo.get_history()
        if not history:
            self.cli.display.print_dim("No undo history")
        else:
            lines = ["[bold]Undo History:[/bold]"]
            for entry in history:
                lines.append(
                    f"  [{entry['index']}] [{entry['timestamp']}] "
                    f"{entry['operation']}: {entry['description']}"
                )
            self.cli.console.print("\n".join(lines))

    # Git commands
    async def handle_diff(self, args: Optional[str]):
        """Handle /diff command."""
        await self.cli.show_diff()

    async def handle_commit(self, args: Optional[str]):
        """Handle /commit command."""
        query = f"/commit {args}" if args else "/commit"
        await self.cli.smart_commit(query)

    # Testing
    async def handle_test(self, args: Optional[str]):
        """Handle /test command."""
        await self.cli.run_tests()

    async def handle_watch_tests(self, args: Optional[str]):
        """Handle /watch command (test watch mode)."""
        await self.cli.start_watch_mode()

    async def handle_watch_stop(self, args: Optional[str]):
        """Handle /watch-stop command."""
        self.cli.stop_watch_mode()

    # Workflow & approval stats
    async def handle_workflow_status(self, args: Optional[str]):
        """Handle /workflow-status command."""
        from rich.panel import Panel
        summary = self.cli.workflow.get_summary()
        self.cli.console.print(Panel(summary, title="🔄 Workflow Status", border_style="blue"))

    async def handle_approval(self, args: Optional[str]):
        """Handle /approval command."""
        from rich.panel import Panel
        stats = self.cli.approval.get_approval_stats()
        summary = (
            f"Total requests: {stats['total']}\n"
            f"Approved: [green]{stats['approved']}[/green]\n"
            f"Rejected: [red]{stats['rejected']}[/red]\n"
            f"Approval rate: {stats['rate']:.1%}"
        )
        self.cli.console.print(Panel(summary, title="✅ Approval Stats", border_style="blue"))

    # Codebase intelligence
    async def handle_index(self, args: Optional[str]):
        """Handle /index command."""
        await self.cli.build_codebase_graph()

    async def handle_analyze(self, args: Optional[str]):
        """Handle /analyze command."""
        if not args:
            self.cli.display.print_error("Usage: /analyze <file>")
            return
        await self.cli.analyze_file_structure(args)

    async def handle_related(self, args: Optional[str]):
        """Handle /related command."""
        if not args:
            self.cli.display.print_error("Usage: /related <file|query>")
            return
        await self.cli.show_related_files(args)

    async def handle_architecture(self, args: Optional[str]):
        """Handle /architecture command."""
        await self.cli.show_architecture()

    async def handle_preview(self, args: Optional[str]):
        """Handle /preview command."""
        if not args:
            self.cli.display.print_error("Usage: /preview <file>")
            return
        await self.cli.show_file_preview(args)

    async def handle_suggest_ai(self, args: Optional[str]):
        """Handle AI suggestions."""
        await self.cli.show_suggestions()

    # Workspace
    async def handle_newtask(self, args: Optional[str]):
        """Handle /newtask command."""
        if not args:
            self.cli.display.print_error("Usage: /newtask <title>")
            return
        await self.cli.create_task(args)

    async def handle_tasks(self, args: Optional[str]):
        """Handle /tasks command."""
        await self.cli.list_tasks()

    async def handle_summary(self, args: Optional[str]):
        """Handle /summary command."""
        await self.cli.show_work_summary()

    async def handle_stats(self, args: Optional[str]):
        """Handle /stats command."""
        await self.cli.show_project_stats()

    async def handle_performance(self, args: Optional[str]):
        """Handle /performance or /perf command."""
        from rich.panel import Panel
        metrics = self.cli.bg_processor.get_metrics()
        summary = (
            f"Files preloaded: [cyan]{metrics.files_preloaded}[/cyan]\n"
            f"Cache hits: [green]{metrics.cache_hits}[/green]\n"
            f"Cache misses: [yellow]{metrics.cache_misses}[/yellow]\n"
            f"Hit rate: [cyan]{metrics.hit_rate():.1%}[/cyan]\n"
            f"Time saved: [green]{metrics.time_saved_ms}ms[/green]\n"
            f"Predictions: {metrics.predictions_made}"
        )
        self.cli.console.print(Panel(summary, title="⚡ Background Processing", border_style="blue"))

    async def handle_metrics(self, args: Optional[str]):
        """Handle /metrics command."""
        from rich.panel import Panel
        summary = self.cli.tool_metrics.get_summary()
        self.cli.console.print(Panel(summary, title="📊 Tool Reliability Metrics", border_style="cyan"))

    # Validation
    async def handle_validate(self, args: Optional[str]):
        """Handle /validate command."""
        modified_files = self.cli.workflow.get_modified_files()
        if not modified_files:
            self.cli.display.print_dim("No modified files to validate")
            return

        self.cli.console.print(f"\n[bold]Validating {len(modified_files)} files...[/bold]")
        result = self.cli.code_validator.validate_before_completion(modified_files)
        report = self.cli.code_validator.get_validation_report(result)
        self.cli.console.print(report)

    # Debug
    async def handle_debug(self, args: Optional[str]):
        """Handle /debug command."""
        from rich.panel import Panel
        if self.cli.debug_logger.enabled:
            summary = self.cli.debug_logger.get_summary()
            self.cli.console.print(Panel(summary, title="🐛 Debug Info", border_style="yellow"))
        else:
            self.cli.display.print_warning("Debug mode is disabled. Enable with /debug-on")

    async def handle_debug_on(self, args: Optional[str]):
        """Handle /debug-on command."""
        self.cli.debug_logger.enable()
        self.cli.display.print_success("✓ Debug logging enabled")
        self.cli.display.print_dim(f"Logs will be saved to: {self.cli.debug_logger.log_file}")

    async def handle_debug_off(self, args: Optional[str]):
        """Handle /debug-off command."""
        self.cli.debug_logger.disable()
        self.cli.display.print_success("✓ Debug logging disabled")

    async def handle_debug_analyze(self, args: Optional[str]):
        """Handle /debug-analyze command."""
        from rich.panel import Panel
        if not args:
            self.cli.display.print_error("Please provide an issue description")
            return
        analysis = self.cli.debug_logger.analyze_issue(args)
        self.cli.console.print(Panel(analysis, title="🔍 Analysis", border_style="cyan"))

    # Auto-fix commands
    async def handle_autofix(self, args: Optional[str]):
        """Handle /autofix command."""
        await self.cli.run_autofix()

    async def handle_autofix_on(self, args: Optional[str]):
        """Handle /autofix-on command."""
        self.cli.auto_fixer.enabled = True
        self.cli.display.print_success("✓ Auto-fix enabled")
        self.cli.display.print_dim("Flux will automatically fix safe issues in the background")

    async def handle_autofix_off(self, args: Optional[str]):
        """Handle /autofix-off command."""
        self.cli.auto_fixer.enabled = False
        self.cli.display.print_warning("Auto-fix disabled")

    async def handle_autofix_undo(self, args: Optional[str]):
        """Handle /autofix-undo command."""
        fix = self.cli.auto_fixer.undo_last_fix()
        if fix:
            self.cli.display.print_success(f"✓ Undone: {fix.description}")
            self.cli.console.print(f"  File: {fix.file_path}")
        else:
            self.cli.display.print_warning("No auto-fixes to undo")

    async def handle_autofix_summary(self, args: Optional[str]):
        """Handle /autofix-summary command."""
        from rich.panel import Panel
        summary = self.cli.auto_fixer.get_fix_summary()
        if summary:
            total = sum(summary.values())
            summary_text = f"Total fixes applied: [cyan]{total}[/cyan]\n\n"
            for fix_type, count in summary.items():
                summary_text += f"  {fix_type}: {count}\n"
            self.cli.console.print(Panel(summary_text, title="🔧 Auto-Fix Summary", border_style="blue"))
        else:
            self.cli.display.print_dim("No auto-fixes applied yet")

    async def handle_autofix_watch(self, args: Optional[str]):
        """Handle /autofix-watch command."""
        await self.cli.start_autofix_watch()

    async def handle_autofix_watch_stop(self, args: Optional[str]):
        """Handle /autofix-watch-stop command."""
        self.cli.stop_autofix_watch()

    async def handle_autofix_stats(self, args: Optional[str]):
        """Handle /autofix-stats command."""
        from rich.panel import Panel
        if self.cli.auto_fix_watcher:
            stats = self.cli.auto_fix_watcher.get_stats()
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
                    rel_path = event.file_path.relative_to(self.cli.cwd) if event.file_path.is_relative_to(self.cli.cwd) else event.file_path
                    stats_text += f"  • {rel_path} - {event.fixes_applied} fix(es)\n"

            self.cli.console.print(Panel(stats_text, title="📊 Auto-Fix Watch Stats", border_style="blue"))
        else:
            self.cli.display.print_warning("Auto-fix watch not started. Use /autofix-watch to start.")
    
    # ============================================
    # UX DIFFERENTIATOR COMMANDS
    # ============================================
    
    # Copilot Mode commands
    async def handle_copilot(self, args: Optional[str]):
        """Handle /copilot command - show current suggestions."""
        from rich.panel import Panel
        suggestions = self.cli.copilot.get_suggestions()
        
        if not suggestions:
            self.cli.display.print_success("✨ Flux Copilot is monitoring your project")
            self.cli.display.print_dim("No suggestions at the moment - everything looks good!")
            return
        
        output = "[bold]🤖 Flux Copilot Suggestions:[/bold]\n\n"
        
        for i, sug in enumerate(suggestions, 1):
            priority_emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(sug.priority.value, '⚪')
            
            output += f"{priority_emoji} [bold]{sug.title}[/bold]\n"
            output += f"   {sug.description}\n"
            output += f"   [dim]→ {sug.action_prompt}[/dim]\n"
            if sug.auto_fixable:
                output += f"   [green]✓ Auto-fixable[/green]\n"
            output += f"   [dim]ID: {sug.id[:8]}[/dim]\n\n"
        
        self.cli.console.print(Panel(output, title="✨ Copilot Suggestions", border_style="magenta"))
    
    async def handle_copilot_status(self, args: Optional[str]):
        """Handle /copilot-status command."""
        from rich.panel import Panel
        stats = self.cli.copilot.get_stats()
        
        status_text = (
            f"Status: [{'green' if stats['monitoring'] else 'yellow'}]{'Active' if stats['monitoring'] else 'Inactive'}[/{'green' if stats['monitoring'] else 'yellow'}]\n"
            f"Current suggestions: [cyan]{stats['suggestion_count']}[/cyan]\n"
            f"Total generated: [cyan]{stats['total_generated']}[/cyan]\n"
            f"Dismissed: [dim]{stats['dismissed_count']}[/dim]\n\n"
            f"[bold]Last check:[/bold]\n"
            f"  Git: {stats['last_git_check'] or 'Never'}\n"
            f"  Tests: {stats['last_test_check'] or 'Never'}\n"
            f"  Code quality: {stats['last_quality_check'] or 'Never'}\n"
        )
        
        self.cli.console.print(Panel(status_text, title="🤖 Copilot Status", border_style="magenta"))
    
    async def handle_copilot_dismiss(self, args: Optional[str]):
        """Handle /copilot-dismiss command."""
        if not args:
            self.cli.display.print_error("Please provide suggestion ID")
            self.cli.display.print_dim("Usage: /copilot-dismiss <id>")
            return
        
        success = self.cli.copilot.dismiss_suggestion(args)
        if success:
            self.cli.display.print_success(f"✓ Dismissed suggestion {args[:8]}")
        else:
            self.cli.display.print_error(f"Suggestion {args} not found")
    
    async def handle_copilot_on(self, args: Optional[str]):
        """Handle /copilot-on command."""
        import asyncio
        if not self.cli.copilot.monitoring:
            asyncio.create_task(self.cli.copilot.start_monitoring())
            self.cli.display.print_success("✓ Flux Copilot started")
            self.cli.display.print_dim("Monitoring your project for improvements...")
        else:
            self.cli.display.print_dim("Copilot is already running")
    
    async def handle_copilot_off(self, args: Optional[str]):
        """Handle /copilot-off command."""
        await self.cli.copilot.stop_monitoring()
        self.cli.display.print_warning("Flux Copilot stopped")
    
    # Time Machine commands
    async def handle_snapshot(self, args: Optional[str]):
        """Handle /snapshot command - create a snapshot."""
        description = args if args else "Manual snapshot"
        
        try:
            snapshot = self.cli.time_machine.create_snapshot(
                description=description,
                git=self.cli.git,
                llm=self.cli.llm,
                memory=self.cli.memory,
                workspace=self.cli.workspace,
                state_tracker=self.cli.state_tracker
            )
            
            self.cli.display.print_success(f"✓ Snapshot created: {snapshot.snapshot_id}")
            self.cli.display.print_dim(f"  {description}")
            if snapshot.git_commit:
                self.cli.display.print_dim(f"  Git: {snapshot.git_commit[:8]} on {snapshot.git_branch}")
            self.cli.display.print_dim(f"  {len(snapshot.modified_files)} modified files backed up")
        except Exception as e:
            self.cli.display.print_error(f"Failed to create snapshot: {e}")
    
    async def handle_snapshots(self, args: Optional[str]):
        """Handle /snapshots command - list snapshots."""
        from rich.panel import Panel
        from rich.table import Table
        
        limit = 20
        if args:
            try:
                limit = int(args)
            except ValueError:
                pass
        
        snapshots = self.cli.time_machine.list_snapshots(limit=limit)
        
        if not snapshots:
            self.cli.display.print_dim("No snapshots yet")
            self.cli.display.print_dim("Create one with /snapshot <description>")
            return
        
        table = Table(title="⏰ Time Machine Snapshots", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Time")
        table.add_column("Description")
        table.add_column("Git", style="cyan")
        table.add_column("Files", justify="right")
        
        for snap in snapshots:
            table.add_row(
                snap.snapshot_id[:12],
                snap.get_display_time(),
                snap.description[:40],
                f"{snap.git_branch or '-'}" if snap.git_branch else "-",
                str(len(snap.modified_files))
            )
        
        self.cli.console.print(table)
        self.cli.display.print_dim(f"\nShowing {len(snapshots)} snapshots (use /restore <id> to restore)")
    
    async def handle_restore(self, args: Optional[str]):
        """Handle /restore command - restore from snapshot."""
        if not args:
            self.cli.display.print_error("Please provide snapshot ID")
            self.cli.display.print_dim("Usage: /restore <snapshot_id> [--files]")
            return
        
        # Parse args
        parts = args.split()
        snapshot_id = parts[0]
        restore_files = '--files' in parts
        
        # Get snapshot
        snapshot = self.cli.time_machine.get_snapshot(snapshot_id)
        if not snapshot:
            self.cli.display.print_error(f"Snapshot {snapshot_id} not found")
            return
        
        # Confirm if restoring files
        if restore_files:
            from rich.prompt import Confirm
            confirm = Confirm.ask(
                f"⚠️  This will restore {len(snapshot.modified_files)} files. Continue?",
                default=False
            )
            if not confirm:
                self.cli.display.print_dim("Cancelled")
                return
        
        # Restore
        try:
            success = self.cli.time_machine.restore_snapshot(
                snapshot_id=snapshot_id,
                llm=self.cli.llm,
                memory=self.cli.memory,
                restore_files=restore_files
            )
            
            if success:
                self.cli.display.print_success(f"✓ Restored from {snapshot.get_display_time()}")
                self.cli.display.print_dim(f"  {snapshot.description}")
                if restore_files:
                    self.cli.display.print_dim(f"  {len(snapshot.modified_files)} files restored")
                else:
                    self.cli.display.print_dim("  Conversation and memory restored (use --files to restore files)")
            else:
                self.cli.display.print_error("Failed to restore snapshot")
        except Exception as e:
            self.cli.display.print_error(f"Restore failed: {e}")
    
    async def handle_compare(self, args: Optional[str]):
        """Handle /compare command - compare two snapshots."""
        if not args:
            self.cli.display.print_error("Please provide two snapshot IDs")
            self.cli.display.print_dim("Usage: /compare <snapshot_id1> <snapshot_id2>")
            return
        
        parts = args.split()
        if len(parts) < 2:
            self.cli.display.print_error("Need two snapshot IDs")
            return
        
        comparison = self.cli.time_machine.compare_snapshots(parts[0], parts[1])
        
        if not comparison:
            self.cli.display.print_error("One or both snapshots not found")
            return
        
        from rich.panel import Panel
        output = (
            f"Time difference: [cyan]{comparison['time_diff'] / 60:.1f}[/cyan] minutes\n"
            f"Conversation messages: [cyan]{comparison['conversation_messages_diff']:+d}[/cyan]\n"
            f"Files changed: [cyan]{comparison['files_changed']}[/cyan]\n"
            f"Tasks difference: [cyan]{comparison['task_diff']:+d}[/cyan]\n"
            f"Git commits differ: [{'yellow' if comparison['git_commits_diff'] else 'green'}]{comparison['git_commits_diff']}[/{'yellow' if comparison['git_commits_diff'] else 'green'}]\n"
        )
        
        self.cli.console.print(Panel(output, title="📊 Snapshot Comparison", border_style="cyan"))
    
    async def handle_timeline(self, args: Optional[str]):
        """Handle /timeline command - show Time Machine stats."""
        from rich.panel import Panel
        summary = self.cli.time_machine.get_summary()
        
        status_text = (
            f"Auto-snapshot: [{'green' if summary['enabled'] else 'yellow'}]{'Enabled' if summary['enabled'] else 'Disabled'}[/{'green' if summary['enabled'] else 'yellow'}]\n"
            f"Interval: [cyan]{summary['interval_minutes']}[/cyan] minutes\n"
            f"Total snapshots: [cyan]{summary['total_snapshots']}[/cyan]\n"
            f"Retention: [dim]{summary['max_snapshots']} snapshots or {summary['max_age_days']} days[/dim]\n\n"
        )
        
        if summary['oldest_snapshot']:
            status_text += f"[bold]Timeline:[/bold]\n"
            status_text += f"  Oldest: {summary['oldest_snapshot']}\n"
            status_text += f"  Newest: {summary['newest_snapshot']}\n"
        
        self.cli.console.print(Panel(status_text, title="⏰ Time Machine", border_style="blue"))
    
    # Smart Context commands
    async def handle_learn(self, args: Optional[str]):
        """Handle /learn command - learn from a file."""
        if not args:
            self.cli.display.print_error("Please provide a file path")
            self.cli.display.print_dim("Usage: /learn <file_path>")
            return
        
        from pathlib import Path
        file_path = Path(args)
        
        if not file_path.exists():
            self.cli.display.print_error(f"File not found: {args}")
            return
        
        try:
            content = file_path.read_text()
            language = "python" if file_path.suffix == ".py" else "unknown"
            
            self.cli.smart_context.learn_from_code(str(file_path), content, language)
            self.cli.smart_context.save()
            
            self.cli.display.print_success(f"✓ Learned from {args}")
            stats = self.cli.smart_context.get_stats()
            self.cli.display.print_dim(f"  Knowledge graph: {stats['total_entities']} entities, {stats['total_relationships']} relationships")
        except Exception as e:
            self.cli.display.print_error(f"Failed to learn: {e}")
    
    async def handle_context(self, args: Optional[str]):
        """Handle /context command - get relevant context."""
        if not args:
            self.cli.display.print_error("Please provide a query")
            self.cli.display.print_dim("Usage: /context <query>")
            return
        
        from rich.panel import Panel
        from rich.table import Table
        
        context = self.cli.smart_context.get_relevant_context(query=args, limit=10)
        
        if not context['entities']:
            self.cli.display.print_dim("No relevant context found")
            return
        
        # Show entities
        table = Table(title="🧠 Relevant Entities", show_header=True)
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("File", style="dim")
        table.add_column("Access", justify="right")
        
        for entity in context['entities']:
            table.add_row(
                entity['type'],
                entity['name'],
                entity['file_path'][:40] if entity['file_path'] else "-",
                str(entity['access_count'])
            )
        
        self.cli.console.print(table)
        
        # Show relationships if any
        if context['relationships']:
            self.cli.display.print_dim(f"\nFound {len(context['relationships'])} relationships")
        
        # Show recent conversations
        if context['conversations']:
            self.cli.display.print_dim(f"Found {len(context['conversations'])} related past conversations")
    
    async def handle_knowledge(self, args: Optional[str]):
        """Handle /knowledge command - show knowledge graph stats."""
        from rich.panel import Panel
        from rich.table import Table
        
        stats = self.cli.smart_context.get_stats()
        
        output = (
            f"[bold]Knowledge Graph Statistics:[/bold]\n\n"
            f"Total entities: [cyan]{stats['total_entities']}[/cyan]\n"
            f"Total relationships: [cyan]{stats['total_relationships']}[/cyan]\n"
            f"Conversations stored: [cyan]{stats['total_conversations']}[/cyan]\n"
            f"Patterns registered: [cyan]{stats['total_patterns']}[/cyan]\n\n"
        )
        
        if stats['entity_types']:
            output += "[bold]Entity Types:[/bold]\n"
            for entity_type, count in stats['entity_types'].items():
                output += f"  {entity_type}: {count}\n"
            output += "\n"
        
        if stats['relationship_types']:
            output += "[bold]Relationship Types:[/bold]\n"
            for rel_type, count in stats['relationship_types'].items():
                output += f"  {rel_type}: {count}\n"
        
        self.cli.console.print(Panel(output, title="🧠 Smart Context", border_style="magenta"))
        
        # Show most accessed entities
        if stats['most_accessed_entities']:
            self.cli.display.print_dim("\n[bold]Most Accessed:[/bold]")
            for entity in stats['most_accessed_entities'][:5]:
                self.cli.display.print_dim(f"  • {entity['name']} ({entity['count']} times)")
    
    async def handle_patterns(self, args: Optional[str]):
        """Handle /patterns command - show registered patterns."""
        from rich.panel import Panel
        
        if not self.cli.smart_context.patterns:
            self.cli.display.print_dim("No design patterns registered yet")
            return
        
        output = "[bold]Registered Design Patterns:[/bold]\n\n"
        
        for pattern_name, entity_ids in self.cli.smart_context.patterns.items():
            output += f"[cyan]{pattern_name}[/cyan]:\n"
            output += f"  {len(entity_ids)} entities\n"
            
            # Show first 3 entities
            for eid in entity_ids[:3]:
                if eid in self.cli.smart_context.entities:
                    entity = self.cli.smart_context.entities[eid]
                    output += f"  • {entity.name}\n"
            
            if len(entity_ids) > 3:
                output += f"  ... and {len(entity_ids) - 3} more\n"
            output += "\n"
        
        self.cli.console.print(Panel(output, title="🎨 Design Patterns", border_style="yellow"))
    
    # Onboarding commands
    async def handle_guide(self, args: Optional[str]):
        """Handle /guide command - show interactive walkthrough."""
        from flux.commands.guide import guide
        guide(self.cli)

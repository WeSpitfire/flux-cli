"""Session and task manager - handles session management, tasks, and state inspection."""


class SessionTaskManager:
    """Manages sessions, tasks, state inspection, and project statistics."""

    def __init__(self, cli):
        """Initialize session/task manager with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli

    async def handle_session_command(self, args: str):
        """Handle session sub-commands."""
        parts = args.split(maxsplit=1)
        if not parts:
            self.cli.console.print("[red]Usage: /session save <name> | /session restore <id>[/red]")
            return

        command = parts[0].lower()

        if command == "save":
            name = parts[1] if len(parts) > 1 else "Work Session"
            session = self.cli.workspace.save_session(name)
            self.cli.console.print(f"[green]✓ Session saved:[/green] {session.name}")
            self.cli.console.print(f"   ID: [cyan]{session.id}[/cyan]")
            self.cli.console.print(f"   Files: {len(session.files_modified)}")
            self.cli.console.print(f"   Time: {session.time_spent_seconds / 60:.1f} minutes")

        elif command == "restore":
            if len(parts) < 2:
                self.cli.console.print("[red]Please provide session ID[/red]")
                return

            session_id = parts[1]
            session = self.cli.workspace.restore_session(session_id)

            if session:
                self.cli.console.print(f"[green]✓ Restored session:[/green] {session.name}")
                self.cli.console.print(f"   Files: {len(session.open_files)}")
                if session.current_task_id:
                    task = self.cli.workspace.get_task(session.current_task_id)
                    if task:
                        self.cli.console.print(f"   Task: [yellow]{task.title}[/yellow]")
            else:
                self.cli.console.print(f"[red]✗ Session not found: {session_id}[/red]")

        elif command == "end":
            summary = self.cli.workspace.end_session()
            if summary:
                self.cli.console.print(f"[green]✓ Session ended:[/green] {summary.session_name}")
                self.cli.console.print(f"\n{summary.summary_text}")

                if summary.key_achievements:
                    self.cli.console.print(f"\n[bold]Key Achievements:[/bold]")
                    for achievement in summary.key_achievements:
                        self.cli.console.print(f"  {achievement}")
            else:
                self.cli.console.print("[yellow]No active session[/yellow]")

        else:
            self.cli.console.print(f"[red]Unknown session command: {command}[/red]")

    async def list_sessions(self):
        """List all sessions."""
        sessions = self.cli.workspace.list_sessions(limit=10)

        if not sessions:
            self.cli.console.print("\n[yellow]No sessions found[/yellow]\n")
            return

        self.cli.console.print("\n[bold]📋 Work Sessions:[/bold]")
        self.cli.console.print("=" * 60)

        for i, session in enumerate(sessions, 1):
            # Time info
            from datetime import datetime
            updated = datetime.fromtimestamp(session.updated_at).strftime("%Y-%m-%d %H:%M")
            duration = session.time_spent_seconds / 60

            # Status indicator
            is_active = self.cli.workspace.active_session and self.cli.workspace.active_session.id == session.id
            status = "▶️ [green]ACTIVE[/green]" if is_active else "  "

            self.cli.console.print(f"\n{status} {i}. [bold]{session.name}[/bold]")
            self.cli.console.print(f"     ID: [dim]{session.id}[/dim]")
            self.cli.console.print(f"     Updated: {updated}")
            self.cli.console.print(f"     Duration: {duration:.1f} minutes")
            self.cli.console.print(f"     Files: {len(session.files_modified)}")

            if session.description:
                self.cli.console.print(f"     [dim]{session.description}[/dim]")

        self.cli.console.print("\n" + "=" * 60)
        self.cli.console.print("[dim]Use /session restore <id> to restore a session[/dim]\n")

    async def create_task(self, title: str):
        """Create a new task."""
        if not title:
            self.cli.console.print("[red]Please provide a task title[/red]")
            return

        task = self.cli.workspace.create_task(title)
        self.cli.console.print(f"[green]✓ Task created:[/green] {task.title}")
        self.cli.console.print(f"   ID: [cyan]{task.id}[/cyan]")
        self.cli.console.print(f"   Priority: {task.priority.value}")
        self.cli.console.print(f"   Status: {task.status.value}")

    async def list_tasks(self):
        """List all tasks."""
        tasks = self.cli.workspace.list_tasks(limit=20)
        next_task = self.cli.workspace.suggest_next_task()
        self.cli.display.print_tasks(tasks, next_task)

    async def show_work_summary(self):
        """Show work summary for today."""
        summary = self.cli.workspace.get_daily_summary()

        # Prepare active session info
        active_session_info = None
        if self.cli.workspace.active_session:
            session = self.cli.workspace.active_session
            active_session_info = {
                'name': session.name,
                'duration_minutes': session.time_spent_seconds / 60,
                'files_count': len(session.files_modified)
            }
            if session.current_task_id:
                task = self.cli.workspace.get_task(session.current_task_id)
                if task:
                    active_session_info['current_task'] = task.title

        self.cli.display.print_work_summary(
            total_minutes=summary['total_minutes'],
            sessions=summary['sessions'],
            files_modified=summary['files_modified'],
            tasks_completed=summary['tasks_completed'],
            completed_task_titles=summary['completed_task_titles'],
            active_session_info=active_session_info
        )

    async def inspect_state(self):
        """Inspect current conversation and context state."""
        self.cli.console.print("\n[bold]🔍 Conversation State Inspector[/bold]")
        self.cli.console.print("=" * 70)

        # Conversation history stats
        history = self.cli.llm.conversation_history
        self.cli.console.print(f"\n[bold cyan]Conversation History:[/bold cyan]")
        self.cli.console.print(f"  Total messages: [cyan]{len(history)}[/cyan]")

        # Count by role
        user_msgs = sum(1 for m in history if m.get('role') == 'user')
        assistant_msgs = sum(1 for m in history if m.get('role') == 'assistant')
        tool_msgs = sum(1 for m in history if m.get('role') == 'tool')

        self.cli.console.print(f"  User messages: [green]{user_msgs}[/green]")
        self.cli.console.print(f"  Assistant messages: [yellow]{assistant_msgs}[/yellow]")
        self.cli.console.print(f"  Tool messages: [blue]{tool_msgs}[/blue]")

        # Estimate token usage
        total_chars = sum(len(str(m.get('content', ''))) for m in history)
        est_tokens = total_chars // 4
        self.cli.console.print(f"  Estimated tokens: [cyan]~{est_tokens:,}[/cyan]")

        # Recent messages
        self.cli.console.print(f"\n[bold cyan]Last 5 Messages:[/bold cyan]")
        for i, msg in enumerate(history[-5:], 1):
            role = msg.get('role', 'unknown')
            content = str(msg.get('content', ''))[:100]
            has_tools = 'tool_calls' in msg

            role_color = {'user': 'green', 'assistant': 'yellow', 'tool': 'blue'}.get(role, 'white')
            self.cli.console.print(f"  {i}. [{role_color}]{role}[/{role_color}]: {content}{'...' if len(str(msg.get('content', ''))) > 100 else ''}")
            if has_tools:
                self.cli.console.print(f"     [dim](includes tool calls)[/dim]")

        # Current context
        self.cli.console.print(f"\n[bold cyan]Current Context:[/bold cyan]")
        if self.cli.memory.state.current_task:
            self.cli.console.print(f"  Task: [yellow]{self.cli.memory.state.current_task}[/yellow]")
        else:
            self.cli.console.print(f"  Task: [dim]None[/dim]")

        # Modified files
        modified = self.cli.workflow.get_modified_files()
        self.cli.console.print(f"  Modified files: [cyan]{len(modified)}[/cyan]")
        if modified:
            for f in modified[:5]:
                self.cli.console.print(f"    - {f}")
            if len(modified) > 5:
                self.cli.console.print(f"    ... and {len(modified) - 5} more")

        # Failure tracker state
        if self.cli.failure_tracker.failures:
            self.cli.console.print(f"\n[bold yellow]⚠️  Active Failures:[/bold yellow]")
            for tool_name, count in self.cli.failure_tracker.failure_count_by_tool.items():
                self.cli.console.print(f"  - {tool_name}: {count} failures")

        # Token usage from LLM
        usage = self.cli.llm.get_token_usage()
        self.cli.console.print(f"\n[bold cyan]Token Usage:[/bold cyan]")
        self.cli.console.print(f"  Input: [cyan]{usage['input_tokens']:,}[/cyan]")
        self.cli.console.print(f"  Output: [cyan]{usage['output_tokens']:,}[/cyan]")
        self.cli.console.print(f"  Total: [cyan]{usage['total_tokens']:,}[/cyan]")
        self.cli.console.print(f"  Cost: [green]${usage['estimated_cost']:.4f}[/green]")

        max_history = getattr(self.cli.config, 'max_history', 8000)
        usage_percent = (usage['total_tokens'] / max_history) * 100 if max_history > 0 else 0

        if usage_percent > 80:
            self.cli.console.print(f"  [yellow]⚠️  At {usage_percent:.0f}% of limit[/yellow]")

        self.cli.console.print("\n" + "=" * 70 + "\n")

    async def show_project_stats(self):
        """Show project-level statistics."""
        if not self.cli.codebase_graph:
            await self.cli.build_codebase_graph()

        if not self.cli.codebase_graph:
            self.cli.console.print("[red]Could not build codebase graph[/red]")
            return

        total_files = len(self.cli.codebase_graph.files)
        total_entities = len(self.cli.codebase_graph.entities)

        self.cli.console.print("\n[bold]📊 Project Statistics:[/bold]")
        self.cli.console.print("=" * 60)

        self.cli.console.print(f"\n📂 Total Files: [cyan]{total_files}[/cyan]")
        self.cli.console.print(f"📚 Total Entities: [cyan]{total_entities}[/cyan]")

        if self.cli.project_info:
            self.cli.console.print(f"\n📈 Project: [green]{self.cli.project_info.name}[/green] ({self.cli.project_info.project_type})")
            if self.cli.project_info.frameworks:
                self.cli.console.print(f"💻 Tech: [dim]{', '.join(self.cli.project_info.frameworks)}[/dim]")

        self.cli.console.print("\n" + "=" * 60 + "\n")

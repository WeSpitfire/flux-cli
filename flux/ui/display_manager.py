"""Display manager - handles all console output and formatting."""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from flux.core.config import Config
from flux.core.project import ProjectInfo
from flux.core.workspace import TaskStatus, TaskPriority, Task
from flux.core.test_runner import TestResult


class DisplayManager:
    """Manages all console display logic."""

    def __init__(self):
        """Initialize display manager."""
        # Force UTF-8 encoding for console to handle emojis
        self.console = Console(file=sys.stdout, force_terminal=False)

    def print_banner(
        self,
        cwd: Path,
        config: Config,
        project_info: Optional[ProjectInfo],
        session_summary: Optional[str],
        current_task: Optional[str]
    ):
        """Print minimal Flux startup banner."""
        # Simple, fast startup - just the essentials
        project_name = project_info.name if project_info else cwd.name
        self.console.print(f"[bold cyan]Flux[/bold cyan] • {project_name}")
        
        # Show session context if resuming
        if session_summary:
            self.console.print(f"[dim]{session_summary}[/dim]")
        
        self.console.print()

    def print_help_text(self):
        """Print help text for starting session."""
        # Skip help text - users know how to exit
        pass

    def prompt_user(self, enable_paste_mode: bool = True) -> str:
        """Get user input."""
        if enable_paste_mode:
            # Real terminal - show fancy prompt
            return Prompt.ask("\n[bold green]You[/bold green]")
        else:
            # Piped/desktop mode - just read from stdin without showing prompt
            return input()

    def print_message(self, message: str, style: str = ""):
        """Print a message with optional style."""
        if style:
            self.console.print(f"[{style}]{message}[/{style}]")
        else:
            self.console.print(message)

    def print_dim(self, message: str):
        """Print dimmed text."""
        self.console.print(f"[dim]{message}[/dim]")

    def print_error(self, message: str):
        """Print error message."""
        self.console.print(f"[red]{message}[/red]")

    def print_warning(self, message: str):
        """Print warning message."""
        self.console.print(f"[yellow]{message}[/yellow]")

    def print_success(self, message: str):
        """Print success message."""
        self.console.print(f"[green]{message}[/green]")

    def print_info(self, message: str):
        """Print info message."""
        self.console.print(f"[cyan]{message}[/cyan]")

    def print_text_stream(self, content: str, end: str = ""):
        """Print streaming text content."""
        self.console.print(content, end=end)

    def print_thinking_indicator(self):
        """Print thinking indicator for AI response."""
        if sys.stdin.isatty():
            self.console.print("\n[bold cyan]Flux[/bold cyan]:", end=" ")

    def print_panel(
        self,
        content: str,
        title: str = "",
        border_style: str = "blue"
    ):
        """Print a panel with content."""
        self.console.print(Panel(content, title=title, border_style=border_style))

    def print_tool_execution(self, tool_name: str, tool_input: dict):
        """Display tool execution panel."""
        self.print_panel(
            f"[bold]{tool_name}[/bold]\n[dim]{tool_input}[/dim]",
            title="🔧 Tool",
            border_style="blue"
        )

    def print_tool_result(self, result: str, is_error: bool = False):
        """Display tool result panel."""
        if is_error:
            self.print_panel(result, title="❌ Error", border_style="red")
        else:
            # Truncate long results
            display_result = result[:500] + "..." if len(result) > 500 else result
            self.print_panel(
                f"[dim]{display_result}[/dim]",
                title="✓ Result",
                border_style="green"
            )

    def print_context_cleared(self, old_tokens: int):
        """Print context cleared message."""
        self.console.print(
            f"[dim]✨ Context automatically refreshed ({old_tokens:,} → 0 tokens)[/dim]"
        )

    def print_emergency_context_clear(self, tokens: int):
        """Print emergency context clear message."""
        self.console.print(
            f"[bold red]🚨 Emergency context clear ({tokens:,} tokens exceeded limits)[/bold red]"
        )

    def print_token_usage(
        self,
        conversation_tokens: int,
        max_tokens: int,
        estimated_cost: float
    ):
        """Display token usage with color coding."""
        usage_percent = (conversation_tokens / max_tokens) * 100 if max_tokens > 0 else 0

        if conversation_tokens > 500:
            color = "red" if usage_percent > 90 else "yellow" if usage_percent > 80 else "dim cyan"
            self.console.print(
                f"[{color}]📊 Context: {conversation_tokens:,}/{max_tokens:,} tokens "
                f"({usage_percent:.0f}%) | Cost: ${estimated_cost:.4f}[/{color}]"
            )

    def print_token_warning(self, usage_percent: float):
        """Print token usage warning."""
        if usage_percent > 90:
            self.console.print("[bold red]⚠ WARNING: Context is at 90%+ of limit![/bold red]")
            self.console.print(
                "[yellow]Strongly recommend using /clear to avoid rate limit errors[/yellow]\n"
            )
        elif usage_percent > 80:
            self.console.print(
                f"[yellow]⚠ Context at {usage_percent:.0f}% - consider using /clear soon[/yellow]\n"
            )

    def print_history_stats(
        self,
        history_len: int,
        conversation_tokens: int,
        max_tokens: int,
        cumulative_tokens: int,
        estimated_cost: float
    ):
        """Display conversation history statistics."""
        usage_percent = (conversation_tokens / max_tokens) * 100 if max_tokens > 0 else 0

        self.console.print(
            f"\n[bold]💬 Conversation History:[/bold]\n"
            f"  Messages: [cyan]{history_len}[/cyan]\n"
            f"  Current context: [cyan]{conversation_tokens:,}[/cyan] / "
            f"[dim]{max_tokens:,}[/dim] tokens ([cyan]{usage_percent:.1f}%[/cyan])\n"
            f"  API usage (cumulative): [dim]{cumulative_tokens:,} tokens[/dim]\n"
            f"  Estimated cost: [green]${estimated_cost:.4f}[/green]\n"
        )

    def print_architecture_detected(self, framework: str, structure: str):
        """Print detected architecture."""
        self.console.print(
            f"[dim]Detected: {framework} ({structure} structure)[/dim]"
        )

    def print_processing_blocker(self):
        """Print message when input is blocked during processing."""
        self.console.print(
            "[yellow]⏳ Please wait for current operation to complete, "
            "or press Ctrl+C to cancel[/yellow]"
        )

    def print_processing_ready(self):
        """Print message when processing is complete."""
        self.console.print("[dim]✓ Ready for next command[/dim]")

    def print_nl_command_interpretation(self, command: str, args: Optional[str]):
        """Print natural language command interpretation."""
        args_str = f" {args}" if args else ""
        self.console.print(f"[dim]→ Interpreted as: {command}{args_str}[/dim]")

    def print_goodbye(self):
        """Print goodbye message."""
        self.console.print("\n[cyan]Goodbye![/cyan]")

    def print_test_results(self, results: List[TestResult]):
        """Display test results."""
        if not results:
            self.print_warning("No test results")
            return

        # Summary counts
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")

        self.console.print(f"\n[bold]🧪 Test Results:[/bold]")
        self.console.print(f"  ✓ Passed: [green]{passed}[/green]")
        if failed > 0:
            self.console.print(f"  ✗ Failed: [red]{failed}[/red]")
        if skipped > 0:
            self.console.print(f"  ⊘ Skipped: [yellow]{skipped}[/yellow]")

        # Show failed tests
        if failed > 0:
            self.console.print("\n[bold red]Failed Tests:[/bold red]")
            for result in results:
                if result.status == "failed":
                    self.console.print(f"  • {result.name}")
                    if result.error:
                        self.console.print(f"    [dim]{result.error[:200]}[/dim]")

    def print_tasks(self, tasks: List[Task], next_task: Optional[Task]):
        """Display task list."""
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
                self.console.print(f"   {priority_icon} [bold]{task.title}[/bold]")
                self.console.print(f"       [dim]ID: {task.id} | Priority: {task.priority.value}[/dim]")

                if task.description:
                    desc = task.description[:60] + "..." if len(task.description) > 60 else task.description
                    self.console.print(f"       [dim]{desc}[/dim]")

        # Suggest next task
        if next_task:
            self.console.print(f"\n[bold cyan]💡 Suggested Next Task:[/bold cyan]")
            self.console.print(f"   {next_task.title}")
            self.console.print(
                f"   [dim]Priority: {next_task.priority.value} | ID: {next_task.id}[/dim]"
            )

        self.console.print("\n" + "=" * 60 + "\n")

    def print_work_summary(
        self,
        total_minutes: float,
        sessions: int,
        files_modified: int,
        tasks_completed: int,
        completed_task_titles: List[str],
        active_session_info: Optional[Dict[str, Any]]
    ):
        """Display daily work summary."""
        self.console.print("\n[bold]📊 Today's Work Summary:[/bold]")
        self.console.print("=" * 60)

        self.console.print(f"\n🕒 Time: {total_minutes:.1f} minutes")
        if total_minutes >= 60:
            hours = total_minutes / 60
            self.console.print(f"      ({hours:.1f} hours)")

        self.console.print(f"\n📋 Sessions: {sessions}")
        self.console.print(f"📄 Files Modified: {files_modified}")
        self.console.print(f"✅ Tasks Completed: {tasks_completed}")

        if completed_task_titles:
            self.console.print(f"\n[bold]Completed Tasks:[/bold]")
            for task_title in completed_task_titles:
                self.console.print(f"  ✓ {task_title}")

        # Show active session info
        if active_session_info:
            self.console.print(
                f"\n[bold cyan]Active Session:[/bold cyan] {active_session_info['name']}"
            )
            self.console.print(f"  Duration: {active_session_info['duration_minutes']:.1f} minutes")
            self.console.print(f"  Files: {active_session_info['files_count']}")

            if active_session_info.get('current_task'):
                self.console.print(
                    f"  Current Task: [yellow]{active_session_info['current_task']}[/yellow]"
                )

        self.console.print("\n" + "=" * 60 + "\n")

    def print_monitor_notification(self, notification: Dict[str, Any]):
        """Print proactive monitor notification."""
        notification_type = notification.get('type', 'info')
        message = notification.get('message', '')
        title = notification.get('title', '💡 Notification')

        if notification_type == 'warning':
            border_style = "yellow"
        elif notification_type == 'error':
            border_style = "red"
        else:
            border_style = "cyan"

        self.print_panel(message, title=title, border_style=border_style)

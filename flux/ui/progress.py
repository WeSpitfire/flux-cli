"""Progress tracking and display for operations."""

from typing import List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.table import Table
from enum import Enum


class StepStatus(Enum):
    """Status of an operation step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class OperationStep:
    """A step in a multi-step operation."""
    name: str
    description: str
    status: StepStatus = StepStatus.PENDING
    error_message: Optional[str] = None


class ProgressTracker:
    """Tracks and displays progress for multi-step operations."""

    def __init__(self, console: Console, operation_name: str = "Operation"):
        """Initialize progress tracker.

        Args:
            console: Rich console for display
            operation_name: Name of the overall operation
        """
        self.console = console
        self.operation_name = operation_name
        self.steps: List[OperationStep] = []
        self.current_step_index: Optional[int] = None

    def add_steps(self, steps: List[tuple]):
        """Add steps to track.

        Args:
            steps: List of (name, description) tuples
        """
        for name, description in steps:
            self.steps.append(OperationStep(name, description))

    def start_step(self, step_index: int):
        """Mark a step as running.

        Args:
            step_index: Index of step to start (0-based)
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = StepStatus.RUNNING
            self.current_step_index = step_index
            self._display_progress()

    def complete_step(self, step_index: int):
        """Mark a step as complete.

        Args:
            step_index: Index of step to complete
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = StepStatus.COMPLETE
            self._display_progress()

    def fail_step(self, step_index: int, error_message: str):
        """Mark a step as failed.

        Args:
            step_index: Index of step that failed
            error_message: Error description
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = StepStatus.ERROR
            self.steps[step_index].error_message = error_message
            self._display_progress()

    def skip_step(self, step_index: int):
        """Mark a step as skipped.

        Args:
            step_index: Index of step to skip
        """
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].status = StepStatus.SKIPPED
            self._display_progress()

    def _display_progress(self):
        """Display current progress state."""
        # Create a table showing all steps
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Step", style="bold")
        table.add_column("Status", justify="center", width=12)
        table.add_column("Description")

        for i, step in enumerate(self.steps, 1):
            # Status icon and color
            if step.status == StepStatus.COMPLETE:
                status = "[green]✓ Done[/green]"
            elif step.status == StepStatus.RUNNING:
                status = "[blue]⟳ Running[/blue]"
            elif step.status == StepStatus.ERROR:
                status = "[red]✗ Error[/red]"
            elif step.status == StepStatus.SKIPPED:
                status = "[dim]○ Skipped[/dim]"
            else:  # PENDING
                status = "[dim]○ Waiting[/dim]"

            # Description (include error if present)
            desc = step.description
            if step.error_message:
                desc += f"\\n[red]{step.error_message}[/red]"

            table.add_row(f"{i}. {step.name}", status, desc)

        # Clear and show table
        self.console.print(f"\\n[bold]{self.operation_name}[/bold]")
        self.console.print(table)

    def show_summary(self):
        """Show final summary of operation."""
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETE)
        failed = sum(1 for s in self.steps if s.status == StepStatus.ERROR)
        skipped = sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)

        total = len(self.steps)

        self.console.print(f"\\n[bold]Summary:[/bold]")
        self.console.print(f"  Total steps: {total}")
        self.console.print(f"  [green]Completed: {completed}[/green]")
        if failed > 0:
            self.console.print(f"  [red]Failed: {failed}[/red]")
        if skipped > 0:
            self.console.print(f"  [dim]Skipped: {skipped}[/dim]")

    def get_status_emoji(self) -> str:
        """Get overall status emoji."""
        if any(s.status == StepStatus.ERROR for s in self.steps):
            return "❌"
        elif all(s.status == StepStatus.COMPLETE for s in self.steps):
            return "✅"
        elif any(s.status == StepStatus.RUNNING for s in self.steps):
            return "⏳"
        else:
            return "⏸️"


class SimpleProgress:
    """Simple progress indicator for single operations."""

    def __init__(self, console: Console):
        """Initialize simple progress.

        Args:
            console: Rich console
        """
        self.console = console
        self.progress: Optional[Progress] = None
        self.task: Optional[TaskID] = None

    def start(self, description: str, total: Optional[int] = None):
        """Start progress indicator.

        Args:
            description: What's being done
            total: Total steps (None for indeterminate)
        """
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn() if total else TextColumn(""),
            console=self.console,
            transient=False
        )
        self.progress.start()
        self.task = self.progress.add_task(description, total=total or 100)

    def update(self, advance: int = 1, description: Optional[str] = None):
        """Update progress.

        Args:
            advance: Amount to advance
            description: New description (optional)
        """
        if self.progress and self.task is not None:
            self.progress.update(
                self.task,
                advance=advance,
                description=description
            )

    def stop(self, success: bool = True, message: Optional[str] = None):
        """Stop progress indicator.

        Args:
            success: Whether operation succeeded
            message: Final message
        """
        if self.progress:
            self.progress.stop()
            self.progress = None

        if message:
            if success:
                self.console.print(f"[green]✓[/green] {message}")
            else:
                self.console.print(f"[red]✗[/red] {message}")


def with_progress(operation_name: str):
    """Decorator to add progress tracking to a function.

    Usage:
        @with_progress("My Operation")
        def my_func(progress_tracker: ProgressTracker):
            progress_tracker.add_steps([
                ("step1", "Doing step 1"),
                ("step2", "Doing step 2")
            ])

            progress_tracker.start_step(0)
            # do work
            progress_tracker.complete_step(0)

            progress_tracker.start_step(1)
            # do work
            progress_tracker.complete_step(1)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if first arg is a Console
            if args and isinstance(args[0], Console):
                console = args[0]
                tracker = ProgressTracker(console, operation_name)
                return func(tracker, *args[1:], **kwargs)
            else:
                # Create default console
                console = Console()
                tracker = ProgressTracker(console, operation_name)
                return func(tracker, *args, **kwargs)
        return wrapper
    return decorator

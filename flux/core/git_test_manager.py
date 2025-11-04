"""Git and test manager - handles Git operations and test execution."""

from typing import Optional
import asyncio
from rich.panel import Panel
from flux.core.test_runner import TestResult


class GitTestManager:
    """Manages Git operations and test execution."""

    def __init__(self, cli):
        """Initialize Git/Test manager with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli

    async def show_diff(self):
        """Show git diff using visual diff viewer."""
        from flux.ui.diff_viewer import create_diff_viewer_from_git

        status = self.cli.git.get_status()

        if not status.is_repo:
            self.cli.console.print("[red]Not in a git repository[/red]")
            return

        if not status.has_changes:
            self.cli.console.print("[green]No changes to show[/green]")
            return

        # Show branch info
        self.cli.console.print(f"\n[bold]Branch:[/bold] {status.branch}")

        # Create and populate diff viewer
        viewer = create_diff_viewer_from_git(self.cli.console, self.cli.git, self.cli.cwd)

        # Display the visual diff
        viewer.display_summary()

    async def smart_commit(self, query: str):
        """Create a smart commit."""
        status = self.cli.git.get_status()

        if not status.is_repo:
            self.cli.console.print("[red]Not in a git repository[/red]")
            return

        if not status.has_changes:
            self.cli.console.print("[yellow]No changes to commit[/yellow]")
            return

        # Check if message provided
        message = None
        if len(query.strip()) > 7:  # More than just "/commit"
            message = query[7:].strip()

        # Generate message if not provided
        if not message:
            all_files = status.staged_files + status.modified_files + status.untracked_files
            message = self.cli.git.create_smart_commit_message(all_files)
            self.cli.console.print(f"\n[bold]Generated commit message:[/bold]")
            self.cli.console.print(f"  {message}\n")

            # Ask for confirmation
            from rich.prompt import Confirm
            if not Confirm.ask("Use this message?"):
                self.cli.console.print("[yellow]Commit cancelled[/yellow]")
                return

        # Stage all changed files
        files_to_commit = status.modified_files + status.untracked_files
        if files_to_commit:
            success, msg = self.cli.git.stage_files(files_to_commit)
            if not success:
                self.cli.console.print(f"[red]Failed to stage files: {msg}[/red]")
                return

        # Create commit
        success, msg = self.cli.git.commit(message)
        if success:
            self.cli.console.print(f"[green]✓ {msg}[/green]")
            self.cli.memory.add_checkpoint(f"Committed: {message}")
        else:
            self.cli.console.print(f"[red]✗ {msg}[/red]")

    async def run_tests(self, file_filter: Optional[str] = None):
        """Run project tests using the smart test runner."""
        self.cli.console.print(f"\n[bold]Running tests...[/bold] (Framework: {self.cli.test_runner.framework.value})\n")

        # Run tests
        result = await asyncio.to_thread(self.cli.test_runner.run_tests, file_filter)

        # Display results
        self.display_test_result(result)

        # Update state tracker
        if result.status.value == "failed":
            self.cli.state_tracker.record_test_failure([
                {"name": f.test_name, "error": f.error_message}
                for f in result.failures
            ])
        else:
            self.cli.state_tracker.record_test_success()

        # Update session with test status
        self.cli.session_manager.update_test_status({
            'total': result.total_tests,
            'passed': result.passed,
            'failed': result.failed,
            'skipped': result.skipped,
            'duration': result.duration
        })

    def display_test_result(self, result: TestResult):
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

        self.cli.console.print(Panel(
            summary,
            title=f"{status_icon} Test Results",
            border_style=status_color
        ))

        # Show failures if any
        if result.failures:
            self.cli.console.print("\n[bold red]Failures:[/bold red]\n")
            for failure in result.failures:
                self.cli.console.print(f"  ❌ {failure.test_name}")
                if failure.file_path:
                    self.cli.console.print(f"     File: [cyan]{failure.file_path}[/cyan]")
                if failure.error_message:
                    # Truncate long error messages
                    error = failure.error_message[:200]
                    if len(failure.error_message) > 200:
                        error += "..."
                    self.cli.console.print(f"     Error: [dim]{error}[/dim]")
                self.cli.console.print()

    async def start_watch_mode(self):
        """Start test watch mode."""
        if self.cli.test_watcher and self.cli.test_watcher.is_running:
            self.cli.console.print("[yellow]Watch mode already running[/yellow]")
            return

        self.cli.console.print("\n[bold cyan]Starting test watch mode...[/bold cyan]")
        self.cli.console.print(f"Framework: [green]{self.cli.test_runner.framework.value}[/green]")
        self.cli.console.print(f"Watching: [cyan]{self.cli.cwd}[/cyan]")
        self.cli.console.print("\n[dim]Tests will run automatically when files change[/dim]")
        self.cli.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        # Create watcher with callback
        from flux.testing.test_watcher import TestWatcher
        self.cli.test_watcher = TestWatcher(
            self.cli.test_runner,
            on_test_complete=self._on_watch_test_complete
        )

        await self.cli.test_watcher.start()

        # Run tests once on start
        self.cli.console.print("[dim]Running initial test suite...[/dim]\n")
        result = await asyncio.to_thread(self.cli.test_runner.run_tests)
        self.display_test_result(result)

        try:
            # Keep running until interrupted
            while self.cli.test_watcher.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.cli.console.print("\n[yellow]Stopping watch mode...[/yellow]")
            self.stop_watch_mode()

    def stop_watch_mode(self):
        """Stop test watch mode."""
        if self.cli.test_watcher:
            self.cli.test_watcher.stop()
            self.cli.test_watcher = None
            self.cli.console.print("[green]✓ Watch mode stopped[/green]")

    def _on_watch_test_complete(self, result: TestResult):
        """Callback when watch mode tests complete."""
        self.cli.console.print("\n" + "─" * 80 + "\n")
        self.cli.console.print("[bold]Tests completed[/bold]")
        self.display_test_result(result)

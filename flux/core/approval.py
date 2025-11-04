"""Interactive approval system for file changes."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import difflib
from pathlib import Path
from typing import Dict, Any, Optional


class ApprovalManager:
    """Manage interactive approval for file modifications."""

    def __init__(self, auto_approve: bool = False):
        """
        Initialize approval manager.

        Args:
            auto_approve: If True, automatically approve all changes
        """
        self.console = Console()
        self.auto_approve = auto_approve
        self.approval_history = []

    def request_approval(
        self,
        operation: str,
        file_path: Path,
        old_content: Optional[str],
        new_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Request user approval for a file modification.

        Args:
            operation: Type of operation (write, edit, etc.)
            file_path: Path to the file
            old_content: Original content (None for new files)
            new_content: New content to write
            context: Additional context about the change

        Returns:
            True if approved, False if rejected
        """
        if self.auto_approve:
            return True

        # Show operation header
        self.console.print()
        self.console.rule(f"[bold cyan]Proposed {operation}: {file_path.name}[/bold cyan]")

        # Show diff or full content
        if old_content is None:
            # New file - show full content
            self._show_new_file(file_path, new_content)
        else:
            # Modified file - show diff
            self._show_diff(file_path, old_content, new_content)

        # Show additional context if provided
        if context:
            self._show_context(context)

        # Show help text
        self.console.print("\n[dim]Options: y/yes (approve), n/no (reject), skip (reject this), stop/cancel/abort (cancel entire workflow)[/dim]")

        # Ask for approval with escape handling
        from rich.prompt import Prompt
        while True:
            try:
                response = Prompt.ask(
                    "\n[bold yellow]Apply these changes?[/bold yellow]",
                    choices=["y", "n", "yes", "no", "stop", "cancel", "skip", "abort"],
                    default="y",
                    show_choices=False
                )
                response = response.lower().strip()

                # Handle escape commands
                if response in ['stop', 'cancel', 'abort']:
                    self.console.print("[yellow]⚠ Workflow cancelled by user[/yellow]")
                    # Raise KeyboardInterrupt to break out of orchestrator
                    raise KeyboardInterrupt("User cancelled workflow")

                # Handle skip
                if response == 'skip':
                    self.console.print("[yellow]⊘ Skipped[/yellow]")
                    return False

                # Handle yes/no
                if response in ['y', 'yes']:
                    approved = True
                    break
                elif response in ['n', 'no']:
                    approved = False
                    break
                else:
                    self.console.print("[red]Please enter y/n, or 'stop' to cancel workflow[/red]")
            except KeyboardInterrupt:
                # User pressed Ctrl+C
                self.console.print("\n[yellow]⚠ Workflow cancelled[/yellow]")
                raise

        # Record decision
        self.approval_history.append({
            "operation": operation,
            "file": str(file_path),
            "approved": approved
        })

        # Show result
        if approved:
            self.console.print("[green]✓ Changes approved[/green]")
        else:
            self.console.print("[red]✗ Changes rejected[/red]")

        return approved

    def _show_new_file(self, file_path: Path, content: str):
        """Show content for a new file."""
        lines = content.splitlines()
        line_count = len(lines)

        self.console.print(f"\n[dim]Creating new file with {line_count} lines[/dim]")

        # Show syntax-highlighted preview (max 50 lines)
        preview_lines = lines[:50]
        preview = "\n".join(preview_lines)

        if line_count > 50:
            preview += f"\n... ({line_count - 50} more lines)"

        try:
            lexer = self._get_lexer(file_path)
            syntax = Syntax(preview, lexer, theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, title=f"[cyan]{file_path.name}[/cyan]", border_style="green"))
        except Exception:
            self.console.print(Panel(preview, title=f"[cyan]{file_path.name}[/cyan]", border_style="green"))

    def _show_diff(self, file_path: Path, old_content: str, new_content: str):
        """Show diff between old and new content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # Generate unified diff
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{file_path.name} (before)",
            tofile=f"{file_path.name} (after)",
            lineterm=""
        ))

        if not diff:
            self.console.print("[dim]No changes detected[/dim]")
            return

        # Show diff with syntax highlighting
        diff_text = "".join(diff)

        try:
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
            self.console.print(Panel(syntax, title="[cyan]Changes[/cyan]", border_style="yellow"))
        except Exception:
            self.console.print(Panel(diff_text, title="[cyan]Changes[/cyan]", border_style="yellow"))

        # Show stats
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        self.console.print(f"[green]+{additions}[/green] [red]-{deletions}[/red]")

    def _show_context(self, context: Dict[str, Any]):
        """Show additional context about the change."""
        if not context:
            return

        items = []
        for key, value in context.items():
            items.append(f"[cyan]{key}:[/cyan] {value}")

        if items:
            self.console.print("\n[dim]Context:[/dim]")
            for item in items:
                self.console.print(f"  {item}")

    def _get_lexer(self, file_path: Path) -> str:
        """Get lexer name for syntax highlighting based on file extension."""
        suffix = file_path.suffix.lower()
        lexer_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".json": "json",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".sh": "bash",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".toml": "toml",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
        }
        return lexer_map.get(suffix, "text")

    def get_approval_stats(self) -> Dict[str, Any]:
        """Get statistics about approval history."""
        if not self.approval_history:
            return {"total": 0, "approved": 0, "rejected": 0}

        approved = sum(1 for entry in self.approval_history if entry["approved"])
        rejected = len(self.approval_history) - approved

        return {
            "total": len(self.approval_history),
            "approved": approved,
            "rejected": rejected,
            "rate": approved / len(self.approval_history) if self.approval_history else 0
        }

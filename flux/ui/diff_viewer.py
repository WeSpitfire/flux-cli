"""Interactive visual diff viewer with TUI navigation."""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
import difflib


@dataclass
class FileDiff:
    """Represents a file diff with metadata."""
    file_path: str
    status: str  # 'modified', 'added', 'deleted', 'staged'
    additions: int = 0
    deletions: int = 0
    diff_lines: List[str] = None
    
    def __post_init__(self):
        if self.diff_lines is None:
            self.diff_lines = []


class DiffViewer:
    """Interactive visual diff viewer using Rich TUI."""
    
    def __init__(self, console: Console):
        """Initialize the diff viewer.
        
        Args:
            console: Rich console for output
        """
        self.console = console
        self.current_file_index = 0
        self.scroll_position = 0
        self.files: List[FileDiff] = []
    
    def add_file_diff(
        self,
        file_path: str,
        status: str,
        original: str,
        modified: str
    ):
        """Add a file diff to the viewer.
        
        Args:
            file_path: Path to the file
            status: File status (modified, added, deleted, staged)
            original: Original file content
            modified: Modified file content
        """
        diff_lines = self._generate_unified_diff(original, modified, file_path)
        additions, deletions = self._count_changes(diff_lines)
        
        self.files.append(FileDiff(
            file_path=file_path,
            status=status,
            additions=additions,
            deletions=deletions,
            diff_lines=diff_lines
        ))
    
    def _generate_unified_diff(
        self,
        original: str,
        modified: str,
        filename: str
    ) -> List[str]:
        """Generate unified diff."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )
        
        return list(diff)
    
    def _count_changes(self, diff_lines: List[str]) -> Tuple[int, int]:
        """Count additions and deletions in diff."""
        additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        return additions, deletions
    
    def _render_file_list(self) -> Table:
        """Render the file list panel."""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Status", style="bold", width=10)
        table.add_column("File", style="cyan", width=50)
        table.add_column("Changes", justify="right", width=15)
        
        for idx, file_diff in enumerate(self.files):
            # Highlight current file
            style = "bold yellow" if idx == self.current_file_index else ""
            
            # Status icon
            status_icon = {
                'modified': '📝',
                'added': '✨',
                'deleted': '🗑️',
                'staged': '📦'
            }.get(file_diff.status, '📄')
            
            # Change summary
            changes = f"[green]+{file_diff.additions}[/green] [red]-{file_diff.deletions}[/red]"
            
            # Highlight current selection
            if idx == self.current_file_index:
                table.add_row(
                    f"{status_icon} {file_diff.status}",
                    f"→ {file_diff.file_path}",
                    changes,
                    style=style
                )
            else:
                table.add_row(
                    f"{status_icon} {file_diff.status}",
                    file_diff.file_path,
                    changes
                )
        
        return table
    
    def _render_diff_panel(self) -> Panel:
        """Render the diff display panel for current file."""
        if not self.files or self.current_file_index >= len(self.files):
            return Panel(
                "[dim]No files to display[/dim]",
                title="Diff Preview",
                border_style="blue"
            )
        
        current_file = self.files[self.current_file_index]
        
        # Color the diff lines
        colored_lines = []
        for line in current_file.diff_lines:
            if line.startswith('+++') or line.startswith('---'):
                colored_lines.append(f"[bold cyan]{line}[/bold cyan]")
            elif line.startswith('+'):
                colored_lines.append(f"[green]{line}[/green]")
            elif line.startswith('-'):
                colored_lines.append(f"[red]{line}[/red]")
            elif line.startswith('@@'):
                colored_lines.append(f"[bold blue]{line}[/bold blue]")
            else:
                colored_lines.append(f"[dim]{line}[/dim]")
        
        # Apply scroll position
        visible_lines = 30  # Show 30 lines at a time
        start = self.scroll_position
        end = min(start + visible_lines, len(colored_lines))
        
        display_lines = colored_lines[start:end]
        
        # Add scroll indicator
        if len(colored_lines) > visible_lines:
            scroll_info = f"[dim]Lines {start+1}-{end} of {len(colored_lines)}[/dim]"
            display_lines.append("\n" + scroll_info)
        
        diff_text = "\n".join(display_lines)
        
        return Panel(
            diff_text,
            title=f"📝 {current_file.file_path} ({current_file.status})",
            border_style="yellow",
            subtitle=f"[green]+{current_file.additions}[/green] [red]-{current_file.deletions}[/red]"
        )
    
    def _render_help(self) -> Text:
        """Render help text."""
        return Text.from_markup(
            "[dim]Navigation: ↑/↓ (files) | j/k (scroll) | q (quit) | enter (apply)[/dim]"
        )
    
    def display_summary(self):
        """Display a quick summary without interactive mode."""
        if not self.files:
            self.console.print("[yellow]No changes to display[/yellow]")
            return
        
        # Summary header
        total_files = len(self.files)
        total_additions = sum(f.additions for f in self.files)
        total_deletions = sum(f.deletions for f in self.files)
        
        self.console.print(
            Panel(
                f"[bold]{total_files} file(s) changed[/bold]\n"
                f"[green]+{total_additions} additions[/green]\n"
                f"[red]-{total_deletions} deletions[/red]",
                title="📊 Change Summary",
                border_style="cyan"
            )
        )
        
        # File list
        table = self._render_file_list()
        self.console.print(table)
        
        # Show first file's diff preview
        if self.files:
            self.console.print("\n" + "─" * 80)
            diff_panel = self._render_diff_panel()
            self.console.print(diff_panel)
            
            if len(self.files) > 1:
                self.console.print(
                    f"\n[dim]Showing 1 of {len(self.files)} files. "
                    "Use interactive mode to see all.[/dim]"
                )
    
    def display_file_diff(self, file_index: int = 0):
        """Display diff for a specific file.
        
        Args:
            file_index: Index of file to display
        """
        if not self.files or file_index >= len(self.files):
            self.console.print("[yellow]No file at that index[/yellow]")
            return
        
        self.current_file_index = file_index
        self.scroll_position = 0
        
        diff_panel = self._render_diff_panel()
        self.console.print(diff_panel)
    
    def display_all(self):
        """Display all file diffs sequentially."""
        if not self.files:
            self.console.print("[yellow]No changes to display[/yellow]")
            return
        
        # Summary first
        self.display_summary()
        
        # Then show each file
        for idx in range(len(self.files)):
            self.console.print("\n" + "─" * 80 + "\n")
            self.display_file_diff(idx)
    
    def next_file(self):
        """Navigate to next file."""
        if self.current_file_index < len(self.files) - 1:
            self.current_file_index += 1
            self.scroll_position = 0
    
    def previous_file(self):
        """Navigate to previous file."""
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.scroll_position = 0
    
    def scroll_up(self):
        """Scroll diff view up."""
        if self.scroll_position > 0:
            self.scroll_position -= 5
    
    def scroll_down(self):
        """Scroll diff view down."""
        if not self.files:
            return
        
        current_file = self.files[self.current_file_index]
        max_scroll = max(0, len(current_file.diff_lines) - 30)
        
        if self.scroll_position < max_scroll:
            self.scroll_position += 5


def create_diff_viewer_from_git(console: Console, git_integration, cwd: Path) -> DiffViewer:
    """Create a diff viewer populated with git changes.
    
    Args:
        console: Rich console
        git_integration: GitIntegration instance
        cwd: Current working directory
        
    Returns:
        Configured DiffViewer instance
    """
    from flux.core.git_utils import GitIntegration
    
    viewer = DiffViewer(console)
    status = git_integration.get_status()
    
    if not status.has_changes:
        return viewer
    
    # Process modified files
    for file_path in status.modified_files:
        try:
            full_path = cwd / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    modified = f.read()
                
                # Get original from git
                original = git_integration.get_file_content_at_commit(file_path, 'HEAD')
                if original is not None:
                    viewer.add_file_diff(file_path, 'modified', original, modified)
        except Exception:
            # Skip files we can't read
            pass
    
    # Process staged files
    for file_path in status.staged_files:
        if file_path in status.modified_files:
            continue  # Already processed
        
        try:
            full_path = cwd / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    modified = f.read()
                
                original = git_integration.get_file_content_at_commit(file_path, 'HEAD')
                if original is not None:
                    viewer.add_file_diff(file_path, 'staged', original, modified)
        except Exception:
            pass
    
    # Process new files
    for file_path in status.untracked_files:
        try:
            full_path = cwd / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    modified = f.read()
                
                viewer.add_file_diff(file_path, 'added', '', modified)
        except Exception:
            pass
    
    return viewer

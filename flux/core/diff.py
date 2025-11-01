"""Diff preview and visualization utilities."""

import difflib
from typing import List, Tuple, Iterator
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


class DiffPreview:
    """Generate and display code diffs."""
    
    def __init__(self, console: Console):
        """Initialize with Rich console."""
        self.console = console
    
    def generate_unified_diff(
        self,
        original: str,
        modified: str,
        filename: str = "file"
    ) -> List[str]:
        """Generate unified diff output."""
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
    
    def display_unified_diff(
        self,
        original: str,
        modified: str,
        filename: str = "file",
        title: str = "Proposed Changes"
    ):
        """Display unified diff in terminal."""
        diff_lines = self.generate_unified_diff(original, modified, filename)
        
        if not diff_lines:
            self.console.print("[dim]No changes[/dim]")
            return
        
        # Color the diff lines
        colored_lines = []
        for line in diff_lines:
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
        
        diff_text = "\n".join(colored_lines)
        
        self.console.print(Panel(
            diff_text,
            title=f"📝 {title}",
            border_style="yellow",
            expand=False
        ))
    
    def display_side_by_side(
        self,
        original: str,
        modified: str,
        filename: str = "file",
        context_lines: int = 3
    ):
        """Display side-by-side comparison."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Find changed lines
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
        changes = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            # Get context
            start_i = max(0, i1 - context_lines)
            end_i = min(len(original_lines), i2 + context_lines)
            start_j = max(0, j1 - context_lines)
            end_j = min(len(modified_lines), j2 + context_lines)
            
            changes.append({
                'tag': tag,
                'original': original_lines[start_i:end_i],
                'modified': modified_lines[start_j:end_j],
                'line_num': i1 + 1
            })
        
        if not changes:
            self.console.print("[dim]No changes[/dim]")
            return
        
        # Display changes
        for change in changes[:5]:  # Limit to first 5 changes
            table = Table(show_header=True, box=None, padding=(0, 1))
            table.add_column("Before", style="red", width=50)
            table.add_column("After", style="green", width=50)
            
            max_len = max(len(change['original']), len(change['modified']))
            for i in range(max_len):
                before = change['original'][i] if i < len(change['original']) else ""
                after = change['modified'][i] if i < len(change['modified']) else ""
                table.add_row(before, after)
            
            self.console.print(Panel(
                table,
                title=f"Line {change['line_num']}",
                border_style="blue"
            ))
    
    def display_summary(
        self,
        original: str,
        modified: str
    ):
        """Display a summary of changes."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
        
        additions = 0
        deletions = 0
        modifications = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                additions += (j2 - j1)
            elif tag == 'delete':
                deletions += (i2 - i1)
            elif tag == 'replace':
                modifications += max(i2 - i1, j2 - j1)
        
        summary = f"[green]+{additions}[/green] [red]-{deletions}[/red]"
        if modifications:
            summary += f" [yellow]~{modifications}[/yellow]"
        
        self.console.print(f"Changes: {summary}")
    
    def get_change_stats(
        self,
        original: str,
        modified: str
    ) -> Tuple[int, int, int]:
        """Get statistics about changes."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
        
        additions = 0
        deletions = 0
        modifications = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                additions += (j2 - j1)
            elif tag == 'delete':
                deletions += (i2 - i1)
            elif tag == 'replace':
                modifications += max(i2 - i1, j2 - j1)
        
        return additions, deletions, modifications
    
    def should_show_preview(
        self,
        original: str,
        modified: str,
        threshold_lines: int = 50
    ) -> bool:
        """Determine if diff is small enough to show."""
        additions, deletions, _ = self.get_change_stats(original, modified)
        total_changes = additions + deletions
        return total_changes <= threshold_lines
    
    def display_streamed_diff(
        self,
        original: str,
        modified: str,
        filename: str = "file",
        chunk_size: int = 50,
        show_progress: bool = True
    ):
        """Display diff in chunks to handle large files efficiently.
        
        Optimized for Haiku - avoids overwhelming output tokens.
        
        Args:
            original: Original file content
            modified: Modified file content
            filename: Name of file being diffed
            chunk_size: Number of diff lines to show per chunk
            show_progress: Show progress indicator
        """
        diff_lines = self.generate_unified_diff(original, modified, filename)
        
        if not diff_lines:
            self.console.print("[dim]No changes[/dim]")
            return
        
        total_lines = len(diff_lines)
        
        # If small enough, show all at once
        if total_lines <= chunk_size:
            self.display_unified_diff(original, modified, filename)
            return
        
        # For large diffs, show summary first
        additions, deletions, modifications = self.get_change_stats(original, modified)
        self.console.print(f"\n[bold]Large diff detected:[/bold] {total_lines} lines")
        self.console.print(f"Changes: [green]+{additions}[/green] [red]-{deletions}[/red] [yellow]~{modifications}[/yellow]")
        
        # Show chunks with progress
        num_chunks = (total_lines + chunk_size - 1) // chunk_size
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Processing diff..."),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("diff", total=num_chunks) if show_progress else None
            
            for chunk_num in range(num_chunks):
                start_idx = chunk_num * chunk_size
                end_idx = min(start_idx + chunk_size, total_lines)
                chunk = diff_lines[start_idx:end_idx]
                
                # Show chunk header
                self.console.print(f"\n[dim]--- Chunk {chunk_num + 1}/{num_chunks} (lines {start_idx}-{end_idx}) ---[/dim]")
                
                # Display chunk
                self._display_diff_chunk(chunk)
                
                if show_progress and task is not None:
                    progress.update(task, advance=1)
                
                # For very large diffs, pause between chunks
                if num_chunks > 5 and chunk_num < num_chunks - 1:
                    # Just show separator
                    pass
        
        self.console.print(f"\n[bold green]✓ Diff complete[/bold green]: {total_lines} lines processed")
    
    def _display_diff_chunk(self, lines: List[str]):
        """Display a chunk of diff lines with color coding."""
        colored = []
        for line in lines:
            if line.startswith('+++') or line.startswith('---'):
                colored.append(f"[bold cyan]{line}[/bold cyan]")
            elif line.startswith('+'):
                colored.append(f"[green]{line}[/green]")
            elif line.startswith('-'):
                colored.append(f"[red]{line}[/red]")
            elif line.startswith('@@'):
                colored.append(f"[bold blue]{line}[/bold blue]")
            else:
                colored.append(f"[dim]{line}[/dim]")
        
        self.console.print("\n".join(colored))
    
    def get_diff_iterator(
        self,
        original: str,
        modified: str,
        filename: str = "file",
        chunk_size: int = 50
    ) -> Iterator[List[str]]:
        """Generate diff chunks as an iterator for memory efficiency.
        
        Useful for very large files where you don't want to hold
        the entire diff in memory.
        
        Args:
            original: Original content
            modified: Modified content  
            filename: File name
            chunk_size: Lines per chunk
            
        Yields:
            Lists of diff lines (chunks)
        """
        # Generate diff as iterator (memory efficient)
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff_iter = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=''
        )
        
        # Yield chunks
        chunk = []
        for line in diff_iter:
            chunk.append(line)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        # Yield remaining
        if chunk:
            yield chunk
    
    def display_compact_diff(
        self,
        original: str,
        modified: str,
        filename: str = "file",
        max_lines: int = 20
    ):
        """Display a compact diff for large changes."""
        diff_lines = self.generate_unified_diff(original, modified, filename)
        
        # Count change lines
        change_lines = [l for l in diff_lines if l.startswith('+') or l.startswith('-')]
        
        if len(change_lines) > max_lines:
            # Show summary for large diffs
            additions, deletions, modifications = self.get_change_stats(original, modified)
            
            self.console.print(Panel(
                f"[bold]Large change detected[/bold]\n\n"
                f"[green]+{additions} lines added[/green]\n"
                f"[red]-{deletions} lines removed[/red]\n"
                f"[yellow]~{modifications} lines modified[/yellow]\n\n"
                f"[dim]Preview limited due to size. Full diff will be applied.[/dim]",
                title="📊 Change Summary",
                border_style="yellow"
            ))
            
            # Show first few and last few lines
            preview_lines = diff_lines[:10] + ["...", "[dim]... (truncated) ...[/dim]", "..."] + diff_lines[-10:]
            colored = []
            for line in preview_lines:
                if line.startswith('+'):
                    colored.append(f"[green]{line}[/green]")
                elif line.startswith('-'):
                    colored.append(f"[red]{line}[/red]")
                else:
                    colored.append(f"[dim]{line}[/dim]")
            
            self.console.print("\n".join(colored[:15]))
        else:
            # Show full diff for small changes
            self.display_unified_diff(original, modified, filename)


def display_streamed_diff(
    self,
    original: str,
    modified: str,
    filename: str = "file",
    chunk_size: int = 100
):
    """Display diff in chunks to handle large files.
    
    Args:
        original: Original file content
        modified: Modified file content  
        filename: Name of file being diffed
        chunk_size: Number of diff lines to show per chunk
    """
    # Generate diff as iterator (not list)
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    
    diff_iter = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=''
    )
    
    # Stream chunks
    chunk = []
    total_lines = 0
    
    for line in diff_iter:
        chunk.append(line)
        
        if len(chunk) >= chunk_size:
            # Display this chunk
            self._display_diff_chunk(chunk, total_lines)
            total_lines += len(chunk)
            chunk = []
    
    # Display final chunk
    if chunk:
        self._display_diff_chunk(chunk, total_lines)

def _display_diff_chunk(self, lines: List[str], start_line: int):
    """Display a chunk of diff lines.
    
    Args:
        lines: List of diff lines to display
        start_line: Starting line number for this chunk
    """
    colored = []
    for line in lines:
        if line.startswith('+++') or line.startswith('---'):
            colored.append(f"[bold cyan]{line}[/bold cyan]")
        elif line.startswith('+'):
            colored.append(f"[green]{line}[/green]")
        elif line.startswith('-'):
            colored.append(f"[red]{line}[/red]")
        elif line.startswith('@@'):
            colored.append(f"[bold blue]{line}[/bold blue]")
        else:
            colored.append(f"[dim]{line}[/dim]")
    
    self.console.print("\\n".join(colored))
    
    if start_line > 0:
        self.console.print(f"[dim]... showing lines {start_line}-{start_line + len(lines)}[/dim]")
    """Display a chunk of diff lines.
    
    Args:
        lines: List of diff lines to display
        start_line: Starting line number for this chunk
    """
    colored = []
    for line in lines:
        if line.startswith('+++') or line.startswith('---'):
            colored.append(f"[bold cyan]{line}[/bold cyan]")
        elif line.startswith('+'):
            colored.append(f"[green]{line}[/green]")
        elif line.startswith('-'):
            colored.append(f"[red]{line}[/red]")
        elif line.startswith('@@'):
            colored.append(f"[bold blue]{line}[/bold blue]")
        else:
            colored.append(f"[dim]{line}[/dim]")
    
    self.console.print("\\n".join(colored))
    
    if start_line > 0:
        self.console.print(f"[dim]... showing lines {start_line}-{start_line + len(lines)}[/dim]")

"""Test the visual diff viewer."""

import asyncio
from pathlib import Path
from rich.console import Console
from flux.ui.diff_viewer import create_diff_viewer_from_git
from flux.core.git_utils import GitIntegration

async def main():
    """Test the diff viewer."""
    cwd = Path.cwd()
    console = Console()
    git = GitIntegration(cwd)

    # Check git status
    status = git.get_status()

    if not status.is_repo:
        console.print("[red]Not in a git repository[/red]")
        return

    if not status.has_changes:
        console.print("[green]No changes to show[/green]")
        return

    console.print(f"\n[bold]Branch:[/bold] {status.branch}\n")

    # Create and display diff viewer
    viewer = create_diff_viewer_from_git(console, git, cwd)
    viewer.display_summary()

    console.print("\n[bold cyan]✓ Visual diff viewer test complete![/bold cyan]")

if __name__ == "__main__":
    asyncio.run(main())

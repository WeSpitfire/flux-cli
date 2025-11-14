"""Interactive walkthrough guide command for Flux CLI."""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown


def guide(cli=None):
    """Display the interactive Flux CLI walkthrough.
    
    Args:
        cli: Optional CLI instance (not used, but kept for consistency with other commands)
    """
    console = Console()
    
    # Find the walkthrough file
    flux_root = Path(__file__).parent.parent.parent
    walkthrough_path = flux_root / "flux-cli-interactive-walkthrough.md"
    
    if not walkthrough_path.exists():
        console.print(Panel(
            "[red]Walkthrough file not found![/red]\n\n"
            f"Expected location: {walkthrough_path}\n\n"
            "The interactive walkthrough helps you learn Flux CLI through hands-on exercises.",
            title="❌ Guide Not Found",
            border_style="red"
        ))
        return
    
    try:
        # Read and display the walkthrough
        content = walkthrough_path.read_text()
        
        # Create a nice header
        console.print("\n")
        console.print(Panel(
            "[bold cyan]Welcome to the Flux CLI Interactive Walkthrough![/bold cyan]\n\n"
            "This guide will help you learn Flux through hands-on exercises.\n"
            "Follow along and complete each task to master Flux CLI.\n\n"
            "[dim]Press 'q' to exit when viewing the guide[/dim]",
            title="🎓 Flux CLI Guide",
            border_style="cyan"
        ))
        console.print("\n")
        
        # Render markdown content
        md = Markdown(content)
        console.print(md)
        
        # Footer with helpful tips
        console.print("\n")
        console.print(Panel(
            "[bold]Quick Tips:[/bold]\n\n"
            "• Try each command in the walkthrough to learn by doing\n"
            "• Ask Flux questions naturally: 'show me what changed', 'run tests'\n"
            "• Use [cyan]/help[/cyan] to see all available commands\n"
            "• Use [cyan]/guide[/cyan] to view this walkthrough anytime\n\n"
            "[dim]Ready to build amazing things with Flux? Let's go! 🚀[/dim]",
            title="💡 Tips",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(Panel(
            f"[red]Error loading walkthrough:[/red]\n\n{str(e)}",
            title="❌ Error",
            border_style="red"
        ))


# Make guide callable as a function
__all__ = ['guide']

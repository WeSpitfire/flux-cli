"""Todo management commands for Flux CLI."""

from rich.console import Console
from rich.table import Table
from flux.core.todo_manager import TodoStatus, TodoPriority


def register_todo_commands(command_router):
    """Register todo management commands.
    
    Args:
        command_router: CommandRouter instance
    """
    command_router.register_command("todos", show_todos, "Show current todos")
    command_router.register_command("todo", todo_command, "Manage todos (add, done, clear)")


def show_todos(cli):
    """Show current todos."""
    console = Console()
    
    todos = cli.todo_manager.get_current_todos()
    
    if not todos:
        console.print("[dim]No active todos. Todos will be automatically created for complex tasks.[/dim]")
        return
    
    # Use the formatted display from TodoManager
    console.print(cli.todo_manager.format_todos_display())


def todo_command(cli, *args):
    """Manage todos.
    
    Subcommands:
        todo add <title> [description]  - Add a new todo
        todo done <number>              - Mark todo as done
        todo clear                      - Clear all todos
        todo show                       - Show todos (same as /todos)
    """
    console = Console()
    
    if not args:
        show_todos(cli)
        return
    
    subcommand = args[0]
    
    if subcommand == "add":
        # Add a new todo
        if len(args) < 2:
            console.print("[red]Usage: /todo add <title> [description][/red]")
            return
        
        title = args[1]
        description = " ".join(args[2:]) if len(args) > 2 else ""
        
        todo = cli.todo_manager.add_todo(title, description)
        console.print(f"[green]✓ Added todo:[/green] {todo.title}")
        show_todos(cli)
    
    elif subcommand == "done" or subcommand == "complete":
        # Mark a todo as done
        if len(args) < 2:
            console.print("[red]Usage: /todo done <number>[/red]")
            return
        
        try:
            todo_num = int(args[1])
            todos = cli.todo_manager.get_current_todos()
            
            if todo_num < 1 or todo_num > len(todos):
                console.print(f"[red]Invalid todo number. Must be between 1 and {len(todos)}[/red]")
                return
            
            todo = todos[todo_num - 1]
            cli.todo_manager.mark_completed(todo.id)
            console.print(f"[green]✓ Marked as done:[/green] {todo.title}")
            
            # Show updated progress
            progress = cli.todo_manager.get_progress()
            if progress['completed'] == progress['total']:
                console.print("\n[bold green]🎉 All todos completed![/bold green]")
            else:
                console.print(f"\n[dim]Progress: {progress['completed']}/{progress['total']} ({progress['percentage']}%)[/dim]")
        
        except ValueError:
            console.print("[red]Invalid number. Usage: /todo done <number>[/red]")
    
    elif subcommand == "clear":
        # Clear todos
        cli.todo_manager.clear_current_list()
        console.print("[yellow]✓ Cleared all todos[/yellow]")
    
    elif subcommand == "show" or subcommand == "list":
        # Show todos
        show_todos(cli)
    
    else:
        console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
        console.print("[dim]Available subcommands: add, done, clear, show[/dim]")

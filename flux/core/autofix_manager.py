"""Auto-fix manager - handles automatic code fixing and watch mode."""

import asyncio


class AutoFixManager:
    """Manages auto-fix operations and watch mode."""

    def __init__(self, cli):
        """Initialize auto-fix manager with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli

    async def run_autofix(self):
        """Run auto-fix on all project files."""
        if not self.cli.auto_fixer.enabled:
            self.cli.console.print("[yellow]Auto-fix is disabled. Enable with /autofix-on[/yellow]")
            return

        self.cli.console.print("\n[bold cyan]🔧 Running Auto-Fix...[/bold cyan]\n")

        # Find all supported files
        supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yaml', '.yml'}
        files_to_check = []

        for ext in supported_extensions:
            files_to_check.extend(self.cli.cwd.rglob(f'*{ext}'))

        # Filter out node_modules, venv, etc.
        ignore_dirs = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build'}
        files_to_check = [
            f for f in files_to_check
            if not any(part in f.parts for part in ignore_dirs)
        ]

        if not files_to_check:
            self.cli.console.print("[yellow]No files found to auto-fix[/yellow]")
            return

        self.cli.console.print(f"Found {len(files_to_check)} files to analyze...")

        total_fixes = 0
        files_fixed = 0

        # Process files
        for i, file_path in enumerate(files_to_check, 1):
            if i % 10 == 0:
                self.cli.console.print(f"[dim]Analyzing... {i}/{len(files_to_check)}[/dim]")

            # Analyze and apply fixes
            fixes = await asyncio.to_thread(self.cli.auto_fixer.analyze_file, file_path)
            if fixes:
                success, count = await asyncio.to_thread(self.cli.auto_fixer.apply_fixes, file_path, fixes)
                if success and count > 0:
                    total_fixes += count
                    files_fixed += 1
                    rel_path = file_path.relative_to(self.cli.cwd)
                    self.cli.console.print(f"  ✓ [green]{rel_path}[/green] - {count} fix(es)")

        # Show summary
        self.cli.console.print("\n[bold]Summary:[/bold]")
        self.cli.console.print(f"  Files analyzed: [cyan]{len(files_to_check)}[/cyan]")
        self.cli.console.print(f"  Files fixed: [green]{files_fixed}[/green]")
        self.cli.console.print(f"  Total fixes: [green]{total_fixes}[/green]")

        if total_fixes > 0:
            self.cli.console.print("\n[dim]Use /autofix-undo to undo last fix[/dim]")
            self.cli.console.print("[dim]Use /autofix-summary to see detailed statistics[/dim]")

    async def start_autofix_watch(self, silent: bool = False):
        """Start auto-fix watch mode.

        Args:
            silent: If True, suppress startup messages (for auto-init)
        """
        if self.cli.auto_fix_watcher and self.cli.auto_fix_watcher.is_running:
            if not silent:
                self.cli.console.print("[yellow]Auto-fix watch already running[/yellow]")
            return

        if not self.cli.auto_fixer.enabled:
            if not silent:
                self.cli.console.print("[yellow]Auto-fix is disabled. Enable with /autofix-on first.[/yellow]")
            return

        if not silent:
            self.cli.console.print("\n[bold cyan]👁️ Starting Auto-Fix Watch Mode...[/bold cyan]")
            self.cli.console.print(f"Watching: [cyan]{self.cli.cwd}[/cyan]")
            self.cli.console.print("[dim]Files will be auto-fixed when you save them[/dim]")
            self.cli.console.print("[dim]Use /autofix-watch-stop to stop[/dim]\n")

        # Create watcher with callback
        def on_fix_applied(event):
            """Show subtle notification when fix is applied."""
            rel_path = event.file_path.relative_to(self.cli.cwd) if event.file_path.is_relative_to(self.cli.cwd) else event.file_path
            fix_desc = ", ".join(event.fix_types)
            # Subtle single-line notification
            self.cli.console.print(f"[dim]✨ Auto-fixed {rel_path} ({event.fixes_applied} fix: {fix_desc})[/dim]")

        from flux.tools.auto_fixer import AutoFixWatcher
        self.cli.auto_fix_watcher = AutoFixWatcher(
            self.cli.auto_fixer,
            on_fix_applied=on_fix_applied
        )

        await self.cli.auto_fix_watcher.start()
        self.cli.console.print("[green]✓ Auto-fix watch started[/green]")

    def stop_autofix_watch(self):
        """Stop auto-fix watch mode."""
        if not self.cli.auto_fix_watcher:
            self.cli.console.print("[yellow]Auto-fix watch not running[/yellow]")
            return

        if not self.cli.auto_fix_watcher.is_running:
            self.cli.console.print("[yellow]Auto-fix watch not running[/yellow]")
            return

        # Show final stats
        stats = self.cli.auto_fix_watcher.get_stats()

        self.cli.auto_fix_watcher.stop()
        self.cli.console.print("\n[green]✓ Auto-fix watch stopped[/green]")

        if stats['total_fixes'] > 0:
            self.cli.console.print(f"  Fixed [cyan]{stats['files_fixed']}[/cyan] files with [cyan]{stats['total_fixes']}[/cyan] total fixes")

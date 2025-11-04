"""Codebase analyzer - handles codebase analysis and architecture inspection."""

from flux.core.suggestions_engine import Priority


class CodebaseAnalyzer:
    """Analyzes codebase structure, architecture, and impact."""

    def __init__(self, cli):
        """Initialize codebase analyzer with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli

    async def show_related_files(self, file_or_query: str):
        """Show files related to a file or query."""
        # Build graph if not built
        if not self.cli.codebase_graph:
            await self.cli.build_codebase_graph()

        if not self.cli.codebase_graph:
            self.cli.console.print("[red]Could not build codebase graph[/red]")
            return

        # Find related files
        related = self.cli.codebase_graph.find_related_files(file_or_query, limit=10)

        if not related:
            self.cli.console.print(f"[yellow]No related files found for '{file_or_query}'[/yellow]")
            return

        self.cli.console.print(f"\n[bold]Related files for '{file_or_query}':[/bold]\n")
        for file_path, score in related:
            # Show file with score indicator
            score_indicator = "🔥" if score > 10 else "🔹" if score > 5 else "🔸"
            self.cli.console.print(f"  {score_indicator} [cyan]{file_path}[/cyan] [dim](score: {score:.1f})[/dim]")

            # Show file context
            context = self.cli.codebase_graph.get_file_context(file_path)
            if context.get('entities'):
                entities = context['entities'][:3]  # Show first 3
                for ent in entities:
                    self.cli.console.print(f"     - {ent['type']}: {ent['name']}")

        self.cli.console.print()

    async def show_file_preview(self, file_path: str):
        """Show preview of what would happen if file is modified."""
        if not self.cli.impact_analyzer:
            self.cli.console.print("[yellow]Impact analyzer not available. Run /index first.[/yellow]")
            return

        # Read current file
        full_path = self.cli.cwd / file_path
        if not full_path.exists():
            self.cli.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            with open(full_path, 'r') as f:
                current_content = f.read()
        except Exception as e:
            self.cli.console.print(f"[red]Error reading file: {e}[/red]")
            return

        # Show current file info
        self.cli.console.print(f"\n[bold]Preview for:[/bold] [cyan]{file_path}[/cyan]\n")

        # Get file context from codebase graph
        if self.cli.codebase_graph and file_path in self.cli.codebase_graph.files:
            context = self.cli.codebase_graph.get_file_context(file_path)

            self.cli.console.print(f"[bold]Current State:[/bold]")
            self.cli.console.print(f"  Language: {context.get('language', 'unknown')}")
            self.cli.console.print(f"  Entities: {len(context.get('entities', []))}")

            if context.get('entities'):
                self.cli.console.print(f"\n[bold]Defined in this file:[/bold]")
                for entity in context['entities'][:5]:
                    self.cli.console.print(f"  - {entity['type']}: {entity['name']} (line {entity['line']})")

            if context.get('dependencies'):
                self.cli.console.print(f"\n[bold]Dependencies:[/bold]")
                for dep in context['dependencies'][:3]:
                    self.cli.console.print(f"  → {dep}")

            if context.get('dependents'):
                self.cli.console.print(f"\n[bold]Files that depend on this:[/bold]")
                for dep in context['dependents'][:3]:
                    self.cli.console.print(f"  ← {dep}")
                if len(context['dependents']) > 3:
                    self.cli.console.print(f"  ... and {len(context['dependents']) - 3} more")

        self.cli.console.print(f"\n[dim]To see impact of specific changes, modify the file and Flux will show the analysis.[/dim]")
        self.cli.console.print()

    def show_impact_analysis(self, impact, show_diff: bool = False):
        """Display impact analysis in a beautiful format."""
        from flux.core.impact_analyzer import ImpactLevel

        # Impact level badge
        level_colors = {
            ImpactLevel.LOW: "green",
            ImpactLevel.MEDIUM: "yellow",
            ImpactLevel.HIGH: "red",
            ImpactLevel.CRITICAL: "bold red"
        }
        level_emoji = {
            ImpactLevel.LOW: "🟢",
            ImpactLevel.MEDIUM: "🟡",
            ImpactLevel.HIGH: "🔴",
            ImpactLevel.CRITICAL: "⚫"
        }

        color = level_colors.get(impact.impact_level, "white")
        emoji = level_emoji.get(impact.impact_level, "○")

        self.cli.console.print(f"\n[bold]📊 Impact Analysis[/bold]")
        self.cli.console.print("=" * 50)

        # Summary
        self.cli.console.print(f"\n[{color}]{emoji} {impact.impact_level.value.upper()}[/{color}] - {impact.change_type.value}")
        self.cli.console.print(f"Confidence: [{self._get_confidence_color(impact.confidence_score)}]{impact.confidence_score * 100:.0f}%[/]")

        # What's affected
        if impact.functions_affected:
            self.cli.console.print(f"\n[bold]Functions:[/bold] {', '.join(impact.functions_affected[:5])}")
            if len(impact.functions_affected) > 5:
                self.cli.console.print(f"  ... and {len(impact.functions_affected) - 5} more")

        if impact.classes_affected:
            self.cli.console.print(f"[bold]Classes:[/bold] {', '.join(impact.classes_affected)}")

        if impact.dependencies_affected:
            self.cli.console.print(f"\n[bold]Dependencies affected:[/bold]")
            for dep in impact.dependencies_affected:
                self.cli.console.print(f"  ← {dep}")

        # Dependency Impact Tree
        if impact.dependency_tree:
            self._show_dependency_tree(impact)

        # Warnings
        if impact.warnings:
            self.cli.console.print(f"\n[bold yellow]Warnings:[/bold yellow]")
            for warning in impact.warnings:
                self.cli.console.print(f"  {warning}")

        # Suggestions
        if impact.suggestions:
            self.cli.console.print(f"\n[bold cyan]Suggestions:[/bold cyan]")
            for suggestion in impact.suggestions:
                self.cli.console.print(f"  {suggestion}")

        # Risk flags
        if impact.breaks_existing_code:
            self.cli.console.print(f"\n[bold red]⚠️  May break existing code![/bold red]")
        if impact.requires_migration:
            self.cli.console.print(f"[bold yellow]⚠️  May require data migration[/bold yellow]")
        if impact.affects_public_api:
            self.cli.console.print(f"[bold yellow]⚠️  Affects public API[/bold yellow]")

        self.cli.console.print("=" * 50)

    def _get_confidence_color(self, confidence: float) -> str:
        """Get color for confidence score."""
        if confidence >= 0.95:
            return "green"
        elif confidence >= 0.80:
            return "cyan"
        elif confidence >= 0.60:
            return "yellow"
        else:
            return "red"

    def _show_dependency_tree(self, impact):
        """Display visual dependency impact tree."""
        self.cli.console.print(f"\n[bold]🌳 Dependency Impact Tree:[/bold]")
        self.cli.console.print(f"[dim]Propagation depth: {impact.propagation_depth} layer(s)[/dim]\n")

        # Group by impact type
        direct_deps = {k: v for k, v in impact.dependency_tree.items() if v.impact_type == "direct"}
        indirect_deps = {k: v for k, v in impact.dependency_tree.items() if v.impact_type == "indirect"}
        test_deps = {k: v for k, v in impact.dependency_tree.items() if v.impact_type == "test"}

        # Show direct dependencies
        if direct_deps:
            self.cli.console.print(f"[bold cyan]Direct Impact:[/bold cyan]")
            for file_path, dep_impact in list(direct_deps.items())[:8]:  # Limit display
                self._show_dependency_node(file_path, dep_impact, prefix="  ")

        # Show test dependencies
        if test_deps:
            self.cli.console.print(f"\n[bold yellow]Test Files:[/bold yellow]")
            for file_path, dep_impact in list(test_deps.items())[:5]:
                self._show_dependency_node(file_path, dep_impact, prefix="  ")

        # Show indirect dependencies
        if indirect_deps:
            self.cli.console.print(f"\n[bold magenta]Indirect Impact:[/bold magenta]")
            for file_path, dep_impact in list(indirect_deps.items())[:5]:
                self._show_dependency_node(file_path, dep_impact, prefix="  ", show_details=False)

        # Summary
        total_deps = len(impact.dependency_tree)
        if total_deps > 18:  # If we didn't show all
            self.cli.console.print(f"\n[dim]... and {total_deps - 18} more files affected[/dim]")

    def _show_dependency_node(self, file_path: str, dep_impact, prefix: str = "", show_details: bool = True):
        """Display a single dependency node."""
        # Risk emoji and color
        risk_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }
        risk_color = {
            "high": "red",
            "medium": "yellow",
            "low": "green"
        }

        emoji = risk_emoji.get(dep_impact.break_risk, "○")
        color = risk_color.get(dep_impact.break_risk, "white")

        # File path with risk indicator
        self.cli.console.print(f"{prefix}├─ {emoji} [{color}]{file_path}[/{color}]")

        if show_details:
            # Show what functions/classes are used
            if dep_impact.functions_used:
                funcs = ", ".join(dep_impact.functions_used[:3])
                if len(dep_impact.functions_used) > 3:
                    funcs += f" +{len(dep_impact.functions_used) - 3}"
                self.cli.console.print(f"{prefix}│  [dim]→ uses functions: {funcs}[/dim]")

            if dep_impact.classes_used:
                classes = ", ".join(dep_impact.classes_used[:3])
                if len(dep_impact.classes_used) > 3:
                    classes += f" +{len(dep_impact.classes_used) - 3}"
                self.cli.console.print(f"{prefix}│  [dim]→ uses classes: {classes}[/dim]")

            # Show break risk if not low
            if dep_impact.break_risk != "low":
                self.cli.console.print(f"{prefix}│  [{color}]⚠ {dep_impact.break_risk} risk of breaking[/{color}]")

    async def show_architecture(self):
        """Show detected architecture patterns."""
        # Build graph if not built
        if not self.cli.codebase_graph:
            await self.cli.build_codebase_graph()

        if not self.cli.codebase_graph:
            self.cli.console.print("[red]Could not build codebase graph[/red]")
            return

        patterns = self.cli.codebase_graph.detect_architecture_patterns()

        self.cli.console.print("\n[bold]Project Architecture:[/bold]\n")
        self.cli.console.print(f"  Framework: [cyan]{patterns.get('framework', 'Unknown')}[/cyan]")
        self.cli.console.print(f"  Structure: [cyan]{patterns.get('structure', 'Unknown')}[/cyan]")
        self.cli.console.print(f"  Testing: [cyan]{patterns.get('testing', 'None detected')}[/cyan]")
        self.cli.console.print(f"  Has tests: [{'green' if patterns.get('has_tests') else 'red'}]{patterns.get('has_tests')}[/]")
        self.cli.console.print(f"  Has docs: [{'green' if patterns.get('has_docs') else 'red'}]{patterns.get('has_docs')}[/]")

        # Show file/entity statistics
        self.cli.console.print(f"\n[bold]Statistics:[/bold]")
        self.cli.console.print(f"  Total files: [cyan]{len(self.cli.codebase_graph.files)}[/cyan]")
        self.cli.console.print(f"  Total entities: [cyan]{len(self.cli.codebase_graph.entities)}[/cyan]")

        # Show most connected files
        most_connected = sorted(
            self.cli.codebase_graph.files.items(),
            key=lambda x: len(x[1].dependencies) + len(x[1].dependents),
            reverse=True
        )[:5]

        if most_connected:
            self.cli.console.print(f"\n[bold]Most Connected Files:[/bold]")
            for file_path, file_node in most_connected:
                connections = len(file_node.dependencies) + len(file_node.dependents)
                self.cli.console.print(f"  [cyan]{file_path}[/cyan] [dim]({connections} connections)[/dim]")

        self.cli.console.print()

    async def analyze_file_structure(self, file_path: str):
        """Analyze file structure for large files before editing."""
        from flux.core.large_file_handler import get_handler
        from pathlib import Path

        # Resolve file path
        full_path = self.cli.cwd / file_path if not Path(file_path).is_absolute() else Path(file_path)

        if not full_path.exists():
            self.cli.console.print(f"[red]File not found: {file_path}[/red]")
            return

        try:
            # Get handler and analyze
            handler = get_handler()
            analysis = handler.analyze_file(full_path)
            guide = handler.get_reading_guide(full_path)

            # Display analysis
            self.cli.console.print(f"\n[bold]📊 File Structure Analysis[/bold]")
            self.cli.console.print("=" * 70)
            self.cli.console.print()

            # Show the guide (it's already formatted nicely)
            self.cli.console.print(guide)

            self.cli.console.print("\n" + "=" * 70)
            self.cli.console.print("[dim]💡 Tip: Use the commands above to read specific sections efficiently[/dim]")
            self.cli.console.print()

        except Exception as e:
            self.cli.console.print(f"[red]Error analyzing file: {e}[/red]")

    async def show_suggestions(self):
        """Show proactive AI suggestions."""
        # Build graph and initialize suggestions engine if needed
        if not self.cli.suggestions_engine:
            await self.cli.build_codebase_graph()

        if not self.cli.suggestions_engine:
            self.cli.console.print("[red]Suggestions engine not available[/red]")
            return

        # Get suggestions
        suggestions = self.cli.suggestions_engine.get_suggestions(max_suggestions=10, min_priority=Priority.LOW)

        if not suggestions:
            self.cli.console.print("\n[dim]No structural suggestions detected.[/dim]")
            self.cli.console.print("[dim]For deeper feature analysis, ask: 'Review this codebase and suggest specific improvements'[/dim]\n")
            return

        # Display suggestions
        self.cli.console.print("\n[bold]💡 Proactive Suggestions:[/bold]")
        self.cli.console.print("=" * 60)

        # Group by priority
        by_priority = {}
        for s in suggestions:
            if s.priority not in by_priority:
                by_priority[s.priority] = []
            by_priority[s.priority].append(s)

        priority_order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]

        for priority in priority_order:
            if priority not in by_priority:
                continue

            priority_suggestions = by_priority[priority]

            # Priority header
            priority_emoji = {
                Priority.CRITICAL: "🔴",
                Priority.HIGH: "🟠",
                Priority.MEDIUM: "🟡",
                Priority.LOW: "🟢"
            }
            priority_color = {
                Priority.CRITICAL: "red",
                Priority.HIGH: "yellow",
                Priority.MEDIUM: "cyan",
                Priority.LOW: "green"
            }

            emoji = priority_emoji.get(priority, "○")
            color = priority_color.get(priority, "white")

            self.cli.console.print(f"\n[{color}]{emoji} {priority.value.upper()}[/{color}]")

            # Show suggestions
            for i, suggestion in enumerate(priority_suggestions, 1):
                self._show_suggestion(suggestion, index=i)

        self.cli.console.print("\n" + "=" * 60)
        self.cli.console.print("[dim]Tip: Ask Flux to implement any of these suggestions![/dim]\n")

    def _show_suggestion(self, suggestion, index: int):
        """Display a single suggestion."""
        # Type icon
        type_icons = {
            "next_action": "▶️",
            "code_quality": "✨",
            "security": "🔒",
            "performance": "⚡",
            "testing": "🧪",
            "documentation": "📝",
            "refactoring": "♻️"
        }
        icon = type_icons.get(suggestion.type.value, "•")

        # Title
        self.cli.console.print(f"\n  {index}. {icon} [bold]{suggestion.title}[/bold]")

        # Description
        self.cli.console.print(f"     [dim]{suggestion.description}[/dim]")

        # File and line
        if suggestion.file_path:
            location = f"{suggestion.file_path}"
            if suggestion.line_number:
                location += f":{suggestion.line_number}"
            self.cli.console.print(f"     📍 {location}")

        # Action (what Flux can do)
        if suggestion.action_prompt:
            self.cli.console.print(f"     💬 [cyan]Try: \"{suggestion.action_prompt}\"[/cyan]")

"""Workflow coordinator - handles task planning and orchestration."""

from typing import Optional
import re


class WorkflowCoordinator:
    """Coordinates workflow execution through task planner and orchestrator."""

    def __init__(self, cli):
        """Initialize workflow coordinator with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli

    async def process_with_task_planner(self, query: str):
        """Process query using smart task planner.

        This uses the TaskPlanner to autonomously break down and execute complex tasks.

        Args:
            query: User's complex task/goal
        """
        # Set processing flag
        self.cli._llm_processing = True
        self.cli._processing_cancelled = False

        try:
            # Step 1: Analyze and create plan
            plan = await self.cli.task_planner.analyze_and_plan(query)

            self.cli.console.print(f"[bold]\u2705 Plan created:[/bold] {len(plan.steps)} steps")
            self.cli.console.print(f"[dim]Complexity: {plan.complexity}[/dim]\n")

            # Step 1.5: Create todo list from plan
            todo_list = self.cli.todo_manager.create_todo_list_from_plan(plan)
            self.cli.console.print(f"[dim]📋 Created {len(todo_list.todos)} todos for tracking[/dim]\n")

            # Step 2: Show plan to user with todo display
            self.cli.console.print(self.cli.todo_manager.format_todos_display())

            # Step 3: Execute plan step by step
            for i, step in enumerate(plan.steps):
                if self.cli._processing_cancelled:
                    self.cli.console.print("[yellow]Task cancelled by user[/yellow]")
                    break

                # Mark current todo as in progress
                todo_id = f"{todo_list.id}-{i+1}"
                self.cli.todo_manager.mark_in_progress(todo_id)

                self.cli.console.print(f"\n[bold cyan]Step {step.step_number}:[/bold cyan] {step.description}")

                # Gather required context for this step
                if step.requires_context:
                    self.cli.console.print(f"[dim]Reading context: {', '.join(step.requires_context)}[/dim]")
                    # TODO: Actually read the context files

                try:
                    # Execute the step through normal conversation mode
                    # This allows LLM to use all available tools
                    await self.cli.process_query_normal(step.description)

                    # Mark step as completed
                    step.completed = True
                    self.cli.todo_manager.mark_completed(todo_id)

                    self.cli.console.print(f"[green]✓ Step {step.step_number} completed[/green]")
                    
                    # Show updated progress
                    progress = self.cli.todo_manager.get_progress()
                    self.cli.console.print(f"[dim]Progress: {progress['completed']}/{progress['total']} ({progress['percentage']}%)[/dim]")
                    
                except Exception as e:
                    self.cli.todo_manager.mark_failed(todo_id, str(e))
                    raise

            if not self.cli._processing_cancelled:
                self.cli.console.print("\n[bold green]🎉 Task completed successfully![/bold green]")

        except Exception as e:
            self.cli.console.print(f"\n[red]Task planning error: {e}[/red]")
            self.cli.console.print("[yellow]Falling back to normal conversation mode...[/yellow]")
            # Fall back to normal processing
            await self.cli.process_query_normal(query)
        finally:
            self.cli._llm_processing = False

    async def process_with_orchestrator(self, query: str):
        """Process a query using the AI orchestrator.

        Args:
            query: User's natural language goal
        """
        # Set processing flag to block new input
        self.cli._llm_processing = True
        self.cli._processing_cancelled = False

        try:
            await self._process_with_orchestrator_impl(query)
        finally:
            # Always clear processing flag when done
            self.cli._llm_processing = False

    async def _process_with_orchestrator_impl(self, query: str):
        """Internal implementation of process_with_orchestrator.

        Args:
            query: User's natural language goal
        """
        try:
            # Show that we're planning
            self.cli.console.print("\n[bold cyan]🎯 Planning workflow...[/bold cyan]")

            # Execute goal through orchestrator
            result = await self.cli.orchestrator.execute_goal(
                goal=query,
                auto_approve=self.cli.config.auto_approve
            )

            # Display plan
            plan = result['plan']

            # Check if plan has parse error (fallback scenario)
            if len(plan['steps']) == 1 and plan['steps'][0].get('tool_name') == '_parse_error':
                self.cli.console.print("[yellow]Could not create workflow plan, using normal conversation mode[/yellow]")
                await self.cli.process_query_normal(query)
                return

            self.cli.console.print(f"\n[bold]Goal:[/bold] {plan['goal']}")
            self.cli.console.print(f"[dim]Steps: {len(plan['steps'])}[/dim]\n")

            # Show plan to user
            if plan['requires_approval'] and not self.cli.config.auto_approve:
                self.cli.console.print("[bold]Execution Plan:[/bold]")
                for i, step in enumerate(plan['steps'], 1):
                    tool_name = step['tool_name']
                    desc = step['description']
                    self.cli.console.print(f"  {i}. [{tool_name}] {desc}")

                # Ask for approval
                self.cli.console.print()
                from rich.prompt import Prompt
                approve = Prompt.ask(
                    "[bold yellow]Proceed with execution?[/bold yellow]",
                    choices=["y", "n"],
                    default="y"
                )

                if approve.lower() != 'y':
                    self.cli.console.print("[yellow]Cancelled[/yellow]")
                    return

            # Execute (plan already executed, just show results)
            self.cli.console.print("\n[bold cyan]📋 Execution Summary:[/bold cyan]\n")
            self.cli.console.print(result['summary'])

            # Show success/failure
            if result['success']:
                self.cli.console.print("\n[bold green]✓ Workflow completed successfully[/bold green]")
            else:
                self.cli.console.print("\n[bold yellow]⚠ Workflow completed with some errors[/bold yellow]")

        except Exception as e:
            self.cli.console.print(f"\n[red]Orchestration error: {e}[/red]")
            self.cli.console.print("[dim]Falling back to normal conversation mode...[/dim]")
            # Fall back to normal processing
            await self.cli.process_query_normal(query)

    def should_use_orchestrator(self, query: str) -> bool:
        """Determine if query should be handled by orchestrator.

        Queries that benefit from orchestration:
        - Build/create features ("add login page")
        - Multi-step workflows ("fix failing tests")
        - Testing workflows ("run tests and fix failures")
        - Code changes with validation ("refactor X and test")

        Queries that should use normal flow:
        - Simple questions ("what does this do?")
        - Explanations ("explain this code")
        - Direct slash commands already handled
        """
        query_lower = query.lower()

        # Orchestration triggers
        # NOTE: Orchestrator is designed for KNOWN WORKFLOWS with clear steps,
        # NOT for complex feature development which needs iterative LLM reasoning
        orchestration_patterns = [
            # Testing workflows (known steps: run → analyze → fix → test)
            r'(run|execute).*?tests?.*?(fix|and)',
            r'fix.*?(test|failing).*?(and|then)',
            # Commit workflows (known steps: review → commit)
            r'(commit|save).*?(changes|work)',
            # REMOVED: build/create/implement patterns - these need conversation mode
        ]

        for pattern in orchestration_patterns:
            if re.search(pattern, query_lower):
                return True

        # Avoid orchestration for questions and reviews
        question_patterns = [
            r'^(what|why|how|when|where|who)',
            r'^(do|does|can|could|would|should|is|are)',
            r'(explain|describe|tell me|show me)',
            r'^(review|look|check|examine|see)',
            r'(please|just|simply)\s+(review|look|check)',
            r'\?\s*$'  # Ends with question mark
        ]

        for pattern in question_patterns:
            if re.search(pattern, query_lower):
                return False

        # Avoid orchestration for continuation requests
        # These should use normal conversation mode with existing context
        continuation_patterns = [
            r'^(continue|keep going|go on|proceed)',
            r'(please|let\'?s)\s+(continue|keep)',
            r'continue (building|implementing|working)',
            r'finish (this|it|that|the)',
            r'complete (this|it|that|the)',
        ]

        for pattern in continuation_patterns:
            if re.search(pattern, query_lower):
                return False

        # Default: DO NOT use orchestrator
        # Orchestrator should only trigger on explicit workflow patterns above
        # All build/create/feature work should use conversation mode for iterative reasoning
        return False

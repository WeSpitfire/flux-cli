"""Conversation manager - handles query processing and tool execution."""

import sys
from typing import Optional, List, Dict, Any


class ConversationManager:
    """Manages AI conversation flow, query processing, and tool execution."""

    def __init__(self, cli):
        """Initialize conversation manager with CLI context.

        Args:
            cli: The CLI instance (provides access to all dependencies)
        """
        self.cli = cli

    async def process_query(self, query: str):
        """Process a user query.

        Args:
            query: User's query or question
        """
        # Log the raw input
        self.cli.debug_logger.log_user_input(query, query)

        # SMART TASK DECOMPOSITION
        if self.cli.task_planner:
            should_decompose, reason = await self.cli.task_planner.should_decompose(query)
            if should_decompose:
                self.cli.console.print(f"[dim]💡 Complex task detected: {reason}[/dim]")
                self.cli.console.print("[dim]🧠 Analyzing and planning execution...[/dim]\n")
                await self.cli.process_with_task_planner(query)
                return

        # Check if this should be orchestrated (legacy workflows)
        use_orchestrator = self.cli.should_use_orchestrator(query)

        if use_orchestrator:
            await self.cli.process_with_orchestrator(query)
            return

        # Otherwise use normal LLM conversation flow
        await self.process_query_normal(query)

    async def process_query_normal(self, query: str):
        """Process query through normal LLM conversation (non-orchestrated).

        Args:
            query: User's query or question
        """
        # Set processing flag to block new input
        self.cli._llm_processing = True
        self.cli._processing_cancelled = False

        try:
            await self._process_query_normal_impl(query)
        except Exception as e:
            # Handle errors gracefully
            error_str = str(e)
            self.cli.console.print(f"\n[red]Error in conversation: {e}[/red]")

            # EMERGENCY: If rate limit error, aggressively clear history
            if "rate_limit" in error_str.lower() or "429" in error_str or "too large" in error_str.lower():
                self.cli.console.print("[yellow]⚠️  Rate limit exceeded - clearing history to recover[/yellow]")
                self.cli.llm.clear_history()
                self.cli.console.print("[dim]History cleared. You can continue with a fresh context.[/dim]")
            else:
                self.cli.console.print("[dim]You can continue chatting - the error has been handled[/dim]")
        finally:
            # Always clear processing flag when done
            self.cli._llm_processing = False

    async def _process_query_normal_impl(self, query: str):
        """Internal implementation of process_query_normal.

        Args:
            query: User's query or question
        """
        # Check token usage and warn if approaching limits
        conversation_tokens = self.cli.llm.estimate_conversation_tokens()
        max_tokens = getattr(self.cli.config, 'max_history', 8000)
        usage_percent = (conversation_tokens / max_tokens) * 100 if max_tokens > 0 else 0

        usage = self.cli.llm.get_token_usage()

        # Show token status
        self.cli.display.print_token_usage(
            conversation_tokens=conversation_tokens,
            max_tokens=max_tokens,
            estimated_cost=usage['estimated_cost']
        )

        # Show token warnings
        self.cli.display.print_token_warning(usage_percent)

        # Start new workflow for each query
        self.cli.workflow.start_workflow()

        # Show thinking indicator
        self.cli.display.print_thinking_indicator()

        response_text = ""
        tool_uses = []

        # Build system prompt with project context
        system_prompt = self._build_system_prompt(query=query)

        # Add contextual state to prompt
        state_context = self.cli.state_tracker.get_contextual_prompt_addon()
        if state_context:
            system_prompt += state_context

        # Log system prompt and context
        self.cli.debug_logger.log_system_prompt(system_prompt)
        self.cli.debug_logger.log_conversation_history(self.cli.llm.conversation_history)

        # Get LLM response
        async for event in self.cli.llm.send_message(
            message=query,
            system_prompt=system_prompt,
            tools=self.cli.tools.get_all_schemas()
        ):
            # Check if user cancelled
            if self.cli._processing_cancelled:
                self.cli.console.print("\n[yellow]Cancelled by user[/yellow]")
                return

            if event["type"] == "text":
                # Stream text to console
                content = event["content"]
                response_text += content
                self.cli.display.print_text_stream(content, end="")

                # SMART BACKGROUND PROCESSING
                tasks = self.cli.bg_processor.analyze_chunk(content)
                if tasks:
                    await self.cli.bg_processor.schedule_and_run(tasks)

            elif event["type"] == "tool_use":
                # Collect tools but DON'T execute yet
                tool_uses.append(event)

        # Log LLM response
        self.cli.debug_logger.log_llm_response(response_text, tool_uses)

        # Track conversation in state tracker
        files_mentioned = []
        for tool_use in tool_uses:
            if 'path' in tool_use['input']:
                files_mentioned.append(tool_use['input']['path'])
            elif 'file_path' in tool_use['input']:
                files_mentioned.append(tool_use['input']['file_path'])
            elif 'paths' in tool_use['input']:
                files_mentioned.extend(tool_use['input']['paths'])
        tools_used = [t['name'] for t in tool_uses]
        self.cli.state_tracker.track_conversation(query, response_text, files_mentioned, tools_used)

        # Record message event in session
        self.cli.session_manager.record_event(
            self.cli.EventType.MESSAGE,
            {
                'query': query,
                'response': response_text[:200],
                'tools_used': tools_used,
                'files_mentioned': files_mentioned
            }
        )

        # If there was text, add newline
        if response_text:
            self.cli.display.print_message("")

        # Check if cancelled before executing tools
        if self.cli._processing_cancelled:
            return

        # Execute tools NOW (after LLM finished generating all tool_calls)
        if tool_uses:
            self.cli.display.print_message("")
            for tool_use in tool_uses:
                # Check cancellation before each tool
                if self.cli._processing_cancelled:
                    self.cli.console.print("[yellow]Remaining tool executions cancelled[/yellow]")
                    return
                await self.execute_tool(tool_use)

            # Continue conversation with tool results
            if not self.cli._processing_cancelled:
                await self.continue_after_tools()
        
        # UX Differentiators - learn and snapshot after successful query
        try:
            # Smart Context: Learn from this conversation
            self.cli.smart_context.learn_from_conversation(
                topic=query[:100],
                user_message=query,
                assistant_message=response_text,
                entities_mentioned=files_mentioned
            )
            
            # Learn from any files that were modified
            for file_path in files_mentioned:
                try:
                    from pathlib import Path
                    full_path = self.cli.cwd / file_path
                    if full_path.exists() and full_path.suffix == '.py':
                        content = full_path.read_text()
                        self.cli.smart_context.learn_from_code(str(file_path), content, "python")
                except Exception:
                    pass
            
            # Save knowledge graph
            self.cli.smart_context.save()
            
            # Time Machine: Create auto-snapshot if it's time
            if self.cli.time_machine.should_auto_snapshot():
                try:
                    snapshot = self.cli.time_machine.create_snapshot(
                        description="Auto-snapshot",
                        git=self.cli.git,
                        llm=self.cli.llm,
                        memory=self.cli.memory,
                        workspace=self.cli.workspace,
                        state_tracker=self.cli.state_tracker
                    )
                    self.cli.console.print(f"[dim]⏰ Auto-snapshot created: {snapshot.snapshot_id[:12]}[/dim]")
                except Exception:
                    pass  # Don't fail the conversation if snapshot fails
        except Exception:
            # Don't fail the conversation if UX features fail
            pass

    async def execute_tool(self, tool_use: dict):
        """Execute a tool and display results.

        Args:
            tool_use: Tool execution request dict with name, id, input
        """
        tool_name = tool_use["name"]
        tool_id = tool_use["id"]
        tool_input = tool_use["input"]

        # Display tool execution
        self.cli.display.print_tool_execution(tool_name, tool_input)

        # CHECK FOR RETRY LOOP BEFORE EXECUTING
        if self.cli.failure_tracker.is_retry_loop(tool_name, threshold=2):
            guidance = self.cli.failure_tracker.get_retry_guidance(tool_name)
            if guidance:
                # BLOCK execution - force strategy change
                result = {
                    "error": {
                        "code": "RETRY_LOOP_DETECTED",
                        "message": f"Too many consecutive failures for {tool_name}. You MUST try a different approach.",
                    },
                    "retry_guidance": guidance,
                    "retry_blocked": True,
                    "previous_failures": self.cli.failure_tracker.failure_count_by_tool.get(tool_name, 0)
                }

                # Add result and display blocking message
                self.cli.llm.add_tool_result(tool_id, result)
                from rich.panel import Panel
                self.cli.console.print(Panel(
                    f"[bold red]⚠️  RETRY LOOP DETECTED[/bold red]\n\n{guidance}",
                    title="❌ Blocked",
                    border_style="red"
                ))
                return  # Don't execute the tool

        # Execute tool
        try:
            import time
            start_time = time.time()

            result = await self.cli.tools.execute(tool_name, **tool_input)
            success = not (isinstance(result, dict) and "error" in result)

            # Record metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self.cli.tool_metrics.record_attempt(tool_name, success, execution_time_ms)

            # Log tool execution
            self.cli.debug_logger.log_tool_call(tool_name, tool_input, result, success)

            # SMART RETRY: If edit_file fails, auto-read and provide context
            if (tool_name == "edit_file" and
                isinstance(result, dict) and
                result.get("error", {}).get("code") == "SEARCH_TEXT_NOT_FOUND"):

                file_path = tool_input.get("path")
                if file_path:
                    retry_count = self.cli.failure_tracker.failure_count_by_tool.get(tool_name, 0)
                    self.cli.console.print(f"[yellow]⚠ Search text not found (attempt {retry_count + 1}). Reading file for context...[/yellow]")

                    # Read the file to get current content
                    try:
                        read_result = await self.cli.tools.execute("read_files", paths=[file_path])

                        # Add helpful context to the error with stronger guidance
                        if retry_count >= 1:
                            message = (
                                "🛑 SECOND FAILURE DETECTED\n\n"
                                "This approach is NOT working. Next attempt will be BLOCKED.\n\n"
                                "You MUST change strategy now:\n"
                                "1. Try a completely different tool\n"
                                "2. Break the change into smaller steps\n"
                                "3. Re-read the file to understand the current state\n\n"
                                "DO NOT retry edit_file with the same approach."
                            )
                        else:
                            message = (
                                "⚠️  SEARCH TEXT NOT FOUND - File has been auto-read for you.\n\n"
                                "BEFORE RETRYING:\n"
                                "1. Look at the EXACT file content in the Result panel below\n"
                                "2. Copy the EXACT text you want to change (including ALL spaces/tabs)\n"
                                "3. DO NOT guess or try to remember - use the exact content shown\n\n"
                                f"Attempt {retry_count + 1}/2 - next failure will be blocked"
                            )

                        result["auto_recovery"] = {
                            "action": "file_read_completed",
                            "message": message,
                            "file_content_available": True,
                            "retry_count": retry_count + 1,
                            "will_block_next": retry_count >= 1
                        }

                        # Show the file content to user
                        from rich.panel import Panel
                        self.cli.console.print(Panel(
                            f"[dim]Auto-read {file_path} to help with retry[/dim]",
                            border_style="yellow"
                        ))

                        # Include the read content in the main tool result
                        result["auto_read_content"] = read_result

                    except Exception as read_error:
                        result["auto_recovery"] = {
                            "action": "file_read_failed",
                            "message": f"Failed to auto-read file: {str(read_error)}"
                        }

            # Check if result is an error
            is_error = isinstance(result, dict) and "error" in result

            if is_error:
                # Record failure
                error_data = result.get("error", {})
                if isinstance(error_data, dict):
                    error_code = error_data.get("code")
                    error_message = error_data.get("message", str(error_data))
                else:
                    error_code = None
                    error_message = str(error_data)

                self.cli.failure_tracker.record_failure(
                    tool_name=tool_name,
                    error_code=error_code,
                    error_message=error_message,
                    input_params=tool_input
                )

                # Get failure count and show visual warning
                failure_count = self.cli.failure_tracker.failure_count_by_tool.get(tool_name, 0)
                if failure_count == 2:
                    from rich.panel import Panel
                    self.cli.console.print(Panel(
                        f"[bold yellow]⚠️  {tool_name} has failed twice in a row[/bold yellow]\n\n"
                        f"The LLM should now try a DIFFERENT approach or tool.\n"
                        f"Next attempt will be automatically blocked.",
                        title="🔄 Retry Warning",
                        border_style="yellow"
                    ))

                # Check for retry loop and inject guidance
                if self.cli.failure_tracker.is_retry_loop(tool_name):
                    guidance = self.cli.failure_tracker.get_retry_guidance(tool_name)
                    if guidance:
                        result["retry_guidance"] = guidance
            else:
                # Success - clear ALL failures (fresh start)
                if self.cli.failure_tracker.failures:
                    self.cli.console.print("[dim]✓ Operation successful - failure tracking reset[/dim]")
                self.cli.failure_tracker.reset()

            # Track test commands
            if tool_name == "run_command":
                command = tool_input.get("command", "")
                if "test" in command.lower() or "pytest" in command.lower():
                    passed = not is_error
                    failures = []
                    if not passed and isinstance(result, dict) and 'output' in result:
                        for line in result['output'].split('\n'):
                            if 'FAILED' in line or 'failed' in line.lower():
                                failures.append(line.strip()[:100])
                    self.cli.state_tracker.track_test_result(command, passed, failures[:5])

            # Add result to conversation
            self.cli.llm.add_tool_result(tool_id, result)

            # Display result (truncated if too long)
            result_str = str(result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."

            from rich.panel import Panel
            self.cli.console.print(Panel(
                result_str,
                title="✓ Result",
                border_style="green"
            ))

            # Show workflow progress indicator
            if self.cli.workflow.context:
                files_read = len(self.cli.workflow.context.files_read)
                stage = self.cli.workflow.context.stage.value
                self.cli.console.print(
                    f"[dim]Workflow: {stage} | Files read: {files_read}[/dim]"
                )

        except KeyboardInterrupt:
            # User cancelled during tool execution
            error_msg = "Operation cancelled by user"
            self.cli.llm.add_tool_result(tool_id, {"error": error_msg, "cancelled": True})
            from rich.panel import Panel
            self.cli.console.print(Panel(
                error_msg,
                title="✗ Cancelled",
                border_style="yellow"
            ))
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.cli.llm.add_tool_result(tool_id, {"error": error_msg})

            from rich.panel import Panel
            self.cli.console.print(Panel(
                error_msg,
                title="✗ Error",
                border_style="red"
            ))

    async def continue_after_tools(self):
        """Continue conversation after tool execution."""
        try:
            # ALWAYS show that we're processing
            self.cli.console.print("\n[dim]⏳ Processing tool results...[/dim]")

            # Show thinking indicator (only in real terminal)
            if sys.stdin.isatty():
                self.cli.console.print("[bold cyan]Flux[/bold cyan]:", end=" ")

            response_text = ""
            tool_uses = []

            # Build system prompt with retry warnings
            system_prompt = self._build_system_prompt()

            # Add retry context if there are failures
            retry_context = self._get_retry_context()
            if retry_context:
                system_prompt += retry_context

            # Continue conversation with tool results (no new message needed)
            # The tool results have already been added to conversation history
            async for event in self.cli.llm.continue_with_tool_results(
                system_prompt=system_prompt,
                tools=self.cli.tools.get_all_schemas()
            ):
                if event["type"] == "text":
                    content = event["content"]
                    response_text += content
                    self.cli.console.print(content, end="")

                elif event["type"] == "tool_use":
                    tool_uses.append(event)

            if response_text:
                self.cli.console.print()

            # Execute more tools if needed (recursive)
            if tool_uses:
                self.cli.console.print()
                for tool_use in tool_uses:
                    await self.execute_tool(tool_use)

                await self.continue_after_tools()

        except KeyboardInterrupt:
            # User cancelled during continuation
            self.cli.console.print("\n[yellow]Operation cancelled[/yellow]")
        except Exception as e:
            # Log error but don't crash
            error_str = str(e)
            self.cli.console.print(f"\n[red]Error in conversation: {e}[/red]")

            # AUTO-CLEAR: If context overflow, automatically clear
            if "rate_limit" in error_str.lower() or "429" in error_str or "too large" in error_str.lower() or "context" in error_str.lower():
                self.cli.llm.clear_history()
                self.cli.console.print("[dim]✨ Context automatically refreshed. Continuing...[/dim]")
            else:
                self.cli.console.print("[dim]You can continue chatting - the error has been handled[/dim]")

    def _get_retry_context(self) -> str:
        """Get retry context warning for system prompt."""
        if not self.cli.failure_tracker.failures:
            return ""

        # Check for tools that have failed multiple times
        warnings = []
        for tool_name, count in self.cli.failure_tracker.failure_count_by_tool.items():
            if count >= 2:
                warnings.append(
                    f"⚠️  CRITICAL: {tool_name} has failed {count} times. "
                    f"DO NOT retry the same approach. Try:\n"
                    f"  - Re-read files and copy EXACT text\n"
                    f"  - Use a different tool (e.g., ast_edit for Python)\n"
                    f"  - Break the change into smaller steps\n"
                    f"  - Ask for clarification if unclear"
                )

        if warnings:
            return "\n\n" + "\n\n".join(warnings) + "\n"
        return ""

    def _build_system_prompt(self, query: Optional[str] = None) -> str:
        """Build system prompt with project context and intelligence."""
        from flux.llm.prompts import get_system_prompt

        # Get model-appropriate prompt
        prompt = get_system_prompt(self.cli.config.model)

        # Add minimal project context
        if self.cli.project_info:
            prompt += f"\n\nProject: {self.cli.project_info.name} ({self.cli.project_info.project_type})"
            if self.cli.project_info.frameworks:
                prompt += f" | {', '.join(self.cli.project_info.frameworks[:2])}"

        # Add README only on first query
        if self.cli._project_readme and query and len(self.cli.llm.conversation_history) < 2:
            readme_snippet = self.cli._project_readme[:500]
            prompt += f"\n\nREADME: {readme_snippet}"

        # Codebase intelligence
        if self.cli.codebase_graph and query:
            suggested_files = self.cli.get_intelligent_context(query)
            if suggested_files:
                prompt += f"\n\nRelevant: {', '.join(suggested_files[:2])}"

        # Memory context
        if self.cli.memory.state.current_task:
            prompt += f"\n\nCurrent task: {self.cli.memory.state.current_task}"

        # Session context
        session_context = self.cli.session_manager.get_context_for_ai()
        if session_context.get('recent_events'):
            prompt += "\n\nRecent session activity:"
            for event in session_context['recent_events'][:3]:
                prompt += f"\n- {event['type']}: {event.get('summary', 'N/A')}"

        if session_context.get('current_task'):
            prompt += f"\n\nActive task: {session_context['current_task']}"

        return prompt

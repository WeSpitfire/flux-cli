"""Integration module to connect performance improvements to the main CLI.

This module integrates:
- ParallelToolExecutor for concurrent tool execution
- StreamingPipeline for non-blocking LLM responses
- SemanticSearch for intelligent code search
- IntelligentCache for caching LLM responses and tool results
- WorkflowAutomation for macro support and replay
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

from flux.core.parallel_executor import ParallelToolExecutor
from flux.core.streaming_pipeline import StreamingPipeline
from flux.core.semantic_search import SemanticSearchEngine
from flux.core.intelligent_cache import IntelligentCache
from flux.core.workflow_automation import WorkflowAutomation


class PerformanceIntegrator:
    """Integrates all performance improvements into the CLI."""
    
    def __init__(self, cli):
        """Initialize with CLI instance.
        
        Args:
            cli: The main CLI instance to enhance
        """
        self.cli = cli
        self.cwd = cli.cwd
        
        # Initialize components
        # ParallelToolExecutor needs tool_registry, we'll set it up later
        self.parallel_executor = None  # Will be initialized when tools are available
        self.streaming_pipeline = StreamingPipeline()
        
        # Make semantic search optional - it requires heavy dependencies
        try:
            self.semantic_search = SemanticSearchEngine(str(self.cwd))
        except Exception as e:
            print(f"[Warning] Semantic search disabled: {e}")
            self.semantic_search = None
        # Initialize cache with default settings
        cache_dir = Path.home() / ".flux" / "cache"
        self.cache = IntelligentCache(cache_dir=cache_dir)
        self.workflow_automation = WorkflowAutomation()
        
        # Patch CLI methods
        self._patch_cli_methods()
        
    def _patch_cli_methods(self):
        """Patch CLI methods to use performance improvements."""
        # Initialize parallel executor with tool registry
        if hasattr(self.cli, 'tools'):
            # Create tool registry dict for parallel executor
            tool_registry = {}
            for tool_name, tool in self.cli.tools.tools.items():
                tool_registry[tool_name] = tool.execute
            if tool_registry:
                self.parallel_executor = ParallelToolExecutor(tool_registry, max_concurrent=4)
        
        # Save original methods
        self.cli._original_execute_tool = self.cli.execute_tool
        self.cli._original_process_query = self.cli.process_query
        
        # Replace with enhanced versions
        self.cli.execute_tool = self._enhanced_execute_tool
        self.cli.process_query = self._enhanced_process_query
        self.cli.execute_tools_parallel = self._execute_tools_parallel
        self.cli.search_semantic = self._search_semantic
        
    async def _enhanced_execute_tool(self, tool_use: dict):
        """Enhanced tool execution with caching and parallelization support.
        
        Args:
            tool_use: Tool use dictionary from LLM
        """
        tool_name = tool_use.get("name")
        tool_input = tool_use.get("input", {})
        
        # Check cache first
        cache_key = f"{tool_name}:{str(tool_input)}"
        cached_result = await self.cache.get(cache_key)
        
        if cached_result is not None:
            self.cli.console.print(f"[dim]⚡ Using cached result for {tool_name}[/dim]")
            # Add to conversation with cached result
            self.cli.llm.add_tool_result(tool_use.get("id"), cached_result)
            return
        
        # Execute tool normally
        await self.cli._original_execute_tool(tool_use)
        
        # Cache successful results
        # Note: We need to get the result from the conversation history
        # This is a simplified approach - in production, modify execute_tool to return result
        
    async def _enhanced_process_query(self, query: str):
        """Enhanced query processing with workflow automation.
        
        Args:
            query: User query to process
        """
        # Check if this is a workflow command
        if query.startswith("/replay"):
            # Extract workflow name
            parts = query.split()
            if len(parts) > 1:
                workflow_name = parts[1]
                await self._replay_workflow(workflow_name)
                return
        elif query.startswith("/record"):
            # Start recording
            parts = query.split()
            if len(parts) > 1:
                workflow_name = parts[1]
                self.workflow_automation.start_recording(workflow_name)
                self.cli.console.print(f"[green]📹 Recording workflow: {workflow_name}[/green]")
                return
            
        elif query == "/stop-record":
            # Stop recording
            workflow = self.workflow_automation.stop_recording()
            if workflow:
                self.cli.console.print(f"[green]✅ Workflow recorded: {workflow.name}[/green]")
                self.cli.console.print(f"[dim]Use /replay {workflow.name} to replay[/dim]")
            return
            
        # Use semantic search for context if query looks like a code question
        if self.semantic_search and any(keyword in query.lower() for keyword in ['function', 'class', 'method', 'file', 'code', 'implement']):
            results = await self.semantic_search.search(query, k=3)
            if results:
                self.cli.console.print("[dim]📚 Found relevant context:[/dim]")
                for result in results[:2]:  # Show top 2
                    self.cli.console.print(f"[dim]  • {result['file_path']}:{result.get('line', '?')}[/dim]")
                    
        # Process normally with streaming
        await self._process_with_streaming(query)
        
    async def _process_with_streaming(self, query: str):
        """Process query with streaming responses.
        
        Args:
            query: User query to process
        """
        # For now, just call the original process query since streaming needs more setup
        # TODO: Implement proper streaming when LLM provider supports it
        await self.cli._original_process_query(query)
                
    async def _execute_tools_parallel(self, tool_uses: List[dict]):
        """Execute multiple tools in parallel.
        
        Args:
            tool_uses: List of tool use dictionaries
        """
        if not self.parallel_executor:
            # Fallback to sequential execution
            for tool_use in tool_uses:
                await self.cli._original_execute_tool(tool_use)
            return
            
        # Analyze dependencies
        dependencies = self._analyze_tool_dependencies(tool_uses)
        
        # Create ToolCall objects for parallel executor
        from flux.core.parallel_executor import ToolCall
        tool_calls = []
        for tool_use in tool_uses:
            tool_name = tool_use.get("name")
            tool_input = tool_use.get("input", {})
            tool_id = tool_use.get("id")
            
            # Create ToolCall
            tool_call = ToolCall(
                id=tool_id,
                name=tool_name,
                params=tool_input,
                dependencies=set(dependencies.get(tool_id, []))
            )
            tool_calls.append(tool_call)
            
        # Execute in parallel
        self.cli.console.print(f"[dim]⚡ Executing {len(tool_calls)} tools in parallel...[/dim]")
        
        results = await self.parallel_executor.execute_batch(
            tool_calls,
            auto_detect_deps=True
        )
        
        # Add results to conversation
        for result in results:
            if result.status.value == "completed":
                self.cli.llm.add_tool_result(result.id, result.result)
            else:
                self.cli.llm.add_tool_result(result.id, {"error": result.error or "Unknown error"})
                
    def _analyze_tool_dependencies(self, tool_uses: List[dict]) -> Dict[str, List[str]]:
        """Analyze dependencies between tools.
        
        Args:
            tool_uses: List of tool use dictionaries
            
        Returns:
            Dictionary mapping tool IDs to their dependencies
        """
        dependencies = {}
        
        # Simple heuristic: file writes depend on file reads of the same file
        file_reads = {}
        file_writes = {}
        
        for tool_use in tool_uses:
            tool_id = tool_use.get("id")
            tool_name = tool_use.get("name")
            tool_input = tool_use.get("input", {})
            
            if tool_name == "read_files":
                path = tool_input.get("path")
                if path:
                    file_reads[path] = tool_id
                    
            elif tool_name in ["write_file", "edit_file"]:
                path = tool_input.get("path")
                if path and path in file_reads:
                    # This write depends on the read
                    dependencies[tool_id] = [file_reads[path]]
                    
        return dependencies
        
    def _create_tool_executor(self, cli):
        """Create a tool executor function for the parallel executor.
        
        Args:
            cli: CLI instance with tools
            
        Returns:
            Async function that executes tools
        """
        async def executor(task: dict) -> dict:
            """Execute a single tool task."""
            tool_name = task["name"]
            tool_input = task["input"]
            
            # Get tool
            tool = cli.tools.get(tool_name)
            if not tool:
                return {"error": f"Tool {tool_name} not found"}
                
            # Execute tool
            try:
                result = await tool.execute(**tool_input)
                
                # Cache result
                cache_key = f"{tool_name}:{str(tool_input)}"
                await self.cache.set(cache_key, result, ttl=3600)
                
                return result
            except Exception as e:
                return {"error": str(e)}
                
        return executor
        
    async def _search_semantic(self, query: str, max_results: int = 5) -> List[dict]:
        """Perform semantic search on the codebase.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        if self.semantic_search:
            return await self.semantic_search.search(query, k=max_results)
        return []
        
    async def _replay_workflow(self, workflow_name: str):
        """Replay a recorded workflow.
        
        Args:
            workflow_name: Name of workflow to replay
        """
        self.cli.console.print(f"[cyan]🔄 Replaying workflow: {workflow_name}[/cyan]")
        
        success = await self.workflow_automation.replay_workflow(
            workflow_name,
            self._create_tool_executor(self.cli)
        )
        
        if success:
            self.cli.console.print(f"[green]✅ Workflow completed successfully[/green]")
        else:
            self.cli.console.print(f"[red]❌ Workflow failed[/red]")


def integrate_performance_improvements(cli):
    """Main integration function to be called from CLI initialization.
    
    Args:
        cli: CLI instance to enhance
        
    Returns:
        PerformanceIntegrator instance
    """
    return PerformanceIntegrator(cli)
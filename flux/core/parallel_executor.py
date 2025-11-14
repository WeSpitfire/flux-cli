"""Parallel Tool Executor - Execute multiple tools concurrently.

This module enables Flux to execute tools in parallel when safe,
dramatically improving performance for multi-step operations.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Callable, Awaitable
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolCall:
    """Represents a single tool call."""
    id: str
    name: str
    params: Dict[str, Any]
    dependencies: Set[str] = field(default_factory=set)  # IDs of tools that must complete first
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class ToolResult:
    """Result of tool execution."""
    id: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time
        }


class DependencyResolver:
    """Resolves dependencies between tool calls."""
    
    def analyze_dependencies(self, tool_calls: List[ToolCall]) -> List[List[ToolCall]]:
        """
        Analyze tool calls and group them into execution batches.
        
        Returns list of batches where each batch can be executed in parallel.
        """
        # Build dependency graph
        graph = {call.id: call for call in tool_calls}
        in_degree = {call.id: len(call.dependencies) for call in tool_calls}
        
        # Topological sort with level grouping
        batches = []
        while graph:
            # Find all nodes with no dependencies
            current_batch = [
                call for call_id, call in graph.items()
                if in_degree[call_id] == 0
            ]
            
            if not current_batch:
                # Circular dependency detected
                raise ValueError("Circular dependency detected in tool calls")
            
            batches.append(current_batch)
            
            # Remove processed nodes and update dependencies
            for call in current_batch:
                del graph[call.id]
                del in_degree[call.id]
                
                # Update in-degree for dependent nodes
                for other_id in in_degree:
                    if call.id in graph.get(other_id, ToolCall("", "", {})).dependencies:
                        in_degree[other_id] -= 1
        
        return batches
    
    def auto_detect_dependencies(self, tool_calls: List[ToolCall]) -> None:
        """
        Automatically detect dependencies based on tool types and parameters.
        
        Rules:
        - File writes must complete before reads of the same file
        - File deletes must happen after all operations on that file
        - Test runs should happen after code changes
        """
        for i, call in enumerate(tool_calls):
            for j, other in enumerate(tool_calls[:i]):
                # Check file dependencies
                if self._has_file_dependency(other, call):
                    call.dependencies.add(other.id)
                
                # Check test dependencies
                if self._has_test_dependency(other, call):
                    call.dependencies.add(other.id)
    
    def _has_file_dependency(self, first: ToolCall, second: ToolCall) -> bool:
        """Check if second depends on first due to file operations."""
        # Write -> Read dependency
        if first.name in ['write_file', 'edit_file'] and second.name == 'read_files':
            first_path = first.params.get('path') or first.params.get('file_path')
            second_paths = second.params.get('paths', [])
            if first_path and first_path in second_paths:
                return True
        
        # Any operation -> Delete dependency
        if second.name == 'delete_file':
            second_path = second.params.get('path')
            first_path = first.params.get('path') or first.params.get('file_path')
            if first_path == second_path:
                return True
        
        return False
    
    def _has_test_dependency(self, first: ToolCall, second: ToolCall) -> bool:
        """Check if test execution depends on code changes."""
        code_change_tools = ['write_file', 'edit_file', 'create_file']
        test_tools = ['run_tests', 'pytest', 'test']
        
        return first.name in code_change_tools and second.name in test_tools


class ParallelToolExecutor:
    """
    Executes tools in parallel when safe to do so.
    
    Features:
    - Automatic dependency detection
    - Parallel execution within batches
    - Failure handling and retry
    - Progress tracking
    - Cancellation support
    """
    
    def __init__(self, tool_registry: Dict[str, Callable], max_concurrent: int = 10):
        """
        Initialize parallel executor.
        
        Args:
            tool_registry: Dictionary mapping tool names to execution functions
            max_concurrent: Maximum number of concurrent tool executions
        """
        self.tool_registry = tool_registry
        self.max_concurrent = max_concurrent
        self.resolver = DependencyResolver()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, ToolResult] = {}
        self._cancelled = False
    
    async def execute_batch(
        self,
        tool_calls: List[ToolCall],
        auto_detect_deps: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[ToolResult]:
        """
        Execute a batch of tool calls, respecting dependencies.
        
        Args:
            tool_calls: List of tools to execute
            auto_detect_deps: Whether to auto-detect dependencies
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of results in the same order as input
        """
        start_time = time.time()
        
        # Auto-detect dependencies if requested
        if auto_detect_deps:
            self.resolver.auto_detect_dependencies(tool_calls)
        
        # Resolve into execution batches
        batches = self.resolver.analyze_dependencies(tool_calls)
        
        logger.info(f"Executing {len(tool_calls)} tools in {len(batches)} batches")
        
        # Execute batches in order
        for batch_num, batch in enumerate(batches):
            if self._cancelled:
                break
                
            logger.info(f"Executing batch {batch_num + 1}/{len(batches)} with {len(batch)} tools")
            
            # Execute batch in parallel
            await self._execute_parallel_batch(batch, progress_callback)
        
        # Collect results in original order
        results = []
        for call in tool_calls:
            if call.id in self.results:
                results.append(self.results[call.id])
            else:
                # Tool was not executed (cancelled or failed dependency)
                results.append(ToolResult(
                    id=call.id,
                    status=ExecutionStatus.CANCELLED,
                    error="Execution cancelled or dependency failed"
                ))
        
        total_time = time.time() - start_time
        logger.info(f"Batch execution completed in {total_time:.2f}s")
        
        return results
    
    async def _execute_parallel_batch(
        self,
        batch: List[ToolCall],
        progress_callback: Optional[Callable]
    ) -> None:
        """Execute a batch of tools in parallel."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def execute_with_semaphore(call: ToolCall):
            async with semaphore:
                if self._cancelled:
                    return
                return await self._execute_single_tool(call, progress_callback)
        
        tasks = [execute_with_semaphore(call) for call in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_single_tool(
        self,
        call: ToolCall,
        progress_callback: Optional[Callable]
    ) -> ToolResult:
        """Execute a single tool and track result."""
        start_time = time.time()
        
        # Update progress
        if progress_callback:
            await progress_callback({
                'type': 'tool_start',
                'tool': call.name,
                'id': call.id
            })
        
        try:
            # Get tool executor
            if call.name not in self.tool_registry:
                raise ValueError(f"Unknown tool: {call.name}")
            
            tool_func = self.tool_registry[call.name]
            
            # Execute tool
            logger.debug(f"Executing {call.name} with params: {call.params}")
            
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**call.params)
            else:
                # Run sync function in thread pool
                result = await asyncio.to_thread(tool_func, **call.params)
            
            execution_time = time.time() - start_time
            
            tool_result = ToolResult(
                id=call.id,
                status=ExecutionStatus.COMPLETED,
                result=result,
                execution_time=execution_time
            )
            
            self.results[call.id] = tool_result
            
            # Update progress
            if progress_callback:
                await progress_callback({
                    'type': 'tool_complete',
                    'tool': call.name,
                    'id': call.id,
                    'time': execution_time
                })
            
            return tool_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Tool {call.name} failed: {error_msg}")
            
            tool_result = ToolResult(
                id=call.id,
                status=ExecutionStatus.FAILED,
                error=error_msg,
                execution_time=execution_time
            )
            
            self.results[call.id] = tool_result
            
            # Update progress
            if progress_callback:
                await progress_callback({
                    'type': 'tool_failed',
                    'tool': call.name,
                    'id': call.id,
                    'error': error_msg,
                    'time': execution_time
                })
            
            return tool_result
    
    def cancel(self) -> None:
        """Cancel all pending executions."""
        self._cancelled = True
        for task in self.active_tasks.values():
            task.cancel()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        completed = sum(1 for r in self.results.values() if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in self.results.values() if r.status == ExecutionStatus.FAILED)
        total_time = sum(r.execution_time for r in self.results.values())
        
        return {
            'total': len(self.results),
            'completed': completed,
            'failed': failed,
            'cancelled': self._cancelled,
            'total_time': total_time,
            'average_time': total_time / len(self.results) if self.results else 0
        }


class SmartBatcher:
    """
    Intelligently batch operations for optimal execution.
    
    Groups related operations together to minimize overhead and
    maximize cache efficiency.
    """
    
    def batch_file_operations(self, operations: List[Dict]) -> List[List[Dict]]:
        """
        Batch file operations by directory and type.
        
        Strategy:
        - Group reads from same directory
        - Group writes to same directory
        - Separate deletes into final batch
        """
        reads = []
        writes = []
        deletes = []
        others = []
        
        for op in operations:
            if op['type'] == 'read':
                reads.append(op)
            elif op['type'] in ['write', 'edit', 'create']:
                writes.append(op)
            elif op['type'] == 'delete':
                deletes.append(op)
            else:
                others.append(op)
        
        batches = []
        
        # Batch reads by directory
        if reads:
            dir_groups = {}
            for op in reads:
                dir_path = Path(op.get('path', '')).parent
                if dir_path not in dir_groups:
                    dir_groups[dir_path] = []
                dir_groups[dir_path].append(op)
            
            for ops in dir_groups.values():
                batches.append(ops)
        
        # Batch writes by directory
        if writes:
            dir_groups = {}
            for op in writes:
                dir_path = Path(op.get('path', '')).parent
                if dir_path not in dir_groups:
                    dir_groups[dir_path] = []
                dir_groups[dir_path].append(op)
            
            for ops in dir_groups.values():
                batches.append(ops)
        
        # Others can go in parallel
        if others:
            batches.append(others)
        
        # Deletes go last
        if deletes:
            batches.append(deletes)
        
        return batches


# Example usage and testing
async def example_usage():
    """Example of how to use the parallel executor."""
    
    # Define some mock tools
    async def read_file(path: str) -> str:
        await asyncio.sleep(0.1)  # Simulate I/O
        return f"Content of {path}"
    
    async def write_file(path: str, content: str) -> bool:
        await asyncio.sleep(0.2)  # Simulate I/O
        return True
    
    async def run_tests() -> Dict:
        await asyncio.sleep(0.5)  # Simulate test run
        return {"passed": 10, "failed": 0}
    
    # Create tool registry
    tools = {
        'read_file': read_file,
        'write_file': write_file,
        'run_tests': run_tests
    }
    
    # Create executor
    executor = ParallelToolExecutor(tools)
    
    # Define tool calls
    calls = [
        ToolCall(id="1", name="read_file", params={"path": "config.py"}),
        ToolCall(id="2", name="read_file", params={"path": "main.py"}),
        ToolCall(id="3", name="write_file", params={"path": "output.py", "content": "data"}),
        ToolCall(id="4", name="run_tests", params={}),
    ]
    
    # Auto-detect dependencies (tests will wait for writes)
    executor.resolver.auto_detect_dependencies(calls)
    
    # Execute in parallel where possible
    results = await executor.execute_batch(calls)
    
    # Print results
    for result in results:
        print(f"Tool {result.id}: {result.status.value} in {result.execution_time:.2f}s")
    
    print(f"\nStats: {executor.get_stats()}")


if __name__ == "__main__":
    asyncio.run(example_usage())
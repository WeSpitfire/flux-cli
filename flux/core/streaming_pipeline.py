"""Streaming Response Pipeline for Flux-CLI.

This module provides non-blocking, streaming execution for all LLM operations
and tool executions, enabling real-time feedback and cancellable operations.
"""

import asyncio
from typing import AsyncIterator, Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import time
import logging
from queue import Queue
import threading

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of streaming events."""
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_PROGRESS = "tool_progress"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    THINKING = "thinking"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class StreamEvent:
    """Represents a single streaming event."""
    type: StreamEventType
    content: Any
    metadata: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.type.value,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }


class StreamingPipeline:
    """
    Non-blocking streaming pipeline for LLM and tool operations.
    
    Features:
    - Real-time streaming of LLM responses
    - Progressive tool execution feedback
    - Cancellable operations
    - Parallel processing with streaming updates
    """
    
    def __init__(self, llm_provider=None, tool_executor=None):
        """Initialize streaming pipeline.
        
        Args:
            llm_provider: LLM provider for text generation
            tool_executor: Tool executor for running tools
        """
        self.llm = llm_provider
        self.tool_executor = tool_executor
        self._cancelled = False
        self._active_tasks = set()
        self._event_queue = asyncio.Queue()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._cancelled = False
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cancel any active operations
        self._cancelled = True
        # Wait for active tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        return False
    
    async def stream_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream_callback: Optional[Callable] = None
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream LLM completion with real-time updates.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            tools: Available tools for the LLM
            stream_callback: Optional callback for each event
            
        Yields:
            StreamEvent objects as they occur
        """
        self._cancelled = False
        
        try:
            # Start thinking indicator
            yield StreamEvent(
                type=StreamEventType.THINKING,
                content="Processing request...",
                metadata={'stage': 'initialization'}
            )
            
            # Stream LLM response
            async for chunk in self._stream_llm_response(prompt, system_prompt, tools):
                if self._cancelled:
                    yield StreamEvent(
                        type=StreamEventType.CANCELLED,
                        content="Operation cancelled",
                        metadata={}
                    )
                    break
                
                yield chunk
                
                if stream_callback:
                    await stream_callback(chunk)
            
            # Complete event
            if not self._cancelled:
                yield StreamEvent(
                    type=StreamEventType.COMPLETE,
                    content="Response complete",
                    metadata={'success': True}
                )
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=str(e),
                metadata={'error_type': type(e).__name__}
            )
    
    async def _stream_llm_response(
        self,
        prompt: str,
        system_prompt: Optional[str],
        tools: Optional[List[Dict]]
    ) -> AsyncIterator[StreamEvent]:
        """Stream LLM response chunks."""
        if self.llm is None:
            # Mock streaming for demonstration
            response = "This is a simulated streaming response. "
            response += "It demonstrates how text appears progressively. "
            response += "In production, this would come from the actual LLM."
            
            words = response.split()
            for i, word in enumerate(words):
                await asyncio.sleep(0.05)  # Simulate streaming delay
                yield StreamEvent(
                    type=StreamEventType.TEXT,
                    content=word + " ",
                    metadata={'chunk_index': i, 'total_chunks': len(words)}
                )
        else:
            # Real LLM streaming
            async for event in self.llm.send_message(prompt, system_prompt, tools):
                if event['type'] == 'text':
                    yield StreamEvent(
                        type=StreamEventType.TEXT,
                        content=event['content'],
                        metadata={}
                    )
                elif event['type'] == 'tool_use':
                    # Handle tool execution
                    async for tool_event in self._execute_tool_streaming(event):
                        yield tool_event
    
    async def _execute_tool_streaming(self, tool_call: Dict) -> AsyncIterator[StreamEvent]:
        """Execute a tool with streaming updates."""
        tool_id = tool_call.get('id', 'unknown')
        tool_name = tool_call.get('name', 'unknown')
        tool_input = tool_call.get('input', {})
        
        # Start event
        yield StreamEvent(
            type=StreamEventType.TOOL_START,
            content=f"Executing {tool_name}",
            metadata={'tool_id': tool_id, 'tool_name': tool_name}
        )
        
        try:
            # Execute tool (would use actual tool executor)
            start_time = time.time()
            
            # Simulate progressive updates
            for progress in range(0, 101, 20):
                await asyncio.sleep(0.1)
                yield StreamEvent(
                    type=StreamEventType.TOOL_PROGRESS,
                    content=f"Progress: {progress}%",
                    metadata={
                        'tool_id': tool_id,
                        'progress': progress,
                        'elapsed': time.time() - start_time
                    }
                )
            
            # Complete
            result = {"status": "success", "output": "Tool executed successfully"}
            yield StreamEvent(
                type=StreamEventType.TOOL_COMPLETE,
                content=result,
                metadata={
                    'tool_id': tool_id,
                    'duration': time.time() - start_time
                }
            )
        
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.TOOL_ERROR,
                content=str(e),
                metadata={'tool_id': tool_id, 'error': str(e)}
            )
    
    async def stream_parallel_tools(
        self,
        tool_calls: List[Dict],
        max_concurrent: int = 5
    ) -> AsyncIterator[StreamEvent]:
        """
        Execute multiple tools in parallel with streaming updates.
        
        Args:
            tool_calls: List of tool calls to execute
            max_concurrent: Maximum concurrent executions
            
        Yields:
            StreamEvent objects for all tool executions
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_streaming(tool_call: Dict):
            """Execute single tool with semaphore."""
            async with semaphore:
                async for event in self._execute_tool_streaming(tool_call):
                    await self._event_queue.put(event)
        
        # Start all tool executions
        tasks = [
            asyncio.create_task(execute_with_streaming(call))
            for call in tool_calls
        ]
        self._active_tasks.update(tasks)
        
        # Create queue reader task
        async def queue_reader():
            """Read events from queue until all tasks complete."""
            while any(not task.done() for task in tasks):
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=0.1
                    )
                    yield event
                except asyncio.TimeoutError:
                    continue
            
            # Drain remaining events
            while not self._event_queue.empty():
                yield await self._event_queue.get()
        
        # Stream events as they occur
        async for event in queue_reader():
            yield event
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean up
        self._active_tasks.difference_update(tasks)
    
    def cancel(self):
        """Cancel all active streaming operations."""
        self._cancelled = True
        for task in self._active_tasks:
            task.cancel()


class ProgressTracker:
    """Track and report progress for long-running operations."""
    
    def __init__(self):
        self.operations = {}
        self.start_time = None
    
    def start_operation(self, operation_id: str, total_steps: int = 100):
        """Start tracking an operation."""
        self.operations[operation_id] = {
            'total': total_steps,
            'current': 0,
            'start_time': time.time(),
            'status': 'running'
        }
    
    def update_progress(self, operation_id: str, current: int, message: str = ""):
        """Update operation progress."""
        if operation_id in self.operations:
            op = self.operations[operation_id]
            op['current'] = current
            op['message'] = message
            op['elapsed'] = time.time() - op['start_time']
            
            # Calculate ETA
            if current > 0:
                rate = current / op['elapsed']
                remaining = op['total'] - current
                op['eta'] = remaining / rate if rate > 0 else 0
    
    def complete_operation(self, operation_id: str):
        """Mark operation as complete."""
        if operation_id in self.operations:
            op = self.operations[operation_id]
            op['status'] = 'complete'
            op['current'] = op['total']
            op['duration'] = time.time() - op['start_time']
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all operations."""
        return {
            op_id: {
                'progress': f"{op['current']}/{op['total']}",
                'percentage': (op['current'] / op['total'] * 100) if op['total'] > 0 else 0,
                'status': op['status'],
                'elapsed': op.get('elapsed', 0),
                'eta': op.get('eta', 0),
                'message': op.get('message', '')
            }
            for op_id, op in self.operations.items()
        }


class StreamingUI:
    """UI component for displaying streaming responses."""
    
    def __init__(self):
        self.current_line = ""
        self.lines = []
        self.tool_status = {}
    
    async def handle_event(self, event: StreamEvent):
        """Handle a streaming event for display."""
        if event.type == StreamEventType.TEXT:
            # Accumulate text
            self.current_line += event.content
            
            # Check for line breaks
            if '\n' in self.current_line:
                parts = self.current_line.split('\n')
                self.lines.extend(parts[:-1])
                self.current_line = parts[-1]
        
        elif event.type == StreamEventType.TOOL_START:
            self.tool_status[event.metadata['tool_id']] = {
                'name': event.metadata['tool_name'],
                'status': 'running',
                'start_time': event.timestamp
            }
        
        elif event.type == StreamEventType.TOOL_PROGRESS:
            if event.metadata['tool_id'] in self.tool_status:
                self.tool_status[event.metadata['tool_id']]['progress'] = event.metadata['progress']
        
        elif event.type == StreamEventType.TOOL_COMPLETE:
            if event.metadata['tool_id'] in self.tool_status:
                self.tool_status[event.metadata['tool_id']]['status'] = 'complete'
                self.tool_status[event.metadata['tool_id']]['duration'] = event.metadata['duration']
    
    def get_display(self) -> str:
        """Get current display state."""
        display = "\n".join(self.lines)
        if self.current_line:
            display += "\n" + self.current_line
        
        # Add tool status
        if self.tool_status:
            display += "\n\n--- Tools ---\n"
            for tool_id, status in self.tool_status.items():
                display += f"{status['name']}: {status['status']}"
                if 'progress' in status:
                    display += f" ({status['progress']}%)"
                if 'duration' in status:
                    display += f" [{status['duration']:.1f}s]"
                display += "\n"
        
        return display


# Demo function
async def demo_streaming():
    """Demonstrate streaming capabilities."""
    print("🌊 Streaming Pipeline Demo")
    print("=" * 60)
    
    # Create pipeline
    pipeline = StreamingPipeline()
    ui = StreamingUI()
    
    # Demo 1: Stream text completion
    print("\n📝 Streaming Text Completion:")
    async for event in pipeline.stream_completion("Explain parallel processing"):
        await ui.handle_event(event)
        if event.type == StreamEventType.TEXT:
            print(event.content, end="", flush=True)
    print("\n")
    
    # Demo 2: Parallel tool execution with streaming
    print("\n🔧 Parallel Tool Execution with Streaming:")
    tool_calls = [
        {"id": "1", "name": "analyze_file", "input": {"path": "main.py"}},
        {"id": "2", "name": "run_tests", "input": {"suite": "unit"}},
        {"id": "3", "name": "format_code", "input": {"files": ["*.py"]}},
    ]
    
    progress_tracker = ProgressTracker()
    
    async for event in pipeline.stream_parallel_tools(tool_calls):
        await ui.handle_event(event)
        
        if event.type == StreamEventType.TOOL_START:
            progress_tracker.start_operation(event.metadata['tool_id'])
            print(f"▶️  {event.content}")
        
        elif event.type == StreamEventType.TOOL_PROGRESS:
            progress_tracker.update_progress(
                event.metadata['tool_id'],
                event.metadata['progress']
            )
            print(f"  📊 {event.metadata['tool_id']}: {event.content}")
        
        elif event.type == StreamEventType.TOOL_COMPLETE:
            progress_tracker.complete_operation(event.metadata['tool_id'])
            print(f"  ✅ Tool {event.metadata['tool_id']} complete!")
    
    # Show summary
    print("\n📈 Execution Summary:")
    for op_id, summary in progress_tracker.get_summary().items():
        print(f"  Tool {op_id}: {summary['percentage']:.0f}% - {summary['status']}")
    
    print("\n✨ Streaming pipeline ready for real-time operations!")


if __name__ == "__main__":
    asyncio.run(demo_streaming())
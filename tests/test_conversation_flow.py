"""Integration tests for conversation flow with tool execution.

These tests verify that the core conversation flow works correctly:
- Single turn conversations
- Multi-turn conversations
- Tool execution and continuation
- Tool result handling
- Context pruning without breaking tool pairs
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from flux.core.config import Config
from flux.llm.anthropic_provider import AnthropicProvider
from flux.core.context_manager import ContextManager


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=Config)
    config.model = "claude-3-haiku-20240307"
    config.anthropic_api_key = "test-key"
    config.max_tokens = 1024
    config.temperature = 0.7
    config.max_context_tokens = 8000
    config.max_history = 8000
    return config


@pytest.fixture
def anthropic_provider(mock_config):
    """Create an Anthropic provider with mocked client."""
    with patch('flux.llm.anthropic_provider.AsyncAnthropic'):
        provider = AnthropicProvider(mock_config, enable_context_pruning=False)
        return provider


class TestSingleTurnConversation:
    """Test single turn conversations without tools."""
    
    @pytest.mark.asyncio
    async def test_simple_message(self, anthropic_provider):
        """Test a simple message without tools."""
        # Mock the stream response
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()
        
        # Create mock events
        async def mock_events():
            # Simulate text delta events
            yield MagicMock(
                type="content_block_start",
                content_block=MagicMock(spec=['id', 'type'], type='text')
            )
            yield MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text="Hello")
            )
            yield MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text=" world")
            )
        
        mock_stream.__aiter__ = mock_events
        
        # Mock final message
        from anthropic.types import TextBlock
        mock_final_message = MagicMock()
        mock_final_message.content = [TextBlock(type="text", text="Hello world")]
        mock_final_message.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_stream.get_final_message = AsyncMock(return_value=mock_final_message)
        
        # Mock the client
        anthropic_provider.client.messages.stream = MagicMock(return_value=mock_stream)
        
        # Send message
        response_text = ""
        async for event in anthropic_provider.send_message(
            message="Hello",
            system_prompt="You are a helpful assistant."
        ):
            if event["type"] == "text":
                response_text += event["content"]
        
        assert response_text == "Hello world"
        assert len(anthropic_provider.conversation_history) == 2  # User + assistant
        assert anthropic_provider.conversation_history[0]["role"] == "user"
        assert anthropic_provider.conversation_history[1]["role"] == "assistant"


class TestToolExecution:
    """Test conversation flows with tool execution."""
    
    @pytest.mark.asyncio
    async def test_tool_use_and_result(self, anthropic_provider):
        """Test tool use followed by tool result."""
        from anthropic.types import ToolUseBlock, TextBlock
        
        # Mock the stream for initial message with tool use
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()
        
        async def mock_events():
            yield MagicMock(
                type="content_block_start",
                content_block=MagicMock(
                    spec=['id', 'name', 'type'],
                    id="tool_123",
                    name="read_file",
                    type="tool_use"
                )
            )
        
        mock_stream.__aiter__ = mock_events
        
        # Mock final message with tool use
        mock_tool_block = ToolUseBlock(
            id="tool_123",
            name="read_file",
            input={"path": "test.py"},
            type="tool_use"
        )
        mock_final_message = MagicMock()
        mock_final_message.content = [mock_tool_block]
        mock_final_message.usage = MagicMock(input_tokens=20, output_tokens=10)
        mock_stream.get_final_message = AsyncMock(return_value=mock_final_message)
        
        anthropic_provider.client.messages.stream = MagicMock(return_value=mock_stream)
        
        # Send message and collect tool uses
        tool_uses = []
        async for event in anthropic_provider.send_message(
            message="Read test.py",
            system_prompt="You are a helpful assistant.",
            tools=[{
                "name": "read_file",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            }]
        ):
            if event["type"] == "tool_use":
                tool_uses.append(event)
        
        # Verify tool use was captured
        assert len(tool_uses) == 1
        assert tool_uses[0]["name"] == "read_file"
        assert tool_uses[0]["id"] == "tool_123"
        
        # Add tool result
        anthropic_provider.add_tool_result("tool_123", "File content here")
        
        # Verify history structure
        assert len(anthropic_provider.conversation_history) == 3
        assert anthropic_provider.conversation_history[0]["role"] == "user"
        assert anthropic_provider.conversation_history[1]["role"] == "assistant"
        assert anthropic_provider.conversation_history[2]["role"] == "user"
        
        # Verify tool result format
        last_msg = anthropic_provider.conversation_history[2]
        assert isinstance(last_msg["content"], list)
        assert last_msg["content"][0]["type"] == "tool_result"
        assert last_msg["content"][0]["tool_use_id"] == "tool_123"


class TestContinueWithToolResults:
    """Test continuing conversation after tool execution."""
    
    @pytest.mark.asyncio
    async def test_continue_after_tools(self, anthropic_provider):
        """Test continuing conversation with tool results."""
        from anthropic.types import ToolUseBlock, TextBlock
        
        # Set up existing conversation with tool result
        anthropic_provider.conversation_history = [
            {"role": "user", "content": "Read test.py"},
            {
                "role": "assistant",
                "content": [
                    ToolUseBlock(
                        id="tool_123",
                        name="read_file",
                        input={"path": "test.py"},
                        type="tool_use"
                    )
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_123",
                        "content": "def hello(): pass"
                    }
                ]
            }
        ]
        
        # Mock stream for continuation
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock()
        
        async def mock_events():
            yield MagicMock(
                type="content_block_start",
                content_block=MagicMock(spec=['id', 'type'], type='text')
            )
            yield MagicMock(
                type="content_block_delta",
                delta=MagicMock(type="text_delta", text="I see a function")
            )
        
        mock_stream.__aiter__ = mock_events
        
        mock_final_message = MagicMock()
        mock_final_message.content = [TextBlock(type="text", text="I see a function")]
        mock_final_message.usage = MagicMock(input_tokens=30, output_tokens=5)
        mock_stream.get_final_message = AsyncMock(return_value=mock_final_message)
        
        anthropic_provider.client.messages.stream = MagicMock(return_value=mock_stream)
        
        # Continue with tool results
        response_text = ""
        async for event in anthropic_provider.continue_with_tool_results(
            system_prompt="You are a helpful assistant."
        ):
            if event["type"] == "text":
                response_text += event["content"]
        
        assert "function" in response_text.lower()
        assert len(anthropic_provider.conversation_history) == 4


class TestContextPruning:
    """Test context pruning with tool pairs."""
    
    def test_anthropic_tool_pairs_preserved(self):
        """Test that Anthropic tool_use/tool_result pairs are preserved during pruning."""
        context_manager = ContextManager(max_context_tokens=8000)
        
        # Create conversation with tool pairs
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": [{"type": "text", "text": "Response 1"}]},
            {"role": "user", "content": "Read file"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "tool_1", "name": "read_file", "input": {}}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "tool_1", "content": "file content"}
                ]
            },
            {"role": "assistant", "content": [{"type": "text", "text": "I see the file"}]},
        ]
        
        # Force pruning by making some messages low priority
        pruned = context_manager._ensure_tool_pairs(
            pruned=messages[2:],  # Skip first two messages
            original=messages
        )
        
        # Verify tool pair is intact
        tool_use_ids = set()
        tool_result_ids = set()
        
        for msg in pruned:
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_use_ids.add(block.get("id"))
            
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_result_ids.add(block.get("tool_use_id"))
        
        # All tool_use blocks should have corresponding tool_result
        assert tool_use_ids == tool_result_ids
    
    def test_incomplete_tool_pairs_removed(self):
        """Test that incomplete tool pairs are removed during pruning."""
        context_manager = ContextManager(max_context_tokens=8000)
        
        # Create conversation with incomplete tool pair (tool_use without result)
        messages = [
            {"role": "user", "content": "Message 1"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "tool_orphan", "name": "read_file", "input": {}}
                ]
            },
            # Missing tool_result for tool_orphan
            {"role": "user", "content": "Different question"},
            {"role": "assistant", "content": [{"type": "text", "text": "Different answer"}]},
        ]
        
        # Prune and fix tool pairs
        pruned = context_manager._ensure_tool_pairs(
            pruned=messages,
            original=messages
        )
        
        # The orphaned tool_use message should be removed
        has_orphaned_tool = False
        for msg in pruned:
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if block.get("id") == "tool_orphan":
                            has_orphaned_tool = True
        
        assert not has_orphaned_tool, "Orphaned tool_use should have been removed"


class TestMultiTurnConversation:
    """Test multi-turn conversations."""
    
    @pytest.mark.asyncio
    async def test_multi_turn_with_tools(self, anthropic_provider):
        """Test multiple turns with tool execution."""
        # This simulates a real conversation flow:
        # Turn 1: User asks, AI responds with tool use
        # Turn 2: Tool result, AI continues with text
        # Turn 3: User asks follow-up, AI responds
        
        # Manually build up conversation history
        anthropic_provider.conversation_history = [
            {"role": "user", "content": "What's in test.py?"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "tool_1", "name": "read_file", "input": {"path": "test.py"}}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "tool_1", "content": "def hello(): pass"}
                ]
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "It contains a hello function"}]
            },
        ]
        
        # Verify conversation structure
        assert len(anthropic_provider.conversation_history) == 4
        
        # Estimate tokens
        tokens = anthropic_provider.estimate_conversation_tokens()
        assert tokens > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

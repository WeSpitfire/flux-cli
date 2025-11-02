"""Anthropic provider implementation for Claude models."""

import json
from typing import List, Dict, Any, AsyncIterator, Optional
from anthropic import AsyncAnthropic
from anthropic.types import MessageStreamEvent, ContentBlock, ToolUseBlock, TextBlock

from flux.core.config import Config
from flux.core.context_manager import ContextManager
from flux.llm.base_provider import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic's Claude models."""
    
    def __init__(self, config: Config, enable_context_pruning: bool = True):
        """Initialize Anthropic provider.
        
        Args:
            config: Flux configuration
            enable_context_pruning: Enable automatic context pruning for Haiku
        """
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.anthropic_api_key)
        self.enable_context_pruning = enable_context_pruning
        # Use max_history if available, fall back to max_context_tokens for backward compatibility
        max_history = getattr(config, 'max_history', config.max_context_tokens)
        self.context_manager = ContextManager(max_context_tokens=max_history)
        self.current_file_context: Optional[str] = None
        self.pruning_stats: List[Dict[str, Any]] = []
    
    async def send_message(
        self,
        message: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message to Claude and stream the response.
        
        Yields events:
        - {"type": "text", "content": str}
        - {"type": "tool_use", "id": str, "name": str, "input": dict}
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Apply context pruning if enabled
        messages_to_send = self.conversation_history
        if self.enable_context_pruning and len(self.conversation_history) > 4:
            pruned_history = self.context_manager.prune_history(
                self.conversation_history,
                self.current_file_context
            )
            
            # Track pruning stats
            if len(pruned_history) < len(self.conversation_history):
                stats = self.context_manager.get_pruning_stats(
                    self.conversation_history,
                    pruned_history
                )
                self.pruning_stats.append(stats)
                messages_to_send = pruned_history
        
        # Build request
        request_args = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": system_prompt,
            "messages": messages_to_send,
        }
        
        if tools:
            request_args["tools"] = tools
        
        # Stream response
        assistant_message_content = []
        
        async with self.client.messages.stream(**request_args) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if isinstance(block, TextBlock):
                        pass  # Text will come in deltas
                    elif isinstance(block, ToolUseBlock):
                        # Tool use started
                        assistant_message_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": {}
                        })
                
                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        # Text content
                        text = delta.text
                        
                        # Add to assistant message if not already there
                        if not assistant_message_content or assistant_message_content[-1].get("type") != "text":
                            assistant_message_content.append({
                                "type": "text",
                                "text": text
                            })
                        else:
                            assistant_message_content[-1]["text"] += text
                        
                        yield {"type": "text", "content": text}
                    
                    elif delta.type == "input_json_delta":
                        # Tool input being built
                        # We'll emit tool_use once complete
                        pass
                
                elif event.type == "content_block_stop":
                    # Check if this was a tool use block
                    if assistant_message_content and assistant_message_content[-1].get("type") == "tool_use":
                        # Get the complete tool use from the stream
                        block_index = event.index
                        # We need to wait for the message to complete to get full tool input
                        pass
        
        # Get final message
        final_message = await stream.get_final_message()
        
        # Track token usage
        if hasattr(final_message, 'usage'):
            self.total_input_tokens += final_message.usage.input_tokens
            self.total_output_tokens += final_message.usage.output_tokens
        
        # Process final content blocks for tool uses
        for block in final_message.content:
            if isinstance(block, ToolUseBlock):
                yield {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                }
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": final_message.content
        })
    
    def add_tool_result(self, tool_use_id: str, result: Any):
        """Add tool result to conversation history."""
        self.conversation_history.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result) if not isinstance(result, str) else result
                }
            ]
        })
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.pruning_stats = []
    
    def set_current_file_context(self, file_path: Optional[str]):
        """Set the current file being worked on for context pruning.
        
        Args:
            file_path: Path to current file (None to clear)
        """
        self.current_file_context = file_path
    
    def get_token_usage(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        # Rough cost estimates (as of 2024)
        # Claude 3 Haiku: $0.25 / 1M input, $1.25 / 1M output
        # Claude 3.5 Sonnet: $3.00 / 1M input, $15.00 / 1M output
        
        # Determine pricing based on model
        if "haiku" in self.config.model.lower():
            input_price = 0.25
            output_price = 1.25
        elif "sonnet" in self.config.model.lower():
            input_price = 3.00
            output_price = 15.00
        elif "opus" in self.config.model.lower():
            input_price = 15.00
            output_price = 75.00
        else:
            # Default to Sonnet pricing
            input_price = 3.00
            output_price = 15.00
        
        input_cost = (self.total_input_tokens / 1_000_000) * input_price
        output_cost = (self.total_output_tokens / 1_000_000) * output_price
        
        # Calculate tokens saved by pruning
        total_tokens_saved = sum(s.get("tokens_saved", 0) for s in self.pruning_stats)
        total_prunings = len(self.pruning_stats)
        
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost": input_cost + output_cost,
            "context_pruning": {
                "enabled": self.enable_context_pruning,
                "prunings_performed": total_prunings,
                "tokens_saved": total_tokens_saved,
                "avg_tokens_saved_per_pruning": total_tokens_saved / max(total_prunings, 1)
            }
        }

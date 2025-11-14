"""OpenAI provider implementation for GPT models."""

import json
from typing import List, Dict, Any, AsyncIterator, Optional
from openai import AsyncOpenAI

from flux.core.config import Config
from flux.core.context_manager import ContextManager
from flux.llm.base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI's GPT models."""

    def __init__(self, config: Config):
        """Initialize OpenAI provider.

        Args:
            config: Flux configuration
        """
        super().__init__(config)

        # OpenAI expects its own API key
        api_key = getattr(config, 'openai_api_key', None)
        if not api_key:
            raise ValueError(
                "\n❌ OPENAI_API_KEY is required when using OpenAI provider.\n"
                "   Please set it in your .env file or shell environment.\n"
                "   Get your API key from: https://platform.openai.com/api-keys\n"
            )

        self.client = AsyncOpenAI(api_key=api_key)
        # OpenAI uses different conversation format
        self.messages: List[Dict[str, Any]] = []
        # Context manager for pruning history (configurable via --max-history)
        # Default to 2000 for GPT-4o to stay well under 30K token/min limit
        # GPT-4o limit: 30K tokens/min for input
        # Budget: 2K history + 8K system+tools + 4K response = ~14K total (safe margin)
        max_history = getattr(config, 'max_history', 2000)
        self.context_manager = ContextManager(max_context_tokens=max_history)

    async def send_message(
        self,
        message: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message to OpenAI and stream the response.

        Yields events:
        - {"type": "text", "content": str}
        - {"type": "tool_use", "id": str, "name": str, "input": dict}
        """
        # Build messages list with system prompt at the start
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Prune conversation history to stay within token limits
        pruned_messages = self.context_manager.prune_history(self.messages)

        # Log pruning stats for debugging
        if len(self.messages) != len(pruned_messages):
            stats = self.context_manager.get_pruning_stats(self.messages, pruned_messages)
            print(f"   ✂️  Pruned history: {stats['messages_removed']} messages removed, saved ~{stats['tokens_saved']} tokens")

        # IMPORTANT: Update self.messages with pruned version to prevent unbounded growth
        self.messages = pruned_messages.copy()

        # Add pruned conversation history
        messages.extend(pruned_messages)

        # Add current user message
        messages.append({"role": "user", "content": message})

        # Build request
        request_args = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        # Convert Anthropic tool format to OpenAI format if tools provided
        if tools:
            request_args["tools"] = self._convert_tools_to_openai_format(tools)

        # Track response
        full_response = ""
        tool_calls = {}
        current_tool_call_index = None

        # Stream response
        stream = await self.client.chat.completions.create(**request_args)

        async for chunk in stream:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            # Handle text content
            if delta.content:
                full_response += delta.content
                yield {"type": "text", "content": delta.content}

            # Handle tool calls
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index

                    # Initialize tool call if new
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": ""
                        }

                    # Update tool call data
                    if tool_call_delta.id:
                        tool_calls[idx]["id"] = tool_call_delta.id

                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            tool_calls[idx]["arguments"] += tool_call_delta.function.arguments

        # Track token usage from final response
        # Note: For streaming, we get usage in the final chunk
        if hasattr(chunk, 'usage') and chunk.usage:
            self.total_input_tokens += chunk.usage.prompt_tokens
            self.total_output_tokens += chunk.usage.completion_tokens

        # Emit complete tool calls
        for idx in sorted(tool_calls.keys()):
            tool_call = tool_calls[idx]
            try:
                arguments = json.loads(tool_call["arguments"])
            except json.JSONDecodeError:
                arguments = {}

            yield {
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": arguments
            }

        # Update conversation history
        self.messages.append({"role": "user", "content": message})

        # Build assistant message
        assistant_message = {"role": "assistant"}
        if full_response:
            assistant_message["content"] = full_response

        if tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    }
                }
                for tc in tool_calls.values()
            ]

        self.messages.append(assistant_message)

        # Also track in conversation_history for compatibility
        self.conversation_history.append({"role": "user", "content": message})
        self.conversation_history.append({"role": "assistant", "content": full_response or "[tool_calls]"})

    def add_tool_result(self, tool_use_id: str, result: Any):
        """Add tool result to conversation history."""
        # OpenAI format for tool results
        result_str = json.dumps(result) if not isinstance(result, str) else result

        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_use_id,
            "content": result_str
        })

        # Also track in conversation_history for compatibility
        self.conversation_history.append({
            "role": "user",
            "content": f"[tool_result: {tool_use_id}]"
        })
    
    async def continue_with_tool_results(
        self,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Continue conversation after tool results have been added.
        
        For OpenAI, the tool results have already been added to self.messages,
        so we just need to send a continuation request.
        """
        # Build messages list
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add all conversation history (includes tool results)
        messages.extend(self.messages)
        
        # Build request
        request_args = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }
        
        if tools:
            request_args["tools"] = self._convert_tools_to_openai_format(tools)
        
        # Track response
        full_response = ""
        tool_calls = {}
        
        # Stream response
        stream = await self.client.chat.completions.create(**request_args)
        
        async for chunk in stream:
            if not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            delta = choice.delta
            
            # Handle text content
            if delta.content:
                full_response += delta.content
                yield {"type": "text", "content": delta.content}
            
            # Handle tool calls
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index
                    
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": ""
                        }
                    
                    if tool_call_delta.id:
                        tool_calls[idx]["id"] = tool_call_delta.id
                    
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            tool_calls[idx]["arguments"] += tool_call_delta.function.arguments
        
        # Track token usage
        if hasattr(chunk, 'usage') and chunk.usage:
            self.total_input_tokens += chunk.usage.prompt_tokens
            self.total_output_tokens += chunk.usage.completion_tokens
        
        # Emit complete tool calls
        for idx in sorted(tool_calls.keys()):
            tool_call = tool_calls[idx]
            try:
                arguments = json.loads(tool_call["arguments"])
            except json.JSONDecodeError:
                arguments = {}
            
            yield {
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": arguments
            }
        
        # Update conversation history
        assistant_message = {"role": "assistant"}
        if full_response:
            assistant_message["content"] = full_response
        
        if tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    }
                }
                for tc in tool_calls.values()
            ]
        
        self.messages.append(assistant_message)
        self.conversation_history.append({"role": "assistant", "content": full_response or "[tool_calls]"})

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.messages = []

    def get_token_usage(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        # OpenAI pricing (as of 2024)
        # GPT-4o: $2.50 / 1M input, $10.00 / 1M output
        # GPT-4 Turbo: $10.00 / 1M input, $30.00 / 1M output
        # GPT-4: $30.00 / 1M input, $60.00 / 1M output

        model = self.config.model.lower()

        if "gpt-4o" in model:
            input_price = 2.50
            output_price = 10.00
        elif "gpt-4-turbo" in model or "gpt-4-1106" in model or "gpt-4-0125" in model:
            input_price = 10.00
            output_price = 30.00
        elif "gpt-4" in model:
            input_price = 30.00
            output_price = 60.00
        elif "gpt-3.5-turbo" in model:
            input_price = 0.50
            output_price = 1.50
        else:
            # Default to GPT-4o pricing
            input_price = 2.50
            output_price = 10.00

        input_cost = (self.total_input_tokens / 1_000_000) * input_price
        output_cost = (self.total_output_tokens / 1_000_000) * output_price

        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost": input_cost + output_cost,
        }

    def _convert_tools_to_openai_format(self, anthropic_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Anthropic tool format to OpenAI format.

        Anthropic format:
        {
            "name": "tool_name",
            "description": "...",
            "input_schema": {...}
        }

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        openai_tools = []
        for tool in anthropic_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {})
                }
            })
        return openai_tools

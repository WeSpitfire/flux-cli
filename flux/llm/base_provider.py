"""Base abstract class for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional


class BaseLLMProvider(ABC):
    """Abstract base class that all LLM providers must implement."""

    def __init__(self, config):
        """Initialize the provider with configuration."""
        self.config = config
        self.conversation_history: List[Dict[str, Any]] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def estimate_conversation_tokens(self) -> int:
        """Estimate token count of current conversation history.

        Returns approximate token count (chars / 3) for context management.
        This is different from total_input_tokens which tracks API usage.
        """
        total_chars = 0
        for msg in self.conversation_history:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                import json
                for block in content:
                    if isinstance(block, dict):
                        total_chars += len(json.dumps(block))
        return total_chars // 3  # Conservative estimate: 3 chars per token

    @abstractmethod
    async def send_message(
        self,
        message: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message to the LLM and stream the response.

        Args:
            message: User message to send
            system_prompt: System prompt for context
            tools: Optional list of tools available to the LLM

        Yields:
            Events in format:
            - {"type": "text", "content": str}  # Text response chunks
            - {"type": "tool_use", "id": str, "name": str, "input": dict}  # Tool calls
        """
        pass

    @abstractmethod
    def add_tool_result(self, tool_use_id: str, result: Any):
        """
        Add tool execution result to conversation history.

        Args:
            tool_use_id: ID of the tool use being responded to
            result: Result of the tool execution
        """
        pass

    @abstractmethod
    def clear_history(self):
        """Clear conversation history."""
        pass

    @abstractmethod
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Get token usage statistics.

        Returns:
            Dict with keys:
            - input_tokens: int
            - output_tokens: int
            - total_tokens: int
            - estimated_cost: float
            - (optional) provider-specific stats
        """
        pass

    def set_current_file_context(self, file_path: Optional[str]):
        """
        Set the current file being worked on (for context management).

        Optional to implement - providers can use this for context pruning.

        Args:
            file_path: Path to current file (None to clear)
        """
        pass  # Optional method, not abstract

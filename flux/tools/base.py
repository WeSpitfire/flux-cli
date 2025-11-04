"""Base tool class and tool registry."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    items: Optional[Dict[str, Any]] = None  # For array types


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool.

        Returns:
            Tool result (will be serialized to JSON for LLM)
        """
        pass

    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool schema."""
        properties = {}
        required = []

        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }

            if param.enum:
                param_schema["enum"] = param.enum

            # Add items for array types (required by OpenAI)
            if param.type == "array" and param.items:
                param_schema["items"] = param.items

            properties[param.name] = param_schema

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM."""
        return [tool.to_anthropic_tool() for tool in self.tools.values()]

    async def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        return await tool.execute(**kwargs)

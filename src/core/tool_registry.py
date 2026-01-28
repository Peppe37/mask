from typing import Any, Dict, List
from src.core.plugin_manager import plugin_manager
from src.interfaces.types import Tool

class ToolRegistry:
    def __init__(self):
        self.manager = plugin_manager

    def initialize(self):
        self.manager.discover_plugins()

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        tools = self.manager.get_all_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in tools
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        tools = self.manager.get_all_tools()
        for tool in tools:
            if tool.name == name:
                return await tool.handler(arguments)
        raise ValueError(f"Tool {name} not found")

tool_registry = ToolRegistry()

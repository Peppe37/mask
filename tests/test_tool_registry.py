"""Tests for Tool Registry."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.tool_registry import ToolRegistry, tool_registry
from src.interfaces.types import Tool


class TestToolRegistry:
    """Test cases for ToolRegistry."""

    def test_registry_initialization(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        assert hasattr(registry, 'manager')

    def test_initialize_calls_discover(self):
        """Test that initialize calls discover_plugins."""
        registry = ToolRegistry()

        with patch.object(registry.manager, 'discover_plugins') as mock_discover:
            registry.initialize()
            mock_discover.assert_called_once()

    def test_list_tools_empty(self):
        """Test listing tools when none are registered."""
        registry = ToolRegistry()

        with patch.object(registry.manager, 'get_all_tools', return_value=[]):
            tools = registry.list_tools()
            assert tools == []

    def test_list_tools_returns_formatted_tools(self, mock_tool):
        """Test listing tools with proper formatting."""
        registry = ToolRegistry()

        tool_obj = Tool(**mock_tool)

        with patch.object(registry.manager, 'get_all_tools', return_value=[tool_obj]):
            tools = registry.list_tools()

            assert len(tools) == 1
            assert tools[0]["name"] == "test_tool"
            assert tools[0]["description"] == "A test tool"
            assert "inputSchema" in tools[0]
            assert tools[0]["inputSchema"]["type"] == "object"

    def test_list_tools_multiple_tools(self):
        """Test listing multiple tools."""
        registry = ToolRegistry()

        tools_list = [
            Tool(name="tool1", description="Tool 1", input_schema={"type": "object"}, handler=AsyncMock()),
            Tool(name="tool2", description="Tool 2", input_schema={"type": "object"}, handler=AsyncMock()),
        ]

        with patch.object(registry.manager, 'get_all_tools', return_value=tools_list):
            tools = registry.list_tools()

            assert len(tools) == 2
            assert tools[0]["name"] == "tool1"
            assert tools[1]["name"] == "tool2"

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_tool):
        """Test successfully calling a tool."""
        registry = ToolRegistry()

        tool_obj = Tool(**mock_tool)
        tool_obj.handler = AsyncMock(return_value="tool result")

        with patch.object(registry.manager, 'get_all_tools', return_value=[tool_obj]):
            result = await registry.call_tool("test_tool", {"arg1": "value"})

            assert result == "tool result"
            tool_obj.handler.assert_called_once_with({"arg1": "value"})

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        """Test calling a non-existent tool."""
        registry = ToolRegistry()

        with patch.object(registry.manager, 'get_all_tools', return_value=[]):
            with pytest.raises(ValueError) as exc_info:
                await registry.call_tool("nonexistent_tool", {})

            assert "nonexistent_tool not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_searches_all_plugins(self):
        """Test that call_tool searches through all plugin tools."""
        registry = ToolRegistry()

        tool1 = Tool(name="tool1", description="T1", input_schema={}, handler=AsyncMock())
        tool2 = Tool(name="tool2", description="T2", input_schema={}, handler=AsyncMock())

        with patch.object(registry.manager, 'get_all_tools', return_value=[tool1, tool2]):
            await registry.call_tool("tool2", {"key": "value"})

            tool2.handler.assert_called_once_with({"key": "value"})
            tool1.handler.assert_not_called()


class TestToolRegistrySingleton:
    """Test cases for tool_registry singleton."""

    def test_singleton_exists(self):
        """Test that tool_registry singleton exists."""
        assert isinstance(tool_registry, ToolRegistry)

    def test_singleton_has_manager(self):
        """Test that singleton has manager."""
        assert hasattr(tool_registry, 'manager')
        assert tool_registry.manager is not None

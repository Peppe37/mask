import pytest
from src.core.plugin_manager import PluginManager
from pathlib import Path

def test_plugin_loading():
    manager = PluginManager(plugin_dir="src/plugins")
    manager.discover_plugins()

    assert "ExamplePlugin" in manager.plugins
    plugin = manager.plugins["ExamplePlugin"]
    assert plugin.name == "ExamplePlugin"
    assert len(plugin.tools) == 1
    assert plugin.tools[0].name == "hello_world"

@pytest.mark.asyncio
async def test_plugin_tool_execution():
    manager = PluginManager(plugin_dir="src/plugins")
    manager.discover_plugins()
    plugin = manager.plugins["ExamplePlugin"]
    tool = plugin.tools[0]

    result = await tool.handler({"name": "Tester"})
    assert result == "Hello, Tester!"

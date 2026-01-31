"""Tests for Plugin Manager."""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from src.core.plugin_manager import PluginManager, plugin_manager
from src.interfaces.types import Plugin, Tool, Agent


class TestPluginManager:
    """Test cases for PluginManager."""

    def test_initialization_default_path(self):
        """Test PluginManager initialization with default path."""
        manager = PluginManager()
        assert manager.plugin_dir == Path("src/plugins")
        assert isinstance(manager.plugins, dict)

    def test_initialization_custom_path(self):
        """Test PluginManager initialization with custom path."""
        manager = PluginManager(plugin_dir="custom/plugins")
        assert manager.plugin_dir == Path("custom/plugins")

    def test_discover_plugins_no_directory(self, capsys):
        """Test discover_plugins when directory doesn't exist."""
        manager = PluginManager(plugin_dir="nonexistent/path")
        manager.discover_plugins()

        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    def test_discover_plugins_empty_directory(self, tmp_path):
        """Test discover_plugins with empty directory."""
        manager = PluginManager(plugin_dir=str(tmp_path))
        manager.discover_plugins()
        assert len(manager.plugins) == 0

    def test_discover_plugins_valid_plugin(self, tmp_path, capsys):
        """Test discovering a valid plugin."""
        # Create plugin directory structure
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()

        # Create plugin.py file
        plugin_content = '''
from src.interfaces.types import Plugin, Tool, Agent

plugin = Plugin(
    name="test_plugin",
    description="A test plugin",
    version="1.0.0",
    agents=[],
    tools=[]
)
'''
        (plugin_dir / "plugin.py").write_text(plugin_content)

        manager = PluginManager(plugin_dir=str(tmp_path))

        with patch.dict(sys.modules, {}):
            manager.discover_plugins()

        captured = capsys.readouterr()
        assert "test_plugin" in captured.out
        assert "test_plugin" in manager.plugins

    def test_discover_plugins_without_plugin_variable(self, tmp_path, capsys):
        """Test discovering a plugin without plugin variable."""
        plugin_dir = tmp_path / "bad_plugin"
        plugin_dir.mkdir()

        # Create plugin.py without plugin variable
        (plugin_dir / "plugin.py").write_text("# No plugin variable here")

        manager = PluginManager(plugin_dir=str(tmp_path))
        manager.discover_plugins()

        captured = capsys.readouterr()
        assert "No valid 'plugin' instance" in captured.out

    def test_load_plugin_success(self, tmp_path, capsys):
        """Test loading a valid plugin."""
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()

        plugin_content = '''
from src.interfaces.types import Plugin, Tool, Agent

plugin = Plugin(
    name="my_plugin",
    description="My plugin",
    version="2.0.0"
)
'''
        (plugin_dir / "plugin.py").write_text(plugin_content)

        manager = PluginManager()

        with patch.dict(sys.modules, {}):
            manager.load_plugin(plugin_dir)

        captured = capsys.readouterr()
        assert "my_plugin" in captured.out
        assert manager.plugins["my_plugin"].version == "2.0.0"

    def test_load_plugin_with_on_load(self, tmp_path):
        """Test that plugin's on_load is called."""
        plugin_dir = tmp_path / "callback_plugin"
        plugin_dir.mkdir()

        on_load_called = []

        # Create a mock plugin class with on_load
        mock_plugin = MagicMock(spec=Plugin)
        mock_plugin.name = "callback_plugin"
        mock_plugin.on_load = MagicMock(side_effect=lambda: on_load_called.append(True))

        plugin_content = f'''
from unittest.mock import MagicMock
plugin = MagicMock()
plugin.name = "callback_plugin"
plugin.on_load = MagicMock()
'''
        (plugin_dir / "plugin.py").write_text(plugin_content)

        manager = PluginManager()

        # Load and verify on_load was called
        with patch.object(manager, 'plugins', {}):
            with patch('importlib.util.spec_from_file_location') as mock_spec:
                mock_module = MagicMock()
                mock_module.plugin = mock_plugin

                mock_spec_obj = MagicMock()
                mock_spec_obj.loader = MagicMock()
                mock_spec.return_value = mock_spec_obj

                with patch('importlib.util.module_from_spec', return_value=mock_module):
                    with patch.object(mock_spec_obj.loader, 'exec_module'):
                        manager.load_plugin(plugin_dir)

        mock_plugin.on_load.assert_called_once()

    def test_load_plugin_exception(self, tmp_path, capsys):
        """Test handling exceptions during plugin loading."""
        plugin_dir = tmp_path / "error_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.py").write_text("raise Exception('Plugin error')")

        manager = PluginManager()
        manager.load_plugin(plugin_dir)

        captured = capsys.readouterr()
        assert "Failed to load" in captured.out

    def test_get_all_tools_empty(self):
        """Test getting tools when no plugins loaded."""
        manager = PluginManager()
        tools = manager.get_all_tools()
        assert tools == []

    def test_get_all_tools_from_plugins(self):
        """Test getting all tools from plugins."""
        manager = PluginManager()

        tool1 = Tool(name="tool1", description="T1", input_schema={}, handler=Mock())
        tool2 = Tool(name="tool2", description="T2", input_schema={}, handler=Mock())

        plugin1 = Plugin(name="p1", description="P1", tools=[tool1])
        agent1 = Agent(name="a1", description="A1", system_prompt="", tools=[tool2])
        plugin2 = Plugin(name="p2", description="P2", agents=[agent1])

        manager.plugins = {"p1": plugin1, "p2": plugin2}

        tools = manager.get_all_tools()

        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

    def test_get_agent_found(self):
        """Test getting an agent that exists."""
        manager = PluginManager()

        agent = Agent(name="my_agent", description="MA", system_prompt="System")
        plugin = Plugin(name="p1", description="P1", agents=[agent])
        manager.plugins = {"p1": plugin}

        result = manager.get_agent("my_agent")
        assert result == agent

    def test_get_agent_not_found(self):
        """Test getting an agent that doesn't exist."""
        manager = PluginManager()
        manager.plugins = {}

        result = manager.get_agent("nonexistent")
        assert result is None


class TestPluginManagerIntegration:
    """Integration tests with real plugins directory."""

    def test_plugin_loading(self):
        """Test loading real plugins from src/plugins."""
        manager = PluginManager(plugin_dir="src/plugins")
        manager.discover_plugins()

        assert "ExamplePlugin" in manager.plugins
        plugin = manager.plugins["ExamplePlugin"]
        assert plugin.name == "ExamplePlugin"
        assert len(plugin.tools) == 1
        assert plugin.tools[0].name == "hello_world"

    @pytest.mark.asyncio
    async def test_plugin_tool_execution(self):
        """Test executing a plugin tool."""
        manager = PluginManager(plugin_dir="src/plugins")
        manager.discover_plugins()
        plugin = manager.plugins["ExamplePlugin"]
        tool = plugin.tools[0]

        result = await tool.handler({"name": "Tester"})
        assert result == "Hello, Tester!"


class TestPluginManagerSingleton:
    """Test cases for plugin_manager singleton."""

    def test_singleton_exists(self):
        """Test that plugin_manager singleton exists."""
        assert isinstance(plugin_manager, PluginManager)

    def test_singleton_default_path(self):
        """Test that singleton has default plugin path."""
        assert plugin_manager.plugin_dir == Path("src/plugins")

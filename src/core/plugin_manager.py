import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict
from src.interfaces.types import Plugin

class PluginManager:
    def __init__(self, plugin_dir: str = "src/plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, Plugin] = {}

    def discover_plugins(self):
        """Scans the plugin directory for plugins."""
        if not self.plugin_dir.exists():
            print(f"Plugin directory {self.plugin_dir} does not exist.")
            return

        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "plugin.py").exists():
                self.load_plugin(item)

    def load_plugin(self, plugin_path: Path):
        """Loads a plugin from a specific directory."""
        plugin_file = plugin_path / "plugin.py"
        module_name = f"plugins.{plugin_path.name}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Expecting a 'plugin' variable in the module
                if hasattr(module, "plugin") and isinstance(module.plugin, Plugin):
                    self.plugins[module.plugin.name] = module.plugin
                    module.plugin.on_load()
                    print(f"Loaded plugin: {module.plugin.name}")
                else:
                    print(f"No valid 'plugin' instance found in {plugin_path.name}")
        except Exception as e:
            print(f"Failed to load plugin {plugin_path.name}: {e}")

    def get_all_tools(self):
        """Returns a combined list of tools from all plugins."""
        tools = []
        for plugin in self.plugins.values():
            tools.extend(plugin.tools)
            for agent in plugin.agents:
                tools.extend(agent.tools)
        return tools

    def get_agent(self, agent_name: str):
        for plugin in self.plugins.values():
            for agent in plugin.agents:
                if agent.name == agent_name:
                    return agent
        return None

plugin_manager = PluginManager()

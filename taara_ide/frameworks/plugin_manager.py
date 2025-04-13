"""
Plugin Manager - Discovers and manages framework plugins.
"""
import importlib
import pkgutil
from typing import Dict, List, Optional, Type
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.frameworks.base import FrameworkBase, FrameworkInfo
from taara_ide.utils.resource import Result


class PluginManager(QObject):
    """
    Manages framework plugins for the IDE.
    
    Discovers plugins from the frameworks directory and provides
    access to registered framework handlers.
    
    Signals:
        plugin_loaded: Emitted when a plugin is loaded (framework_id)
        plugin_unloaded: Emitted when a plugin is unloaded (framework_id)
    """
    
    plugin_loaded = Signal(str)
    plugin_unloaded = Signal(str)
    
    def __init__(self, settings_manager=None, terminal=None, parent=None):
        super().__init__(parent)
        self._settings = settings_manager
        self._terminal = terminal
        self._plugins: Dict[str, FrameworkBase] = {}
        self._plugin_classes: Dict[str, Type[FrameworkBase]] = {}
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the frameworks directory.
        
        Returns:
            List of discovered plugin IDs
        """
        discovered = []
        frameworks_path = Path(__file__).parent
        
        # Scan subdirectories for plugins
        for item in frameworks_path.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugin_file = item / 'plugin.py'
                if plugin_file.exists():
                    try:
                        module_name = f"taara_ide.frameworks.{item.name}.plugin"
                        module = importlib.import_module(module_name)
                        
                        # Look for Plugin class
                        if hasattr(module, 'Plugin'):
                            plugin_class = module.Plugin
                            if issubclass(plugin_class, FrameworkBase):
                                # Get plugin ID from class
                                temp_instance = plugin_class(self._settings, self._terminal)
                                plugin_id = temp_instance.info.id
                                self._plugin_classes[plugin_id] = plugin_class
                                discovered.append(plugin_id)
                    except Exception as e:
                        print(f"Failed to load plugin from {item.name}: {e}")
        
        return discovered
    
    def load_plugin(self, plugin_id: str) -> Result:
        """
        Load and instantiate a plugin.
        
        Args:
            plugin_id: The plugin identifier
            
        Returns:
            Result indicating success or failure
        """
        if plugin_id in self._plugins:
            return Result(success=True, data=self._plugins[plugin_id])
        
        if plugin_id not in self._plugin_classes:
            return Result(success=False, message=f"Plugin '{plugin_id}' not found")
        
        try:
            plugin_class = self._plugin_classes[plugin_id]
            plugin = plugin_class(self._settings, self._terminal)
            self._plugins[plugin_id] = plugin
            self.plugin_loaded.emit(plugin_id)
            return Result(success=True, data=plugin)
        except Exception as e:
            return Result(success=False, message=f"Failed to load plugin: {e}")
    
    def unload_plugin(self, plugin_id: str) -> Result:
        """Unload a plugin."""
        if plugin_id not in self._plugins:
            return Result(success=False, message=f"Plugin '{plugin_id}' not loaded")
        
        del self._plugins[plugin_id]
        self.plugin_unloaded.emit(plugin_id)
        return Result(success=True)
    
    def get_plugin(self, plugin_id: str) -> Optional[FrameworkBase]:
        """Get a loaded plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def get_all_plugins(self) -> Dict[str, FrameworkBase]:
        """Get all loaded plugins."""
        return self._plugins.copy()
    
    def get_available_plugins(self) -> List[FrameworkInfo]:
        """Get info for all available plugins."""
        infos = []
        for plugin_id, plugin_class in self._plugin_classes.items():
            if plugin_id in self._plugins:
                infos.append(self._plugins[plugin_id].info)
            else:
                # Create temporary instance to get info
                temp = plugin_class(self._settings, self._terminal)
                infos.append(temp.info)
        return infos
    
    def register_plugin(self, plugin_class: Type[FrameworkBase]) -> Result:
        """
        Register a plugin class manually.
        
        Args:
            plugin_class: The framework plugin class
            
        Returns:
            Result indicating success or failure
        """
        if not issubclass(plugin_class, FrameworkBase):
            return Result(success=False, message="Invalid plugin class")
        
        try:
            temp = plugin_class(self._settings, self._terminal)
            plugin_id = temp.info.id
            self._plugin_classes[plugin_id] = plugin_class
            return Result(success=True, data=plugin_id)
        except Exception as e:
            return Result(success=False, message=f"Failed to register plugin: {e}")

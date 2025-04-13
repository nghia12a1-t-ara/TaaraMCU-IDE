"""
Settings management using QSettings
"""
from PyQt6.QtCore import QSettings
from typing import Any, Optional, List
from taara_ide.config.constants import AppConstants


class SettingsManager:
    """
    Centralized settings manager for the application.
    Wraps QSettings with type-safe accessors.
    """
    
    _instance: Optional['SettingsManager'] = None
    
    def __new__(cls) -> 'SettingsManager':
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._settings = QSettings(
            AppConstants.ORGANIZATION, 
            AppConstants.APP_NAME
        )
        self._initialized = True
    
    # ========== STM32 framework path methods ==========
    
    def get_stm32_framework_path(self) -> Optional[str]:
        """Get STM32 framework installation path"""
        return self.get("frameworks/stm32Path")
    
    def set_stm32_framework_path(self, path: str) -> None:
        """Set STM32 framework installation path"""
        self.set("frameworks/stm32Path", path)
    
    # ========== Generic accessors ==========
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self._settings.value(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        self._settings.setValue(key, value)
    
    def remove(self, key: str) -> None:
        """Remove a setting"""
        self._settings.remove(key)
    
    def contains(self, key: str) -> bool:
        """Check if setting exists"""
        return self._settings.contains(key)
    
    def sync(self) -> None:
        """Force sync to storage"""
        self._settings.sync()
    
    # ========== Window settings ==========
    
    def get_window_geometry(self) -> Optional[bytes]:
        """Get main window geometry"""
        return self.get("window/geometry")
    
    def set_window_geometry(self, geometry: bytes) -> None:
        """Save main window geometry"""
        self.set("window/geometry", geometry)
    
    def get_window_state(self) -> Optional[bytes]:
        """Get main window state"""
        return self.get("window/state")
    
    def set_window_state(self, state: bytes) -> None:
        """Save main window state"""
        self.set("window/state", state)
    
    # ========== Editor settings ==========
    
    def get_font_family(self) -> str:
        """Get editor font family"""
        return self.get("editor/fontFamily", "Consolas")
    
    def set_font_family(self, family: str) -> None:
        """Set editor font family"""
        self.set("editor/fontFamily", family)
    
    def get_font_size(self) -> int:
        """Get editor font size"""
        return int(self.get("editor/fontSize", 12))
    
    def set_font_size(self, size: int) -> None:
        """Set editor font size"""
        self.set("editor/fontSize", size)
    
    def get_tab_size(self) -> int:
        """Get tab size in spaces"""
        return int(self.get("editor/tabSize", 4))
    
    def set_tab_size(self, size: int) -> None:
        """Set tab size"""
        self.set("editor/tabSize", size)
    
    def get_theme(self) -> str:
        """Get current theme name"""
        return self.get("editor/theme", "khaki")
    
    def set_theme(self, theme: str) -> None:
        """Set current theme"""
        self.set("editor/theme", theme)
    
    # ========== Project settings ==========
    
    def get_recent_projects(self) -> List[str]:
        """Get list of recent project paths"""
        return self.get("projects/recent", []) or []
    
    def add_recent_project(self, path: str, max_items: int = 10) -> None:
        """Add project to recent list"""
        recent = self.get_recent_projects()
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.set("projects/recent", recent[:max_items])
    
    def get_last_project(self) -> Optional[str]:
        """Get last opened project path"""
        return self.get("projects/last")
    
    def set_last_project(self, path: str) -> None:
        """Set last opened project"""
        self.set("projects/last", path)
    
    # ========== Tool paths ==========
    
    def get_gcc_path(self) -> str:
        """Get GCC compiler path"""
        return self.get("tools/gccPath", "arm-none-eabi-gcc")
    
    def set_gcc_path(self, path: str) -> None:
        """Set GCC compiler path"""
        self.set("tools/gccPath", path)
    
    def get_gdb_path(self) -> str:
        """Get GDB debugger path"""
        return self.get("tools/gdbPath", "arm-none-eabi-gdb")
    
    def set_gdb_path(self, path: str) -> None:
        """Set GDB debugger path"""
        self.set("tools/gdbPath", path)
    
    def get_openocd_path(self) -> str:
        """Get OpenOCD path"""
        return self.get("tools/openocdPath", "openocd")
    
    def set_openocd_path(self, path: str) -> None:
        """Set OpenOCD path"""
        self.set("tools/openocdPath", path)
    
    def get_ctags_path(self) -> str:
        """Get ctags path"""
        return self.get("tools/ctagsPath", "ctags")
    
    def set_ctags_path(self, path: str) -> None:
        """Set ctags path"""
        self.set("tools/ctagsPath", path)
    
    # ========== Build settings ==========
    
    def get_parallel_jobs(self) -> int:
        """Get number of parallel build jobs"""
        import os
        default = os.cpu_count() or 4
        return int(self.get("build/parallelJobs", default))
    
    def set_parallel_jobs(self, jobs: int) -> None:
        """Set number of parallel build jobs"""
        self.set("build/parallelJobs", jobs)
    
    def get_optimization_level(self) -> str:
        """Get default optimization level"""
        return self.get("build/optimization", "Debug")
    
    def set_optimization_level(self, level: str) -> None:
        """Set default optimization level"""
        self.set("build/optimization", level)

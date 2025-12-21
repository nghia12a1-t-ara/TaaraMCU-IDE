"""
Project management service
"""
import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.config.settings_manager import SettingsManager
from taara_ide.config.constants import AppConstants
from taara_ide.utils.file_utils import FileUtils
from taara_ide.utils.resource import Result


@dataclass
class ProjectConfig:
    """Project configuration data"""
    name: str
    path: str = ""
    target_mcu: str = ""
    framework: str = ""
    toolchain: str = "arm-none-eabi"
    project_type: str = "embedded"  # Added project_type: "embedded", "native", "python"
    
    # Build settings
    optimization: str = "Debug"
    debug_info: bool = True
    defines: List[str] = field(default_factory=list)
    include_paths: List[str] = field(default_factory=list)
    source_paths: List[str] = field(default_factory=list)
    compiler_flags: List[str] = field(default_factory=list)
    linker_flags: List[str] = field(default_factory=list)
    linker_script: str = ""
    
    # Framework specific
    framework_version: str = ""
    hal_modules: List[str] = field(default_factory=list)
    
    python_args: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProjectService(QObject):
    """
    Service for project management operations.
    
    Signals:
        project_opened: Emitted when project is opened (project_path)
        project_closed: Emitted when project is closed
        project_saved: Emitted when project is saved
        config_changed: Emitted when project config changes
    """
    
    project_opened = Signal(str)
    project_closed = Signal()
    project_saved = Signal()
    config_changed = Signal(object)  # ProjectConfig
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = SettingsManager()
        self._current_path: Optional[str] = None
        self._config: Optional[ProjectConfig] = None
    
    @property
    def is_open(self) -> bool:
        return self._current_path is not None
    
    @property
    def path(self) -> Optional[str]:
        return self._current_path
    
    @property
    def config(self) -> Optional[ProjectConfig]:
        return self._config
    
    @property
    def name(self) -> str:
        if self._config:
            return self._config.name
        if self._current_path:
            return os.path.basename(self._current_path)
        return ""
    
    def create_project(
        self,
        path: str,
        name: str,
        target_mcu: str = "",
        framework: str = "",
        template: Optional[str] = None,
        project_type: str = "embedded"  # Added project_type parameter
    ) -> Result:
        """
        Create a new project.
        
        Args:
            path: Project directory path
            name: Project name
            target_mcu: Target MCU (e.g., "STM32F407VG")
            framework: Framework name (e.g., "stm32-taara")
            template: Optional template name to use
            project_type: Type of the project ("embedded", "native", "python")
        """
        # Create project directory
        result = FileUtils.ensure_dir(path)
        if not result.success:
            return result
        
        # Create project structure
        for subdir in ['src', 'inc', 'lib', 'build', 'docs']:
            FileUtils.ensure_dir(os.path.join(path, subdir))
        
        # Create project config
        self._config = ProjectConfig(
            name=name,
            path=path,
            target_mcu=target_mcu,
            framework=framework,
            source_paths=['src'],
            include_paths=['inc'],
            project_type=project_type  # Set project_type
        )
        
        # Save config
        config_path = os.path.join(path, AppConstants.CONFIG_FILE)
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
        except Exception as e:
            return Result(success=False, message=f"Failed to save config: {e}")
        
        # Create marker file
        marker_path = os.path.join(path, AppConstants.PROJECT_FILE)
        Path(marker_path).touch()
        
        # Create main.c template
        main_path = os.path.join(path, 'src', 'main.c')
        if not os.path.exists(main_path):
            self._create_main_template(main_path, target_mcu)
        
        self._current_path = path
        self._settings.add_recent_project(path)
        self._settings.set_last_project(path)
        
        self.project_opened.emit(path)
        return Result(success=True, data=path)
    
    def open_project(self, path: str) -> Result:
        """Open an existing project."""
        if not os.path.isdir(path):
            return Result(success=False, message="Project directory not found")
        
        # Look for config file
        config_path = os.path.join(path, AppConstants.CONFIG_FILE)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                self._config = ProjectConfig.from_dict(data)
            except Exception as e:
                return Result(success=False, message=f"Failed to load config: {e}")
        else:
            # Create default config
            self._config = ProjectConfig(name=os.path.basename(path), path=path)
        
        self._current_path = path
        self._settings.add_recent_project(path)
        self._settings.set_last_project(path)
        
        self.project_opened.emit(path)
        return Result(success=True, data=path)
    
    def close_project(self) -> None:
        """Close current project."""
        if self._current_path:
            self.save_config()
        
        self._current_path = None
        self._config = None
        self.project_closed.emit()
    
    def save_config(self) -> Result:
        """Save project configuration."""
        if not self._current_path or not self._config:
            return Result(success=False, message="No project open")
        
        config_path = os.path.join(self._current_path, AppConstants.CONFIG_FILE)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            self.project_saved.emit()
            return Result(success=True)
        except Exception as e:
            return Result(success=False, message=f"Failed to save config: {e}")
    
    def update_config(self, **kwargs) -> None:
        """Update project configuration."""
        if not self._config:
            return
        
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        self.config_changed.emit(self._config)
    
    def get_source_files(self) -> List[str]:
        """Get all source files in project."""
        if not self._current_path or not self._config:
            return []
        
        files = []
        for src_path in self._config.source_paths:
            full_path = os.path.join(self._current_path, src_path)
            if os.path.isdir(full_path):
                files.extend(FileUtils.find_files(full_path))
        
        return files
    
    def get_include_paths(self) -> List[str]:
        """Get all include paths (absolute)."""
        if not self._current_path or not self._config:
            return []
        
        paths = []
        for inc_path in self._config.include_paths:
            full_path = os.path.join(self._current_path, inc_path)
            if os.path.isdir(full_path):
                paths.append(full_path)
        
        return paths
    
    def get_recent_projects(self) -> List[str]:
        """Get list of recent projects."""
        return self._settings.get_recent_projects()
    
    def _create_main_template(self, path: str, mcu: str) -> None:
        """Create a basic main.c template."""
        content = '''/**
 * @file main.c
 * @brief Main application entry point
 */

#include <stdint.h>

int main(void)
{
    /* Initialize system */
    
    /* Main loop */
    while (1)
    {
        /* Application code */
    }
    
    return 0;
}
'''
        FileUtils.write_file(path, content)

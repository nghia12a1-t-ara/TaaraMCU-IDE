"""
Abstract base class for framework handlers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.utils.resource import Result


@dataclass
class FrameworkInfo:
    """Information about a framework"""
    id: str
    name: str
    version: str
    description: str
    supported_mcus: List[str] = field(default_factory=list)
    installed: bool = False
    install_path: str = ""


@dataclass
class ProjectTemplate:
    """Project template information"""
    id: str
    name: str
    description: str
    files: Dict[str, str] = field(default_factory=dict)  # path -> content
    

class FrameworkBase(QObject):
    """
    Abstract base class for framework handlers.
    
    All framework plugins must inherit from this class and implement
    the abstract methods.
    
    Signals:
        install_started: Emitted when installation starts
        install_progress: Emitted with progress (message, percentage)
        install_finished: Emitted when installation finishes (success)
        project_created: Emitted when project is created (path)
    """
    
    install_started = Signal()
    install_progress = Signal(str, int)  # message, percentage
    install_finished = Signal(bool)  # success
    project_created = Signal(str)  # project_path
    
    def __init__(self, settings_manager=None, terminal=None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = settings_manager
        self._terminal = terminal
    
    @property
    @abstractmethod
    def info(self) -> FrameworkInfo:
        """Get framework information"""
        pass
    
    @abstractmethod
    def is_installed(self) -> bool:
        """Check if framework is installed"""
        pass
    
    @abstractmethod
    def get_install_path(self) -> Optional[str]:
        """Get the framework installation path"""
        pass
    
    @abstractmethod
    def set_install_path(self, path: str) -> Result:
        """Set/update the framework installation path"""
        pass
    
    @abstractmethod
    def install(self, target_path: str) -> Result:
        """Install framework to target path"""
        pass
    
    @abstractmethod
    def uninstall(self) -> Result:
        """Uninstall framework"""
        pass
    
    @abstractmethod
    def get_templates(self) -> List[ProjectTemplate]:
        """Get available project templates"""
        pass
    
    @abstractmethod
    def create_project(
        self,
        project_path: str,
        project_name: str,
        template_id: str = "default",
        mcu: str = "",
        options: Optional[Dict[str, Any]] = None
    ) -> Result:
        """Create a new project from template"""
        pass
    
    @abstractmethod
    def load_project(self, project_path: str) -> Result:
        """Load an existing project"""
        pass
    
    @abstractmethod
    def build_project(self) -> Result:
        """Build the current project"""
        pass
    
    @abstractmethod
    def clean_project(self) -> Result:
        """Clean the current project"""
        pass
    
    @abstractmethod
    def flash_project(self) -> Result:
        """Flash the project to target device"""
        pass
    
    def get_include_paths(self, project_path: str) -> List[str]:
        """Get include paths for framework"""
        return []
    
    def get_source_files(self, project_path: str) -> List[str]:
        """Get framework source files"""
        return []
    
    def get_defines(self, mcu: str) -> List[str]:
        """Get preprocessor defines for MCU"""
        return []
    
    def get_linker_script(self, mcu: str) -> Optional[str]:
        """Get linker script path for MCU"""
        return None
    
    def log(self, log_type: str, message: str):
        """Log message to terminal if available"""
        if self._terminal:
            self._terminal.add_log(log_type, message)

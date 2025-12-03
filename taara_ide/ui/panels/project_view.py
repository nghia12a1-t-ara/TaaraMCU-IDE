"""
Project View Panel - Tree view for navigating project files.
"""

from PyQt6.QtWidgets import (
    QTreeView, QDockWidget, QHeaderView
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QDir, Qt, pyqtSignal as Signal
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class ProjectView(QDockWidget):
    """
    Project file browser panel.
    
    Signals:
        file_requested: Emitted when user double-clicks a file
        project_changed: Emitted when project directory changes
        index_requested: Emitted to request project indexing
    """
    
    file_requested = Signal(str)  # file_path
    project_changed = Signal(str)  # directory
    index_requested = Signal(str)  # directory to index

    def __init__(self, parent: Optional['MainWindow'] = None):
        super().__init__("Project View", parent)
        self._parent = parent
        self._current_project_directory: Optional[str] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setObjectName("ProjectDock")
        
        # Create file system model
        self._model = QFileSystemModel()
        self._model.setRootPath(QDir.rootPath())
        self._model.setFilter(
            QDir.Filter.NoDotAndDotDot | 
            QDir.Filter.Files | 
            QDir.Filter.Dirs
        )
        
        # Filter to highlight source files
        self._model.setNameFilters([
            "*.c", "*.cpp", "*.h", "*.hpp", 
            "*.py", "*.s", "*.S", "*.asm"
        ])
        self._model.setNameFilterDisables(True)
        
        # Create tree view
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setRootIndex(self._model.index(""))
        
        # Hide unnecessary columns
        self._tree.hideColumn(1)  # Size
        self._tree.hideColumn(2)  # Type
        self._tree.hideColumn(3)  # Date Modified
        self._tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        
        self.setWidget(self._tree)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._tree.doubleClicked.connect(self._on_file_double_clicked)
        self.visibilityChanged.connect(self._on_visibility_changed)
    
    def _on_file_double_clicked(self, index):
        """Handle double-click on file."""
        file_path = self._model.filePath(index)
        if os.path.isfile(file_path):
            self.file_requested.emit(file_path)
    
    def _on_visibility_changed(self, visible: bool):
        """Handle visibility change for action sync."""
        if self._parent and hasattr(self._parent, '_actions'):
            action = self._parent._actions.get('view.project_panel')
            if action:
                action.setChecked(visible)
    
    # Public API
    
    def set_project_directory(self, directory: str) -> bool:
        """
        Set the project root directory.
        
        Args:
            directory: Path to the project directory
            
        Returns:
            True if successful, False otherwise
        """
        if not directory or not os.path.isdir(directory):
            return False
        
        # Update model and view
        self._model.setRootPath(directory)
        self._tree.setRootIndex(self._model.index(directory))
        
        # Update title and header
        folder_name = os.path.basename(directory)
        self.setWindowTitle(f"Project View - {folder_name}")
        self._model.setHeaderData(0, Qt.Orientation.Horizontal, folder_name)
        
        # Store and emit signal
        self._current_project_directory = directory
        self.project_changed.emit(directory)
        
        self.index_requested.emit(directory)
        
        return True
    
    def get_project_directory(self) -> Optional[str]:
        """Get the current project directory."""
        return self._current_project_directory
    
    def get_project_tags_path(self) -> Optional[str]:
        """Get the path to the project.tags file."""
        if self._current_project_directory:
            return str(Path(self._current_project_directory) / "project.tags")
        return None
    
    def refresh(self):
        """Refresh the project view."""
        if self._current_project_directory:
            self._model.setRootPath(self._current_project_directory)

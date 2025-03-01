# project_view.py
from PyQt6.QtWidgets import QTreeView, QDockWidget, QHeaderView
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QDir, Qt
import os

class ProjectView:
    def __init__(self, parent):
        self.parent = parent  # MainWindow will be the parent

        # Create dock widget for Project View
        self.project_dock = QDockWidget("Project View", parent)
        self.project_tree = QTreeView()
        self.project_model = QFileSystemModel()
        
        # Configure QFileSystemModel
        self.project_model.setRootPath(QDir.rootPath())  # Set default root to system root
        self.project_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.Dirs)  # Filter files and dirs
        
        # Configure QTreeView
        self.project_tree.setModel(self.project_model)
        self.project_tree.setRootIndex(self.project_model.index(""))  # Show entire filesystem
        self.project_tree.doubleClicked.connect(self.open_file_from_project)
        self.project_tree.hideColumn(1)  # Hide Size column
        self.project_tree.hideColumn(2)  # Hide Type column
        self.project_tree.hideColumn(3)  # Hide Date Modified column
        self.project_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Auto-resize first column
        
        # Set widget into dock
        self.project_dock.setWidget(self.project_tree)
        parent.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)

    def set_project_directory(self, directory):
        """Update project directory for Project View."""
        if directory and os.path.isdir(directory):
            self.project_model.setRootPath(directory)
            self.project_tree.setRootIndex(self.project_model.index(directory))
            self.project_dock.setWindowTitle(f"Project View - {directory}")
            print(f"Opened project directory: {directory}")

    def open_file_from_project(self, index):
        """Open file when double-clicked in Project View."""
        file_path = self.project_model.filePath(index)
        if os.path.isfile(file_path):
            self.parent.open_file(file_path)  # Call open_file from MainWindow
            print(f"Opened file from Project View: {file_path}")

    def get_project_directory(self):
        """Get the current project directory."""
        return self.project_model.rootPath()

# project_view.py
from PyQt6.QtWidgets import QTreeView, QDockWidget, QHeaderView
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QDir, Qt
import os
import subprocess

class ProjectView:
    def __init__(self, parent):
        self.parent = parent  # MainWindow will be the parent
        self.current_project_directory = None  # Keep track of the current project directory

        # Create dock widget for Project View
        self.project_dock = QDockWidget("Project View", parent)
        self.project_tree = QTreeView()
        self.project_model = QFileSystemModel()
        
        # Configure QFileSystemModel
        self.project_model.setRootPath(QDir.rootPath())  # Set default root to system root
        self.project_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.Dirs)  # Show files and dirs
        
        # Optional: Filter to highlight source files, but still show directories
        self.project_model.setNameFilters(["*.c", "*.cpp", "*.h", "*.hpp", "*.py"])  # Filter source files
        self.project_model.setNameFilterDisables(True)  # Show non-matching files/folders as disabled
        
        # Configure QTreeView
        self.project_tree.setModel(self.project_model)
        self.project_tree.setRootIndex(self.project_model.index(""))  # Show entire filesystem initially
        self.project_tree.doubleClicked.connect(self.open_file_from_project)
        self.project_tree.hideColumn(1)  # Hide Size column
        self.project_tree.hideColumn(2)  # Hide Type column
        self.project_tree.hideColumn(3)  # Hide Date Modified column
        self.project_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Auto-resize first column
        
        # Set widget into dock
        self.project_dock.setWidget(self.project_tree)
        parent.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)

    def set_project_directory(self, directory):
        """Update project directory for Project View, set column header to folder name, and generate CTags."""
        if directory and os.path.isdir(directory):
            # Remove the project.tags file from the previous project directory
            if self.current_project_directory:
                self.remove_project_ctags(self.current_project_directory)
            
            # Set the root path and update the view
            self.project_model.setRootPath(directory)
            self.project_tree.setRootIndex(self.project_model.index(directory))
            
            # Set the dock title to "Project View - directory"
            self.project_dock.setWindowTitle(f"Project View - {directory}")
            
            # Set the column header to the folder name
            folder_name = os.path.basename(directory)  # Get the folder name from the directory path
            self.project_model.setHeaderData(0, Qt.Orientation.Horizontal, folder_name)  # Update the first column header
            # # print(f"Set column header to folder name: {folder_name}")
            
            # Generate CTags for the project
            self.generate_project_ctags(directory)
            
            # Update the current project directory
            self.current_project_directory = directory

    def open_file_from_project(self, index):
        """Open file when double-clicked in Project View."""
        file_path = self.project_model.filePath(index)
        if os.path.isfile(file_path):
            self.parent.open_file(file_path)  # Call open_file from MainWindow
            # print(f"Opened file from Project View: {file_path}")

    def get_project_directory(self):
        """Get the current project directory."""
        return self.project_model.rootPath()

    def generate_project_ctags(self, directory):
        """Generate a single CTags file for the entire project."""
        tags_file = os.path.join(directory, "project.tags")
        try:
            # Command to generate CTags recursively for the project
            ctags_cmd = [r".\ctags\ctags.exe", "--fields=+n", "-R", "-f", tags_file, directory]
            result = subprocess.run(ctags_cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            return False
        
    def remove_project_ctags(self, directory):
        tags_file = os.path.join(directory, "project.tags")

        if os.path.exists(tags_file):
            os.remove(tags_file)
            return True
        else:
            return False

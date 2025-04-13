# project_view.py
from PyQt6.QtWidgets import QTreeView, QDockWidget, QHeaderView, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import QDir, Qt
import os, sys
import subprocess
from pathlib import Path

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ProjectView:
    def __init__(self, parent):
        self.parent = parent  # MainWindow will be the parent
        self.current_project_directory = None  # Keep track of the current project directory

        # Create dock widget for Project View
        self.project_dock = QDockWidget("Project View", parent)
        self.project_dock.setObjectName("ProjectDock")
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

        self.project_dock.visibilityChanged.connect(self.on_project_view_visibility_changed)

    def on_project_view_visibility_changed(self, visible):
        """Handle when Project View is hidden/shown (including clicking the 'X' button)."""
        if hasattr(self.parent, 'projectviewAction'):
            self.parent.projectviewAction.setChecked(visible)

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
            
            # Generate CTags for the project
            self.generate_project_ctags(directory)
            
            # Update the current project directory
            self.current_project_directory = directory

    def open_file_from_project(self, index):
        """Open file when double-clicked in Project View."""
        file_path = self.project_model.filePath(index)
        if os.path.isfile(file_path):
            self.parent.open_file(file_path)  # Call open_file from MainWindow

    def get_project_directory(self):
        """Get the current project directory."""
        return self.project_model.rootPath()

    def generate_project_ctags(self, directory):
        """Generate a single CTags file for the entire project."""
        tags_file = os.path.join(directory, "project.tags")
        try:
            # Command to generate CTags recursively for the project, including macros
            from ctags_handler import CtagsHandler
            ctags_cmd = [CtagsHandler.ctags_path, "--fields=+n", "--kinds-C=+d", "-R", "-f", tags_file, directory]
            result = subprocess.run(ctags_cmd, capture_output=True, text=True, shell=True)
            return True if result.returncode == 0 else False
        except Exception as e:
            return False
        
    def remove_project_ctags(self, directory):
        tags_file = os.path.join(directory, "project.tags")

        if os.path.exists(tags_file):
            os.remove(tags_file)
            return True
        else:
            return False

class FunctionList(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Function List", parent)
        self.parent = parent
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)

        # Main widget for Function List
        self.main_widget = QWidget()
        self.setObjectName("FunctionDock")
        self.layout = QVBoxLayout(self.main_widget)

        # TreeWidget to display the list of functions/variables
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Symbol", "Type"])
        self.tree.setColumnWidth(0, 200)  # Symbol column wider
        self.tree.setColumnWidth(1, 100)  # Type column narrower
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.layout.addWidget(self.tree)

        self.setWidget(self.main_widget)
        self.visibilityChanged.connect(self.on_function_list_visibility_changed)

    def on_function_list_visibility_changed(self, visible):
        """Handle when Function List is hidden/shown (including clicking the 'X' button)."""
        if hasattr(self.parent, 'functionlistAction'):
            self.parent.functionlistAction.setChecked(visible)

    def update_function_list(self, editor):
        """Update the list of functions and variables based on the self.tags_cache of the current editor."""
        self.tree.clear()  # Clear the old list
        if not editor or not hasattr(editor, 'file_path') or not editor.file_path:
            return

        # Ensure tags_cache has been updated
        if not hasattr(editor, 'tags_cache') or not editor.tags_cache:
            file_tag = f"{editor.file_path}.tags"
            if not os.path.exists(file_tag):
                self.parent.statusBar().showMessage(f"Tags file not found: {file_tag}")
                return
            
            project_dir = self.parent.project_view.get_project_directory() if self.parent.project_view else None
            project_tag = str(Path(project_dir) / "project.tags") if project_dir else None
            tag_files = [file_tag]
            if project_tag and os.path.exists(project_tag):
                tag_files.append(project_tag)
            editor.logic.update_tags_cache(tag_files)

        # Use tags_cache from editor
        try:
            # Only display 2 columns: Symbol and Type
            self.tree.setHeaderLabels(["Symbol", "Type"])
            self.tree.setColumnWidth(0, 200)  # Symbol column wider
            self.tree.setColumnWidth(1, 100)  # Type column narrower

            functions = QTreeWidgetItem(self.tree, ["Functions"])
            self.tree.addTopLevelItem(functions)
            variables = QTreeWidgetItem(self.tree, ["Variables"])
            self.tree.addTopLevelItem(variables)
            
            # Classify functions and variables from tags_cache
            for symbol, (file_path, line_number, column) in editor.logic.tags_cache.items():
                tag_type = None

                # Read the .tags file to get tag_type
                with open(f"{editor.file_path}.tags", 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("!"):
                            continue
                        parts = line.strip().split("\t")
                        if len(parts) < 4 or parts[0] != symbol:
                            continue
                        tag_type = parts[3] if len(parts) > 3 else 'unknown'
                        break

                if tag_type == 'f':  # Function
                    item = QTreeWidgetItem(functions)  # Create a new item for each function
                    item.setText(0, symbol)  # Symbol
                    item.setText(1, "Function")  # Type
                    item.setData(0, Qt.ItemDataRole.UserRole, (file_path, line_number, column))
                    functions.addChild(item)
                elif tag_type == 'v':  # Variable
                    item = QTreeWidgetItem(variables)  # Create a new item for each variable
                    item.setText(0, symbol)  # Symbol
                    item.setText(1, "Variable")  # Type
                    item.setData(0, Qt.ItemDataRole.UserRole, (file_path, line_number, column))
                    variables.addChild(item)

            # Expand the Functions and Variables sections to display child items
            functions.setExpanded(True)
            variables.setExpanded(True)

            # Ensure the QTreeWidget is updated
            self.tree.repaint()
        except Exception as e:
            return

    def on_item_double_clicked(self, item, column):
        """Jump to the definition and set the cursor at the symbol position when double-clicked on an item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            file_path, line_number, column = data  # Directly get line_number and column from cache
            editor = self.parent.get_current_editor()
            if editor:
                if line_number is not None:
                    # Open the file and set the cursor at the symbol position
                    success = editor.open_file_at_line(file_path, line_number, column)
                    if not success:
                        self.parent.statusBar().showMessage(f"Failed to jump to definition in {file_path}")
                else:
                    self.parent.statusBar().showMessage(f"Could not find definition in {file_path}")

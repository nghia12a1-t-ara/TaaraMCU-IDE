"""
Project View Panel - Tree view for navigating project files.
"""

from PyQt6.QtWidgets import (
    QTreeView, QDockWidget, QHeaderView, QWidget, QVBoxLayout,
    QHBoxLayout, QToolButton, QMenu, QInputDialog, QMessageBox,
    QApplication, QLineEdit
)
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction, QKeySequence
from PyQt6.QtCore import QDir, Qt, pyqtSignal as Signal, QModelIndex
import os
import shutil
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from taara_ide.utils import resource_path

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class ProjectView(QDockWidget):
    """
    Project file browser panel.
    
    Signals:
        file_requested: Emitted when user clicks a file
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
        self._clipboard_path: Optional[str] = None
        self._clipboard_is_cut: bool = False
        
        self._context_menu = None   # built lazily on first right-click
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setObjectName("ProjectDock")
        
        # Main container
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = QWidget()
        toolbar.setFixedHeight(28)
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
            }
            QToolButton {
                border: none;
                padding: 4px;
                border-radius: 3px;
            }
            QToolButton:hover {
                background-color: #3c3c3c;
            }
            QToolButton:pressed {
                background-color: #4c4c4c;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.setSpacing(2)
        
        # New File button
        self._btn_new_file = QToolButton()
        self._btn_new_file.setToolTip("New File...")
        self._btn_new_file.setText("📄")
        self._btn_new_file.setIcon(QIcon(resource_path(f"icons/new.svg")))
        self._btn_new_file.setFixedSize(22, 22)
        self._btn_new_file.clicked.connect(self._on_new_file)
        toolbar_layout.addWidget(self._btn_new_file)
        
        # New Folder button
        self._btn_new_folder = QToolButton()
        self._btn_new_folder.setToolTip("New Folder...")
        self._btn_new_folder.setText("📁")
        self._btn_new_file.setIcon(QIcon(resource_path(f"icons/new.svg")))
        self._btn_new_folder.setFixedSize(22, 22)
        self._btn_new_folder.clicked.connect(self._on_new_folder)
        toolbar_layout.addWidget(self._btn_new_folder)
        
        # Refresh button
        self._btn_refresh = QToolButton()
        self._btn_refresh.setToolTip("Refresh")
        self._btn_refresh.setText("🔄")
        self._btn_refresh.setFixedSize(22, 22)
        self._btn_refresh.clicked.connect(self.refresh)
        toolbar_layout.addWidget(self._btn_refresh)
        
        # Collapse All button
        self._btn_collapse = QToolButton()
        self._btn_collapse.setToolTip("Collapse All")
        self._btn_collapse.setText("⊟")
        self._btn_collapse.setFixedSize(22, 22)
        self._btn_collapse.clicked.connect(self._on_collapse_all)
        toolbar_layout.addWidget(self._btn_collapse)
        
        toolbar_layout.addStretch()
        layout.addWidget(toolbar)
        
        # Create file system model — do NOT call setRootPath(QDir.rootPath())
        # at init; that triggers a full filesystem scan and costs ~600ms.
        # The real root is set lazily in set_project_directory().
        self._model = QFileSystemModel()
        self._model.setFilter(
            QDir.Filter.NoDotAndDotDot |
            QDir.Filter.Files |
            QDir.Filter.Dirs
        )
        self._model.setNameFilterDisables(False)
        
        # Setup and configure the tree view
        self._setup_tree_view()
        
        layout.addWidget(self._tree)
        self.setWidget(container)
    
    def _setup_tree_view(self):
        """Setup and configure the tree view."""
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        
        # Hide columns except name
        for i in range(1, self._model.columnCount()):
            self._tree.hideColumn(i)
            
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(20)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        self._tree.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self._tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self._tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self._tree.setStyleSheet("""
            QTreeView {
                background-color: #1e1e1e;
                color: #cccccc;
                border: none;
                outline: none;
            }
            QTreeView::item {
                padding: 2px 0;
                border: none;
            }
            QTreeView::item:hover {
                background-color: #2a2d2e;
            }
            QTreeView::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QTreeView::item:selected:active {
                background-color: #094771;
                color: #ffffff;
            }
            QTreeView::item:selected:!active {
                background-color: #37373d;
                color: #ffffff;
            }
            QTreeView::branch:selected {
                background-color: #094771;
            }
            QTreeView::branch:selected:!active {
                background-color: #37373d;
            }
        """)
        
    def _setup_context_menu(self):
        """Setup the right-click context menu."""
        self._context_menu = QMenu(self)
        self._context_menu.setStyleSheet("""
            QMenu {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 30px 6px 20px;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3c3c3c;
                margin: 4px 10px;
            }
        """)
        
        # New File/Folder actions
        self._action_new_file = self._context_menu.addAction("New File...")
        self._action_new_file.triggered.connect(self._on_new_file)
        
        self._action_new_folder = self._context_menu.addAction("New Folder...")
        self._action_new_folder.triggered.connect(self._on_new_folder)
        
        self._context_menu.addSeparator()
        
        # Open actions
        self._action_open = self._context_menu.addAction("Open")
        self._action_open.triggered.connect(self._on_open_file)
        
        self._action_reveal = self._context_menu.addAction("Reveal in File Explorer")
        self._action_reveal.setShortcut(QKeySequence("Shift+Alt+R"))
        self._action_reveal.triggered.connect(self._on_reveal_in_explorer)
        
        self._action_open_terminal = self._context_menu.addAction("Open in Terminal")
        self._action_open_terminal.triggered.connect(self._on_open_in_terminal)
        
        self._context_menu.addSeparator()
        
        # Cut/Copy/Paste actions
        self._action_cut = self._context_menu.addAction("Cut")
        self._action_cut.setShortcut(QKeySequence("Ctrl+X"))
        self._action_cut.triggered.connect(self._on_cut)
        
        self._action_copy = self._context_menu.addAction("Copy")
        self._action_copy.setShortcut(QKeySequence("Ctrl+C"))
        self._action_copy.triggered.connect(self._on_copy)
        
        self._action_paste = self._context_menu.addAction("Paste")
        self._action_paste.setShortcut(QKeySequence("Ctrl+V"))
        self._action_paste.triggered.connect(self._on_paste)
        
        self._context_menu.addSeparator()
        
        # Copy path actions
        self._action_copy_path = self._context_menu.addAction("Copy Path")
        self._action_copy_path.setShortcut(QKeySequence("Shift+Alt+C"))
        self._action_copy_path.triggered.connect(self._on_copy_path)
        
        self._action_copy_relative_path = self._context_menu.addAction("Copy Relative Path")
        self._action_copy_relative_path.triggered.connect(self._on_copy_relative_path)
        
        self._context_menu.addSeparator()
        
        # Rename/Delete actions
        self._action_rename = self._context_menu.addAction("Rename...")
        self._action_rename.setShortcut(QKeySequence("F2"))
        self._action_rename.triggered.connect(self._on_rename)
        
        self._action_delete = self._context_menu.addAction("Delete")
        self._action_delete.setShortcut(QKeySequence("Delete"))
        self._action_delete.triggered.connect(self._on_delete)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._tree.clicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self.visibilityChanged.connect(self._on_visibility_changed)
    
    def _get_selected_path(self) -> Optional[str]:
        """Get the currently selected file/folder path."""
        indexes = self._tree.selectedIndexes()
        if indexes:
            return self._model.filePath(indexes[0])
        return self._current_project_directory
    
    def _get_target_directory(self) -> Optional[str]:
        """Get the target directory for new file/folder creation."""
        selected = self._get_selected_path()
        if selected:
            if os.path.isfile(selected):
                return os.path.dirname(selected)
            return selected
        return self._current_project_directory
    
    def _on_item_clicked(self, index: QModelIndex):
        """Handle single-click on item - expand/collapse folders, open files."""
        file_path = self._model.filePath(index)
        
        self._tree.setCurrentIndex(index)
        
        if os.path.isdir(file_path):
            if self._tree.isExpanded(index):
                self._tree.collapse(index)
            else:
                self._tree.expand(index)
        elif os.path.isfile(file_path):
            self.file_requested.emit(file_path)
    
    def _on_context_menu(self, position):
        """Show context menu at position."""
        if self._context_menu is None:
            self._setup_context_menu()
        index = self._tree.indexAt(position)
        selected_path = self._model.filePath(index) if index.isValid() else None
        
        # Update action states based on selection
        has_selection = selected_path is not None
        is_file = has_selection and os.path.isfile(selected_path)
        is_dir = has_selection and os.path.isdir(selected_path)
        has_clipboard = self._clipboard_path is not None
        
        self._action_open.setVisible(is_file)
        self._action_open.setText("Open" if is_file else "Open Folder")
        
        self._action_cut.setEnabled(has_selection)
        self._action_copy.setEnabled(has_selection)
        self._action_paste.setEnabled(has_clipboard)
        self._action_copy_path.setEnabled(has_selection)
        self._action_copy_relative_path.setEnabled(has_selection)
        self._action_rename.setEnabled(has_selection)
        self._action_delete.setEnabled(has_selection)
        
        if is_dir:
            self._action_reveal.setText("Reveal Folder in File Explorer")
            self._action_open_terminal.setText("Open Folder in Terminal")
        else:
            self._action_reveal.setText("Reveal in File Explorer")
            self._action_open_terminal.setText("Open in Terminal")
        
        self._context_menu.exec(self._tree.viewport().mapToGlobal(position))
    
    def _on_new_file(self):
        """Create a new file."""
        target_dir = self._get_target_directory()
        if not target_dir:
            return
        
        name, ok = QInputDialog.getText(
            self, "New File", "Enter file name:",
            QLineEdit.EchoMode.Normal, "untitled.py"
        )
        if ok and name:
            file_path = os.path.join(target_dir, name)
            try:
                Path(file_path).touch()
                self.refresh()
                self.file_requested.emit(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create file:\n{e}")
    
    def _on_new_folder(self):
        """Create a new folder."""
        target_dir = self._get_target_directory()
        if not target_dir:
            return
        
        name, ok = QInputDialog.getText(
            self, "New Folder", "Enter folder name:",
            QLineEdit.EchoMode.Normal, "new_folder"
        )
        if ok and name:
            folder_path = os.path.join(target_dir, name)
            try:
                os.makedirs(folder_path, exist_ok=True)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder:\n{e}")
    
    def _on_collapse_all(self):
        """Collapse all tree items."""
        self._tree.collapseAll()
    
    def _on_open_file(self):
        """Open the selected file."""
        selected = self._get_selected_path()
        if selected and os.path.isfile(selected):
            self.file_requested.emit(selected)
    
    def _on_reveal_in_explorer(self):
        """Reveal selected item in system file explorer."""
        selected = self._get_selected_path()
        if not selected:
            return
        
        import subprocess
        import sys
        
        if sys.platform == 'win32':
            if os.path.isfile(selected):
                subprocess.run(['explorer', '/select,', selected])
            else:
                subprocess.run(['explorer', selected])
        elif sys.platform == 'darwin':
            subprocess.run(['open', '-R', selected])
        else:
            subprocess.run(['xdg-open', os.path.dirname(selected)])
    
    def _on_open_in_terminal(self):
        """Open terminal at selected location."""
        selected = self._get_selected_path()
        if not selected:
            return
        
        target_dir = selected if os.path.isdir(selected) else os.path.dirname(selected)
        
        if self._parent and hasattr(self._parent, '_terminal'):
            self._parent._terminal.set_working_directory(target_dir)
            self._parent._terminal.show()
    
    def _on_cut(self):
        """Cut selected item to clipboard."""
        selected = self._get_selected_path()
        if selected:
            self._clipboard_path = selected
            self._clipboard_is_cut = True
    
    def _on_copy(self):
        """Copy selected item to clipboard."""
        selected = self._get_selected_path()
        if selected:
            self._clipboard_path = selected
            self._clipboard_is_cut = False
    
    def _on_paste(self):
        """Paste item from clipboard."""
        if not self._clipboard_path:
            return
        
        target_dir = self._get_target_directory()
        if not target_dir:
            return
        
        src = self._clipboard_path
        name = os.path.basename(src)
        dest = os.path.join(target_dir, name)
        
        # Handle name conflicts
        if os.path.exists(dest):
            base, ext = os.path.splitext(name)
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(target_dir, f"{base}_copy{counter}{ext}")
                counter += 1
        
        try:
            if os.path.isfile(src):
                if self._clipboard_is_cut:
                    shutil.move(src, dest)
                else:
                    shutil.copy2(src, dest)
            else:
                if self._clipboard_is_cut:
                    shutil.move(src, dest)
                else:
                    shutil.copytree(src, dest)
            
            if self._clipboard_is_cut:
                self._clipboard_path = None
                self._clipboard_is_cut = False
            
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not paste:\n{e}")
    
    def _on_copy_path(self):
        """Copy absolute path to clipboard."""
        selected = self._get_selected_path()
        if selected:
            QApplication.clipboard().setText(selected)
    
    def _on_copy_relative_path(self):
        """Copy relative path to clipboard."""
        selected = self._get_selected_path()
        if selected and self._current_project_directory:
            try:
                rel_path = os.path.relpath(selected, self._current_project_directory)
                QApplication.clipboard().setText(rel_path)
            except ValueError:
                # Different drives on Windows
                QApplication.clipboard().setText(selected)
    
    def _on_rename(self):
        """Rename selected item."""
        selected = self._get_selected_path()
        if not selected:
            return
        
        old_name = os.path.basename(selected)
        new_name, ok = QInputDialog.getText(
            self, "Rename", "Enter new name:",
            QLineEdit.EchoMode.Normal, old_name
        )
        
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(selected), new_name)
            try:
                os.rename(selected, new_path)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename:\n{e}")
    
    def _on_delete(self):
        """Delete selected item."""
        selected = self._get_selected_path()
        if not selected:
            return
        
        name = os.path.basename(selected)
        is_dir = os.path.isdir(selected)
        item_type = "folder" if is_dir else "file"
        
        warning_msg = f"Are you sure you want to delete the {item_type} '{name}'?"
        if is_dir:
            warning_msg += "\n\nAll contents will be permanently deleted."
        warning_msg += "\n\nThis action cannot be undone."
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            warning_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if is_dir:
                    shutil.rmtree(selected)
                else:
                    os.remove(selected)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete:\n{e}")
    
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

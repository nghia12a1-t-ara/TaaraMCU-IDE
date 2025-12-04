"""
Activity Bar - Left sidebar toolbar like VS Code
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QButtonGroup,
    QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt, QSize
from PyQt6.QtGui import QIcon

from taara_ide.utils.resource import resource_path


class ActivityBarButton(QPushButton):
    """Button for Activity Bar"""
    
    def __init__(self, icon_name: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setFixedSize(48, 48)
        self.setIconSize(QSize(24, 24))
        
        # Try to load icon
        icon_path = resource_path(f"icons/{icon_name}.svg")
        if icon_path:
            self.setIcon(QIcon(icon_path))
        else:
            # Fallback to text
            self.setText(tooltip[0:2])
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 0.15);
                border-left: 3px solid #007ACC;
            }
        """)


class ActivityBar(QWidget):
    """
    Activity Bar widget - vertical toolbar on the left side
    Similar to VS Code's Activity Bar
    """
    
    # Signals
    panel_changed = Signal(str)  # Emits panel name when changed
    
    # Panel identifiers
    PANEL_PROJECT = "project"
    PANEL_SEARCH = "search"
    PANEL_GIT = "git"
    PANEL_DEBUG = "debug"
    PANEL_EXTENSIONS = "extensions"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_panel = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the Activity Bar UI"""
        self.setFixedWidth(48)
        self.setStyleSheet("""
            ActivityBar {
                background-color: #333333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Button group for exclusive selection
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(False)  # Allow unchecking
        
        # Create buttons
        self._buttons = {}
        
        # Project Explorer
        self._buttons[self.PANEL_PROJECT] = ActivityBarButton("explorer", "Explorer")
        layout.addWidget(self._buttons[self.PANEL_PROJECT])
        
        # Search
        self._buttons[self.PANEL_SEARCH] = ActivityBarButton("search", "Search")
        layout.addWidget(self._buttons[self.PANEL_SEARCH])
        
        # Git / Source Control
        self._buttons[self.PANEL_GIT] = ActivityBarButton("git", "Source Control")
        layout.addWidget(self._buttons[self.PANEL_GIT])
        
        # Run & Debug
        self._buttons[self.PANEL_DEBUG] = ActivityBarButton("debug/debug-alt", "Run and Debug")
        layout.addWidget(self._buttons[self.PANEL_DEBUG])
        
        # Extensions
        self._buttons[self.PANEL_EXTENSIONS] = ActivityBarButton("extensions", "Extensions")
        layout.addWidget(self._buttons[self.PANEL_EXTENSIONS])
        
        # Add spacer to push buttons to top
        layout.addSpacerItem(QSpacerItem(
            20, 40, 
            QSizePolicy.Policy.Minimum, 
            QSizePolicy.Policy.Expanding
        ))
        
        # Add buttons to group and connect signals
        for panel_id, button in self._buttons.items():
            self._button_group.addButton(button)
            button.clicked.connect(lambda checked, p=panel_id: self._on_button_clicked(p, checked))
        
        # Set default selection
        self._buttons[self.PANEL_PROJECT].setChecked(True)
        self._current_panel = self.PANEL_PROJECT
    
    def _on_button_clicked(self, panel_id: str, checked: bool):
        """Handle button click"""
        if checked:
            # Uncheck other buttons
            for pid, button in self._buttons.items():
                if pid != panel_id:
                    button.setChecked(False)
            self._current_panel = panel_id
            self.panel_changed.emit(panel_id)
        else:
            # If unchecking current panel, hide it
            if self._current_panel == panel_id:
                self._current_panel = None
                self.panel_changed.emit("")
    
    def set_panel(self, panel_id: str):
        """Programmatically set the active panel"""
        if panel_id in self._buttons:
            for pid, button in self._buttons.items():
                button.setChecked(pid == panel_id)
            self._current_panel = panel_id
    
    def get_current_panel(self) -> str:
        """Get the currently active panel ID"""
        return self._current_panel or ""
    
    def add_button(self, panel_id: str, icon_name: str, tooltip: str, position: int = -1):
        """Add a new button to the Activity Bar"""
        button = ActivityBarButton(icon_name, tooltip)
        self._buttons[panel_id] = button
        self._button_group.addButton(button)
        button.clicked.connect(lambda checked, p=panel_id: self._on_button_clicked(p, checked))
        
        # Insert at position (before spacer)
        layout = self.layout()
        if position < 0:
            position = layout.count() - 1  # Before spacer
        layout.insertWidget(position, button)

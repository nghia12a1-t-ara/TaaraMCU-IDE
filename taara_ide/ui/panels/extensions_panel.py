"""
Extensions Panel - Extension management (placeholder)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QListWidget
)
from PyQt6.QtCore import Qt


class ExtensionsPanel(QWidget):
    """Panel for Extensions management (placeholder for future implementation)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the Extensions panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Extensions")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Search input
        search = QLineEdit()
        search.setPlaceholderText("Search Extensions...")
        layout.addWidget(search)
        
        # Placeholder message
        placeholder = QLabel(
            "Extension marketplace will be available in a future update.\n\n"
            "Planned features:\n"
            "- Browse extensions\n"
            "- Install/uninstall\n"
            "- Extension settings\n"
            "- Auto-updates"
        )
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color: #888;")
        layout.addWidget(placeholder)
        
        layout.addStretch()

"""
Git Panel - Source control functionality (placeholder)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTreeWidget
)
from PyQt6.QtCore import Qt


class GitPanel(QWidget):
    """Panel for Git/Source Control (placeholder for future implementation)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the Git panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Source Control")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Placeholder message
        placeholder = QLabel(
            "Git integration will be available in a future update.\n\n"
            "Planned features:\n"
            "- View changed files\n"
            "- Stage/unstage changes\n"
            "- Commit changes\n"
            "- Push/Pull\n"
            "- Branch management"
        )
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("color: #888;")
        layout.addWidget(placeholder)
        
        layout.addStretch()

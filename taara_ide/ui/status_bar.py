"""
Status bar management for MainWindow
"""
from typing import Optional
from PyQt6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal as Signal, QObject


class StatusBarManager(QObject):
    """
    Manages the status bar and its widgets.
    
    Signals:
        encoding_clicked: Emitted when encoding label is clicked
        line_ending_clicked: Emitted when line ending label is clicked
    """
    
    encoding_clicked = Signal()
    line_ending_clicked = Signal()
    
    def __init__(self, status_bar: QStatusBar):
        super().__init__()
        self._status_bar = status_bar
        
        # Create status bar widgets
        self._message_label = QLabel()
        self._position_label = QLabel("Ln 1, Col 1")
        self._encoding_label = ClickableLabel("UTF-8")
        self._line_ending_label = ClickableLabel("LF")
        self._language_label = QLabel("Plain Text")
        
        self._setup_widgets()
    
    def _setup_widgets(self) -> None:
        """Setup status bar layout"""
        # Style labels
        for label in [self._position_label, self._encoding_label, 
                      self._line_ending_label, self._language_label]:
            label.setStyleSheet("padding: 0 8px;")
        
        # Add permanent widgets (right side)
        self._status_bar.addPermanentWidget(self._position_label)
        self._status_bar.addPermanentWidget(self._encoding_label)
        self._status_bar.addPermanentWidget(self._line_ending_label)
        self._status_bar.addPermanentWidget(self._language_label)
        
        # Connect clickable labels
        self._encoding_label.clicked.connect(self.encoding_clicked.emit)
        self._line_ending_label.clicked.connect(self.line_ending_clicked.emit)
    
    def set_message(self, message: str, timeout: int = 0) -> None:
        """Show a message in the status bar"""
        self._status_bar.showMessage(message, timeout)
    
    def set_position(self, line: int, column: int) -> None:
        """Update cursor position display"""
        self._position_label.setText(f"Ln {line}, Col {column}")
    
    def set_cursor_position(self, line: int, column: int) -> None:
        """Update cursor position display (alias for set_position)"""
        self.set_position(line, column)
    
    def update_cursor_position(self, line: int, column: int) -> None:
        """Update cursor position display (alias for set_position)"""
        self.set_position(line, column)
    
    def set_encoding(self, encoding: str) -> None:
        """Update encoding display"""
        self._encoding_label.setText(encoding)
    
    def set_line_ending(self, line_ending: str) -> None:
        """Update line ending display"""
        self._line_ending_label.setText(line_ending)
    
    def set_language(self, language: str) -> None:
        """Update language display"""
        self._language_label.setText(language)


class ClickableLabel(QLabel):
    """A QLabel that emits a signal when clicked"""
    
    clicked = Signal()
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

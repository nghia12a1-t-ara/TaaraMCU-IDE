"""
Go To Line dialog
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton
)
from PyQt6.QtCore import pyqtSignal as Signal


class GoToLineDialog(QDialog):
    """
    Dialog for jumping to a specific line number.
    
    Signals:
        line_selected: Emitted when user confirms line selection (line_number)
    """
    
    line_selected = Signal(int)
    
    def __init__(self, parent=None, current_line: int = 1, max_line: int = 1):
        super().__init__(parent)
        self.setWindowTitle("Go To Line")
        self.setMinimumWidth(250)
        self._setup_ui(current_line, max_line)
    
    def _setup_ui(self, current_line: int, max_line: int) -> None:
        layout = QVBoxLayout(self)
        
        # Line input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Line number:"))
        
        self._line_spinbox = QSpinBox()
        self._line_spinbox.setMinimum(1)
        self._line_spinbox.setMaximum(max_line)
        self._line_spinbox.setValue(current_line)
        self._line_spinbox.selectAll()
        input_layout.addWidget(self._line_spinbox)
        
        input_layout.addWidget(QLabel(f"(1 - {max_line})"))
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        go_btn = QPushButton("Go")
        go_btn.clicked.connect(self._on_go)
        go_btn.setDefault(True)
        button_layout.addWidget(go_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Focus the spinbox
        self._line_spinbox.setFocus()
    
    def _on_go(self) -> None:
        self.line_selected.emit(self._line_spinbox.value())
        self.accept()

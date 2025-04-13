"""
Find and Replace dialog
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal as Signal


class FindDialog(QDialog):
    """
    Find and Replace dialog.
    
    Signals:
        find_requested: Emitted when Find is clicked (text, options)
        replace_requested: Emitted when Replace is clicked (find_text, replace_text, options)
        replace_all_requested: Emitted when Replace All is clicked
    """
    
    find_requested = Signal(str, dict)
    replace_requested = Signal(str, str, dict)
    replace_all_requested = Signal(str, str, dict)
    
    def __init__(self, parent=None, show_replace: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Find" if not show_replace else "Find and Replace")
        self.setMinimumWidth(400)
        self._show_replace = show_replace
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Find input
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self._find_input = QLineEdit()
        self._find_input.returnPressed.connect(self._on_find)
        find_layout.addWidget(self._find_input)
        layout.addLayout(find_layout)
        
        # Replace input (optional)
        if self._show_replace:
            replace_layout = QHBoxLayout()
            replace_layout.addWidget(QLabel("Replace:"))
            self._replace_input = QLineEdit()
            replace_layout.addWidget(self._replace_input)
            layout.addLayout(replace_layout)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self._case_sensitive = QCheckBox("Case sensitive")
        self._whole_word = QCheckBox("Whole word")
        self._regex = QCheckBox("Regular expression")
        self._wrap_around = QCheckBox("Wrap around")
        self._wrap_around.setChecked(True)
        
        options_layout.addWidget(self._case_sensitive)
        options_layout.addWidget(self._whole_word)
        options_layout.addWidget(self._regex)
        options_layout.addWidget(self._wrap_around)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._find_btn = QPushButton("Find Next")
        self._find_btn.clicked.connect(self._on_find)
        button_layout.addWidget(self._find_btn)
        
        if self._show_replace:
            self._replace_btn = QPushButton("Replace")
            self._replace_btn.clicked.connect(self._on_replace)
            button_layout.addWidget(self._replace_btn)
            
            self._replace_all_btn = QPushButton("Replace All")
            self._replace_all_btn.clicked.connect(self._on_replace_all)
            button_layout.addWidget(self._replace_all_btn)
        
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.close)
        button_layout.addWidget(self._close_btn)
        
        layout.addLayout(button_layout)
    
    def _get_options(self) -> dict:
        """Get current search options"""
        return {
            "case_sensitive": self._case_sensitive.isChecked(),
            "whole_word": self._whole_word.isChecked(),
            "regex": self._regex.isChecked(),
            "wrap_around": self._wrap_around.isChecked()
        }
    
    def _on_find(self) -> None:
        text = self._find_input.text()
        if text:
            self.find_requested.emit(text, self._get_options())
    
    def _on_replace(self) -> None:
        find_text = self._find_input.text()
        replace_text = self._replace_input.text()
        if find_text:
            self.replace_requested.emit(find_text, replace_text, self._get_options())
    
    def _on_replace_all(self) -> None:
        find_text = self._find_input.text()
        replace_text = self._replace_input.text()
        if find_text:
            self.replace_all_requested.emit(find_text, replace_text, self._get_options())
    
    def set_find_text(self, text: str) -> None:
        """Set the find text field"""
        self._find_input.setText(text)
        self._find_input.selectAll()

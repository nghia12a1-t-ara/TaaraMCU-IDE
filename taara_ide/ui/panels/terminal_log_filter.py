"""
Terminal Log Filter - Search and filter functionality for terminal logs.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton,
    QCheckBox, QLabel, QComboBox
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt
from PyQt6.QtGui import QTextDocument, QTextCursor
import re


class TerminalLogFilter(QWidget):
    """
    Log filtering and search controls for terminal.
    
    Signals:
        filter_changed: Emitted when filter criteria changes
        search_requested: Emitted when user requests search (search_text, case_sensitive, regex)
        search_next: Emitted when user wants next match
        search_previous: Emitted when user wants previous match
    """
    
    filter_changed = Signal(dict)  # {log_types: set, custom_pattern: str}
    search_requested = Signal(str, bool, bool)  # text, case_sensitive, regex
    search_next = Signal()
    search_previous = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # Search input
        self._search_label = QLabel("Search:")
        layout.addWidget(self._search_label)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search in logs...")
        self._search_input.setMinimumWidth(200)
        layout.addWidget(self._search_input)
        
        # Search options
        self._case_sensitive_cb = QCheckBox("Aa")
        self._case_sensitive_cb.setToolTip("Case sensitive")
        layout.addWidget(self._case_sensitive_cb)
        
        self._regex_cb = QCheckBox(".*")
        self._regex_cb.setToolTip("Use regular expression")
        layout.addWidget(self._regex_cb)
        
        # Navigation buttons
        self._prev_btn = QPushButton("↑")
        self._prev_btn.setToolTip("Previous match (Shift+F3)")
        self._prev_btn.setMaximumWidth(30)
        layout.addWidget(self._prev_btn)
        
        self._next_btn = QPushButton("↓")
        self._next_btn.setToolTip("Next match (F3)")
        self._next_btn.setMaximumWidth(30)
        layout.addWidget(self._next_btn)
        
        # Match counter
        self._match_label = QLabel("")
        self._match_label.setMinimumWidth(60)
        layout.addWidget(self._match_label)
        
        # Separator
        layout.addWidget(QLabel("|"))
        
        # Filter by log type
        self._filter_label = QLabel("Filter:")
        layout.addWidget(self._filter_label)
        
        self._filter_combo = QComboBox()
        self._filter_combo.addItems([
            "All",
            "Errors Only",
            "Warnings Only",
            "Info Only",
            "Commands Only",
            "Custom Pattern"
        ])
        self._filter_combo.setMinimumWidth(120)
        layout.addWidget(self._filter_combo)
        
        # Custom filter pattern
        self._custom_filter_input = QLineEdit()
        self._custom_filter_input.setPlaceholderText("Custom filter pattern...")
        self._custom_filter_input.setMinimumWidth(150)
        self._custom_filter_input.setVisible(False)
        layout.addWidget(self._custom_filter_input)
        
        # Clear filter button
        self._clear_filter_btn = QPushButton("Clear")
        self._clear_filter_btn.setMaximumWidth(60)
        layout.addWidget(self._clear_filter_btn)
        
        layout.addStretch()
        
        # Style
        self.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 4px;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
            }
            QLineEdit {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #4C4C4C;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QLineEdit:focus {
                border-color: #007ACC;
            }
            QCheckBox {
                color: #CCCCCC;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #4C4C4C;
                border-radius: 3px;
                background-color: #3C3C3C;
            }
            QCheckBox::indicator:checked {
                background-color: #007ACC;
                border-color: #007ACC;
            }
            QComboBox {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #4C4C4C;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QComboBox:hover {
                border-color: #007ACC;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #CCCCCC;
                margin-right: 5px;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #4C4C4C;
                color: #808080;
            }
        """)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._search_input.returnPressed.connect(self._on_search)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._prev_btn.clicked.connect(self.search_previous.emit)
        self._next_btn.clicked.connect(self.search_next.emit)
        
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._custom_filter_input.textChanged.connect(self._on_custom_filter_changed)
        self._clear_filter_btn.clicked.connect(self._clear_filter)
    
    def _on_search(self):
        """Handle search request."""
        text = self._search_input.text()
        if text:
            case_sensitive = self._case_sensitive_cb.isChecked()
            use_regex = self._regex_cb.isChecked()
            self.search_requested.emit(text, case_sensitive, use_regex)
    
    def _on_search_text_changed(self, text: str):
        """Handle search text change."""
        if text:
            self._on_search()
        else:
            self.update_match_count(0, 0)
    
    def _on_filter_changed(self, index: int):
        """Handle filter type change."""
        # Show/hide custom filter input
        is_custom = (index == 5)  # "Custom Pattern" option
        self._custom_filter_input.setVisible(is_custom)
        
        if not is_custom:
            self._emit_filter()
    
    def _on_custom_filter_changed(self):
        """Handle custom filter pattern change."""
        if self._filter_combo.currentIndex() == 5:
            self._emit_filter()
    
    def _emit_filter(self):
        """Emit current filter settings."""
        index = self._filter_combo.currentIndex()
        
        filter_data = {
            'log_types': set(),
            'custom_pattern': ''
        }
        
        if index == 0:  # All
            filter_data['log_types'] = {'all'}
        elif index == 1:  # Errors Only
            filter_data['log_types'] = {'error', 'stderr'}
        elif index == 2:  # Warnings Only
            filter_data['log_types'] = {'warning'}
        elif index == 3:  # Info Only
            filter_data['log_types'] = {'info', 'stdout', 'success'}
        elif index == 4:  # Commands Only
            filter_data['log_types'] = {'command'}
        elif index == 5:  # Custom Pattern
            filter_data['log_types'] = {'all'}  # Show all types when using custom pattern
            filter_data['custom_pattern'] = self._custom_filter_input.text()
        
        self.filter_changed.emit(filter_data)
    
    def _clear_filter(self):
        """Clear all filters and search."""
        self._filter_combo.setCurrentIndex(0)
        self._custom_filter_input.clear()
        self._search_input.clear()
        self._emit_filter()
    
    def update_match_count(self, current: int, total: int):
        """Update the match counter display."""
        if total == 0:
            self._match_label.setText("")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
        else:
            self._match_label.setText(f"{current}/{total}")
            self._prev_btn.setEnabled(total > 1)
            self._next_btn.setEnabled(total > 1)
    
    def get_search_text(self) -> str:
        """Get current search text."""
        return self._search_input.text()
    
    def is_case_sensitive(self) -> bool:
        """Check if case sensitive search is enabled."""
        return self._case_sensitive_cb.isChecked()
    
    def is_regex(self) -> bool:
        """Check if regex search is enabled."""
        return self._regex_cb.isChecked()


class TerminalSearchHelper:
    """Helper class for searching in terminal text."""
    
    def __init__(self, text_edit):
        self._text_edit = text_edit
        self._matches = []
        self._current_match = -1
    
    def search(self, pattern: str, case_sensitive: bool = False, use_regex: bool = False) -> int:
        """
        Search for pattern in text.
        
        Returns:
            Number of matches found
        """
        self._matches.clear()
        self._current_match = -1
        
        if not pattern:
            return 0
        
        document = self._text_edit.document()
        
        # Build search flags
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        
        # Search through document
        cursor = document.find(pattern, 0, flags)
        
        while not cursor.isNull():
            self._matches.append((cursor.position(), cursor.anchor()))
            cursor = document.find(pattern, cursor, flags)
        
        if self._matches:
            self._current_match = 0
            self._highlight_current()
        
        return len(self._matches)
    
    def next_match(self):
        """Move to next match."""
        if not self._matches:
            return
        
        self._current_match = (self._current_match + 1) % len(self._matches)
        self._highlight_current()
    
    def previous_match(self):
        """Move to previous match."""
        if not self._matches:
            return
        
        self._current_match = (self._current_match - 1) % len(self._matches)
        self._highlight_current()
    
    def _highlight_current(self):
        """Highlight the current match."""
        if not self._matches or self._current_match < 0:
            return
        
        position, anchor = self._matches[self._current_match]
        
        cursor = self._text_edit.textCursor()
        cursor.setPosition(anchor)
        cursor.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()
    
    def get_current_match(self) -> int:
        """Get current match index (1-based)."""
        return self._current_match + 1 if self._current_match >= 0 else 0
    
    def get_total_matches(self) -> int:
        """Get total number of matches."""
        return len(self._matches)
    
    def clear(self):
        """Clear all matches."""
        self._matches.clear()
        self._current_match = -1

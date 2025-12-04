"""
Search Panel - Search in files functionality
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QLabel,
    QCheckBox
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt
from PyQt6.QtGui import QIcon

import os
import re
from pathlib import Path


class SearchPanel(QWidget):
    """Panel for searching in files"""
    
    # Signals
    file_requested = Signal(str, int)  # file_path, line_number
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_path = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the search panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search...")
        self._search_input.returnPressed.connect(self._do_search)
        layout.addWidget(self._search_input)
        
        # Replace input
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace...")
        layout.addWidget(self._replace_input)
        
        # Options
        options_layout = QHBoxLayout()
        
        self._case_sensitive = QCheckBox("Aa")
        self._case_sensitive.setToolTip("Match Case")
        options_layout.addWidget(self._case_sensitive)
        
        self._whole_word = QCheckBox("W")
        self._whole_word.setToolTip("Match Whole Word")
        options_layout.addWidget(self._whole_word)
        
        self._regex = QCheckBox(".*")
        self._regex.setToolTip("Use Regular Expression")
        options_layout.addWidget(self._regex)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Results tree
        self._results_tree = QTreeWidget()
        self._results_tree.setHeaderHidden(True)
        self._results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._results_tree)
        
        # Status label
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)
    
    def set_project_path(self, path: str):
        """Set the project path for searching"""
        self._project_path = path
    
    def _do_search(self):
        """Perform search in files"""
        query = self._search_input.text()
        if not query or not self._project_path:
            return
        
        self._results_tree.clear()
        
        # Search options
        case_sensitive = self._case_sensitive.isChecked()
        whole_word = self._whole_word.isChecked()
        use_regex = self._regex.isChecked()
        
        # Build pattern
        if use_regex:
            try:
                pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
            except re.error:
                self._status_label.setText("Invalid regex pattern")
                return
        else:
            if whole_word:
                query_pattern = r'\b' + re.escape(query) + r'\b'
            else:
                query_pattern = re.escape(query)
            pattern = re.compile(query_pattern, 0 if case_sensitive else re.IGNORECASE)
        
        # Search in files
        results = {}
        extensions = {'.c', '.h', '.cpp', '.hpp', '.py', '.txt', '.md', '.json'}
        
        for root, dirs, files in os.walk(self._project_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                ext = Path(file).suffix.lower()
                if ext not in extensions:
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                if file_path not in results:
                                    results[file_path] = []
                                results[file_path].append((line_num, line.strip()))
                except Exception:
                    continue
        
        # Display results
        total_matches = 0
        for file_path, matches in results.items():
            rel_path = os.path.relpath(file_path, self._project_path)
            file_item = QTreeWidgetItem([f"{rel_path} ({len(matches)} matches)"])
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            for line_num, line_text in matches:
                match_item = QTreeWidgetItem([f"  {line_num}: {line_text[:100]}"])
                match_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                match_item.setData(0, Qt.ItemDataRole.UserRole + 1, line_num)
                file_item.addChild(match_item)
                total_matches += 1
            
            self._results_tree.addTopLevelItem(file_item)
        
        self._status_label.setText(f"{total_matches} results in {len(results)} files")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click on result item"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        line_num = item.data(0, Qt.ItemDataRole.UserRole + 1)
        
        if file_path:
            self.file_requested.emit(file_path, line_num or 1)

"""
Breadcrumb bar component showing file path and current symbol (class/function).
Similar to VS Code's breadcrumb navigation.
"""
from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QMenu, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt
from PyQt6.QtGui import QIcon, QFont


class BreadcrumbItem(QPushButton):
    """A single clickable breadcrumb item"""
    
    clicked_item = Signal(str, str)  # (type, value) - type: 'folder', 'file', 'class', 'function'
    
    def __init__(self, text: str, item_type: str, value: str, parent=None):
        super().__init__(text, parent)
        self._item_type = item_type
        self._value = value
        
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 2px 4px;
                color: #606060;
                background: transparent;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #e0e0e0;
                border-radius: 3px;
            }
        """)
        
        self.clicked.connect(self._on_clicked)
    
    def _on_clicked(self):
        self.clicked_item.emit(self._item_type, self._value)


class BreadcrumbSeparator(QLabel):
    """Separator between breadcrumb items"""
    
    def __init__(self, parent=None):
        super().__init__(">", parent)
        self.setStyleSheet("""
            QLabel {
                color: #909090;
                padding: 0 2px;
                font-size: 11px;
            }
        """)


class BreadcrumbBar(QWidget):
    """
    Breadcrumb navigation bar showing:
    - File path (folder > folder > file.py)
    - Current symbol (Class > function)
    """
    
    # Signals
    folder_clicked = Signal(str)  # folder path
    file_clicked = Signal(str)    # file path
    symbol_clicked = Signal(str, int)  # symbol name, line number
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_file: Optional[str] = None
        self._current_class: Optional[str] = None
        self._current_function: Optional[str] = None
        self._project_root: Optional[str] = None
        self._symbols: List[dict] = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the breadcrumb bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(0)
        
        # Container for breadcrumb items
        self._items_container = QWidget()
        self._items_layout = QHBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(0)
        
        layout.addWidget(self._items_container)
        layout.addStretch()
        
        self.setStyleSheet("""
            BreadcrumbBar {
                background: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        
        self.setFixedHeight(24)
    
    def set_project_root(self, path: str):
        """Set the project root for relative path display"""
        self._project_root = path
        self._update_display()
    
    def set_file(self, file_path: Optional[str]):
        """Set the current file path"""
        self._current_file = file_path
        self._current_class = None
        self._current_function = None
        self._update_display()
    
    def set_symbols(self, symbols: List[dict]):
        """Set available symbols for the current file"""
        self._symbols = symbols
    
    def set_current_symbol(self, class_name: Optional[str], function_name: Optional[str]):
        """Set the current class and function"""
        self._current_class = class_name
        self._current_function = function_name
        self._update_display()
    
    def update_from_cursor(self, line: int, symbols: List = None):
        """Update breadcrumb based on cursor position"""
        if symbols:
            self._symbols = symbols
        
        # Find which class/function the cursor is in
        current_class = None
        current_function = None
        
        for symbol in self._symbols:
            # Handle both dict and Symbol objects
            if hasattr(symbol, '__dict__'):
                sym_line = symbol.line
                sym_kind = symbol.kind
                sym_name = symbol.name
            else:
                sym_line = symbol.get('line', 0)
                sym_kind = symbol.get('kind', '')
                sym_name = symbol.get('name', '')
            
            if sym_line <= line:
                if sym_kind in ('class', 'struct'):
                    current_class = sym_name
                elif sym_kind in ('function', 'method', 'def'):
                    current_function = sym_name
        
        self._current_class = current_class
        self._current_function = current_function
        self._update_display()
    
    def _update_display(self):
        """Update the breadcrumb display"""
        # Clear existing items
        while self._items_layout.count():
            item = self._items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._current_file:
            return
        
        # Build path parts
        file_path = Path(self._current_file)
        
        # Get relative path if project root is set
        if self._project_root:
            try:
                relative_path = file_path.relative_to(self._project_root)
                parts = list(relative_path.parts)
            except ValueError:
                parts = list(file_path.parts)
        else:
            # Show last 3 parts of path
            parts = list(file_path.parts)[-4:] if len(file_path.parts) > 4 else list(file_path.parts)
        
        # Add folder items
        current_path = Path(self._project_root) if self._project_root else Path()
        for i, part in enumerate(parts[:-1]):  # All except filename
            current_path = current_path / part
            
            if i > 0:
                self._items_layout.addWidget(BreadcrumbSeparator())
            
            item = BreadcrumbItem(part, 'folder', str(current_path))
            item.clicked_item.connect(self._on_item_clicked)
            self._items_layout.addWidget(item)
        
        # Add file item
        if parts:
            if len(parts) > 1:
                self._items_layout.addWidget(BreadcrumbSeparator())
            
            file_item = BreadcrumbItem(parts[-1], 'file', str(file_path))
            file_item.clicked_item.connect(self._on_item_clicked)
            # Make file name bold
            font = file_item.font()
            font.setBold(True)
            file_item.setFont(font)
            self._items_layout.addWidget(file_item)
        
        # Add class if present
        if self._current_class:
            self._items_layout.addWidget(BreadcrumbSeparator())
            
            class_item = BreadcrumbItem(f"📦 {self._current_class}", 'class', self._current_class)
            class_item.clicked_item.connect(self._on_item_clicked)
            class_item.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 2px 4px;
                    color: #0066cc;
                    background: transparent;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                    border-radius: 3px;
                }
            """)
            self._items_layout.addWidget(class_item)
        
        # Add function if present
        if self._current_function:
            self._items_layout.addWidget(BreadcrumbSeparator())
            
            func_item = BreadcrumbItem(f"⚡ {self._current_function}", 'function', self._current_function)
            func_item.clicked_item.connect(self._on_item_clicked)
            func_item.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 2px 4px;
                    color: #cc6600;
                    background: transparent;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                    border-radius: 3px;
                }
            """)
            self._items_layout.addWidget(func_item)
    
    def _on_item_clicked(self, item_type: str, value: str):
        """Handle breadcrumb item click"""
        if item_type == 'folder':
            self.folder_clicked.emit(value)
        elif item_type == 'file':
            self.file_clicked.emit(value)
        elif item_type in ('class', 'function'):
            # Find symbol line number
            for symbol in self._symbols:
                if hasattr(symbol, '__dict__'):
                    if symbol.name == value:
                        self.symbol_clicked.emit(value, symbol.line)
                        return
                else:
                    if symbol.get('name') == value:
                        self.symbol_clicked.emit(value, symbol.get('line', 1))
                        return
    
    def clear(self):
        """Clear the breadcrumb bar"""
        self._current_file = None
        self._current_class = None
        self._current_function = None
        self._symbols = []
        self._update_display()

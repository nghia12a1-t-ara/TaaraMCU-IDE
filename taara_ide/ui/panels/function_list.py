"""
Function List Panel - Displays functions and variables in current file.
"""
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, 
    QTreeWidget, QTreeWidgetItem, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from PyQt6.QtGui import QIcon
from typing import Optional, Dict, Tuple, List, Any, TYPE_CHECKING
import os
from pathlib import Path

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow
    from taara_ide.ui.editor.code_editor import CodeEditor


class FunctionList(QDockWidget):
    symbol_selected = Signal(str, int, int)  # file_path, line, column
    
    def __init__(self, parent: Optional['MainWindow'] = None):
        super().__init__("Function List", parent)
        self._parent = parent
        self._current_file: Optional[str] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setObjectName("FunctionDock")
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | 
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        
        # Main widget
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filter symbols...")
        self._filter_input.textChanged.connect(self._filter_symbols)
        layout.addWidget(self._filter_input)
        
        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Symbol", "Type", "Line"])
        self._tree.setColumnWidth(0, 180)
        self._tree.setColumnWidth(1, 80)
        self._tree.setColumnWidth(2, 50)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSortingEnabled(True)
        layout.addWidget(self._tree)
        
        self.setWidget(main_widget)
        
        self._all_items: List[Any] = []
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._tree.itemClicked.connect(self._on_item_clicked)
        self.visibilityChanged.connect(self._on_visibility_changed)
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle single click on item - show in editor."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and self._parent:
            file_path, line_number, col = data
            editor = self._parent.editor_manager.get_current_editor()
            if editor:
                editor.goto_line_and_select(line_number - 1)
    
    def _on_visibility_changed(self, visible: bool):
        """Handle visibility change for action sync."""
        if self._parent and hasattr(self._parent, '_actions'):
            action = self._parent._actions.get('view.function_list')
            if action:
                action.setChecked(visible)
    
    def _filter_symbols(self, text: str):
        """Filter symbols by search text."""
        text = text.lower()
        
        # Iterate through all items
        for i in range(self._tree.topLevelItemCount()):
            category_item = self._tree.topLevelItem(i)
            visible_children = 0
            
            for j in range(category_item.childCount()):
                child = category_item.child(j)
                symbol_name = child.text(0).lower()
                matches = text in symbol_name if text else True
                child.setHidden(not matches)
                if matches:
                    visible_children += 1
            
            # Hide category if no visible children
            category_item.setHidden(visible_children == 0 and bool(text))
    
    # ========== Public API ==========
    
    def update_symbols(self, symbols: List[Any]):
        self._tree.clear()
        self._all_items = symbols
        
        if not symbols:
            return
        
        # Create category items
        categories = {
            'function': QTreeWidgetItem(self._tree, ["Functions", "", ""]),
            'prototype': QTreeWidgetItem(self._tree, ["Prototypes", "", ""]),
            'variable': QTreeWidgetItem(self._tree, ["Variables", "", ""]),
            'macro': QTreeWidgetItem(self._tree, ["Macros", "", ""]),
            'struct': QTreeWidgetItem(self._tree, ["Structures", "", ""]),
            'enum': QTreeWidgetItem(self._tree, ["Enumerations", "", ""]),
            'typedef': QTreeWidgetItem(self._tree, ["Typedefs", "", ""]),
            'member': QTreeWidgetItem(self._tree, ["Members", "", ""]),
            'other': QTreeWidgetItem(self._tree, ["Other", "", ""]),
        }
        
        # Style category headers
        for cat_item in categories.values():
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
        
        # Populate symbols
        for symbol in symbols:
            if hasattr(symbol, '__dict__'):  # Symbol dataclass
                name = symbol.name
                kind = symbol.kind
                line = symbol.line
                signature = getattr(symbol, 'signature', '')
            else:  # dict
                name = symbol.get('name', '')
                kind = symbol.get('kind', 'other')
                line = symbol.get('line', 0)
                signature = symbol.get('signature', '')
            
            # Get category
            category = categories.get(kind, categories['other'])
            
            # Create item
            item = QTreeWidgetItem(category)
            display_name = f"{name}{signature}" if signature else name
            item.setText(0, display_name)
            item.setText(1, kind.capitalize())
            item.setText(2, str(line))
            
            # Store data for navigation
            item.setData(0, Qt.ItemDataRole.UserRole, 
                        (self._current_file, line, 0))
        
        # Remove empty categories and expand non-empty ones
        for kind, cat_item in list(categories.items()):
            if cat_item.childCount() == 0:
                index = self._tree.indexOfTopLevelItem(cat_item)
                self._tree.takeTopLevelItem(index)
            else:
                cat_item.setExpanded(True)
    
    def update_from_editor(self, editor: 'CodeEditor'):
        """
        Update the function list based on the current editor.
        
        Args:
            editor: The CodeEditor instance to parse
        """
        self._tree.clear()
        
        if not editor or not hasattr(editor, 'file_path') or not editor.file_path:
            self._current_file = None
            return
        
        self._current_file = editor.file_path
        
        # Get tags cache from editor
        tags_cache = self._get_tags_cache(editor)
        if not tags_cache:
            return
        
        # Get tag types from file
        tag_types = self._get_tag_types(editor.file_path)
        
        # Convert to symbol format
        symbols = []
        for symbol, (file_path, line_number, column) in tags_cache.items():
            tag_type = tag_types.get(symbol, 'other')
            kind_map = {
                'f': 'function',
                'p': 'prototype', 
                'v': 'variable',
                'd': 'macro',
                's': 'struct',
                'g': 'enum',
                't': 'typedef',
                'm': 'member',
            }
            symbols.append({
                'name': symbol,
                'kind': kind_map.get(tag_type, 'other'),
                'line': line_number,
            })
        
        self.update_symbols(symbols)
    
    def set_current_file(self, file_path: str):
        """Set the current file being displayed."""
        self._current_file = file_path
    
    def _get_tags_cache(self, editor: 'CodeEditor') -> Dict[str, Tuple[str, int, int]]:
        """Get or update tags cache from editor."""
        if hasattr(editor, 'logic') and hasattr(editor.logic, 'tags_cache'):
            return editor.logic.tags_cache
        return {}
    
    def _get_tag_types(self, file_path: str) -> Dict[str, str]:
        """Parse tag types from the .tags file."""
        tag_types = {}
        tags_file = f"{file_path}.tags"
        
        if not os.path.exists(tags_file):
            return tag_types
        
        try:
            with open(tags_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith("!"):
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 4:
                        symbol = parts[0]
                        tag_type = parts[3]
                        tag_types[symbol] = tag_type
        except Exception:
            pass
        
        return tag_types
    
    def clear(self):
        """Clear the function list."""
        self._tree.clear()
        self._current_file = None
        self._all_items = []
        self._filter_input.clear()

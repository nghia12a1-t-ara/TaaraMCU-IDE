"""
Code Logic - Business logic for code editor operations.
"""

from PyQt6.QtWidgets import QMessageBox
from pathlib import Path
import os
from typing import Dict, Tuple, Optional, List, TYPE_CHECKING

from taara_ide.utils.resource import Result

if TYPE_CHECKING:
    from taara_ide.ui.editor.code_editor import CodeEditor
    from taara_ide.ui.panels.project_view import ProjectView
    from taara_ide.ui.editor.editor_manager import EditorManager


class CodeLogic:
    """
    Handles code analysis operations like goto definition, tags parsing.
    Separated from CodeEditor for better testability.
    """
    def __init__(self, editor: 'CodeEditor'):
        self._editor = editor
        self.tags_cache: Dict[str, Tuple[str, int, int]] = {}  # symbol -> (file, line, col)
    
    @property
    def _editor_manager(self) -> Optional['EditorManager']:
        """Get editor manager from parent."""
        if self._editor.GUI and hasattr(self._editor.GUI, 'editor_manager'):
            return self._editor.GUI.editor_manager
        return None
    
    @property
    def _project_view(self) -> Optional['ProjectView']:
        """Get project view from parent."""
        if self._editor.GUI and hasattr(self._editor.GUI, 'project_view'):
            return self._editor.GUI.project_view
        return None
    
    def _open_file_at_line(self, file_path: str, line_number: int, column: int = 0):
        """Open a file and navigate to specific line and column."""
        editor_man = self._editor_manager
        if not editor_man:
            return
        
        # Check if file exists
        if not os.path.exists(file_path):
            QMessageBox.warning(None, "Error", f"File '{file_path}' does not exist.")
            return
        
        # Check if already open
        editor = editor_man.get_editor_by_path(file_path)
        if editor:
            # Switch to that tab
            info = editor_man.editors.get(editor)
            if info:
                editor_man._tab_widget.setCurrentIndex(info["index"])
        else:
            # Open new editor
            editor = editor_man.open_editor(file_path)
        
        # Navigate to line
        if editor:
            editor.goto_line(line_number, column)
    
    def update_tags_cache(self, tag_files: List[str]):
        self.tags_cache.clear()
        
        for tag_file in tag_files:
            if not os.path.exists(tag_file):
                continue
            
            try:
                self._parse_tags_file(tag_file)
            except Exception:
                continue
    
    def _parse_tags_file(self, tag_file: str):
        """Parse a single tags file and update cache."""
        with open(tag_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("!"):
                    continue
                
                parts = line.strip().split("\t")
                if len(parts) < 3:
                    continue
                
                symbol = parts[0]
                file_path = parts[1]
                line_info = parts[2]
                tag_type = parts[3] if len(parts) > 3 else 'unknown'
                
                line_number, column = self._parse_line_info(
                    line_info, parts, file_path, symbol, tag_type
                )
                
                if line_number is not None:
                    self.tags_cache[symbol] = (file_path, line_number, column)
    
    def _parse_line_info(self, line_info: str, parts: List[str], 
                         file_path: str, symbol: str, tag_type: str) -> Tuple[Optional[int], int]:
        """Parse line number and column from tag info."""
        line_number = None
        column = 0
        
        # Handle macro definitions
        if tag_type == 'd':
            for field in parts:
                if field.startswith("line:"):
                    line_number = int(field.split(":")[1])
                    break
            
            if line_number:
                column = self._find_column_in_file(file_path, line_number, symbol)
            elif line_info.startswith("/^") and line_info.endswith("$/;\""):
                line_number, column = self._search_pattern(
                    file_path, line_info[2:-4].strip(), symbol
                )
        
        # Handle pattern-based definitions
        elif line_info.startswith("/^") and line_info.endswith("$/;\""):
            pattern = line_info[2:-4].strip()
            line_number, column = self._search_pattern(file_path, pattern, symbol)
        
        # Handle direct line number
        elif line_info.isdigit():
            line_number = int(line_info)
            column = self._find_column_in_file(file_path, line_number, symbol)
        
        return line_number, column
    
    def _find_column_in_file(self, file_path: str, line_number: int, symbol: str) -> int:
        """Find the column position of a symbol in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if i == line_number:
                        col = line.find(symbol)
                        return col if col != -1 else 0
        except Exception:
            pass
        return 0
    
    def _search_pattern(self, file_path: str, pattern: str, symbol: str) -> Tuple[Optional[int], int]:
        """Search for a pattern in file and return line number and column."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if pattern in line.strip():
                        col = line.find(symbol)
                        return i, col if col != -1 else 0
        except Exception:
            pass
        return None, 0

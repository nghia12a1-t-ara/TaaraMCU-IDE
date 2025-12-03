"""
Editor Manager - Manages multiple QScintilla editor tabs.
"""

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QTabWidget
from PyQt6.QtCore import QObject, pyqtSignal as Signal, Qt, QEvent
from PyQt6.QtGui import QTextCursor, QColor
from PyQt6.Qsci import QsciAPIs, QsciScintilla
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, TYPE_CHECKING

from taara_ide.ui.editor.code_editor import CodeEditor
from taara_ide.core.indexer.ctags_handler import CtagsHandler

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class EditorManager(QObject):
    editor_created = Signal(object)  # CodeEditor - Emitted when a new editor is created
    editor_closed = Signal(str)      # file_path - Emitted when an editor is closed
    current_editor_changed = Signal(object)  # CodeEditor - Emitted when the active editor changes
    file_saved = Signal(str)         # file_path - Emitted when a file is saved (file_path)
    file_opened = Signal(str)        # file_path - Emitted when a file is opened (file_path)
    content_modified = Signal()      # any editor modified - Emitted when any editor content is modified
    
    TAB_COLOR_SAVED = QColor("#00AC06")    # Light green
    TAB_COLOR_MODIFIED = QColor("#D6413A") # Light red
    TAB_COLOR_DEFAULT = QColor("#0700D2")  # Blue
    
    def __init__(self, parent: 'MainWindow', tab_widget: QTabWidget):
        super().__init__(parent)
        self._parent = parent
        self._tab_widget = tab_widget
        
        # Editor tracking: editor -> {file_path, index, untitled_number}
        self.editors: dict = {}
        
        # Untitled file numbering (like Notepad++)
        self._untitled_counter = 0
        self._untitled_numbers: set = set()  # Track used numbers
        
        # Closed files history for reopen
        self._closed_files: list = []
        self._max_closed_files = 20
        
        # Find state
        self._find_state = {
            "text": "",
            "case_sensitive": False,
            "whole_word": False,
            "forward": True
        }
        
        # CTags handler
        self._ctags_handler = CtagsHandler()
        
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._tab_widget.tabCloseRequested.connect(self._on_close_tab_requested)
        
        self._tab_widget.tabBar().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle middle mouse button click to close tabs"""
        try:
            if obj == self._tab_widget.tabBar() and self._tab_widget.tabBar():
                if event.type() == event.Type.MouseButtonPress:
                    if event.button() == Qt.MouseButton.MiddleButton:
                        # Get tab index at click position
                        index = self._tab_widget.tabBar().tabAt(event.pos())
                        if index >= 0:
                            self.close_editor(index)
                            return True
        except RuntimeError:
            # Widget has been deleted, ignore
            pass
        return super().eventFilter(obj, event)
    
    # ========== Untitled Management (Notepad++ style) ==========
    
    def _get_next_untitled_number(self) -> int:
        """Get the next available Untitled number."""
        number = 1
        while number in self._untitled_numbers:
            number += 1
        self._untitled_numbers.add(number)
        return number
    
    def _release_untitled_number(self, number: int) -> None:
        """Release an Untitled number for reuse."""
        self._untitled_numbers.discard(number)
    
    def _is_untitled_empty(self, editor: CodeEditor) -> bool:
        """Check if an Untitled editor is empty and unmodified."""
        if editor not in self.editors:
            return False
        
        info = self.editors[editor]
        
        # Must be an Untitled file (no file_path)
        if info["file_path"] is not None:
            return False
        
        # Must not be modified and must be empty
        text = editor.text()
        return not info["modified"] and len(text.strip()) == 0
    
    def _close_empty_untitled(self) -> None:
        """Close any empty Untitled editors (called before opening a file)."""
        indices_to_close = []
        
        for editor in list(self.editors.keys()):
            if self._is_untitled_empty(editor):
                info = self.editors[editor]
                indices_to_close.append((info["index"], editor, info.get("untitled_number")))
        
        # Sort by index descending to avoid index shift when removing
        indices_to_close.sort(key=lambda x: x[0], reverse=True)
        
        for index, editor, untitled_number in indices_to_close:
            # Release the Untitled number
            if untitled_number:
                self._release_untitled_number(untitled_number)
            
            # Remove from tracking first
            if editor in self.editors:
                del self.editors[editor]
            
            # Remove tab
            self._tab_widget.removeTab(index)
        
        # Update remaining editor indices after all removals
        self._update_editor_indices()

    
    def get_untitled_count(self) -> int:
        """Get the number of Untitled editors."""
        count = 0
        for editor, info in self.editors.items():
            if info["file_path"] is None:
                count += 1
        return count
    
    # ========== Editor Operations ==========
    
    def new_editor(self, skip_if_has_editors: bool = False) -> CodeEditor:
        """Create a new empty editor with numbered Untitled name.
        
        Args:
            skip_if_has_editors: If True, don't create if any editors exist
        """
        if skip_if_has_editors and self._tab_widget.count() > 0:
            return None
            
        editor = CodeEditor(self._parent)
        self._connect_editor_signals(editor)
        
        untitled_num = self._get_next_untitled_number()
        tab_name = f"Untitled {untitled_num}" if untitled_num > 1 else "Untitled"
        
        index = self._tab_widget.addTab(editor, tab_name)
        self.editors[editor] = {
            "index": index,
            "file_path": None,
            "modified": False,
            "untitled_number": untitled_num  # Track Untitled number
        }
        
        self._tab_widget.setCurrentWidget(editor)
        self.editor_created.emit(editor)
        
        return editor
    
    def open_editor(self, file_path: Optional[str] = None) -> Optional[CodeEditor]:
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self._parent, 
                "Open File", 
                "",
                "All Files (*);;C/C++ Files (*.c *.cpp *.h *.hpp);;Python Files (*.py)"
            )
        if not file_path:
            return None
        
        # Check if already open
        for editor, info in self.editors.items():
            if info["file_path"] == file_path:
                self._tab_widget.setCurrentIndex(info["index"])
                return editor
        
        self._close_empty_untitled()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            
            editor = CodeEditor(self._parent)
            editor.setText(text)
            editor.file_path = file_path
            editor.setModified(False)
            
            self._connect_editor_signals(editor)
            
            self._set_editor_language(editor, file_path)
            
            index = self._tab_widget.addTab(editor, Path(file_path).name)
            self.editors[editor] = {
                "index": index,
                "file_path": file_path,
                "modified": False,
                "untitled_number": None  # Not an Untitled file
            }
            
            self._tab_widget.setCurrentIndex(index)
            self._set_tab_color(index, "saved")
            
            self.editor_created.emit(editor)
            self.file_opened.emit(file_path)
            
            self._ctags_handler.index_file_async(file_path)
            
            return editor
            
        except Exception as e:
            QMessageBox.critical(
                self._parent, "Error", f"Could not open file: {str(e)}"
            )
            return None
    
    def save_editor(self, editor: Optional[CodeEditor] = None) -> bool:
        editor = editor or self.get_current_editor()
        if not editor or editor not in self.editors:
            return False
        
        info = self.editors[editor]
        
        # Get file path if not set
        if not info["file_path"]:
            return self.save_editor_as(editor)
        
        try:
            with open(info["file_path"], 'w', encoding='utf-8') as f:
                f.write(editor.text())
            
            editor.setModified(False)
            info["modified"] = False
            self._update_tab_title(editor)
            self._set_tab_color(info["index"], "saved")
            
            self.file_saved.emit(info["file_path"])
            
            self._ctags_handler.index_file_async(info["file_path"])
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self._parent, "Error", f"Could not save file: {str(e)}"
            )
            return False
    
    def save_editor_as(self, editor: Optional[CodeEditor] = None) -> bool:
        editor = editor or self.get_current_editor()
        if not editor or editor not in self.editors:
            return False
        
        file_path, _ = QFileDialog.getSaveFileName(
            self._parent, 
            "Save File As", 
            "",
            "All Files (*);;C/C++ Files (*.c *.cpp *.h *.hpp);;Python Files (*.py)"
        )
        
        if not file_path:
            return False
        
        info = self.editors[editor]
        
        if info["untitled_number"]:
            self._release_untitled_number(info["untitled_number"])
            info["untitled_number"] = None
        
        editor.file_path = file_path
        info["file_path"] = file_path
        
        # Update language based on new extension
        self._set_editor_language(editor, file_path)
        
        return self.save_editor(editor)
    
    def save_all(self) -> bool:
        """Save all modified editors."""
        success = True
        for editor, info in self.editors.items():
            if info["modified"]:
                if not self.save_editor(editor):
                    success = False
        return success
    
    def close_editor(self, index: int) -> bool:
        """Close editor at specified index."""
        if index < 0 or index >= self._tab_widget.count():
            return False
        
        editor = self._tab_widget.widget(index)
        if not editor or editor not in self.editors:
            return False
        
        info = self.editors[editor]
        is_untitled = info["file_path"] is None
        is_empty = self._is_untitled_empty(editor)
        
        if editor.isModified() and not is_empty:
            tab_name = self._tab_widget.tabText(index).rstrip('*')
            reply = QMessageBox.question(
                self._parent,
                "Save Changes",
                f"Do you want to save changes to {tab_name}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_editor(editor):
                    return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        
        file_path = info["file_path"]
        
        if info.get("untitled_number"):
            self._release_untitled_number(info["untitled_number"])
        
        # Track closed files (only real files, not Untitled)
        if file_path:
            self._closed_files.append(file_path)
            if len(self._closed_files) > self._max_closed_files:
                self._closed_files.pop(0)
            self._ctags_handler.cleanup_file_tags(file_path)
        
        # Remove tab and editor tracking
        self._tab_widget.removeTab(index)
        del self.editors[editor]
        
        # Update remaining editor indices
        self._update_editor_indices()
        
        if self._tab_widget.count() == 0:
            self.new_editor()
        
        if file_path:
            self.editor_closed.emit(file_path)
        
        return True
    
    def close_all(self) -> bool:
        """Close all editors."""
        while self._tab_widget.count() > 0:
            if not self.close_editor(self._tab_widget.count() - 1):
                return False
        return True
    
    def reopen_last_closed(self) -> Optional[CodeEditor]:
        """Reopen the last closed file."""
        if not self._closed_files:
            return None
        
        file_path = self._closed_files.pop()
        return self.open_editor(file_path)
    
    # ========== Editor Actions ==========
    
    def undo(self) -> None:
        """Undo in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.undo()
    
    def redo(self) -> None:
        """Redo in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.redo()
    
    def cut(self) -> None:
        """Cut selection in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.cut()
    
    def copy(self) -> None:
        """Copy selection in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.copy()
    
    def paste(self) -> None:
        """Paste in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.paste()
    
    def select_all(self) -> None:
        """Select all in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.selectAll()
    
    def comment_lines(self) -> None:
        """Toggle comment on selected lines."""
        editor = self.get_current_editor()
        if editor:
            editor.comment_lines()
    
    def goto_line(self, line: int) -> None:
        """Go to specific line in current editor."""
        editor = self.get_current_editor()
        if editor:
            editor.goto_line(line)
    
    def find_text(self, text: str, case_sensitive: bool = False, 
                  whole_word: bool = False, forward: bool = True) -> bool:
        editor = self.get_current_editor()
        if not editor:
            return False
        
        # Get current position
        line, index = editor.getCursorPosition()
        
        # findFirst(expr, re, cs, wo, wrap, forward, line, index)
        found = editor.findFirst(
            text,           # expression
            False,          # regular expression
            case_sensitive, # case sensitive
            whole_word,     # whole word
            True,           # wrap around
            forward,        # forward search
            line,           # start line
            index           # start index
        )
        
        return found
    
    def find_next(self) -> bool:
        """Find next occurrence."""
        editor = self.get_current_editor()
        if editor:
            return editor.findNext()
        return False
    
    def replace_text(self, find_text: str, replace_text: str,
                     case_sensitive: bool = False, whole_word: bool = False) -> bool:
        """Replace current selection if it matches find_text."""
        editor = self.get_current_editor()
        if not editor:
            return False
        
        selected = editor.selectedText()
        
        # Check if selection matches
        matches = False
        if case_sensitive:
            matches = selected == find_text
        else:
            matches = selected.lower() == find_text.lower()
        
        if matches:
            editor.replaceSelectedText(replace_text)
            return True
        return False
    
    def replace_all(self, find_text: str, replace_text: str,
                    case_sensitive: bool = False, whole_word: bool = False) -> int:
        editor = self.get_current_editor()
        if not editor:
            return 0
        
        count = 0
        
        # Start from beginning
        editor.setCursorPosition(0, 0)
        
        # Find first occurrence
        found = editor.findFirst(
            find_text,
            False,          # regex
            case_sensitive,
            whole_word,
            False,          # wrap (don't wrap for replace all)
            True,           # forward
            0, 0            # start position
        )
        
        while found:
            editor.replaceSelectedText(replace_text)
            count += 1
            found = editor.findNext()
        
        return count
    
    def toggle_word_wrap(self) -> None:
        """Toggle word wrap in current editor."""
        editor = self.get_current_editor()
        if editor:
            if editor.wrapMode() == QsciScintilla.WrapMode.WrapNone:
                editor.setWrapMode(QsciScintilla.WrapMode.WrapWord)
            else:
                editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)
    
    def toggle_whitespace(self) -> None:
        """Toggle whitespace visibility in current editor."""
        editor = self.get_current_editor()
        if editor:
            if editor.whitespaceVisibility() == QsciScintilla.WhitespaceVisibility.WsInvisible:
                editor.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsVisible)
            else:
                editor.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsInvisible)
    
    def goto_definition(self, word: str) -> bool:
        if not word:
            return False
        current_path = self.get_current_filepath()
        if not current_path:
            return False
        
        definition = self._ctags_handler.find_definition(word, current_path)
        if definition:
            print(f"[EditorManager] Going to definition of '{word}': {definition}")
            if len(definition) == 2:
                file_path, line = definition
                column = 0
            else:
                file_path, line, column = definition
            return self.open_file_at_line(file_path, line, column)
        
        QMessageBox.information(
            self._parent, "Go to Definition",
            f"Definition for '{word}' not found."
        )
        return False
    
    def open_file_at_line(self, file_path: str, line: int, column: int = 0) -> bool:
        """Open file and navigate to specific line and column."""
        import os
        if not os.path.exists(file_path):
            QMessageBox.warning(
                self._parent, "Error",
                f"File not found: {file_path}"
            )
            return False
        
        # Check if file is already open
        editor = self.get_editor_by_path(file_path)
        if editor:
            self._tab_widget.setCurrentWidget(editor)
        else:
            editor = self.open_editor(file_path)
        
        if editor:
            editor.setCursorPosition(line - 1, column)
            editor.ensureLineVisible(line - 1)
            return True
        
        return False
    
    # ========== Accessors ==========
    
    def get_current_editor(self) -> Optional[CodeEditor]:
        """Get the currently active editor."""
        index = self._tab_widget.currentIndex()
        if index != -1:
            editor = self._tab_widget.widget(index)
            if editor in self.editors:
                return editor
        return None
    
    def get_current_filepath(self) -> Optional[str]:
        """Get the file path of the current editor."""
        editor = self.get_current_editor()
        if editor and editor in self.editors:
            return self.editors[editor]["file_path"]
        return None
    
    def get_all_editors(self) -> List[CodeEditor]:
        """Get all editor instances."""
        return list(self.editors.keys())
    
    def get_editor_by_path(self, file_path: str) -> Optional[CodeEditor]:
        """Find an editor by its file path."""
        for editor, info in self.editors.items():
            if info["file_path"] == file_path:
                return editor
        return None
    
    def get_modified_editors(self) -> List[CodeEditor]:
        """Get all editors with unsaved changes"""
        modified = []
        for i in range(self._tab_widget.count()):
            editor = self._tab_widget.widget(i)
            if editor and editor.isModified():
                modified.append(editor)
        return modified
    
    def get_open_file_paths(self) -> List[str]:
        """Get list of all open file paths (excluding Untitled tabs)"""
        file_paths = []
        for i in range(self._tab_widget.count()):
            editor = self._tab_widget.widget(i)
            if editor:
                file_path = editor.file_path
                # Only save real files, not Untitled tabs
                if file_path and not file_path.startswith("Untitled"):
                    file_paths.append(file_path)
        return file_paths
    
    def has_unsaved_changes(self) -> bool:
        """Check if any editor has unsaved changes"""
        return len(self.get_modified_editors()) > 0
    
    def get_current_line_count(self) -> int:
        """Get line count of current editor."""
        editor = self.get_current_editor()
        if editor:
            return editor.lines()
        return 0
    
    def get_current_cursor_position(self) -> tuple:
        """Get cursor position (line, column) of current editor."""
        editor = self.get_current_editor()
        if editor:
            line, index = editor.getCursorPosition()
            return (line + 1, index + 1)
        return (0, 0)
    
    @property
    def ctags_handler(self) -> CtagsHandler:
        """Get the CTags handler instance."""
        return self._ctags_handler
    
    @property
    def closed_files(self) -> List[str]:
        """Get list of recently closed files."""
        return self._closed_files.copy()
    
    # ========== Internal Handlers ==========
    
    def _connect_editor_signals(self, editor: CodeEditor) -> None:
        """Connect editor signals to handlers."""
        editor.textChanged.connect(self._on_text_changed)
        editor.cursorPositionChanged.connect(self._on_cursor_changed)
    
    def _on_text_changed(self):
        """Handle text change in an editor."""
        editor = self.sender()
        if editor in self.editors:
            self.editors[editor]["modified"] = True
            self._update_tab_title(editor)
            self._set_tab_color(self.editors[editor]["index"], "modified")
            self.content_modified.emit()
    
    def _on_cursor_changed(self):
        """Handle cursor position change."""
        if hasattr(self._parent, 'update_status_bar'):
            self._parent.update_status_bar()
    
    def _on_tab_changed(self, index: int):
        """Handle tab selection change."""
        editor = self._tab_widget.widget(index)
        if editor in self.editors:
            self.current_editor_changed.emit(editor)
            
            if hasattr(self._parent, '_function_list') and self._parent._function_list:
                file_path = self.editors[editor]["file_path"]
                if file_path:
                    symbols = self._ctags_handler.get_cached_symbols(file_path)
                    if hasattr(self._parent._function_list, 'update_symbols'):
                        self._parent._function_list.update_symbols(symbols)
            
            self._update_autocomplete_with_ctags(editor)
    
    def _on_close_tab_requested(self, index: int) -> None:
        """Handle tab close request from QTabWidget signal"""
        self.close_editor(index)
    
    def _update_tab_title(self, editor: CodeEditor):
        """Update the tab title based on editor state."""
        if editor not in self.editors:
            return
        
        info = self.editors[editor]
        
        if info["file_path"]:
            name = Path(info["file_path"]).name
        else:
            untitled_num = info.get("untitled_number", 1)
            name = f"Untitled {untitled_num}" if untitled_num > 1 else "Untitled"
        
        if info["modified"]:
            name = f"{name}*"
        
        self._tab_widget.setTabText(info["index"], name)
    
    def _update_editor_indices(self):
        """Update stored indices after tab changes."""
        for i in range(self._tab_widget.count()):
            editor = self._tab_widget.widget(i)
            if editor in self.editors:
                self.editors[editor]["index"] = i
    
    def _set_tab_color(self, index: int, state: str) -> None:
        """Set tab background color based on state."""
        tab_bar = self._tab_widget.tabBar()
        if state == "modified":
            tab_bar.setTabTextColor(index, self.TAB_COLOR_MODIFIED)
        elif state == "saved":
            tab_bar.setTabTextColor(index, self.TAB_COLOR_SAVED)
        else:
            tab_bar.setTabTextColor(index, self.TAB_COLOR_DEFAULT)
    
    def _set_editor_language(self, editor: CodeEditor, file_path: str) -> None:
        """Set editor language based on file extension."""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.py', '.pyw']:
            editor.set_language("Python")
        elif ext in ['.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.ino']:
            editor.set_language("CPP")
        else:
            editor.set_language("CPP")
    
    def _update_autocomplete_with_ctags(self, editor: CodeEditor) -> None:
        """Update autocomplete with CTags symbols."""
        file_path = self.get_current_filepath()
        if file_path:
            symbols = self._ctags_handler.get_cached_symbols(file_path)
            apis = QsciAPIs(editor.lexer)
            
            for symbol in symbols:
                # Build autocomplete entry with signature if available
                if hasattr(symbol, 'name'):
                    entry = symbol.name
                    if hasattr(symbol, 'signature') and symbol.signature:
                        entry += symbol.signature
                    apis.add(entry)
                elif isinstance(symbol, str):
                    apis.add(symbol)
            
            apis.prepare()
            editor.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAPIs)

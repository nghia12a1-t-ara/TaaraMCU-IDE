"""
Code Editor - QScintilla-based code editor widget.
Professional syntax highlighting and code editing features.
"""

from PyQt6.Qsci import QsciScintilla, QsciLexerCPP, QsciLexerPython
from PyQt6.QtGui import QFont, QColor, QMouseEvent
from PyQt6.QtCore import QTimer, Qt, pyqtSignal as Signal
from PyQt6.QtWidgets import QMessageBox
from pathlib import Path
import json
import os
from typing import Optional, TYPE_CHECKING

from taara_ide.utils.resource import resource_path

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class CodeEditor(QsciScintilla):
    """
    Advanced code editor based on QScintilla.
    
    Features:
        - Syntax highlighting for C/C++/Python
        - Theme support (JSON-based)
        - Line numbers with margin
        - Current line highlighting
        - Word highlighting on cursor
        - Bracket matching
        - Go to definition (Ctrl+Click)
        - Auto-indentation
        - Auto-completion
        - Call tips
        - Comment toggle
        - Zoom support
    
    Signals:
        cursor_position_changed: Emitted when cursor moves (line, column)
        modification_changed: Emitted when modification state changes (modified)
    """
    
    cursor_changed = Signal(int, int)  # line, column
    modification_changed = Signal(bool)
    
    def __init__(self, parent: Optional['MainWindow'] = None, 
                 theme_name: str = "khaki", language: str = "CPP"):
        super().__init__(parent)
        self.GUI = parent
        self.file_path: Optional[str] = None
        self._language = language
        
        # Font configuration
        self.text_font = QFont("Consolas", 14)
        self.margin_font = QFont("Consolas", 14)
        
        # Load theme first
        self.theme = self._load_theme(theme_name.lower() + ".json")
        
        self._setup_lexer(language)
        self._apply_theme()
        
        # Apply font to all styles
        for style in range(128):
            self.lexer.setFont(self.text_font, style)
        
        # Apply lexer to QScintilla AFTER theme is applied
        self.setLexer(self.lexer)
        
        if self.theme:
            colors = self.theme.get("colors", {})
            editor_bg = colors.get("editor.background", "#D7D7AF")
            self.setPaper(QColor(editor_bg))
        
        # Line number margin configuration
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")
        self.setMarginsForegroundColor(QColor("#2B2B2B"))
        self.setMarginsBackgroundColor(QColor("#D3CBB7"))
        self.setMarginsFont(self.margin_font)
        
        # Separator margin
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 10)
        
        # Current line highlighting
        self.setCaretLineVisible(True)
        
        # Configure search indicators
        self.indicatorDefine(QsciScintilla.IndicatorStyle.StraightBoxIndicator, 0)
        self.setIndicatorDrawUnder(True, 0)
        
        # Set global font
        self.setFont(self.text_font)
        
        # Configure tab and indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        
        # Scroll settings
        self.horizontalScrollBar().setSingleStep(20)
        self.horizontalScrollBar().setPageStep(100)
        
        # Mouse tracking for word highlighting
        self.setMouseTracking(True)
        self.last_highlighted_word = None
        
        # Auto completion
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(2)
        
        # Call tips
        self.setCallTipsVisible(3)
        self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsContext)
        self.setCallTipsPosition(QsciScintilla.CallTipsPosition.CallTipsAboveText)
        self.setCallTipsBackgroundColor(QColor("#222831"))
        self.setCallTipsForegroundColor(QColor("#EEEEEE"))
        self.setCallTipsHighlightColor(QColor("#00ADB5"))
        
        # Configure highlight indicator
        self.highlight_indicator = 8
        self.SendScintilla(self.SCI_INDICSETSTYLE, self.highlight_indicator, 
                          QsciScintilla.INDIC_BOX)
        color = QColor("#FF5733")
        color_int = (color.red() << 16) | (color.green() << 8) | color.blue()
        self.SendScintilla(self.SCI_INDICSETFORE, self.highlight_indicator, color_int)
        
        # Connect cursor position changed
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.cursorPositionChanged.connect(self._highlight_current_word)
        
        # Hotspot for Ctrl+Click
        HOTSPOT_STYLE = 10
        self.SendScintilla(QsciScintilla.SCI_STYLESETHOTSPOT, HOTSPOT_STYLE, True)
        
        # Timer for deferred updates
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._deferred_update)
        self.cursorPositionChanged.connect(self._schedule_update)
        self.textChanged.connect(self._schedule_update)
        
        # Track modification
        self.modificationChanged.connect(self._on_modification_changed)
    
    def _setup_lexer(self, language: str):
        """Setup syntax lexer based on language."""
        if language.upper() == "PYTHON":
            self.lexer = QsciLexerPython()
        else:
            self.lexer = QsciLexerCPP()
        self.lexer.setDefaultFont(self.text_font)
    
    def _schedule_update(self):
        """Schedule deferred update."""
        self.update_timer.start(100)
    
    def _deferred_update(self):
        """Deferred status bar update."""
        if self.GUI and hasattr(self.GUI, 'update_status_bar'):
            self.GUI.update_status_bar()
    
    def _on_cursor_changed(self, line: int, index: int):
        """Handle cursor position change."""
        self.cursor_changed.emit(line + 1, index + 1)
    
    def _on_modification_changed(self, modified: bool):
        """Handle modification state change."""
        self.modification_changed.emit(modified)
    
    def _maintain_margin_font(self):
        """Keep margin font size fixed regardless of zoom level."""
        self.setMarginsFont(self.margin_font)
        width = self.fontMetrics().horizontalAdvance("00000")
        self.setMarginWidth(0, width)
    
    def zoomIn(self, range_val: int = 1):
        """Override zoom in to maintain margin font size."""
        super().zoomIn(range_val)
        self._maintain_margin_font()
    
    def zoomOut(self, range_val: int = 1):
        """Override zoom out to maintain margin font size."""
        super().zoomOut(range_val)
        self._maintain_margin_font()
    
    def wheelEvent(self, event):
        """Handle Ctrl+Wheel zoom."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def _load_theme(self, theme_file: str) -> Optional[dict]:
        """Load theme from JSON file."""
        try:
            # Try multiple paths
            paths = [
                Path(__file__).parent / "themes" / theme_file,
                Path(resource_path("themes")) / theme_file,
                Path("themes") / theme_file,
            ]
            
            for theme_path in paths:
                if theme_path.exists():
                    with open(theme_path, 'r') as f:
                        return json.load(f)
            
            return None
        except Exception:
            return None
    
    def _apply_theme(self):
        """Apply the loaded theme."""
        if not self.theme:
            return
        
        colors = self.theme.get("colors", {})
        token_colors = self.theme.get("tokenColors", [])
        
        # Set editor background and foreground
        editor_bg = colors.get("editor.background", "#D7D7AF")
        editor_fg = colors.get("editor.foreground", "#5F5F00")
        
        bg_color = QColor(editor_bg)
        fg_color = QColor(editor_fg)
        
        self.lexer.setDefaultPaper(bg_color)
        self.lexer.setDefaultColor(fg_color)
        
        for style in range(128):
            self.lexer.setPaper(bg_color, style)
            self.lexer.setColor(fg_color, style)
        
        # Map token colors to Scintilla styles for CPP
        if isinstance(self.lexer, QsciLexerCPP):
            style_map = {
                "comment": [QsciLexerCPP.Comment, QsciLexerCPP.CommentLine, 
                           QsciLexerCPP.CommentDoc, QsciLexerCPP.CommentLineDoc,
                           QsciLexerCPP.CommentDocKeyword, QsciLexerCPP.CommentDocKeywordError],
                "string": [QsciLexerCPP.DoubleQuotedString, QsciLexerCPP.SingleQuotedString,
                          QsciLexerCPP.RawString, QsciLexerCPP.VerbatimString],
                "constant.numeric": [QsciLexerCPP.Number],
                "keyword": [QsciLexerCPP.Keyword],
                "storage": [QsciLexerCPP.KeywordSet2],
                "entity.name.function": [QsciLexerCPP.GlobalClass],
                "meta.preprocessor": [QsciLexerCPP.PreProcessor, QsciLexerCPP.PreProcessorComment],
                "variable.language": [QsciLexerCPP.Operator],
            }
        elif isinstance(self.lexer, QsciLexerPython):
            style_map = {
                "comment": [QsciLexerPython.Comment, QsciLexerPython.CommentBlock],
                "string": [QsciLexerPython.DoubleQuotedString, QsciLexerPython.SingleQuotedString,
                          QsciLexerPython.TripleDoubleQuotedString, QsciLexerPython.TripleSingleQuotedString],
                "constant.numeric": [QsciLexerPython.Number],
                "keyword": [QsciLexerPython.Keyword],
                "entity.name.function": [QsciLexerPython.FunctionMethodName, QsciLexerPython.ClassName],
                "entity.name.class": [QsciLexerPython.ClassName],
                "variable.language": [QsciLexerPython.Operator],
                "storage": [QsciLexerPython.Decorator],
            }
        else:
            style_map = {}
        
        # Apply token colors (only foreground, keep background consistent)
        for token in token_colors:
            scope = token.get("scope", "")
            settings = token.get("settings", {})
            
            scopes = [scope] if isinstance(scope, str) else scope
            
            for scope in scopes:
                if scope in style_map:
                    styles = style_map[scope]
                    for style in styles:
                        if "foreground" in settings:
                            self.lexer.setColor(QColor(settings["foreground"]), style)
                        self.lexer.setPaper(bg_color, style)
        
        # Set editor UI colors
        self.setCaretLineBackgroundColor(
            QColor(colors.get("editor.lineHighlightBackground", "#BFBF97")))
        self.setCaretForegroundColor(
            QColor(colors.get("editorCursor.foreground", "#4D4D4D")))
        self.setSelectionBackgroundColor(
            QColor(colors.get("editor.selectionBackground", "#D7FF87")))
        self.setSelectionForegroundColor(fg_color)
        
        margin_bg = colors.get("editorGroupHeader.tabsBackground", "#D3CBB7")
        self.setMarginsForegroundColor(QColor(colors.get("editorLineNumber.foreground", "#000000")))
        self.setMarginsBackgroundColor(QColor(margin_bg))
        
        # Set indent guides color
        indent_color = colors.get("editorIndentGuide.background", "#586E7580")
        self.setIndentationGuidesBackgroundColor(QColor(indent_color))
        self.setIndentationGuidesForegroundColor(QColor(indent_color))
        
        # Set whitespace color
        ws_color = colors.get("editorWhitespace.foreground", "#586E7580")
        self.setWhitespaceForegroundColor(QColor(ws_color))
        
        self.setMatchedBraceBackgroundColor(QColor(colors.get("editor.selectionBackground", "#D7FF87")))
        self.setMatchedBraceForegroundColor(fg_color)
        self.setUnmatchedBraceBackgroundColor(QColor("#FF0000"))
        self.setUnmatchedBraceForegroundColor(QColor("#FFFFFF"))
    
    def set_language(self, language: str):
        """Change syntax highlighting language."""
        self._language = language
        self._setup_lexer(language)
        self.lexer.setDefaultFont(self.text_font)
        self._apply_theme()
        for style in range(128):
            self.lexer.setFont(self.text_font, style)
        self.setLexer(self.lexer)
        
        if self.theme:
            colors = self.theme.get("colors", {})
            editor_bg = colors.get("editor.background", "#D7D7AF")
            self.setPaper(QColor(editor_bg))
    
    def set_theme(self, theme_name: str):
        """Change color theme."""
        self.theme = self._load_theme(theme_name.lower() + ".json")
        if self.theme:
            self._apply_theme()
            for style in range(128):
                self.lexer.setFont(self.text_font, style)
            self.setLexer(self.lexer)
            
            colors = self.theme.get("colors", {})
            editor_bg = colors.get("editor.background", "#D7D7AF")
            self.setPaper(QColor(editor_bg))
    
    def comment_lines(self):
        """Comment or uncomment selected lines."""
        start_pos = self.SendScintilla(QsciScintilla.SCI_GETSELECTIONSTART)
        end_pos = self.SendScintilla(QsciScintilla.SCI_GETSELECTIONEND)
        
        start_line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, start_pos)
        end_line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, end_pos)
        
        if start_pos == end_pos:
            start_line = end_line = self.SendScintilla(
                QsciScintilla.SCI_LINEFROMPOSITION, start_pos)
        
        # Check if all lines are commented
        all_commented = True
        lines = []
        
        for line in range(start_line, end_line + 1):
            line_text = self.text(line).rstrip()
            lines.append(line_text)
            if not line_text.lstrip().startswith("//"):
                all_commented = False
        
        # Process each line
        new_lines = []
        for line_text in lines:
            if all_commented:
                # Remove comment
                stripped = line_text.lstrip()
                if stripped.startswith("// "):
                    new_lines.append(line_text.replace("// ", "", 1))
                elif stripped.startswith("//"):
                    new_lines.append(line_text.replace("//", "", 1))
                else:
                    new_lines.append(line_text)
            else:
                new_lines.append("// " + line_text)
        
        # Replace content
        new_text = "\n".join(new_lines)
        new_text_bytes = new_text.encode("utf-8")
        
        self.SendScintilla(QsciScintilla.SCI_SETTARGETSTART,
            self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, start_line))
        self.SendScintilla(QsciScintilla.SCI_SETTARGETEND,
            self.SendScintilla(QsciScintilla.SCI_GETLINEENDPOSITION, end_line))
        self.SendScintilla(QsciScintilla.SCI_REPLACETARGET, 
                          len(new_text_bytes), new_text_bytes)
    
    def _highlight_current_word(self):
        """Highlight all occurrences of current word."""
        self.SendScintilla(self.SCI_SETINDICATORCURRENT, self.highlight_indicator)
        self.SendScintilla(self.SCI_INDICATORCLEARRANGE, 0, self.length())
        
        pos = self.SendScintilla(self.SCI_GETCURRENTPOS)
        word = self.get_word_at_position(pos)
        
        if not word or not any(c.isalnum() or c == '_' for c in word):
            return
        
        self.SendScintilla(self.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_WHOLEWORD)
        
        full_text = self.text()
        text_length = len(full_text)
        search_pos = 0
        
        while search_pos < text_length:
            self.SendScintilla(self.SCI_SETTARGETSTART, search_pos)
            self.SendScintilla(self.SCI_SETTARGETEND, text_length)
            
            found_pos = self.SendScintilla(self.SCI_SEARCHINTARGET, 
                                          len(word), word.encode('utf-8'))
            if found_pos == -1:
                break
            
            self.SendScintilla(self.SCI_INDICATORFILLRANGE, found_pos, len(word))
            search_pos = found_pos + len(word)
        
        self.SendScintilla(self.SCI_SETSEARCHFLAGS, 0)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for Ctrl+Click go to definition."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            position = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, x, y)
            
            line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, position)
            index = position - self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMLINE, line)
            self.setCursorPosition(line, index)
            
            # Check Ctrl+Click for go to definition
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                word = self.get_word_at_position(position)
                if word and self.GUI:
                    # Emit signal or call handler
                    if hasattr(self.GUI, '_editor_manager'):
                        self.GUI._editor_manager.goto_definition(word)
                    return
        
        super().mousePressEvent(event)
    
    def get_word_at_position(self, position: int) -> str:
        """Get word at given position."""
        start_pos = self.SendScintilla(self.SCI_WORDSTARTPOSITION, position, True)
        end_pos = self.SendScintilla(self.SCI_WORDENDPOSITION, position, True)
        
        if start_pos == end_pos:
            return ""
        
        text_length = self.SendScintilla(self.SCI_GETTEXTLENGTH)
        
        if start_pos < 0 or end_pos > text_length or start_pos > end_pos:
            return ""
        
        length = end_pos - start_pos + 1
        buffer = bytes(length)
        
        self.SendScintilla(self.SCI_SETTARGETSTART, start_pos)
        self.SendScintilla(self.SCI_SETTARGETEND, end_pos)
        self.SendScintilla(self.SCI_GETTARGETTEXT, 0, buffer)
        
        word = buffer.decode('utf-8', errors='ignore').rstrip('\x00').strip()
        return word
    
    def get_current_word(self) -> str:
        """Get word under cursor."""
        pos = self.SendScintilla(self.SCI_GETCURRENTPOS)
        return self.get_word_at_position(pos)
    
    def goto_line(self, line_number: int, column: int = 0):
        """Navigate to specific line and column."""
        self.setCursorPosition(line_number - 1, column)
        self.ensureLineVisible(line_number - 1)
    
    def open_file(self, file_path: str) -> bool:
        """Open a file in the editor."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            self.setText(content)
            self.file_path = file_path
            self.setModified(False)
            
            # Set language based on extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.py', '.pyw']:
                self.set_language("Python")
            elif ext in ['.c', '.h', '.cpp', '.hpp', '.cc', '.cxx']:
                self.set_language("CPP")
            
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {e}")
            return False
    
    def save_file(self, file_path: Optional[str] = None) -> bool:
        """Save editor content to file."""
        path = file_path or self.file_path
        if not path:
            return False
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.text())
            
            self.file_path = path
            self.setModified(False)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save file: {e}")
            return False
    
    # Compatibility methods for EditorManager
    
    def get_cursor_position(self) -> tuple:
        """Get current cursor position as (line, column)."""
        line, index = self.getCursorPosition()
        return (line + 1, index + 1)
    
    def get_line_count(self) -> int:
        """Get total number of lines."""
        return self.lines()
    
    def is_modified(self) -> bool:
        """Check if document is modified."""
        return self.isModified()
    
    def set_modified(self, modified: bool):
        """Set modification state."""
        self.setModified(modified)

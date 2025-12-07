"""
Code Editor - QScintilla-based code editor widget.
Professional syntax highlighting and code editing features.
"""

from PyQt6.Qsci import QsciScintilla, QsciLexerCPP, QsciLexerPython, QsciAPIs
from PyQt6.QtGui import QFont, QColor, QMouseEvent, QFontMetrics, QFontDatabase  # Added QFontDatabase
from PyQt6.QtCore import QTimer, Qt, pyqtSignal as Signal
from PyQt6.QtWidgets import QMessageBox, QApplication
from pathlib import Path
import json
import os
from typing import Optional, TYPE_CHECKING
from taara_ide.utils.resource import resource_path
from taara_ide.ui.editor.autocomplete_manager import AutocompleteManager

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
        - Enhanced auto-completion with APIs
        - Enhanced call tips with function signatures
        - Comment toggle
        - Zoom support
    
    Signals:
        cursor_position_changed: Emitted when cursor moves (line, column)
        modification_changed: Emitted when modification state changes (modified)
    """
    
    cursor_changed = Signal(int, int)  # line, column
    modification_changed = Signal(bool)
    
    def __init__(self, parent=None):
        """Initialize code editor."""
        super().__init__(parent)
        
        self._parent = parent
        self.file_path: Optional[str] = None
        self._language = "cpp"
        self.lexer = None
        
        # Setup font
        self._setup_font()
        
        # Load theme
        self.theme = self._load_theme("khaki.json")
        
        # Setup lexer first
        self._setup_lexer(self._language)
        self._apply_theme()
        
        # Apply font to all lexer styles
        for style in range(128):
            self.lexer.setFont(self.text_font, style)
        
        self.autocomplete_manager = AutocompleteManager(self)
        self.autocomplete_manager.setup_apis(self.lexer)
        
        # Now set the lexer (with APIs already configured)
        self.setLexer(self.lexer)
        
        # Setup autocompletion and call tips settings
        self.autocomplete_manager.setup_autocompletion()
        self.autocomplete_manager.setup_calltips()
        
        # Apply paper color after setLexer
        if self.theme:
            colors = self.theme.get("colors", {})
            editor_bg = colors.get("editor.background", "#D7D7AF")
            self.setPaper(QColor(editor_bg))
        
        # Setup editor UI
        self._setup_margins()
        self._setup_editing()
        self._setup_indicators()
        
        # Connect signals
        self._connect_signals()
    
    def _setup_font(self):
        """Setup editor fonts with fallback."""
        font_families = ["Consolas", "Courier New", "Monospace"]
        available_fonts = QFontDatabase.families()
        available_font = None
        
        for family in font_families:
            if family in available_fonts:
                available_font = family
                break
        
        if not available_font:
            available_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()
        
        self.text_font = QFont(available_font, 14)
        self.text_font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_font.setFixedPitch(True)
        
        self.margin_font = QFont(available_font, 14)
        self.margin_font.setStyleHint(QFont.StyleHint.Monospace)
        self.margin_font.setFixedPitch(True)
        
        self.setFont(self.text_font)
    
    def _setup_lexer(self, language: str):
        """Setup syntax highlighting lexer."""
        language_lower = language.lower()
        
        if language_lower in ["cpp", "c", "c++"]:
            self.lexer = QsciLexerCPP(self)
        elif language_lower == "python":
            self.lexer = QsciLexerPython(self)
        else:
            self.lexer = QsciLexerCPP(self)
        
        self.lexer.setDefaultFont(self.text_font)
    
    def _setup_margins(self):
        """Setup editor margins."""
        # Line number margin
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")
        self.setMarginsForegroundColor(QColor("#2B2B2B"))
        self.setMarginsBackgroundColor(QColor("#D3CBB7"))
        self.setMarginsFont(self.margin_font)
        
        # Separator margin
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 10)
    
    def _setup_editing(self):
        """Setup editing features."""
        # Current line highlighting
        self.setCaretLineVisible(True)
        
        # Tab and indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        self.setBackspaceUnindents(True)
        
        # Scroll settings
        self.horizontalScrollBar().setSingleStep(20)
        self.horizontalScrollBar().setPageStep(100)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_highlighted_word = None
    
    def _setup_indicators(self):
        """Setup search and highlight indicators."""
        self.highlight_indicator = 0
        self.indicatorDefine(QsciScintilla.IndicatorStyle.StraightBoxIndicator, self.highlight_indicator)
        self.setIndicatorDrawUnder(True, self.highlight_indicator)
        
        # Hotspot for Ctrl+Click
        HOTSPOT_STYLE = 10
        self.SendScintilla(QsciScintilla.SCI_STYLESETHOTSPOT, HOTSPOT_STYLE, True)
    
    def _connect_signals(self):
        """Connect editor signals."""
        # Cursor position
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.cursorPositionChanged.connect(self._highlight_current_word)
        
        self.textChanged.connect(self.autocomplete_manager.on_text_changed)
        
        # Modification tracking
        self.modificationChanged.connect(self._on_modification_changed)
        
        # Deferred updates
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._deferred_update)
        self.cursorPositionChanged.connect(self._schedule_update)
        self.textChanged.connect(self._schedule_update)
    
    def _schedule_update(self):
        """Schedule deferred update."""
        self.update_timer.start(100)
    
    def _deferred_update(self):
        """Deferred status bar update."""
        line, index = self.getCursorPosition()
        self.cursor_changed.emit(line + 1, index + 1)
    
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
        
        # Map token colors to Scintilla styles
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
        
        # Apply token colors
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
        
        # Indent guides color
        indent_color = colors.get("editorIndentGuide.background", "#586E7580")
        self.setIndentationGuidesBackgroundColor(QColor(indent_color))
        self.setIndentationGuidesForegroundColor(QColor(indent_color))
        
        # Whitespace color
        ws_color = colors.get("editorWhitespace.foreground", "#586E7580")
        self.setWhitespaceForegroundColor(QColor(ws_color))
        
        # Brace matching
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
        
        self.autocomplete_manager.setup_apis(self.lexer)
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
            
            self.autocomplete_manager.setup_apis(self.lexer)
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
            position = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT,
                int(event.position().x()), int(event.position().y()))
            
            line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, position)
            index = position - self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMLINE, line)
            self.setCursorPosition(line, index)
            
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                word = self.get_word_at_position(position)
                if word and self._parent:
                    main_window = self._parent
                    while main_window and not hasattr(main_window, '_editor_manager'):
                        main_window = main_window.parent() if hasattr(main_window, 'parent') else None
                    if main_window and hasattr(main_window, '_editor_manager'):
                        main_window._editor_manager.goto_definition(word)
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

    def goto_line_and_select(self, line_number: int):
        """Navigate to line and select it."""
        if line_number < 0 or line_number >= self.lines():
            return
        start_pos = self.SendScintilla(self.SCI_POSITIONFROMLINE, line_number)
        end_pos = self.SendScintilla(self.SCI_GETLINEENDPOSITION, line_number)
        self.SendScintilla(self.SCI_SETSEL, start_pos, end_pos)
        self.ensureLineVisible(line_number)
    
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

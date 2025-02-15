from PyQt6.Qsci import QsciScintilla, QsciLexerCPP
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
from ..config.settings import DEFAULT_FONT, DEFAULT_FONT_SIZE, MARGIN_FONT_SIZE

class CodeEditor(QsciScintilla):
    def __init__(self, parent=None, theme_name="Khaki"):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 12))
        self.setLexer(QsciLexerCPP())  # Set the lexer for syntax highlighting
        self.setup_editor()
        self.setup_margins()
        self.setup_theme(theme_name)

    def setup_editor(self):
        # Editor setup code...
        pass

    def setup_margins(self):
        # Margins setup code...
        pass

    def setup_theme(self, theme_name):
        # Theme setup code...
        pass

    def setup_lexer(self):
        # Lexer setup code...
        pass 
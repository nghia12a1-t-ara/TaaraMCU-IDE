"""
Syntax Highlighter and Theme Manager for code editor.
Uses QSyntaxHighlighter instead of QScintilla.
"""

from PyQt6.QtGui import (
    QColor, QFont, QTextCharFormat, QSyntaxHighlighter,
    QBrush
)
from PyQt6.QtCore import QRegularExpression
from pathlib import Path
import json
from typing import Optional, Dict, Any, List, Tuple

from taara_ide.utils.resource import resource_path


class ThemeManager:
    """ Manages editor themes and syntax highlighting colors """
    def __init__(self, themes_dir: Optional[str] = None):
        if themes_dir:
            self._themes_dir = Path(themes_dir)
        else:
            self._themes_dir = Path(resource_path("themes"))
        
        self._current_theme: Optional[Dict[str, Any]] = None
        self._theme_name: str = "khaki"
    
    def load_theme(self, theme_name: str) -> bool:
        theme_file = self._themes_dir / f"{theme_name.lower()}.json"
        
        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                self._current_theme = json.load(f)
                self._theme_name = theme_name.lower()
                return True
        except Exception:
            # Use default theme if file not found
            self._current_theme = self._get_default_theme()
            return False
    
    def _get_default_theme(self) -> Dict[str, Any]:
        """Return default khaki theme."""
        return {
            "colors": {
                "editor.background": "#D7D7AF",
                "editor.foreground": "#5F5F00",
                "editor.lineHighlightBackground": "#BFBF97",
                "editor.selectionBackground": "#D7FF87",
                "editorCursor.foreground": "#4D4D4D",
                "editorLineNumber.foreground": "#2B2B2B",
                "editorLineNumber.background": "#D3CBB7",
            },
            "tokenColors": [
                {"scope": "comment", "settings": {"foreground": "#87875F"}},
                {"scope": "string", "settings": {"foreground": "#AF5F00"}},
                {"scope": "constant.numeric", "settings": {"foreground": "#875F5F"}},
                {"scope": "keyword", "settings": {"foreground": "#5F8700"}},
                {"scope": "storage", "settings": {"foreground": "#5F8700"}},
                {"scope": "entity.name.function", "settings": {"foreground": "#0087AF"}},
                {"scope": "meta.preprocessor", "settings": {"foreground": "#5F5FAF"}},
            ]
        }
    
    def get_color(self, key: str, default: str = "#FFFFFF") -> QColor:
        """Get a color from the current theme."""
        if self._current_theme:
            colors = self._current_theme.get("colors", {})
            return QColor(colors.get(key, default))
        return QColor(default)
    
    def get_token_color(self, scope: str, default: str = "#000000") -> QColor:
        """Get a token color from the current theme."""
        if self._current_theme:
            for token in self._current_theme.get("tokenColors", []):
                token_scope = token.get("scope", "")
                scopes = [token_scope] if isinstance(token_scope, str) else token_scope
                if scope in scopes:
                    return QColor(token.get("settings", {}).get("foreground", default))
        return QColor(default)
    
    @property
    def current_theme(self) -> Optional[Dict[str, Any]]:
        """Get the current theme dictionary."""
        return self._current_theme
    
    @property
    def theme_name(self) -> str:
        """Get the current theme name."""
        return self._theme_name
    
    def list_themes(self) -> list:
        """List available themes."""
        if self._themes_dir.exists():
            return [f.stem for f in self._themes_dir.glob("*.json")]
        return []


class CppHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for C/C++ code.
    """
    
    def __init__(self, parent, theme_manager: ThemeManager):
        super().__init__(parent)
        self._theme_manager = theme_manager
        self._highlighting_rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._setup_rules()
    
    def _setup_rules(self):
        """Setup syntax highlighting rules."""
        self._highlighting_rules.clear()
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(self._theme_manager.get_token_color("keyword", "#5F8700"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = [
            "auto", "break", "case", "char", "const", "continue", "default",
            "do", "double", "else", "enum", "extern", "float", "for", "goto",
            "if", "inline", "int", "long", "register", "restrict", "return",
            "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
            "union", "unsigned", "void", "volatile", "while",
            # C++ keywords
            "alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel",
            "atomic_commit", "atomic_noexcept", "bitand", "bitor", "bool",
            "catch", "char16_t", "char32_t", "class", "compl", "concept",
            "consteval", "constexpr", "constinit", "const_cast", "co_await",
            "co_return", "co_yield", "decltype", "delete", "dynamic_cast",
            "explicit", "export", "false", "friend", "mutable", "namespace",
            "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or",
            "or_eq", "override", "private", "protected", "public", "reflexpr",
            "reinterpret_cast", "requires", "static_assert", "static_cast",
            "synchronized", "template", "this", "thread_local", "throw",
            "true", "try", "typeid", "typename", "using", "virtual", "wchar_t",
            "xor", "xor_eq"
        ]
        
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self._highlighting_rules.append((pattern, keyword_format))
        
        # Preprocessor
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(self._theme_manager.get_token_color("meta.preprocessor", "#5F5FAF"))
        self._highlighting_rules.append((
            QRegularExpression(r"^\s*#\s*\w+"),
            preprocessor_format
        ))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(self._theme_manager.get_token_color("constant.numeric", "#875F5F"))
        self._highlighting_rules.append((
            QRegularExpression(r"\b[0-9]+\.?[0-9]*([eE][-+]?[0-9]+)?[fFlLuU]*\b"),
            number_format
        ))
        self._highlighting_rules.append((
            QRegularExpression(r"\b0[xX][0-9a-fA-F]+[uUlL]*\b"),
            number_format
        ))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(self._theme_manager.get_token_color("string", "#AF5F00"))
        self._highlighting_rules.append((
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            string_format
        ))
        self._highlighting_rules.append((
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            string_format
        ))
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(self._theme_manager.get_token_color("entity.name.function", "#0087AF"))
        self._highlighting_rules.append((
            QRegularExpression(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()"),
            function_format
        ))
        
        # Single-line comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(self._theme_manager.get_token_color("comment", "#87875F"))
        comment_format.setFontItalic(True)
        self._highlighting_rules.append((
            QRegularExpression(r"//[^\n]*"),
            comment_format
        ))
        
        # Store comment format for multi-line comments
        self._comment_format = comment_format
        self._comment_start = QRegularExpression(r"/\*")
        self._comment_end = QRegularExpression(r"\*/")
    
    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text."""
        # Apply single-line rules
        for pattern, fmt in self._highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        
        # Handle multi-line comments
        self.setCurrentBlockState(0)
        
        start_index = 0
        if self.previousBlockState() != 1:
            match = self._comment_start.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1
        
        while start_index >= 0:
            end_match = self._comment_end.match(text, start_index)
            
            if end_match.hasMatch() and self.previousBlockState() != 1:
                end_index = end_match.capturedEnd()
                comment_length = end_index - start_index
            elif end_match.hasMatch():
                end_index = end_match.capturedEnd()
                comment_length = end_index
                start_index = 0
            else:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            
            self.setFormat(start_index, comment_length, self._comment_format)
            
            match = self._comment_start.match(text, start_index + comment_length)
            start_index = match.capturedStart() if match.hasMatch() else -1
    
    def update_theme(self):
        """Update highlighting rules with current theme colors."""
        self._setup_rules()
        self.rehighlight()


class PythonHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for Python code.
    """
    
    def __init__(self, parent, theme_manager: ThemeManager):
        super().__init__(parent)
        self._theme_manager = theme_manager
        self._highlighting_rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._setup_rules()
    
    def _setup_rules(self):
        """Setup syntax highlighting rules."""
        self._highlighting_rules.clear()
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(self._theme_manager.get_token_color("keyword", "#5F8700"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = [
            "and", "as", "assert", "async", "await", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "False",
            "finally", "for", "from", "global", "if", "import", "in",
            "is", "lambda", "None", "nonlocal", "not", "or", "pass",
            "raise", "return", "True", "try", "while", "with", "yield"
        ]
        
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self._highlighting_rules.append((pattern, keyword_format))
        
        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(self._theme_manager.get_token_color("entity.name.function", "#0087AF"))
        
        builtins = [
            "abs", "all", "any", "bin", "bool", "bytes", "callable", "chr",
            "classmethod", "compile", "complex", "delattr", "dict", "dir",
            "divmod", "enumerate", "eval", "exec", "filter", "float", "format",
            "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex",
            "id", "input", "int", "isinstance", "issubclass", "iter", "len",
            "list", "locals", "map", "max", "memoryview", "min", "next",
            "object", "oct", "open", "ord", "pow", "print", "property", "range",
            "repr", "reversed", "round", "set", "setattr", "slice", "sorted",
            "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip"
        ]
        
        for word in builtins:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self._highlighting_rules.append((pattern, builtin_format))
        
        # Decorators
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(self._theme_manager.get_token_color("meta.preprocessor", "#5F5FAF"))
        self._highlighting_rules.append((
            QRegularExpression(r"@\w+"),
            decorator_format
        ))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(self._theme_manager.get_token_color("constant.numeric", "#875F5F"))
        self._highlighting_rules.append((
            QRegularExpression(r"\b[0-9]+\.?[0-9]*([eE][-+]?[0-9]+)?j?\b"),
            number_format
        ))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(self._theme_manager.get_token_color("string", "#AF5F00"))
        self._highlighting_rules.append((
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            string_format
        ))
        self._highlighting_rules.append((
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            string_format
        ))
        
        # Function definitions
        func_def_format = QTextCharFormat()
        func_def_format.setForeground(self._theme_manager.get_token_color("entity.name.function", "#0087AF"))
        func_def_format.setFontWeight(QFont.Weight.Bold)
        self._highlighting_rules.append((
            QRegularExpression(r"\bdef\s+(\w+)"),
            func_def_format
        ))
        
        # Class definitions
        class_format = QTextCharFormat()
        class_format.setForeground(self._theme_manager.get_token_color("entity.name.function", "#0087AF"))
        class_format.setFontWeight(QFont.Weight.Bold)
        self._highlighting_rules.append((
            QRegularExpression(r"\bclass\s+(\w+)"),
            class_format
        ))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(self._theme_manager.get_token_color("comment", "#87875F"))
        comment_format.setFontItalic(True)
        self._highlighting_rules.append((
            QRegularExpression(r"#[^\n]*"),
            comment_format
        ))
        
        # Store for multi-line strings
        self._string_format = string_format
        self._triple_single = QRegularExpression(r"'''")
        self._triple_double = QRegularExpression(r'"""')
    
    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text."""
        # Apply single-line rules
        for pattern, fmt in self._highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        
        # Handle triple-quoted strings (simplified)
        self.setCurrentBlockState(0)
    
    def update_theme(self):
        """Update highlighting rules with current theme colors."""
        self._setup_rules()
        self.rehighlight()


def create_highlighter(language: str, document, theme_manager: ThemeManager) -> QSyntaxHighlighter:
    if language.lower() == "python":
        return PythonHighlighter(document, theme_manager)
    else:  # Default to C/C++
        return CppHighlighter(document, theme_manager)

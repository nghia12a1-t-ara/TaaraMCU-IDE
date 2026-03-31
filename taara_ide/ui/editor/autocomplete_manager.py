"""
Autocomplete Manager - Handles autocompletion and call tips for QScintilla.
Separated from CodeEditor for better maintainability.
"""

from PyQt6.Qsci import QsciScintilla, QsciLexerCPP, QsciLexerPython, QsciAPIs
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import tempfile

if TYPE_CHECKING:
    from taara_ide.ui.editor.code_editor import CodeEditor


class AutocompleteManager:
    """
    Manages autocompletion and call tips for a CodeEditor instance.
    
    Features:
        - API-based autocompletion for C/C++ and Python
        - Call tips with parameter highlighting
        - Document-based completion (words from current file)
        - CTags integration for custom functions
    """
    
    # C/C++ API keywords and functions
    CPP_KEYWORDS = [
        # C/C++ keywords
        "auto", "break", "case", "char", "const", "continue", "default",
        "do", "double", "else", "enum", "extern", "float", "for", "goto",
        "if", "int", "long", "register", "return", "short", "signed",
        "sizeof", "static", "struct", "switch", "typedef", "union",
        "unsigned", "void", "volatile", "while",
        # C++ specific
        "bool", "catch", "class", "const_cast", "delete", "dynamic_cast",
        "explicit", "export", "false", "friend", "inline", "mutable",
        "namespace", "new", "operator", "private", "protected", "public",
        "reinterpret_cast", "static_cast", "template", "this", "throw",
        "true", "try", "typeid", "typename", "using", "virtual",
        # Common STL
        "vector", "string", "map", "set", "list", "deque", "queue", "stack",
        "cout", "cin", "endl", "cerr",
        "unique_ptr", "shared_ptr", "make_unique", "make_shared",
        # Common types
        "size_t", "nullptr", "NULL",
        # Preprocessor
        "#include", "#define", "#ifdef", "#ifndef", "#endif", "#pragma",
    ]
    
    CPP_FUNCTIONS = [
        # Functions with signatures for call tips
        "printf(const char *format, ...)",
        "scanf(const char *format, ...)",
        "strlen(const char *str)",
        "strcpy(char *dest, const char *src)",
        "strncpy(char *dest, const char *src, size_t n)",
        "strcmp(const char *str1, const char *str2)",
        "strncmp(const char *str1, const char *str2, size_t n)",
        "strcat(char *dest, const char *src)",
        "strncat(char *dest, const char *src, size_t n)",
        "malloc(size_t size)",
        "calloc(size_t num, size_t size)",
        "realloc(void *ptr, size_t size)",
        "free(void *ptr)",
        "memcpy(void *dest, const void *src, size_t n)",
        "memmove(void *dest, const void *src, size_t n)",
        "memset(void *ptr, int value, size_t num)",
        "memcmp(const void *ptr1, const void *ptr2, size_t num)",
        "fopen(const char *filename, const char *mode)",
        "fclose(FILE *stream)",
        "fprintf(FILE *stream, const char *format, ...)",
        "fscanf(FILE *stream, const char *format, ...)",
        "fgets(char *str, int n, FILE *stream)",
        "fputs(const char *str, FILE *stream)",
        "fread(void *ptr, size_t size, size_t count, FILE *stream)",
        "fwrite(const void *ptr, size_t size, size_t count, FILE *stream)",
        "sprintf(char *dest, const char *format, ...)",
        "snprintf(char *dest, size_t size, const char *format, ...)",
        "atoi(const char *str)",
        "atof(const char *str)",
        "atol(const char *str)",
        "abs(int n)",
        "fabs(double x)",
        "sqrt(double x)",
        "pow(double base, double exponent)",
        "sin(double x)",
        "cos(double x)",
        "tan(double x)",
        "log(double x)",
        "log10(double x)",
        "exp(double x)",
        "floor(double x)",
        "ceil(double x)",
        "rand(void)",
        "srand(unsigned int seed)",
    ]
    
    # Python API keywords and functions
    PYTHON_KEYWORDS = [
        # Python keywords
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else",
        "except", "finally", "for", "from", "global", "if", "import",
        "in", "is", "lambda", "not", "or", "pass", "raise",
        "return", "try", "while", "with", "yield", "nonlocal",
        # Built-in functions
        "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
        "callable", "chr", "classmethod", "compile", "complex", "delattr",
        "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
        "float", "format", "frozenset", "getattr", "globals", "hasattr",
        "hash", "help", "hex", "id", "input", "int", "isinstance",
        "issubclass", "iter", "len", "list", "locals", "map", "max",
        "memoryview", "min", "next", "object", "oct", "open", "ord",
        "pow", "print", "property", "range", "repr", "reversed", "round",
        "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum",
        "super", "tuple", "type", "vars", "zip",
        # Common modules
        "os", "sys", "re", "json", "datetime", "time", "math", "random",
        "pathlib", "collections", "itertools", "functools", "typing",
    ]
    
    PYTHON_FUNCTIONS = [
        # Built-in with signatures for call tips
        "print(*args, sep=' ', end='\\n', file=sys.stdout)",
        "len(obj)",
        "range(stop)",
        "range(start, stop, step=1)",
        "open(file, mode='r', buffering=-1, encoding=None)",
        "input(prompt='')",
        "str(object='', encoding='utf-8', errors='strict')",
        "int(x=0, base=10)",
        "float(x=0.0)",
        "list(iterable=())",
        "dict(**kwargs)",
        "set(iterable=())",
        "tuple(iterable=())",
        "type(object)",
        "isinstance(obj, classinfo)",
        "hasattr(object, name)",
        "getattr(object, name, default=None)",
        "setattr(object, name, value)",
        "enumerate(iterable, start=0)",
        "sorted(iterable, key=None, reverse=False)",
        "map(function, iterable)",
        "filter(function, iterable)",
        "zip(*iterables)",
        "super(type=None, object_or_type=None)",
        "abs(x)",
        "all(iterable)",
        "any(iterable)",
        "bin(x)",
        "bool(x=False)",
        "chr(i)",
        "ord(c)",
        "hex(x)",
        "oct(x)",
        "min(*args, key=None)",
        "max(*args, key=None)",
        "sum(iterable, start=0)",
        "round(number, ndigits=None)",
        "pow(base, exp, mod=None)",
        "divmod(a, b)",
        "format(value, format_spec='')",
        "repr(object)",
        "ascii(object)",
        "eval(expression, globals=None, locals=None)",
        "exec(object, globals=None, locals=None)",
        "compile(source, filename, mode)",
        "globals()",
        "locals()",
        "vars(object=None)",
        "dir(object=None)",
        "help(object=None)",
        "id(object)",
        "hash(object)",
        "callable(object)",
        "iter(object, sentinel=None)",
        "next(iterator, default=None)",
        "reversed(seq)",
        "slice(start, stop, step=None)",
    ]
    
    # Built-in signatures for call tips
    BUILTIN_SIGNATURES = {
        # C standard library
        'printf': 'printf(const char *format, ...)',
        'scanf': 'scanf(const char *format, ...)',
        'fprintf': 'fprintf(FILE *stream, const char *format, ...)',
        'sprintf': 'sprintf(char *dest, const char *format, ...)',
        'snprintf': 'snprintf(char *dest, size_t size, const char *format, ...)',
        'strlen': 'strlen(const char *str)',
        'strcpy': 'strcpy(char *dest, const char *src)',
        'strncpy': 'strncpy(char *dest, const char *src, size_t n)',
        'strcat': 'strcat(char *dest, const char *src)',
        'strcmp': 'strcmp(const char *str1, const char *str2)',
        'strncmp': 'strncmp(const char *str1, const char *str2, size_t n)',
        'malloc': 'malloc(size_t size)',
        'calloc': 'calloc(size_t num, size_t size)',
        'realloc': 'realloc(void *ptr, size_t new_size)',
        'free': 'free(void *ptr)',
        'memcpy': 'memcpy(void *dest, const void *src, size_t n)',
        'memset': 'memset(void *ptr, int value, size_t num)',
        'memcmp': 'memcmp(const void *ptr1, const void *ptr2, size_t num)',
        'fopen': 'fopen(const char *filename, const char *mode)',
        'fclose': 'fclose(FILE *stream)',
        'fread': 'fread(void *ptr, size_t size, size_t count, FILE *stream)',
        'fwrite': 'fwrite(const void *ptr, size_t size, size_t count, FILE *stream)',
        'fgets': 'fgets(char *str, int n, FILE *stream)',
        'fputs': 'fputs(const char *str, FILE *stream)',
        # Python
        'print': 'print(*values, sep=" ", end="\\n", file=sys.stdout)',
        'len': 'len(object)',
        'range': 'range(start, stop, step)',
        'open': 'open(file, mode="r", encoding=None)',
        'input': 'input(prompt="")',
        'int': 'int(x=0, base=10)',
        'str': 'str(object="", encoding="utf-8")',
        'list': 'list(iterable=())',
        'dict': 'dict(**kwargs)',
        'enumerate': 'enumerate(iterable, start=0)',
        'sorted': 'sorted(iterable, key=None, reverse=False)',
        'zip': 'zip(*iterables)',
        'map': 'map(function, iterable)',
        'filter': 'filter(function, iterable)',
        'isinstance': 'isinstance(obj, classinfo)',
        'hasattr': 'hasattr(object, name)',
        'getattr': 'getattr(object, name, default=None)',
        'setattr': 'setattr(object, name, value)',
    }
    
    def __init__(self, editor: 'CodeEditor'):
        """Initialize autocomplete manager."""
        self.editor = editor
        self.apis: Optional[QsciAPIs] = None
        self._current_calltip_text: str = ""
        
        # Timer for delayed call tip check
        self.calltip_timer = QTimer()
        self.calltip_timer.setSingleShot(True)
        self.calltip_timer.timeout.connect(self._delayed_calltip_check)
    
    def setup_autocompletion(self):
        """Configure autocompletion settings on the editor."""
        # Use All sources for better completion
        self.editor.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.editor.setAutoCompletionThreshold(1)  # Show after 1 character
        self.editor.setAutoCompletionCaseSensitivity(False)
        self.editor.setAutoCompletionReplaceWord(True)
        self.editor.setAutoCompletionUseSingle(QsciScintilla.AutoCompletionUseSingle.AcusNever)
        self.editor.setAutoCompletionFillupsEnabled(True)
    
    def setup_calltips(self):
        """Configure call tips settings on the editor."""
        self.editor.setCallTipsVisible(5)
        self.editor.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsNoContext)
        self.editor.setCallTipsPosition(QsciScintilla.CallTipsPosition.CallTipsAboveText)
        self.editor.setCallTipsBackgroundColor(QColor("#222831"))
        self.editor.setCallTipsForegroundColor(QColor("#EEEEEE"))
        self.editor.setCallTipsHighlightColor(QColor("#00ADB5"))
    
    def setup_apis(self, lexer):
        """Setup APIs for the given lexer."""
        if not lexer:
            return
        
        self.apis = QsciAPIs(lexer)
        
        # Get appropriate API list based on lexer type
        if isinstance(lexer, QsciLexerCPP):
            api_list = self.CPP_KEYWORDS + self.CPP_FUNCTIONS
        elif isinstance(lexer, QsciLexerPython):
            api_list = self.PYTHON_KEYWORDS + self.PYTHON_FUNCTIONS
        else:
            api_list = []
        
        # Add all APIs
        for api in api_list:
            self.apis.add(api)
        
        # Prepare APIs (compile for faster lookup)
        self._prepare_apis(lexer)
        
        # Set APIs to lexer
        lexer.setAPIs(self.apis)
    
    def _prepare_apis(self, lexer):
        """Prepare APIs with optional caching."""
        try:
            cache_dir = Path(tempfile.gettempdir()) / "taara_ide_apis"
            cache_dir.mkdir(exist_ok=True)
            
            lexer_name = "cpp" if isinstance(lexer, QsciLexerCPP) else "python"
            cache_file = cache_dir / f"{lexer_name}.api"
            
            # Always prepare first
            self.apis.prepare()
            
            # Try to save to cache
            self.apis.savePrepared(str(cache_file))
        except Exception as e:
            print(f"[AutocompleteManager] API prepare error: {e}")
            self.apis.prepare()
    
    def add_document_words(self):
        """Add words from current document to completion list."""
        if not self.apis:
            return
        
        try:
            text = self.editor.text()
            # Extract words (identifiers)
            import re
            words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text))
            
            # Filter out very short words and common keywords
            for word in words:
                if len(word) > 2:
                    self.apis.add(word)
            
            self.apis.prepare()
        except Exception as e:
            print(f"[AutocompleteManager] Document words error: {e}")
    
    def on_text_changed(self):
        """Handle text change - schedule call tip check."""
        self.calltip_timer.start(10)
    
    def _delayed_calltip_check(self):
        """Check and show call tips after text change."""
        try:
            pos = self.editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
            is_calltip_active = self.editor.SendScintilla(QsciScintilla.SCI_CALLTIPACTIVE)

            if pos > 0:
                char_before = chr(self.editor.SendScintilla(QsciScintilla.SCI_GETCHARAT, pos - 1))

                if char_before == '(':
                    func_name = self._get_function_name_before(pos - 1)
                    if func_name:
                        self._show_calltip(func_name, pos)

                elif char_before == ',':
                    if is_calltip_active:
                        self._update_calltip_highlight()
                    else:
                        self._try_restore_calltip(pos)

                elif char_before == ')':
                    # Only cancel if we've closed the outermost call paren.
                    # Walk backwards: if we find an unmatched '(' it means the tip
                    # call is still open (nested paren was closed).
                    depth = 0
                    scan = pos - 1
                    still_inside = False
                    while scan >= 0:
                        ch = chr(self.editor.SendScintilla(QsciScintilla.SCI_GETCHARAT, scan))
                        if ch == ')':
                            depth += 1
                        elif ch == '(':
                            if depth == 0:
                                still_inside = True
                                break
                            depth -= 1
                        scan -= 1

                    if not still_inside:
                        self.editor.SendScintilla(QsciScintilla.SCI_CALLTIPCANCEL)
                        self._current_calltip_text = ""
                    elif is_calltip_active:
                        self._update_calltip_highlight()

        except Exception as e:
            print(f"[AutocompleteManager] Call tip error: {e}")
    
    def _get_function_name_before(self, pos: int) -> str:
        """Get function name before the given position."""
        word_start = self.editor.SendScintilla(QsciScintilla.SCI_WORDSTARTPOSITION, pos - 1, True)
        word_end = pos
        
        if word_start < word_end:
            length = word_end - word_start
            buffer = bytes(length + 1)
            
            self.editor.SendScintilla(QsciScintilla.SCI_SETTARGETSTART, word_start)
            self.editor.SendScintilla(QsciScintilla.SCI_SETTARGETEND, word_end)
            self.editor.SendScintilla(QsciScintilla.SCI_GETTARGETTEXT, 0, buffer)
            
            return buffer.decode('utf-8', errors='ignore').rstrip('\x00')
        return ""
    
    def _show_calltip(self, func_name: str, pos: int):
        """Show call tip for the given function.

        Fast path: built-ins + document extraction show immediately.
        Slow path: CTags disk scan runs async; calltip appears when ready.
        """
        # Fast sources (no I/O)
        signature = (self.BUILTIN_SIGNATURES.get(func_name) or
                     self._extract_signature_from_document(func_name))

        if signature:
            self._display_calltip(signature, pos)
            return

        # Slow source: CTags — run async so the timer is never blocked
        ctags = self._get_ctags_handler()
        if ctags and self.editor.file_path:
            ctags.find_definition_async(
                func_name, self.editor.file_path,
                lambda defn, _fn=func_name, _pos=pos: (
                    QTimer.singleShot(0, lambda: self._on_ctags_definition(_fn, _pos, defn))
                )
            )

    def _on_ctags_definition(self, func_name: str, pos: int, definition) -> None:
        """Called on main thread when async CTags lookup completes."""
        if not definition:
            return
        sig = self._extract_signature_from_definition(func_name, definition)
        if sig:
            self._display_calltip(sig, pos)

    def _display_calltip(self, signature: str, pos: int) -> None:
        formatted = self._format_signature_with_markers(signature)
        self._current_calltip_text = formatted
        self.editor.SendScintilla(
            QsciScintilla.SCI_CALLTIPSHOW,
            pos,
            formatted.encode('utf-8')
        )
        QTimer.singleShot(10, lambda: self._highlight_parameter(0))

    def _get_ctags_handler(self):
        """Walk up parent chain to find EditorManager's ctags_handler."""
        try:
            node = self.editor._parent
            while node:
                if hasattr(node, '_editor_manager'):
                    return node._editor_manager.ctags_handler
                node = node.parent() if callable(getattr(node, 'parent', None)) else None
        except Exception:
            pass
        return None

    def _extract_signature_from_definition(self, func_name: str,
                                            definition: tuple) -> Optional[str]:
        """Read one line from disk to extract a function signature."""
        try:
            file_path, line_num = definition[0], definition[1]
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
                for i, line in enumerate(fh, 1):
                    if i == line_num:
                        line = line.strip()
                        if '(' in line and ')' in line:
                            start = line.find(func_name)
                            if start != -1:
                                rest = line[start:]
                                depth, end = 0, 0
                                for j, ch in enumerate(rest):
                                    if ch == '(':
                                        depth += 1
                                    elif ch == ')':
                                        depth -= 1
                                        if depth == 0:
                                            end = j + 1
                                            break
                                if end:
                                    return rest[:end].replace('{', '').replace(';', '').strip()
                        break
        except Exception:
            pass
        return None
    
    def _extract_signature_from_document(self, func_name: str) -> Optional[str]:
        """Extract function signature from current document."""
        try:
            text = self.editor.text()
            lines = text.split('\n')
            
            for line in lines:
                line_stripped = line.strip()
                
                if line_stripped.startswith('//') or line_stripped.startswith('/*'):
                    continue
                
                if func_name in line_stripped and '(' in line_stripped and ')' in line_stripped:
                    start = line_stripped.find(func_name)
                    if start != -1:
                        rest = line_stripped[start:]
                        paren_count = 0
                        end_pos = 0
                        
                        for i, char in enumerate(rest):
                            if char == '(':
                                paren_count += 1
                            elif char == ')':
                                paren_count -= 1
                                if paren_count == 0:
                                    end_pos = i + 1
                                    break
                        
                        if end_pos > 0:
                            signature = rest[:end_pos].replace('{', '').replace(';', '').strip()
                            return signature
        except Exception as e:
            print(f"[AutocompleteManager] Document extraction failed: {e}")
        return None
    
    def _format_signature_with_markers(self, signature: str) -> str:
        """Format signature with parameter highlight markers."""
        try:
            open_paren = signature.find('(')
            close_paren = signature.rfind(')')
            
            if open_paren == -1 or close_paren == -1:
                return signature
            
            func_name = signature[:open_paren + 1]
            params_str = signature[open_paren + 1:close_paren]
            
            if not params_str.strip():
                return signature
            
            params = self._split_parameters(params_str)
            
            marked_params = []
            for param in params:
                param = param.strip()
                if param:
                    marked_params.append(f"\x01{param}\x02")
            
            return func_name + ', '.join(marked_params) + ')'
        except Exception as e:
            print(f"[AutocompleteManager] Formatting error: {e}")
            return signature
    
    def _split_parameters(self, params_str: str) -> list:
        """Split parameter string by commas, handling nested parentheses."""
        params = []
        current_param = ""
        paren_depth = 0
        
        for char in params_str:
            if char == '(':
                paren_depth += 1
                current_param += char
            elif char == ')':
                paren_depth -= 1
                current_param += char
            elif char == ',' and paren_depth == 0:
                params.append(current_param.strip())
                current_param = ""
            else:
                current_param += char
        
        if current_param.strip():
            params.append(current_param.strip())
        
        return params
    
    def _highlight_parameter(self, param_index: int):
        """Highlight a specific parameter in the active call tip."""
        try:
            if not self.editor.SendScintilla(QsciScintilla.SCI_CALLTIPACTIVE):
                return
            
            if not self._current_calltip_text:
                return
            
            char_start, char_end = self._find_parameter_range(self._current_calltip_text, param_index)
            
            if char_start >= 0 and char_end > char_start:
                self.editor.SendScintilla(
                    QsciScintilla.SCI_CALLTIPSETHLT,
                    char_start,
                    char_end
                )
        except Exception as e:
            print(f"[AutocompleteManager] Highlight parameter error: {e}")
    
    def _find_parameter_range(self, calltip_text: str, param_index: int) -> tuple:
        """Find the character range of a parameter in the call tip text."""
        try:
            marker_count = 0
            start_pos = -1
            end_pos = -1
            
            i = 0
            while i < len(calltip_text):
                if calltip_text[i] == '\x01':
                    if marker_count == param_index:
                        start_pos = i
                    marker_count += 1
                elif calltip_text[i] == '\x02':
                    if start_pos >= 0 and end_pos == -1:
                        end_pos = i + 1
                        break
                i += 1
            
            return (start_pos, end_pos)
        except Exception as e:
            print(f"[AutocompleteManager] Find parameter range error: {e}")
            return (-1, -1)
    
    def _update_calltip_highlight(self):
        """Update call tip to highlight current parameter."""
        try:
            if not self.editor.SendScintilla(QsciScintilla.SCI_CALLTIPACTIVE):
                return
            
            pos = self.editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
            param_index = self._get_current_parameter_index(pos)
            
            if self._current_calltip_text:
                char_start, char_end = self._find_parameter_range(self._current_calltip_text, param_index)
                if char_start >= 0 and char_end > char_start:
                    self.editor.SendScintilla(
                        QsciScintilla.SCI_CALLTIPSETHLT,
                        char_start,
                        char_end
                    )
        except Exception as e:
            print(f"[AutocompleteManager] Update highlight error: {e}")
    
    def _get_current_parameter_index(self, pos: int) -> int:
        """Get the index of current parameter (0-based)."""
        try:
            paren_pos = pos - 1
            paren_depth = 0
            comma_count = 0
            
            while paren_pos >= 0:
                char = chr(self.editor.SendScintilla(QsciScintilla.SCI_GETCHARAT, paren_pos))
                
                if char == ')':
                    paren_depth += 1
                elif char == '(':
                    if paren_depth == 0:
                        break
                    paren_depth -= 1
                elif char == ',' and paren_depth == 0:
                    comma_count += 1
                
                paren_pos -= 1
            
            return comma_count
        except Exception as e:
            print(f"[AutocompleteManager] Parameter index error: {e}")
            return 0
    
    def _try_restore_calltip(self, current_pos: int):
        """Try to restore call tip if it was accidentally closed."""
        try:
            pos = current_pos - 1
            paren_depth = 0
            
            while pos >= 0:
                char = chr(self.editor.SendScintilla(QsciScintilla.SCI_GETCHARAT, pos))
                
                if char == ')':
                    paren_depth += 1
                elif char == '(':
                    if paren_depth == 0:
                        func_name = self._get_function_name_before(pos)
                        if func_name:
                            self._show_calltip(func_name, pos + 1)
                            QTimer.singleShot(20, self._update_calltip_highlight)
                        break
                    else:
                        paren_depth -= 1
                pos -= 1
        except Exception as e:
            print(f"[AutocompleteManager] Restore call tip error: {e}")

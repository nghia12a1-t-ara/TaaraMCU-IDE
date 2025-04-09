from PyQt6.Qsci         import QsciScintilla, QsciLexerCPP, QsciLexerPython
from PyQt6.QtGui        import QFont, QColor, QMouseEvent
from PyQt6.QtCore       import QTimer, Qt
from PyQt6.QtWidgets    import QMessageBox
from pathlib            import Path
import json
import os

class CodeEditor(QsciScintilla):
    def __init__(self, parent=None, theme_name="Khaki", language="CPP"):
        super().__init__(parent)
        self.GUI = parent

        # Font configuration
        self.text_font = QFont("Consolas", 16)
        self.margin_font = QFont("Consolas", 18)  # Fixed size for margin

        # Lexer configuration
        self.lexer = QsciLexerCPP()
        self.lexer.setDefaultFont(self.text_font)

        # Set language for file
        # self.set_language(language)

        # Load and apply theme
        self.theme = self.load_theme(theme_name.lower() + ".json")
        self.apply_theme()

        # Apply font to all styles
        for style in range(128):
            self.lexer.setFont(self.text_font, style)

        # Apply lexer to QScintilla
        self.setLexer(self.lexer)

        # Line number margin configuration
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")  # Width for line numbers
        self.setMarginsForegroundColor(QColor("#2B2B2B"))  # Dark gray for line numbers
        self.setMarginsBackgroundColor(QColor("#D3CBB7"))  # Darker background for margin
        self.setMarginsFont(self.margin_font)

        # Add separator line after line numbers
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 20)  # Width of separator

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

        # Edit Action from User
        self.textChanged.connect(self.on_text_changed)

        # Set the default page step for horizontal scroll bar
        self.horizontalScrollBar().setSingleStep(20)  # Adjust the step size as needed
        self.horizontalScrollBar().setPageStep(100)    # Set the page step size

        self.setMouseTracking(True)  # Enable mouse tracking
        self.last_highlighted_word = None  # To keep track of the last highlighted word

        # Set auto completion source
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)  # Set to AcsAll
        self.setAutoCompletionThreshold(2)  # Set threshold to 2

        # Enable Call Tips
        self.setCallTipsVisible(3)  # Number of call tips displayed at the same time
        self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsContext)  # Display in context
        self.setCallTipsPosition(QsciScintilla.CallTipsPosition.CallTipsAboveText)  # Display above the input line
        self.setCallTipsBackgroundColor(QColor("#222831"))  # Background color
        self.setCallTipsForegroundColor(QColor("#EEEEEE"))  # Text color
        self.setCallTipsHighlightColor(QColor("#00ADB5"))   # Highlight color

        # Configure Indicator for Highlight
        self.highlight_indicator = 8  # ID indicator (from 0-31)
        self.SendScintilla(self.SCI_INDICSETSTYLE, self.highlight_indicator, QsciScintilla.INDIC_BOX)
        color = QColor("#FF5733")  # Orange color
        color_int = (color.red() << 16) | (color.green() << 8) | color.blue()
        self.SendScintilla(self.SCI_INDICSETFORE, self.highlight_indicator, color_int)

        # Connect event when cursor moves
        self.cursorPositionChanged.connect(self.highlight_current_word)

        # Set up Hotspot style for clickable keywords
        HOTSPOT_STYLE = 10
        self.SendScintilla(QsciScintilla.SCI_STYLESETHOTSPOT, HOTSPOT_STYLE, True)

        # Create timer for deferred updates
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.deferred_update_status_bar)
        self.cursorPositionChanged.connect(self.schedule_update)
        self.textChanged.connect(self.schedule_update)

        # Add cache variable for tags
        self.tags_cache = {}  # Store tags content: {word: (file_path, line_number)}
        self.last_modified = None  # Last modified time of the source file

    def schedule_update(self):
        self.update_timer.start(100)  # Delay 100ms

    def deferred_update_status_bar(self):
        self.GUI.update_status_bar()  # Call the function to update the status bar

    def on_text_changed(self):
        """Handle text changes in the editor"""
        self.setModified(True)

    def maintain_margin_font(self):
        """Keep margin font size fixed regardless of zoom level"""
        self.setMarginsFont(self.margin_font)
        # Recalculate margin width to accommodate the fixed font size
        width = self.fontMetrics().horizontalAdvance("0000")
        self.setMarginWidth(0, width)

    def zoomIn(self, range=1):
        """Override zoom in to maintain margin font size"""
        super().zoomIn(range)
        self.maintain_margin_font()

    def zoomOut(self, range=1):
        """Override zoom out to maintain margin font size"""
        super().zoomOut(range)
        self.maintain_margin_font()

    def wheelEvent(self, event):
        """Override wheel event to handle Ctrl+Wheel zoom"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomIn()
            else:
                self.zoomOut()
            event.accept()
        else:
            super().wheelEvent(event)

    def load_theme(self, theme_file):
        """Load theme from JSON file"""
        try:
            script_dir = Path(__file__).parent
            theme_path = script_dir / "themes" / theme_file

            with open(theme_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            return None

    def apply_theme(self):
        """Apply the loaded theme"""
        if not self.theme:
            return

        # Get colors from theme
        colors = self.theme.get("colors", {})
        token_colors = self.theme.get("tokenColors", [])

        # Set editor background and foreground
        editor_bg = colors.get("editor.background", "#D7D7AF")
        editor_fg = colors.get("editor.foreground", "#5F5F00")
        self.lexer.setDefaultPaper(QColor(editor_bg))
        self.lexer.setDefaultColor(QColor(editor_fg))

        # Map token colors to Scintilla styles
        style_map = {
            "comment": QsciLexerCPP.Comment,
            "string": QsciLexerCPP.DoubleQuotedString,
            "constant.numeric": QsciLexerCPP.Number,
            "keyword": QsciLexerCPP.Keyword,
            "storage": QsciLexerCPP.KeywordSet2,
            "entity.name.function": QsciLexerCPP.GlobalClass,
            "meta.preprocessor": QsciLexerCPP.PreProcessor
        }

        # Apply token colors
        for token in token_colors:
            scope = token.get("scope", "")
            settings = token.get("settings", {})

            # Handle both string and list scopes
            scopes = [scope] if isinstance(scope, str) else scope

            for scope in scopes:
                if scope in style_map:
                    style = style_map[scope]
                    if "foreground" in settings:
                        self.lexer.setColor(QColor(settings["foreground"]), style)
                    if "background" in settings:
                        self.lexer.setPaper(QColor(settings["background"]), style)

        # Set editor UI colors
        self.setCaretLineBackgroundColor(QColor(colors.get("editor.lineHighlightBackground", "#BFBF97")))
        self.setCaretForegroundColor(QColor(colors.get("editorCursor.foreground", "#4D4D4D")))
        self.setSelectionBackgroundColor(QColor(colors.get("editor.selectionBackground", "#D7FF87")))
        self.setSelectionForegroundColor(QColor(editor_fg))

        # Set margin colors (darker theme)
        self.setMarginsForegroundColor(QColor("#2B2B2B"))  # Dark gray for line numbers
        self.setMarginsBackgroundColor(QColor("#D3CBB7"))  # Darker khaki for margin background

        # Set indent guides color
        indent_guide_color = colors.get("editorIndentGuide.background", "#586E7580")
        self.setIndentationGuidesBackgroundColor(QColor(indent_guide_color))

        # Set whitespace color
        whitespace_color = colors.get("editorWhitespace.foreground", "#586E7580")
        self.setWhitespaceForegroundColor(QColor(whitespace_color))

        # Apply background color to all styles that don't have specific backgrounds
        for style in range(128):
            if not self.lexer.paper(style).isValid():
                self.lexer.setPaper(QColor(editor_bg), style)

    def comment_lines(self):
        """Comment or uncomment the selected lines or the current line."""
        # Get the cursor position and selection
        start_pos = self.SendScintilla(QsciScintilla.SCI_GETSELECTIONSTART)
        end_pos = self.SendScintilla(QsciScintilla.SCI_GETSELECTIONEND)

        # Determine the first and last lines of the selection
        start_line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, start_pos)
        end_line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, end_pos)

        # If no text is selected, only take the line containing the cursor
        if start_pos == end_pos:
            start_line = end_line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, start_pos)

        # Check if all selected lines are commented or not
        all_commented = True
        lines = []

        for line in range(start_line, end_line + 1):
            line_text = self.text(line).rstrip()
            lines.append(line_text)
            if not line_text.lstrip().startswith("//"):
                all_commented = False

        # Process comment/uncomment each line
        new_lines = []
        for line_text in lines:
            if all_commented:
                new_lines.append(line_text.lstrip("//").lstrip())  # Remove comment
            else:
                new_lines.append("// " + line_text)  # Add comment

        # Convert new_text (str) to bytes (UTF-8)
        new_text = "\n".join(new_lines)
        new_text_bytes = new_text.encode("utf-8")

        # Replace content with new text
        self.SendScintilla(QsciScintilla.SCI_SETTARGETSTART, self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, start_line))
        self.SendScintilla(QsciScintilla.SCI_SETTARGETEND, self.SendScintilla(QsciScintilla.SCI_GETLINEENDPOSITION, end_line))
        self.SendScintilla(QsciScintilla.SCI_REPLACETARGET, len(new_text_bytes), new_text_bytes)

    def get_word_at_position(self, position):
        """Get the entire word at position in the editor, handling Unicode correctly."""
        # Determine the boundaries of the word at position
        start_pos = self.SendScintilla(self.SCI_WORDSTARTPOSITION, position, True)
        end_pos = self.SendScintilla(self.SCI_WORDENDPOSITION, position, True)

        # If the position is invalid or not within a word
        if start_pos == end_pos:
            return ""

        # Get the length of the entire text
        text_length = self.SendScintilla(self.SCI_GETTEXTLENGTH)

        # Check boundaries
        if start_pos < 0 or end_pos > text_length or start_pos > end_pos:
            return ""

        # Create a buffer for the text segment
        length = end_pos - start_pos + 1  # +1 for the null character
        buffer = bytes(length)

        # Set the position range to get the text segment
        self.SendScintilla(self.SCI_SETTARGETSTART, start_pos)
        self.SendScintilla(self.SCI_SETTARGETEND, end_pos)

        # Get the text segment directly from Scintilla as bytes
        self.SendScintilla(self.SCI_GETTARGETTEXT, 0, buffer)

        # Convert from bytes to Unicode string
        word = buffer.decode('utf-8', errors='ignore').rstrip('\x00').strip()
        return word

    def highlight_current_word(self):
        """Highlight all occurrences of the current word in C/C++"""
        # Set the current indicator
        self.SendScintilla(self.SCI_SETINDICATORCURRENT, self.highlight_indicator)
        
        # Clear old highlight
        self.SendScintilla(self.SCI_INDICATORCLEARRANGE, 0, self.length())

        # Get the current cursor position
        pos = self.SendScintilla(self.SCI_GETCURRENTPOS)
        word = self.get_word_at_position(pos)

        # Check if the word is valid (only contains letters, numbers, or underscore)
        if not word or not any(c.isalnum() or c == '_' for c in word):
            return

        # Set search flags with word boundaries
        self.SendScintilla(self.SCI_SETSEARCHFLAGS, QsciScintilla.SCFIND_WHOLEWORD)
        
        # Get the entire text
        full_text = self.text()
        text_length = len(full_text)
        search_pos = 0

        # Find and highlight all occurrences
        while search_pos < text_length:
            self.SendScintilla(self.SCI_SETTARGETSTART, search_pos)
            self.SendScintilla(self.SCI_SETTARGETEND, text_length)
            
            found_pos = self.SendScintilla(self.SCI_SEARCHINTARGET, len(word), word.encode('utf-8'))
            if found_pos == -1:  # No more words found
                break
            
            # Highlight the found word
            self.SendScintilla(self.SCI_INDICATORFILLRANGE, found_pos, len(word))
            search_pos = found_pos + len(word)  # Continue searching from the next position

        # Restore search state (if needed)
        self.SendScintilla(self.SCI_SETSEARCHFLAGS, 0)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            y = event.pos().y()
            # Calculate the position from mouse coordinates
            position = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, x, y)
            # Set the cursor at the exact position
            line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, position)
            index = position - self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
            self.setCursorPosition(line, index)

            # Check Ctrl+Click
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                word = self.get_word_at_position(position)
                if word:
                    self.gotoDefinition(word)
                    return  # Prevent the default event from being called if jumping to definition

        super().mousePressEvent(event)

    def gotoDefinition(self, word):
        """Find the keyword definition in .tags files, first in current file, then in project."""
        # Check if the current file exists
        if not hasattr(self, 'file_path') or not self.file_path:
            QMessageBox.warning(self, "CTags Error", "No file path available for this editor!")
            return

        # .tags file of the current file (e.g. main.c.tags)
        file_tag = f"{self.file_path}.tags"

        # project.tags file of the project directory
        project_dir = self.GUI.project_view.get_project_directory() if self.GUI.project_view else None
        project_tag = str(Path(project_dir) / "project.tags") if project_dir else None

        # Check if the current file has been modified
        if self.isModified() or not self.tags_cache:
            # Only regenerate tags if the file has changed or the cache is empty
            if not os.path.exists(file_tag):
                if not self.GUI.ctags_handler.generate_ctags():
                    QMessageBox.warning(self, "CTags Error", "Failed to generate tags file!")
                    return

            # Create a list of .tags files to update
            tag_files = [file_tag]
            if project_tag and os.path.exists(project_tag):
                tag_files.append(project_tag)

            # Update self.tags_cache with both file_tag and project_tag
            self.update_tags_cache(tag_files)

        # Search for definition in self.tags_cache
        definition = self.tags_cache.get(word)
        if definition:
            file_path, line_number, column = definition
            self.open_file_at_line(file_path, line_number, column)
            return

        # If not found, display an error message
        QMessageBox.warning(self, "CTags", f"Definition for '{word}' not found!")

    def update_tags_cache(self, tag_files):
        """Update cache from multiple .tags files, including column position of the symbol."""
        self.tags_cache.clear()  # Clear the cache once before updating
        for tag_file in tag_files:
            if not os.path.exists(tag_file):
                continue
            try:
                with open(tag_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("!"):  # Skip comment
                            continue
                        parts = line.strip().split("\t")
                        if len(parts) < 3:
                            continue
                        symbol = parts[0]
                        file_path = parts[1]
                        line_info = parts[2]

                        # Determine tag type (if any)
                        tag_type = parts[3] if len(parts) > 3 else 'unknown'

                        # Process definition
                        line_number = None
                        column = 0
                        if tag_type == 'd':  # Macro case (#define)
                            # Find line information from the "line:" field
                            for field in parts:
                                if field.startswith("line:"):
                                    line_number = int(field.split(":")[1])
                                    break
                            if line_number:
                                # Read the line from the file to find the column position
                                with open(file_path, "r", encoding="utf-8") as source_file:
                                    for i, source_line in enumerate(source_file, 1):
                                        if i == line_number:
                                            column = source_line.find(symbol)
                                            if column == -1:
                                                column = 0
                                            break
                            else:
                                # If there's no "line:", use the pattern from line_info
                                if line_info.startswith("/^") and line_info.endswith("$/;\""):
                                    pattern = line_info[2:-4].strip()
                                    with open(file_path, "r", encoding="utf-8") as source_file:
                                        for i, source_line in enumerate(source_file, 1):
                                            if pattern in source_line.strip():
                                                line_number = i
                                                column = source_line.find(symbol)
                                                if column == -1:
                                                    column = 0
                                                break
                        elif line_info.startswith("/^") and line_info.endswith("$/;\""):
                            pattern = line_info[2:-4].strip()
                            with open(file_path, "r", encoding="utf-8") as source_file:
                                for i, source_line in enumerate(source_file, 1):
                                    if pattern in source_line.strip():
                                        line_number = i
                                        column = source_line.find(symbol)
                                        if column == -1:
                                            column = 0
                                        break
                        elif line_info.isdigit():
                            line_number = int(line_info)
                            # Read the line from the file to find the column position
                            with open(file_path, "r", encoding="utf-8") as source_file:
                                for i, source_line in enumerate(source_file, 1):
                                    if i == line_number:
                                        column = source_line.find(symbol)
                                        if column == -1:
                                            column = 0
                                        break

                        if line_number is not None:
                            self.tags_cache[symbol] = (file_path, line_number, column)
            except Exception as e:
                return

    def open_file_at_line(self, file_path, line_number, column=0):
        """Open the file and jump to the corresponding line and column. Return True if successful."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "CTags", f"File '{file_path}' does not exist.")
            return False

        # Check if the file is already open
        for i in range(self.GUI.tabWidget.count()):
            editor = self.GUI.tabWidget.widget(i)
            if hasattr(editor, 'file_path') and editor.file_path == file_path:
                self.GUI.tabWidget.setCurrentIndex(i)
                editor.setCursorPosition(line_number - 1, column)  # Set the cursor at the correct column
                editor.ensureLineVisible(line_number - 1)
                return True

        # If not open, open a new file
        editor = self.GUI.open_file(file_path)
        if editor:
            editor.setCursorPosition(line_number - 1, column)  # Set the cursor at the correct column
            editor.ensureLineVisible(line_number - 1)
            return True
        else:
            return False

    def set_language(self, language):
        if language == "Python":
            self.lexer = QsciLexerPython()
        elif language == "CPP":
            self.lexer = QsciLexerCPP()
        else:
            self.lexer = None
        if self.lexer:
            self.lexer.setDefaultFont(self.text_font)
            self.setLexer(self.lexer)
            self.apply_theme()



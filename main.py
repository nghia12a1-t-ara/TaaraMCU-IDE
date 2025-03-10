import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget,
    QFileDialog, QMessageBox, QToolBar,
    QDialog, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QCheckBox, QGroupBox, QRadioButton,
    QWidget, QMenu, QStatusBar
)
from PyQt6.QtGui import (
    QIcon,
    QAction,
    QFont,
    QColor,
    QMouseEvent
)
from PyQt6.QtCore import (
    Qt,
    QTimer
)
from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerCPP,
    QsciLexerPython
)
import chardet
from ctags_handler import CtagsHandler
import os
import subprocess
from project_view import ProjectView, FunctionList
from Terminal import Terminal
from settings_manager import SettingsManager

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

# Add this class for the Find Dialog
class FindDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Find")
        self.setFixedWidth(450)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_find_tab(), "Find")
        self.tab_widget.addTab(self.create_replace_tab(), "Replace")  # Added Replace tab
        self.tab_widget.addTab(self.create_find_in_files_tab(), "Find in Files")

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def create_find_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Find what
        find_layout = QHBoxLayout()
        find_label = QLabel("Find what:")
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self.reset_search)
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.find_input)

        # Buttons group
        buttons_layout = QHBoxLayout()

        # Left side buttons
        left_buttons = QVBoxLayout()
        self.find_next_button = QPushButton("Find Next")
        self.find_next_button.clicked.connect(self.find_next)
        self.count_button = QPushButton("Count")
        self.count_button.clicked.connect(self.count_occurrences)
        left_buttons.addWidget(self.find_next_button)
        left_buttons.addWidget(self.count_button)

        # Right side buttons
        right_buttons = QVBoxLayout()
        self.find_all_current_button = QPushButton("Find All in Current Document")
        self.find_all_current_button.clicked.connect(self.find_all_current)
        self.find_all_opened_button = QPushButton("Find All in All Opened Documents")
        self.find_all_opened_button.clicked.connect(self.find_all_opened)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        right_buttons.addWidget(self.find_all_current_button)
        right_buttons.addWidget(self.find_all_opened_button)
        right_buttons.addWidget(self.close_button)

        buttons_layout.addLayout(left_buttons)
        buttons_layout.addLayout(right_buttons)

        # Search options
        options_group = QGroupBox("Search Mode")
        options_layout = QVBoxLayout()

        # Search mode options
        self.normal_mode = QRadioButton("Normal")
        self.normal_mode.setChecked(True)
        self.extended_mode = QRadioButton("Extended (\\n, \\r, \\t, \\0, ...)")
        self.regex_mode = QRadioButton("Regular expression")

        options_layout.addWidget(self.normal_mode)
        options_layout.addWidget(self.extended_mode)
        options_layout.addWidget(self.regex_mode)
        options_group.setLayout(options_layout)

        # Checkboxes
        checks_layout = QVBoxLayout()
        self.backward_check = QCheckBox("Backward direction")
        self.match_case = QCheckBox("Match case")
        self.whole_word = QCheckBox("Match whole word only")
        self.wrap_around = QCheckBox("Wrap around")
        self.wrap_around.setChecked(True)

        checks_layout.addWidget(self.backward_check)
        checks_layout.addWidget(self.match_case)
        checks_layout.addWidget(self.whole_word)
        checks_layout.addWidget(self.wrap_around)

        # Transparency options
        trans_group = QGroupBox("Transparency")
        trans_layout = QVBoxLayout()
        self.transparency_check = QCheckBox("Enable")
        self.on_losing_focus = QRadioButton("On losing focus")
        self.on_losing_focus.setChecked(True)
        self.always = QRadioButton("Always")

        trans_layout.addWidget(self.transparency_check)
        trans_layout.addWidget(self.on_losing_focus)
        trans_layout.addWidget(self.always)
        trans_group.setLayout(trans_layout)

        # Add all to main layout
        layout.addLayout(find_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(options_group)
        layout.addLayout(checks_layout)
        layout.addWidget(trans_group)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def create_replace_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Find and Replace inputs
        find_layout = QHBoxLayout()
        find_label = QLabel("Find what:")
        self.replace_find_input = QLineEdit()
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.replace_find_input)

        replace_layout = QHBoxLayout()
        replace_label = QLabel("Replace with:")
        self.replace_input = QLineEdit()
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_input)

        # Buttons
        buttons_layout = QVBoxLayout()
        self.replace_find_next_btn = QPushButton("Find Next")
        self.replace_find_next_btn.clicked.connect(self.replace_find_next)
        self.replace_button = QPushButton("Replace")
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button = QPushButton("Replace All")
        self.replace_all_button.clicked.connect(self.replace_all)

        buttons_layout.addWidget(self.replace_find_next_btn)
        buttons_layout.addWidget(self.replace_button)
        buttons_layout.addWidget(self.replace_all_button)

        # Add all to main layout
        layout.addLayout(find_layout)
        layout.addLayout(replace_layout)
        layout.addLayout(buttons_layout)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def create_find_in_files_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Find input
        find_layout = QHBoxLayout()
        find_label = QLabel("Find what:")
        self.find_files_input = QLineEdit()
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.find_files_input)

        # Directory input
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Directory:")
        self.dir_input = QLineEdit()
        self.browse_button = QPushButton("...")
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_button)

        # Filters
        filters_layout = QHBoxLayout()
        filters_label = QLabel("Filters:")
        self.filters_input = QLineEdit()
        self.filters_input.setPlaceholderText("*.txt, *.py")
        filters_layout.addWidget(filters_label)
        filters_layout.addWidget(self.filters_input)

        # Find button
        self.find_files_button = QPushButton("Find All")

        # Add all to main layout
        layout.addLayout(find_layout)
        layout.addLayout(dir_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.find_files_button)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def reset_search(self):
        editor = self.parent.get_current_editor()
        if editor:
            editor.clearIndicatorRange(0, 0, editor.lines(),
                                    len(editor.text()), 0)

    def find_next(self):
        """Find next occurrence of the search text"""
        editor = self.parent.get_current_editor()
        if not editor:
            return

        text = self.find_input.text()
        if not text:
            return

        # Get current position
        line, index = editor.getCursorPosition()

        # If there's a selection, start from the end of the selection
        if editor.hasSelectedText():
            sel_line, sel_index, _, _ = editor.getSelection()
            if (sel_line, sel_index) == (line, index):
                line, index = editor.getSelection()[2:]

        try:
            # Set search flags
            search_flags = 0
            if self.regex_mode.isChecked():
                search_flags |= QsciScintilla.SCFIND_REGEXP
                search_flags |= QsciScintilla.SCFIND_POSIX  # More standard regex behavior
            if self.match_case.isChecked():
                search_flags |= QsciScintilla.SCFIND_MATCHCASE
            if self.whole_word.isChecked():
                search_flags |= QsciScintilla.SCFIND_WHOLEWORD

            # Set the search flags
            editor.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, search_flags)

            found = editor.findFirst(
                text,
                self.regex_mode.isChecked(),      # Regular expression
                self.match_case.isChecked(),      # Case sensitive
                self.whole_word.isChecked(),      # Whole word
                self.wrap_around.isChecked(),     # Wrap around
                not self.backward_check.isChecked(),  # Forward/backward
                line,
                index,
                True                              # Move cursor and show
            )

            if not found:
                QMessageBox.information(self, "Find", "No more occurrences found.")

        except Exception as e:
            QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {str(e)}")

    def count_occurrences(self):
        """Count all occurrences of the search text"""
        editor = self.parent.get_current_editor()
        if not editor:
            return

        text = self.find_input.text()
        if not text:
            QMessageBox.information(self, "Count", "Please enter text to search for.")
            return

        # Save current position
        original_line, original_index = editor.getCursorPosition()

        try:
            # Get the full text content
            full_text = editor.text()
            count = 0

            if self.regex_mode.isChecked():
                try:
                    # Set up regex flags
                    flags = re.MULTILINE  # Always use multiline mode
                    if not self.match_case.isChecked():
                        flags |= re.IGNORECASE

                    # Compile and find all matches
                    pattern = re.compile(text, flags)
                    matches = pattern.finditer(full_text)
                    count = sum(1 for _ in matches)

                except re.error as e:
                    QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {str(e)}")
                    return

            else:
                # Normal search
                if self.whole_word.isChecked():
                    import re
                    pattern = r'\b' + re.escape(text) + r'\b'
                    flags = re.MULTILINE
                    if not self.match_case.isChecked():
                        flags |= re.IGNORECASE
                    count = len(re.findall(pattern, full_text, flags))
                else:
                    if self.match_case.isChecked():
                        count = full_text.count(text)
                    else:
                        count = full_text.lower().count(text.lower())

            # Show result
            QMessageBox.information(self, "Count", f"Found {count} occurrence(s)")

        finally:
            # Restore original position
            editor.setCursorPosition(original_line, original_index)

    def find_all_current(self):
        """Find all occurrences in current document and highlight them"""
        editor = self.parent.get_current_editor()
        if not editor:
            return

        text = self.find_input.text()
        if not text:
            QMessageBox.information(self, "Find All", "Please enter text to search for.")
            return

        # Clear previous highlights
        editor.clearIndicatorRange(0, 0, editor.lines(), len(editor.text()), 0)

        try:
            # Get the full text content
            full_text = editor.text()
            matches = []

            if self.regex_mode.isChecked():
                try:
                    import re
                    # Set up regex flags
                    flags = re.MULTILINE
                    if not self.match_case.isChecked():
                        flags |= re.IGNORECASE

                    pattern = re.compile(text, flags)
                    matches = list(pattern.finditer(full_text))

                except re.error as e:
                    QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {str(e)}")
                    return
            else:
                # Normal search
                search_text = text
                content = full_text

                if not self.match_case.isChecked():
                    search_text = text.lower()
                    content = full_text.lower()

                start = 0
                while True:
                    index = content.find(search_text, start)
                    if index == -1:
                        break

                    # Check for whole word match if needed
                    if self.whole_word.isChecked():
                        # Check word boundaries
                        before = index == 0 or not content[index-1].isalnum()
                        after = (index + len(search_text) >= len(content) or
                                not content[index + len(search_text)].isalnum())
                        if before and after:
                            matches.append((index, index + len(search_text)))
                    else:
                        matches.append((index, index + len(search_text)))

                    start = index + 1

            # Highlight all matches
            for match in matches:
                if isinstance(match, re.Match):
                    start, end = match.span()
                else:
                    start, end = match

                # Convert string index to line and column
                line_from = full_text.count('\n', 0, start)
                line_to = full_text.count('\n', 0, end)

                # Find column positions
                last_nl = full_text.rfind('\n', 0, start)
                index_from = start - (last_nl + 1 if last_nl != -1 else 0)

                last_nl = full_text.rfind('\n', 0, end)
                index_to = end - (last_nl + 1 if last_nl != -1 else 0)

                # Highlight the match
                editor.fillIndicatorRange(line_from, index_from, line_to, index_to, 0)

            # Show results
            count = len(matches)
            if count > 0:
                QMessageBox.information(self, "Find All", f"Found {count} occurrence(s)")
            else:
                QMessageBox.information(self, "Find All", "No matches found")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")

    def find_all_opened(self):
        """Find all occurrences in all opened documents"""
        if not self.parent.tabWidget.count():
            return

        text = self.find_input.text()
        if not text:
            return

        total_count = 0
        results = []

        # Search in all tabs
        for i in range(self.parent.tabWidget.count()):
            editor = self.parent.tabWidget.widget(i)
            file_name = self.parent.tabWidget.tabText(i)

            # Save current position
            original_line, original_index = editor.getCursorPosition()

            try:
                # Start from the beginning
                editor.setCursorPosition(0, 0)

                # Set search flags
                search_flags = 0
                if self.regex_mode.isChecked():
                    search_flags |= QsciScintilla.SCFIND_REGEXP
                    search_flags |= QsciScintilla.SCFIND_POSIX
                if self.match_case.isChecked():
                    search_flags |= QsciScintilla.SCFIND_MATCHCASE
                if self.whole_word.isChecked():
                    search_flags |= QsciScintilla.SCFIND_WHOLEWORD

                editor.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, search_flags)

                # Find first occurrence
                found = editor.findFirst(
                    text,
                    self.regex_mode.isChecked(),
                    self.match_case.isChecked(),
                    self.whole_word.isChecked(),
                    True,  # wrap
                    True,  # forward
                    0, 0,  # from start
                    False  # don't move cursor
                )

                count = 0
                while found:
                    # Get the selection range
                    line_from, index_from, line_to, index_to = editor.getSelection()

                    # Highlight the found text
                    editor.fillIndicatorRange(line_from, index_from, line_to, index_to, 0)

                    count += 1
                    found = editor.findNext()

                if count > 0:
                    results.append(f"{file_name}: {count} occurrence(s)")
                    total_count += count

            finally:
                # Restore original position
                editor.setCursorPosition(original_line, original_index)

        # Show results
        if total_count > 0:
            result_text = "Found matches in:\n" + "\n".join(results)
            QMessageBox.information(self, "Find All", f"{result_text}\n\nTotal: {total_count} occurrence(s)")
        else:
            QMessageBox.information(self, "Find All", "No matches found in any open documents")

    def replace_find_next(self):
        """Find the next occurrence of the text to replace."""
        editor = self.parent.get_current_editor()
        if not editor or not self.replace_find_input.text():
            return

        text = self.replace_find_input.text()
        line, index = editor.getCursorPosition()

        # If there's a selection, start from the end of the selection
        if editor.hasSelectedText():
            sel_line, sel_index, _, _ = editor.getSelection()
            if (sel_line, sel_index) == (line, index):
                line, index = editor.getSelection()[2:]

        # Search based on the options from the Find tab
        found = editor.findFirst(
            text,
            self.regex_mode.isChecked(),
            self.match_case.isChecked(),
            self.whole_word.isChecked(),
            self.wrap_around.isChecked(),
            not self.backward_check.isChecked(),
            line,
            index,
            True
        )

        if not found:
            QMessageBox.information(self, "Replace", "No more occurrences found.")

    def replace(self):
        """Replace the current occurrence and find the next one."""
        editor = self.parent.get_current_editor()
        if not editor or not self.replace_find_input.text():
            return

        text = self.replace_find_input.text()
        replacement = self.replace_input.text()

        # If there's a matching selected text, replace it
        if editor.hasSelectedText():
            selected_text = editor.selectedText()
            if (self.match_case.isChecked() and selected_text == text) or \
               (not self.match_case.isChecked() and selected_text.lower() == text.lower()):
                editor.replace(replacement)

        # Find the next occurrence
        self.replace_find_next()

    def replace_all(self):
        """Replace all occurrences in the text."""
        editor = self.parent.get_current_editor()
        if not editor or not self.replace_find_input.text():
            return

        text = self.replace_find_input.text()
        replacement = self.replace_input.text()

        # Start from the beginning of the text
        editor.setCursorPosition(0, 0)
        count = 0

        # Find and replace all
        found = editor.findFirst(
            text,
            self.regex_mode.isChecked(),
            self.match_case.isChecked(),
            self.whole_word.isChecked(),
            False,  # No wrap to avoid looping
            True,   # Forward direction
            0, 0,   # Start from the beginning
            False   # Don't move cursor
        )

        while found:
            # Replace the found text
            editor.replace(replacement)
            count += 1
            found = editor.findNext()  # Find the next occurrence

        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrence(s).")

class GoToLineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Go To...")

        # Create layout
        layout = QVBoxLayout()

        # Current line label
        self.current_line_label = QLabel(f"You are here: Line {parent.get_current_editor().getCursorPosition()[0] + 1}")
        layout.addWidget(self.current_line_label)

        # Line number input
        self.line_input = QLineEdit()
        layout.addWidget(QLabel("You want to go to:"))
        layout.addWidget(self.line_input)

        # Buttons
        button_layout = QHBoxLayout()
        go_button = QPushButton("Go")
        go_button.clicked.connect(self.go_to_line)
        button_layout.addWidget(go_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def go_to_line(self):
        """Navigate to the specified line number."""
        line_number = self.line_input.text()
        if not line_number.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid line number.")
            return

        line_number = int(line_number) - 1  # Convert to zero-based index
        editor = self.parent().get_current_editor()

        if editor:
            total_lines = editor.lines()
            if line_number < 0 or line_number >= total_lines:
                QMessageBox.warning(self, "Out of Range", f"You can't go further than: {total_lines}")
                return

            editor.setCursorPosition(line_number, 0)  # Move cursor to the specified line
            self.accept()  # Close the dialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nghia Taarabt Notepad++")
        self.setGeometry(200, 100, 1000, 600)

        # Set window icon
        icon_path = "icons\\logoIcon.ico"
        self.setWindowIcon(QIcon(icon_path))

        # Initialize find dialog
        self.find_dialog = None

        # UI Manager Variables
        self._showallchar   = False
        self._wordwrap      = False

        self.ctags_handler  = None

        # Initialize Tab File Manager
        self.current_tab_index = -1

        # Add Function List
        self.function_list = FunctionList(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.function_list)

        # Initialize TabWidget with custom styling
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_file)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        # Update Function List when switching tabs
        self.tabWidget.currentChanged.connect(self.update_function_list)

        # Add Project View
        self.project_view = ProjectView(self)

        # Install event filter for right mouse click on tabs
        self.tabWidget.tabBar().installEventFilter(self)

        self.setCentralWidget(self.tabWidget)

        # Set the tab style
        self.set_tab_style()

        # Create actions, menu and toolbar
        self.control_shorcut_actions()
        self.create_menubar()
        self.create_toolbar()

        # Create Terminal
        self.terminal = Terminal(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.terminal)

        # Initialize SettingsManager
        self.settings_manager = SettingsManager()

        # Load session from SettingsManager instead of session.json
        self.settings_manager.restore_session(self)
        self.settings_manager.restore_layout(self)

        # If no files were restored, create a new file
        if self.tabWidget.count() == 0:
            self.new_file()

        # Initialize a list to keep track of closed files
        self.closed_files = []

        # Create a status bar
        self.mainStatusBar = QStatusBar()
        self.setStatusBar(self.mainStatusBar)

        # Create labels for status information
        self.length_label = QLabel("length: 0")
        self.lines_label = QLabel("lines: 0")
        self.cursor_label = QLabel("Ln: 1   Col: 1   Pos: 0")
        self.line_endings_label = QLabel("Windows (CR LF)")
        self.encoding_label = QLabel("UTF-8")
        self.mode_label = QLabel("INS")

        # Add labels to the status bar
        self.mainStatusBar.addPermanentWidget(self.length_label)
        self.mainStatusBar.addPermanentWidget(self.lines_label)
        self.mainStatusBar.addPermanentWidget(self.cursor_label)
        self.mainStatusBar.addPermanentWidget(self.line_endings_label)
        self.mainStatusBar.addPermanentWidget(self.encoding_label)
        self.mainStatusBar.addPermanentWidget(self.mode_label)

        self.length_label.setFixedWidth(80)   # Fix the width to 80px
        self.lines_label.setFixedWidth(80)
        self.cursor_label.setFixedWidth(200)
        self.line_endings_label.setFixedWidth(120)
        self.encoding_label.setFixedWidth(80)
        self.mode_label.setFixedWidth(50)

        # Connect right-click event on encoding label
        self.encoding_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.encoding_label.customContextMenuRequested.connect(self.show_encoding_menu)
        self.line_endings_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.line_endings_label.customContextMenuRequested.connect(self.show_line_end_menu)

        # Initialize status bar fields
        self.update_status_bar()
        self.terminal.exe_first_cmd()

        # Connect the cursor position change to update the status bar
        self.tabWidget.currentChanged.connect(self.update_status_bar)

    def set_tab_style(self):
        """Set the style for tabs"""
        # Style for the tab widget
        self.tabWidget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background: #F0F0F0;
            }
            QTabBar::tab {
                background: #E1E1E1;
                border: 1px solid #C4C4C3;
                padding: 5px 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #dcffbd;  /* Moccasin color for selected tab */
                border-bottom: none;
                margin-bottom: -1px;
                font-weight: bold;
            }
            QTabBar::tab:!selected {
                background: #F0F0F0;
            }
            QTabBar::tab:!selected:hover {
                background: #E8E8E8;
            }
            QTabBar::close-button {
                image: url(icons/close.png);
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background: #FFA07A;  /* Light salmon color for close button hover */
                border-radius: 2px;
            }
        """)

    def on_tab_changed(self, index):
        """Handle tab change event"""
        current_editor = self.get_current_editor()

        # Update the UI to reflect the current tab
        if index >= 0:
            # You can add additional handling here if needed
            current_index_file_status = "saved" if not current_editor.isModified() else "changed"
            self.set_tab_background_color(index, current_index_file_status)
            self.tabWidget.setCurrentIndex(index)
            self.current_tab_index = index

    def control_shorcut_actions(self):
        # File actions
        self.newAction = QAction("New", self)
        self.newAction.setShortcut("Ctrl+N")
        self.newAction.triggered.connect(self.new_file)

        self.openAction = QAction("Open...", self)
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.triggered.connect(self.open_file)

        self.saveAction = QAction("Save", self)
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.triggered.connect(self.save_file)

        self.exitAction = QAction("Exit", self)
        self.exitAction.setShortcut("Alt+F4")
        self.exitAction.triggered.connect(self.close)

        # Edit actions
        self.undoAction = QAction("Undo", self)
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.triggered.connect(lambda: self.handle_edit_action("undo"))

        self.redoAction = QAction("Redo", self)
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.triggered.connect(lambda: self.handle_edit_action("redo"))

        self.cutAction = QAction("Cut", self)
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.triggered.connect(lambda: self.handle_edit_action("cut"))

        self.copyAction = QAction("Copy", self)
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.triggered.connect(lambda: self.handle_edit_action("copy"))

        self.pasteAction = QAction("Paste", self)
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.triggered.connect(lambda: self.handle_edit_action("paste"))

        self.selectAllAction = QAction("Select All", self)
        self.selectAllAction.setShortcut("Ctrl+A")
        self.selectAllAction.triggered.connect(lambda: self.handle_edit_action("select_all"))

        # Compile Execute Action
        self.compileAction = QAction("Compile", self)
        self.compileAction.setShortcut("F9")
        self.compileAction.triggered.connect(self.compile_handle)
        self.addAction(self.compileAction)

        self.compilerunAction = QAction("Compile & Run", self)
        self.compilerunAction.setShortcut("F10")
        self.compilerunAction.triggered.connect(self.compile_run_handle)
        self.addAction(self.compilerunAction)

        # Add Find action
        self.findAction = QAction("Find", self)
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.triggered.connect(self.show_find_dialog)
        self.addAction(self.findAction)     # Make the shortcut work globally

        # Add action for reopening the last closed file
        self.reopenAction = QAction("Reopen Last Closed File", self)
        self.reopenAction.setShortcut("Ctrl+H")
        self.reopenAction.triggered.connect(self.reopen_last_closed_file)
        self.addAction(self.reopenAction)   # Make the shortcut work globally

        # Add action for closing the current tab
        self.closeTabAction = QAction("Close Tab", self)
        self.closeTabAction.setShortcut("Ctrl+F4")
        self.closeTabAction.triggered.connect(self.close_current_tab)
        self.addAction(self.closeTabAction)  # Make the shortcut work globally

        # Add action for Go To Line
        self.goToLineAction = QAction("Go To Line", self)
        self.goToLineAction.setShortcut("Ctrl+G") # Change to a unique shortcut
        self.goToLineAction.triggered.connect(self.show_go_to_line_dialog)
        self.addAction(self.goToLineAction)             # Make the shortcut work globally

        # Add shortcut for commenting/uncommenting
        self.commentAction = QAction("Comment/Uncomment", self)
        self.commentAction.setShortcut("Ctrl+Q")
        self.commentAction.triggered.connect(lambda: self.handle_edit_action("comment"))
        self.addAction(self.commentAction)

        # Add Word Wrap action
        self.wordWrapAction = QAction("Word Wrap", self)
        self.wordWrapAction.setCheckable(True)  # Make it checkable
        self.wordWrapAction.setShortcut("Ctrl+W")  # Optional shortcut
        self.wordWrapAction.triggered.connect(self.toggle_word_wrap)
        self.addAction(self.wordWrapAction)  # Make the shortcut work globally

        # Add Show All Characters action
        self.ShowAllCharAction = QAction("Show All Characters", self)
        self.ShowAllCharAction.setCheckable(True)  # Make it checkable
        self.ShowAllCharAction.setShortcut("Ctrl+J")  # Optional shortcut
        self.ShowAllCharAction.triggered.connect(self.toggle_show_all_char)
        self.addAction(self.ShowAllCharAction)  # Make the shortcut work globally

        # Add action to change language
        self.setPythonAction = QAction("Set Python Language", self)
        self.setPythonAction.triggered.connect(lambda: self.set_editor_language("Python"))
        self.setCPPAction = QAction("Set C++ Language", self)
        self.setCPPAction.triggered.connect(lambda: self.set_editor_language("CPP"))
        self.addAction(self.setPythonAction)
        self.addAction(self.setCPPAction)

        # Add action to open project directory
        self.openprojectAction = QAction("Open Project", self)
        self.openprojectAction.setShortcut("Ctrl+Shift+P")
        self.openprojectAction.triggered.connect(self.open_project_directory)
        self.addAction(self.openprojectAction)

        # Create actions for project view and function list
        self.projectviewAction = QAction(QIcon("icons/project.svg"), "Project Explore", self)
        self.projectviewAction.setCheckable(True)
        self.projectviewAction.setChecked(True)
        self.projectviewAction.toggled.connect(self.toggle_project_view)

        self.functionlistAction = QAction(QIcon("icons/function_list.svg"), "Function List", self)
        self.functionlistAction.setCheckable(True)
        self.functionlistAction.setChecked(True)
        self.functionlistAction.toggled.connect(self.toggle_function_list)

        self.toggleterminalAction = QAction("Terminal", self)
        self.toggleterminalAction.setCheckable(True)
        self.toggleterminalAction.setChecked(True)
        self.toggleterminalAction.setShortcut("Ctrl+B")
        self.toggleterminalAction.triggered.connect(self.toggle_terminal)

    def handle_edit_action(self, action):
        current_editor = self.get_current_editor()
        if current_editor:
            if action == "cut":
                current_editor.cut()
            elif action == "copy":
                current_editor.copy()
            elif action == "paste":
                current_editor.paste()
            elif action == "undo":
                current_editor.undo()
            elif action == "redo":
                current_editor.redo()
            elif action == "select_all":
                current_editor.selectAll()
            elif action == "comment":
                current_editor.comment_lines()

    def create_menubar(self):
        menubar = self.menuBar()

        # File Menu
        fileMenu = menubar.addMenu("File")
        fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.openprojectAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.reopenAction)  # Add the reopen action to the menu
        fileMenu.addAction(self.exitAction)

        # Edit Menu
        editMenu = menubar.addMenu("Edit")
        editMenu.addAction(self.undoAction)
        editMenu.addAction(self.redoAction)
        editMenu.addSeparator()
        editMenu.addAction(self.cutAction)
        editMenu.addAction(self.copyAction)
        editMenu.addAction(self.pasteAction)
        editMenu.addSeparator()
        editMenu.addAction(self.findAction)
        editMenu.addAction(self.selectAllAction)
        
        # Edit Menu
        editMenu = menubar.addMenu("Execute")
        editMenu.addAction(self.compileAction)
        editMenu.addAction(self.compilerunAction)
        # editMenu.addSeparator()
        # editMenu.addAction(self.cleanAction)
        # editMenu.addAction(self.debugAction)

        # Add Language menu
        languageMenu = menubar.addMenu("Language")
        languageMenu.addAction(self.setPythonAction)
        languageMenu.addAction(self.setCPPAction)

        # Add Window Toolbar
        windowMenu = menubar.addMenu("Window")
        show_view_menu = QMenu("Show View", self)
        windowMenu.addMenu(show_view_menu)
        show_view_menu.addAction(self.projectviewAction)
        show_view_menu.addAction(self.functionlistAction)
        show_view_menu.addAction(self.toggleterminalAction)
        
        # Help Menu
        helpMenu = menubar.addMenu("Help")
        aboutAction = QAction("About", self)
        aboutAction.triggered.connect(self.about_app)
        helpMenu.addAction(aboutAction)

    def open_project_directory(self):
        """Chọn thư mục dự án và cập nhật Project View."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if directory:
            self.project_view.set_project_directory(directory)

    def set_editor_language(self, language):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.set_language(language)

    def toggle_project_view(self, checked):
        """Toggle visibility of Project View."""
        self.project_view.project_dock.setVisible(checked)

    def toggle_function_list(self, checked):
        """Toggle visibility of Function List."""
        self.function_list.setVisible(checked)

    def toggle_terminal(self, checked):
        """Toggle Terminal."""
        if checked:
            self.terminal.show()
        else:
            self.terminal.hide()

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.setObjectName("MainToolbar")

        # Add icons to actions
        self.newAction.setIcon(QIcon("icons/new.svg"))
        self.openAction.setIcon(QIcon("icons/open.svg"))
        self.openprojectAction.setIcon(QIcon("icons/open_proj.svg"))
        self.saveAction.setIcon(QIcon("icons/save.svg"))
        self.wordWrapAction.setIcon(QIcon("icons/word-wrap.svg"))
        self.ShowAllCharAction.setIcon(QIcon("icons/show_all_char.svg"))

        # Add actions to toolbar
        toolbar.addAction(self.newAction)
        toolbar.addAction(self.openAction)
        toolbar.addAction(self.openprojectAction)
        toolbar.addAction(self.saveAction)
        toolbar.addAction(self.wordWrapAction)
        toolbar.addAction(self.ShowAllCharAction)
        toolbar.addAction(self.functionlistAction)

    def new_file(self):
        """Create a new empty file"""
        editor = CodeEditor(self)  # Ensure self is passed as the parent
        editor.textChanged.connect(self.on_editor_text_changed)  # Connect the signal
        self.add_editor(editor)
        self.tabWidget.addTab(editor, "Untitled")
        self.tabWidget.setCurrentWidget(editor)  # Set the new editor as the current widget

    def open_file(self, file_path=None, cursor_pos=(0, 0)):
        """Open a file in a new tab, generating CTags only for source code files."""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open File",
                "",
                "All Files (*.*)"
            )

        if file_path:
            # Check if file is already open
            for i in range(self.tabWidget.count()):
                editor = self.tabWidget.widget(i)
                if hasattr(editor, 'file_path') and editor.file_path == file_path:
                    self.tabWidget.setCurrentIndex(i)
                    return

            try:
                # Detect file encoding
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']

                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()

                editor = CodeEditor(self)
                editor.textChanged.connect(self.on_editor_text_changed)
                editor.setText(text)
                editor.file_path = file_path
                editor.setModified(False)
                self.add_editor(editor)

                # Restore cursor position
                editor.setCursorPosition(*cursor_pos)
                editor.horizontalScrollBar().setValue(0)  # Set to leftmost position

                filename = Path(file_path).name
                index = self.tabWidget.addTab(editor, filename)
                self.tabWidget.setCurrentIndex(index)
                
                # Update Function List after opening a file
                self.update_function_list()

                # Define recognized source code extensions
                SOURCE_EXTENSIONS = ('.c', '.cpp', '.h', '.hpp', '.py')  # Add more as needed

                # Only generate CTags for source code files
                file_suffix = Path(file_path).suffix.lower()
                if file_suffix in SOURCE_EXTENSIONS:
                    self.ctags_handler = CtagsHandler(editor)
                    self.ctags_handler.generate_ctags()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        current_editor = self.get_current_editor()
        if current_editor is None:
            return
        self.set_tab_background_color(self.current_tab_index, "saved")

        if not hasattr(current_editor, 'file_path'):
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*.*)")
            if file_path:
                current_editor.file_path = file_path
            else:
                return
        try:
            with open(current_editor.file_path, 'w', encoding='utf-8') as f:
                f.write(current_editor.text())

            # Mark the editor as not modified
            current_editor.setModified(False)

            # Update Tab Color Background
            self.set_tab_background_color(self.current_tab_index, "saved")

            # Update the tab title to the file name
            self.tabWidget.setTabText(
                self.current_tab_index,
                Path(current_editor.file_path).name
            )
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
            return False

    def close_file(self, index):
        """Handle closing a tab"""
        editor = self.tabWidget.widget(index)
        if editor.isModified():
            filename = self.tabWidget.tabText(index)
            reply = QMessageBox.question(
                self,
                "Save Changes",
                f"Do you want to save changes to {filename}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file(editor):
                    return  # Don't close if save was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return  # Don't close if user cancelled

        # Store the closed file information
        if hasattr(editor, 'file_path'):
            self.closed_files.append((editor.file_path, editor.text(), editor.getCursorPosition()))

        # Remove ctags file
        self.ctags_handler = CtagsHandler(editor)
        self.ctags_handler.remove_ctags()

        # Remove the tab
        self.tabWidget.removeTab(index)

        # Create a new tab if this was the last one
        if self.tabWidget.count() == 0:
            self.new_file()

    def about_app(self):
        QMessageBox.information(self, "About", "This is a Notepad++ style Text Editor, develop by Nghia Taarabt and Channel laptrinhdientu.com\nDebugger integration coming soon!")

    def set_tab_background_color(self, index, hex_color):
        """Set the background color of a specific tab"""
        if 0 <= index < self.tabWidget.count():
            if hex_color == "changed":
                self.tabWidget.setStyleSheet("""
                    QTabWidget::pane {
                        border: 1px solid #C2C7CB;
                        background: #F0F0F0;
                    }
                    QTabBar::tab {
                        background: #E1E1E1;
                        border: 1px solid #C4C4C3;
                        padding: 5px 10px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background: #edd19d;  /* Moccasin color for selected tab */
                        border-bottom: none;
                        margin-bottom: -1px;
                        font-weight: bold;
                    }
                    QTabBar::tab:!selected {
                        background: #F0F0F0;
                    }
                    QTabBar::tab:!selected:hover {
                        background: #E8E8E8;
                    }
                    QTabBar::close-button {
                        image: url(icons/close.png);
                        subcontrol-position: right;
                    }
                    QTabBar::close-button:hover {
                        background: #FFA07A;  /* Light salmon color for close button hover */
                        border-radius: 2px;
                    }
                """)
            elif hex_color == "saved":
                self.tabWidget.setStyleSheet("""
                    QTabWidget::pane {
                        border: 1px solid #C2C7CB;
                        background: #F0F0F0;
                    }
                    QTabBar::tab {
                        background: #E1E1E1;
                        border: 1px solid #C4C4C3;
                        padding: 5px 10px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background: #dcffbd;  /* Moccasin color for selected tab */
                        border-bottom: none;
                        margin-bottom: -1px;
                        font-weight: bold;
                    }
                    QTabBar::tab:!selected {
                        background: #F0F0F0;
                    }
                    QTabBar::tab:!selected:hover {
                        background: #E8E8E8;
                    }
                    QTabBar::close-button {
                        image: url(icons/close.png);
                        subcontrol-position: right;
                    }
                    QTabBar::close-button:hover {
                        background: #FFA07A;  /* Light salmon color for close button hover */
                        border-radius: 2px;
                    }
                """)
            #self.tabWidget.tabBar().setTabData(index, {"background-color": hex_color})

    def set_tabtext_color(self, index, hex_color):
        """Set the text color of a specific tab"""
        if 0 <= index < self.tabWidget.count():
            self.tabWidget.tabBar().setStyleSheet(f"QTabBar::tab::selected {{ color: {hex_color}; }}")

    def get_current_editor(self):
        """Return the currently active editor"""
        current_index = self.tabWidget.currentIndex()
        if current_index != -1:
            return self.tabWidget.widget(current_index)
        return None

    def show_find_dialog(self):
        if not self.find_dialog:
            self.find_dialog = FindDialog(self)

        # Get selected text if any
        editor = self.get_current_editor()
        if editor and editor.hasSelectedText():
            self.find_dialog.find_input.setText(editor.selectedText())
            self.find_dialog.find_input.selectAll()

        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()
        self.find_dialog.find_input.setFocus()

    def save_file_for_editor(self, editor):
        """Save the specified editor's content"""
        if not hasattr(editor, 'file_path') or not editor.file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*.*)")
            if file_path:
                editor.file_path = file_path
            else:
                return False  # Người dùng hủy lưu

        try:
            with open(editor.file_path, 'w', encoding='utf-8') as f:
                f.write(editor.text())
            editor.setModified(False)
            # Cập nhật tên tab
            tab_index = self.tabWidget.indexOf(editor)
            if tab_index != -1:
                self.tabWidget.setTabText(tab_index, Path(editor.file_path).name)
                self.set_tab_background_color(tab_index, "saved")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
            return False

    def closeEvent(self, event):
        """Handle application close event."""
        modified_saved_files = []
        for i in range(self.tabWidget.count()):
            editor = self.tabWidget.widget(i)
            if editor.isModified() and hasattr(editor, 'file_path') and editor.file_path:
                if editor.text().strip():
                    modified_saved_files.append((i, editor, self.tabWidget.tabText(i)))

        if modified_saved_files:
            tabs_to_remove = []
            for index, editor, filename in modified_saved_files:
                reply = QMessageBox.question(
                    self, "Save Changes", f"Do you want to save changes to {filename}?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                )
                if reply == QMessageBox.StandardButton.Save:
                    if not self.save_file_for_editor(editor):
                        event.ignore()
                        return
                elif reply == QMessageBox.StandardButton.Discard:
                    tabs_to_remove.append(index)

            for index in sorted(tabs_to_remove, reverse=True):
                self.tabWidget.removeTab(index)

        # Remove .tags files for all open files
        for i in range(self.tabWidget.count()):
            editor = self.tabWidget.widget(i)
            if hasattr(editor, 'file_path'):
                self.ctags_handler = CtagsHandler(editor)
                self.ctags_handler.remove_ctags()

        # Remove .tags file for current project
        if hasattr(self, 'project_view') and self.project_view.current_project_directory:
            project_tags = Path(self.project_view.current_project_directory) / 'project.tags'
            if project_tags.exists():
                project_tags.unlink()

        # Lưu session và layout qua SettingsManager
        self.settings_manager.save_session(self)
        self.settings_manager.save_layout(self)
        event.accept()

    def hideEvent(self, event):
        """Lưu trạng thái khi thu nhỏ."""
        self.settings_manager.save_layout(self)
        super().hideEvent(event)

    def showEvent(self, event):
        """Khôi phục trạng thái khi hiển thị lại."""
        self.settings_manager.restore_layout(self)
        super().showEvent(event)

    def eventFilter(self, obj, event):
        """Handle right mouse click on tabs and middle mouse button click to close tabs"""
        if obj is self.tabWidget.tabBar():
            if event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.MiddleButton:  # Middle mouse button
                    tab_index = obj.tabAt(event.pos())
                    if tab_index != -1:  # Valid tab clicked
                        self.close_file(tab_index)  # Close the tab
                        return True
                elif event.button() == Qt.MouseButton.RightButton:
                    tab_index = obj.tabAt(event.pos())
                    if tab_index != -1:  # Valid tab clicked
                        # Use mapToGlobal to get the global position
                        self.show_tab_context_menu(tab_index, obj.mapToGlobal(event.pos()))
                        return True
        return super().eventFilter(obj, event)

    def copy_full_file_path(self, editor):
        """Copy the full file path to the clipboard"""
        if hasattr(editor, 'file_path') and editor.file_path:
            clipboard = QApplication.clipboard()
            clipboard.setText(editor.file_path)

    def open_containing_folder(self, editor):
        """Open the containing folder of the file in Explorer"""
        if hasattr(editor, 'file_path') and editor.file_path:
            folder_path = Path(editor.file_path).parent
            if folder_path.exists():
                subprocess.Popen(f'explorer "{folder_path}"')

    def show_tab_context_menu(self, tab_index, pos):
        """Show context menu for tab actions"""
        menu = QMenu(self)

        # Get the editor associated with the tab
        editor = self.tabWidget.widget(tab_index)

        # Close File action
        close_action = QAction("Close File", self)
        close_action.triggered.connect(lambda: self.close_file(tab_index))
        menu.addAction(close_action)

        # Copy Full File Path action
        copy_path_action = QAction("Copy Full File Path", self)
        copy_path_action.triggered.connect(lambda: self.copy_full_file_path(editor))
        menu.addAction(copy_path_action)

        # Open Containing Folder in Explorer action
        open_folder_action = QAction("Open Containing Folder in Explorer", self)
        open_folder_action.triggered.connect(lambda: self.open_containing_folder(editor))
        menu.addAction(open_folder_action)

        # Show the context menu
        menu.exec(pos)

    def on_editor_text_changed(self):
        """Handle text changes in the editor"""
        current_editor = self.get_current_editor()
        if current_editor:
            current_index = self.tabWidget.indexOf(current_editor)
            self.set_tab_background_color(current_index, "changed")
            self.update_status_bar()  # Update status bar on text change

    def reopen_last_closed_file(self):
        """Reopen the last closed file"""
        if self.closed_files:
            file_path, content, cursor_pos = self.closed_files.pop()  # Get the last closed file info
            self.open_file(file_path, cursor_pos)  # Open the file with the saved cursor position
            editor = self.get_current_editor()
            if editor:
                editor.setText(content)     # Restore the content
                editor.setModified(False)   # Mark as saved
                self.set_tab_background_color(self.tabWidget.indexOf(editor), "saved")

    def close_current_tab(self):
        """Close the currently active tab."""
        current_index = self.tabWidget.currentIndex()
        if current_index != -1:
            self.close_file(current_index)  # Call the existing close_file method

    def show_go_to_line_dialog(self):
        """Show the Go To Line dialog."""
        dialog = GoToLineDialog(self)
        dialog.exec()

    def toggle_word_wrap(self):
        """Toggle word wrap in the current editor."""
        current_editor = self.get_current_editor()
        if current_editor:
            # Check the current wrap mode and toggle accordingly
            if current_editor.wrapMode() == QsciScintilla.WrapMode.WrapWord:
                current_editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)  # Disable wrap
                self.wordWrapAction.setChecked(False)  # Update UI action
            else:
                current_editor.setWrapMode(QsciScintilla.WrapMode.WrapWord)  # Enable word wrap
                self.wordWrapAction.setChecked(True)  # Update UI action

    def show_all_char(self, isShowed):
        current_editor = self.get_current_editor()
        current_editor.setEolVisibility(isShowed)
        self.ShowAllCharAction.setChecked(isShowed)  # Update UI action

    def toggle_show_all_char(self):
        """Toggle show all character in the current editor."""
        current_editor = self.get_current_editor()
        self._showallchar = not self._showallchar
        current_editor.setEolVisibility(self._showallchar)
        self.ShowAllCharAction.setChecked(self._showallchar)

    def add_editor(self, editor):
        """Add a new editor and connect signals for real-time updates."""
        editor.textChanged.connect(self.on_editor_text_changed)  # Update on text change
        editor.cursorPositionChanged.connect(self.update_status_bar)  # Update on cursor position change

    def update_status_bar(self):
        """Update the status bar with current editor information."""
        editor = self.get_current_editor()
        if editor:
            # Chặn tín hiệu để tránh tác dụng phụ
            editor.blockSignals(True)
            try:
                text = editor.text()
                length = len(text)
                lines = editor.SendScintilla(QsciScintilla.SCI_GETLINECOUNT)
                cursor_line, cursor_col = editor.getCursorPosition()
                cursor_pos = editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

                # Determine line endings based on the text content
                eol_mode = editor.eolMode()

                if eol_mode == QsciScintilla.EolMode.EolWindows:
                    line_endings = "Windows (CRLF)"
                elif eol_mode == QsciScintilla.EolMode.EolUnix:
                    line_endings = "Unix (LF)"
                elif eol_mode == QsciScintilla.EolMode.EolMac:
                    line_endings = "Mac (CR)"
                else:
                    line_endings = "Unknown EOL"

                encoding = "UTF-8"  # You can implement detection if needed
                mode = "INS" if editor.SendScintilla(QsciScintilla.SCI_GETOVERTYPE) == 0 else "OVR"

                # Update the status labels
                if hasattr(self, 'mainStatusBar'):
                    self.length_label.setText(f"length: {length}")
                    self.lines_label.setText(f"MaxLine: {lines}")
                    self.cursor_label.setText(f"Line: {cursor_line + 1}   Col: {cursor_col + 1}   Pos: {cursor_pos}")
                    self.line_endings_label.setText(line_endings)
                    self.encoding_label.setText(encoding)
                    self.mode_label.setText(mode)
            finally:
                # Khôi phục tín hiệu
                editor.blockSignals(False)

    def show_encoding_menu(self, pos):
        """Show context menu for encoding options."""
        menu = QMenu(self)

        # Define encoding options
        encodings = ["UTF-8", "ISO-8859-1", "ASCII", "UTF-16", "UTF-32"]
        for encoding in encodings:
            action = QAction(encoding, self)
            action.triggered.connect(lambda checked, enc=encoding: self.change_encoding(enc))
            menu.addAction(action)

        # Show the menu at the cursor position
        menu.exec(self.encoding_label.mapToGlobal(pos))

    def change_encoding(self, new_enc):
        """Change the encoding of the current file."""
        current_editor = self.get_current_editor()
        if current_editor and hasattr(current_editor, 'file_path'):
            try:
                # Read the current content
                coding1 = "utf-8"
                coding2 = "gb18030"

                f = open(current_editor.file_path, 'rb')
                content = unicode(f.read(), coding2)
                f.close()
                f = open(current_editor.file_path, 'wb')
                f.write(content.encode(new_enc))
                f.close()

                # Save the current cursor position
                # cursor_pos = current_editor.getCursorPosition()

                # Write the content with the new encoding
                # with open(current_editor.file_path, 'wb') as f:
                #     f.write(content.encode(new_enc))

                # Update the encoding label
                self.encoding_label.setText(new_enc)

                # Restore the cursor position
                current_editor.setCursorPosition(*cursor_pos)

                QMessageBox.information(self, "Encoding Changed", f"File encoding changed to {new_enc}.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not change encoding: {str(e)}")

    def show_line_end_menu(self, pos):
        """Show context menu for encoding options."""
        menu = QMenu(self)

        # Define encoding options
        line_end_list = ["Windows (CRLF)", "Unix (LF)", "Mac (CR)"]
        for line_end in line_end_list:
            action = QAction(line_end, self)
            action.triggered.connect(lambda checked, type=line_end: self.change_line_end(type))
            menu.addAction(action)

        # Show the menu at the cursor position
        menu.exec(self.line_endings_label.mapToGlobal(pos))

    def change_line_end(self, new_line_end):
        """Change the encoding of the current file."""
        current_editor = self.get_current_editor()
        if current_editor and hasattr(current_editor, 'file_path'):
            try:
                if new_line_end == "Windows (CRLF)":
                    current_editor.setEolMode(QsciScintilla.EolMode.EolWindows)
                elif new_line_end == "Unix (LF)":
                    current_editor.setEolMode(QsciScintilla.EolMode.EolUnix)
                elif new_line_end == "Mac (CR)":
                    current_editor.setEolMode(QsciScintilla.EolMode.EolMac)

                # Save the current cursor position
                cursor_pos = current_editor.getCursorPosition()

                # Update the encoding label
                self.line_endings_label.setText(new_line_end)

                # Restore the cursor position
                current_editor.setCursorPosition(*cursor_pos)

                QMessageBox.information(self, "Line Ending Changed", f"File Line Ending changed to {new_line_end}.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not change line endings: {str(e)}")

    def enable_folding(editor: QsciScintilla):
        editor.setMarginWidth(2, 15)  # Đặt chiều rộng margin thứ 2 (chứa folding)
        editor.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)  # Kiểu hiển thị folding
    
    """ Function List Item Handle Functions """
    def update_function_list(self):
        """Update Function List when switching tabs or opening a file."""
        current_editor = self.get_current_editor()
        self.function_list.update_function_list(current_editor)

    def on_item_double_clicked(self, item, column):
        """Nhảy đến định nghĩa và đặt con trỏ tại vị trí symbol khi nhấp đúp vào item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            file_path, line_info = data
            editor = self.parent.get_current_editor()
            if editor:
                # Tính lại line_number và tìm vị trí cột của symbol từ line_info
                line_number = None
                column = 0  # Vị trí cột của symbol trong dòng
                symbol = item.text(0)  # Lấy tên symbol từ item (cột Symbol)

                if line_info.startswith("/^") and line_info.endswith("$/;\""):
                    pattern = line_info[2:-4].strip()
                    try:
                        with open(file_path, 'r', encoding='utf-8') as source_file:
                            for i, source_line in enumerate(source_file, 1):
                                if pattern in source_line.strip():
                                    line_number = i
                                    # Tìm vị trí cột của symbol trong dòng
                                    column = source_line.find(symbol)
                                    break
                    except Exception as e:
                        return
                elif line_info.isdigit():
                    line_number = int(line_info)
                    # Đọc dòng từ file để tìm vị trí cột của symbol
                    try:
                        with open(file_path, 'r', encoding='utf-8') as source_file:
                            for i, source_line in enumerate(source_file, 1):
                                if i == line_number:
                                    column = source_line.find(symbol)
                                    break
                    except Exception as e:
                        return

                if line_number is not None:
                    # Mở file và đặt con trỏ tại vị trí symbol
                    editor.open_file_at_line(file_path, line_number, column)
    
    ########## Compile and Execute Handle #############
    def compile_handle(self):
        editor = self.get_current_editor()
        file_suffix = Path(editor.file_path).suffix.lower()
        file_path = str(Path(editor.file_path).resolve())

        if '.py' == file_suffix:
            self.terminal.add_log("Command", f"python {file_path}")
            if self.terminal.execute_specific_command(f"python {file_path}"):
                self.terminal.add_log("Info", "Python program is executed!")
        if '.c' == file_suffix:    
            output_path = str(Path(file_path).with_suffix('.exe'))
            current_dir = str(Path(file_path).parent)
            self.terminal.add_log("Command", f"gcc -o {output_path} {file_path} -I {current_dir}")
            if self.terminal.execute_specific_command(f"gcc -o {output_path} {file_path} -I {current_dir}"):
                if Path(output_path).exists():
                    # Get modification times
                    exe_mtime = os.path.getmtime(output_path)
                    src_mtime = os.path.getmtime(file_path)
                    
                    if exe_mtime >= src_mtime:
                        self.terminal.add_log("Info", "Executable is up to date")
                    else:
                        self.terminal.add_log("Info", "Source file has changed, recompiling...")
                else:
                    self.terminal.add_log("Info", "C program is executed!")

    def compile_run_handle(self):
        self.compile_handle()
        editor = self.get_current_editor()
        file_path = str(Path(editor.file_path).resolve())
        exe_path = str(Path(file_path).with_suffix('.exe'))
        
        if Path(exe_path).exists():
            self.terminal.add_log("Command", exe_path)
            self.terminal.execute_specific_command(exe_path)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # Ensure the application directory exists
    app_dir = Path(__file__).parent
    app_dir.mkdir(exist_ok=True)

    main()
import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, 
    QFileDialog, QMessageBox, QToolBar,
    QMenuBar, QDialog, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QCheckBox, QGroupBox, QRadioButton,
    QWidget, QMenu
)
from PyQt6.QtGui import (
    QIcon, 
    QAction,
    QFont,
    QColor
)
from PyQt6.QtCore import (
    Qt,
    QPoint,
    QSize
)
from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerCPP,
    QsciLexerPython
)
from datetime import datetime

class CodeEditor(QsciScintilla):
    def __init__(self, parent=None, theme_name="Khaki"):
        super().__init__(parent)
        self.GUI = parent
        
        # Font configuration
        self.text_font = QFont("Consolas", 16)
        self.margin_font = QFont("Consolas", 18)  # Fixed size for margin
        
        # Lexer configuration
        self.lexer = QsciLexerCPP()
        self.lexer.setDefaultFont(self.text_font)
        
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
            # print(f"Error loading theme: {e}")
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
        self.tab_widget.addTab(self.create_replace_tab(), "Replace")
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
        self.replace_find_next = QPushButton("Find Next")
        self.replace_button = QPushButton("Replace")
        self.replace_all_button = QPushButton("Replace All")
        
        buttons_layout.addWidget(self.replace_find_next)
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
                    import re
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
        
        # Initialize Tab File Manager
        self.current_tab_index = -1
        
        # Initialize TabWidget with custom styling
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_file)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        # Install event filter for right mouse click on tabs
        self.tabWidget.tabBar().installEventFilter(self)
        
        self.setCentralWidget(self.tabWidget)
        
        # Set the tab style
        self.set_tab_style()
        
        # Create actions, menu and toolbar
        self.control_shorcut_actions()
        self.create_menubar()
        self.create_toolbar()
        
        # Set up paths for session and backup
        self.app_dir = Path(__file__).parent
        self.session_file = self.app_dir / "session.json"
        self.backup_dir = self.app_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load last session
        self.load_session()
        
        # If no files were restored, create a new file
        if self.tabWidget.count() == 0:
            self.new_file()

        # Initialize a list to keep track of closed files
        self.closed_files = []

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

        # Add Find action
        self.findAction = QAction("Find", self)
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.triggered.connect(self.show_find_dialog)
        self.addAction(self.findAction)     # Make the shortcut work globally

        # Add action for reopening the last closed file
        self.reopenAction = QAction("Reopen Last Closed File", self)
        self.reopenAction.setShortcut("Ctrl+G")
        self.reopenAction.triggered.connect(self.reopen_last_closed_file)
        self.addAction(self.reopenAction)   # Make the shortcut work globally
        
        # Add action for closing the current tab
        self.closeTabAction = QAction("Close Tab", self)
        self.closeTabAction.setShortcut("Ctrl+F4")
        self.closeTabAction.triggered.connect(self.close_current_tab)
        self.addAction(self.closeTabAction)  # Make the shortcut work globally

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

    def create_menubar(self):
        menubar = self.menuBar()

        # File Menu
        fileMenu = menubar.addMenu("File")
        fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
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

        # Help Menu
        helpMenu = menubar.addMenu("Help")
        aboutAction = QAction("About", self)
        aboutAction.triggered.connect(self.about_app)
        helpMenu.addAction(aboutAction)

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add icons to actions
        self.newAction.setIcon(QIcon("icons/new.png"))
        self.openAction.setIcon(QIcon("icons/open.png"))
        self.saveAction.setIcon(QIcon("icons/save.png"))

        # Add actions to toolbar
        toolbar.addAction(self.newAction)
        toolbar.addAction(self.openAction)
        toolbar.addAction(self.saveAction)
        toolbar.addAction(self.reopenAction)  # Add the reopen action to the toolbar

    def new_file(self):
        """Create a new empty file"""
        editor = CodeEditor(self)  # Ensure self is passed as the parent
        editor.textChanged.connect(self.on_editor_text_changed)  # Connect the signal
        self.tabWidget.addTab(editor, "Untitled")
        self.tabWidget.setCurrentWidget(editor)  # Set the new editor as the current widget

    def open_file(self, file_path=None, cursor_pos=(0, 0)):
        """Open a file in a new tab"""
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
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                editor = CodeEditor(self)
                editor.textChanged.connect(self.on_editor_text_changed)  # Connect the signal
                editor.setText(text)
                editor.file_path = file_path
                editor.setModified(False)
                
                # Restore cursor position
                editor.setCursorPosition(*cursor_pos)
                
                filename = Path(file_path).name
                index = self.tabWidget.addTab(editor, filename)
                self.tabWidget.setCurrentIndex(index)
                
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
                # print(f"File saved: {current_editor.file_path}")  # Debugging line
            
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

    def load_session(self):
        """Load previously opened files and their unsaved content"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    
                    # Load saved files
                    files           = session_data.get('open_files', [])
                    unsaved_files   = session_data.get('unsaved_files', [])
                    current_tab     = session_data.get('current_tab', 0)
                    
                    # Restore saved files
                    for file_info in files:
                        if isinstance(file_info, str):
                            # Handle old format for backward compatibility
                            file_path = file_info
                            cursor_pos = (0, 0)
                        else:
                            file_path = file_info['path']
                            cursor_pos = tuple(file_info['cursor'])
                            
                        if Path(file_path).exists():
                            self.open_file(file_path, cursor_pos)
                    
                    # Restore unsaved files
                    for unsaved in unsaved_files:
                        editor = CodeEditor(self)
                        with open(unsaved['backup_path'], 'r', encoding='utf-8') as f:
                            editor.setText(f.read())
                        editor.setCursorPosition(*tuple(unsaved['cursor']))
                        editor.setModified(True)
                        
                        # Set file path if it was an existing file
                        if unsaved.get('original_path'):
                            editor.file_path = unsaved['original_path']
                        
                        # Use original tab name or generate one from backup
                        if 'tab_name' in unsaved:
                            tab_name = unsaved['tab_name']
                        else:
                            tab_name = Path(unsaved['backup_path']).stem
                        
                        self.current_tab_index = self.tabWidget.addTab(editor, tab_name)
                    
                    # Restore the last active tab
                    if self.tabWidget.count() > current_tab:
                        self.tabWidget.setCurrentIndex(current_tab)

                # Delete the unsaved files in the backup folder
                for unsaved in unsaved_files:
                    if 'backup_path' in unsaved:
                        backup_file = Path(unsaved['backup_path'])
                        if backup_file.exists():
                            backup_file.unlink()
                
                # Remove unsaved files in session file after restore
                with open(self.session_file, 'w', encoding='utf-8') as f:
                    session_data.pop('unsaved_files', None)
                    json.dump(session_data, f)

            else:
                # Create session file if it does not exist
                with open(self.session_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                
        except Exception as e:
            QMessageBox.warning(self, "Session Load Error", 
                              f"Error loading session: {str(e)}")

    def closeEvent(self, event):
        """Handle application close event - automatically store unsaved content"""
        try:
            session_data = {
                'open_files': [],
                'unsaved_files': [],
                'current_tab': self.tabWidget.currentIndex()
            }
            
            # Process each open tab
            for i in range(self.tabWidget.count()):
                editor = self.tabWidget.widget(i)
                cursor_pos = editor.getCursorPosition()
                content = editor.text()
                
                # Store information about saved files
                if hasattr(editor, 'file_path') and editor.file_path and not editor.isModified():
                    session_data['open_files'].append({
                        'path': editor.file_path,
                        'cursor': cursor_pos
                    })
                
                # Store content if the file is modified or is a new unsaved file
                if editor.isModified() or not hasattr(editor, 'file_path'):
                    if content.strip():  # Only save if there's actual content
                        # Generate a unique backup filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        if hasattr(editor, 'file_path') and editor.file_path:
                            # For existing files, use their name in backup
                            original_name = Path(editor.file_path).stem
                            backup_name = f"{original_name}_{timestamp}.txt"
                        else:
                            # For new files, use 'unsaved'
                            backup_name = f"unsaved_{timestamp}_{i}.txt"
                        
                        backup_path = str(self.backup_dir / backup_name)
                        
                        # Save the content to backup file
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        # Store the backup information
                        session_data['unsaved_files'].append({
                            'backup_path': backup_path,
                            # 'content': content,
                            'cursor': cursor_pos,
                            'original_path': getattr(editor, 'file_path', None),
                            'tab_name': self.tabWidget.tabText(i),
                            'timestamp': timestamp
                        })
            
            # Save session data
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=4)
                
        except Exception as e:
            QMessageBox.warning(self, "Session Save Error", 
                              f"Error saving session: {str(e)}")
        
        event.accept()

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
                import subprocess
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
        current_editor = self.get_current_editor()  # Get the current editor instance
        if current_editor:
            current_index = self.tabWidget.indexOf(current_editor)
            self.set_tab_background_color(current_index, "changed")

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

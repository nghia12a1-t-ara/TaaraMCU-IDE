import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, 
    QFileDialog, QMessageBox, QToolBar,
    QMenuBar, QDialog, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QCheckBox
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

class CodeEditor(QsciScintilla):
    def __init__(self, parent=None, theme_name="Khaki"):
        super().__init__(parent)
        
        # Load themes
        self.theme = self.load_theme()
        
        # Font configuration
        font = QFont("Consolas", 16)
        
        # Lexer configuration
        self.lexer = QsciLexerCPP()
        self.lexer.setDefaultFont(font)
        
        # Apply theme
        self.apply_theme()
        
        # Apply font to all styles
        for style in range(128):
            self.lexer.setFont(font, style)
        
        # Apply lexer to QScintilla
        self.setLexer(self.lexer)
        
        # Line number margin configuration
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        
        # Current line highlighting
        self.setCaretLineVisible(True)
        
        # Configure search indicators
        self.indicatorDefine(QsciScintilla.IndicatorStyle.StraightBoxIndicator, 0)
        self.setIndicatorDrawUnder(True, 0)
        
        # Set global font
        self.setFont(font)

        # Configure tab and indentation
        self.setIndentationsUseTabs(False)  # Use spaces instead of tabs
        self.setTabWidth(4)  # Set tab width to 4 spaces
        self.setIndentationGuides(True)  # Show indentation guides
        self.setAutoIndent(True)  # Enable auto-indentation
        self.setBackspaceUnindents(True)  # Backspace unindents

    def load_theme(self):
        """Load theme from JSON file"""
        try:
            script_dir = Path(__file__).parent
            theme_path = script_dir / "themes" / "khaki.json"
            
            with open(theme_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading theme: {e}")
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
        
        # Set margin colors
        margin_fg = colors.get("editorLineNumber.foreground", "#000000")
        margin_active_fg = colors.get("editorLineNumber.activeForeground", "#000000")
        self.setMarginsForegroundColor(QColor(margin_fg))
        self.setMarginsBackgroundColor(QColor(editor_bg))
        
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
        self.setFixedSize(400, 150)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Create search input
        search_layout = QHBoxLayout()
        self.search_label = QLabel("Find what:")
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.reset_search)
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        
        # Create options
        options_layout = QHBoxLayout()
        self.match_case = QCheckBox("Match case")
        self.whole_word = QCheckBox("Match whole word")
        self.wrap_around = QCheckBox("Wrap around")
        self.wrap_around.setChecked(True)  # Enable wrap by default
        options_layout.addWidget(self.match_case)
        options_layout.addWidget(self.whole_word)
        options_layout.addWidget(self.wrap_around)
        
        # Create buttons
        button_layout = QHBoxLayout()
        self.find_next_button = QPushButton("Find Next")
        self.find_next_button.clicked.connect(self.find_next)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.find_next_button)
        button_layout.addWidget(self.close_button)
        
        # Add all layouts to main layout
        layout.addLayout(search_layout)
        layout.addLayout(options_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def reset_search(self):
        editor = self.parent.get_current_editor()
        if editor:
            # Clear previous indicators
            editor.clearIndicatorRange(0, 0, editor.lines(), 
                                    len(editor.text()), 0)
    
    def find_next(self):
        editor = self.parent.get_current_editor()
        if not editor:
            return
            
        # Get search text
        text = self.search_input.text()
        if not text:
            return
            
        # Get search options
        case_sensitive = self.match_case.isChecked()
        whole_word = self.whole_word.isChecked()
        wrap = self.wrap_around.isChecked()
        
        # Get current cursor position
        line, index = editor.getCursorPosition()
        
        # Perform the search
        found = editor.findFirst(
            text,               # Text to find
            False,             # Regular expression
            case_sensitive,    # Case sensitive
            whole_word,        # Whole word only
            wrap,             # Wrap around document
            True,             # Forward search
            line,             # From line
            index,            # From index
            True              # Show & scroll to
        )
        
        if not found:
            QMessageBox.information(self, "Find", "No more occurrences found.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nghia Taarabt Notepad++")
        self.setGeometry(200, 100, 1000, 600)
        
        # Set window icon
        icon_path = "themes\\logoIcon.ico"
        self.setWindowIcon(QIcon(icon_path))
        
        # Initialize find dialog
        self.find_dialog = None
        
        # Initialize TabWidget
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabWidget)
        
        # Create actions, menu and toolbar
        self.create_actions()
        self.create_menubar()
        self.create_toolbar()
        
        # Create initial tab
        self.new_file()

    def create_actions(self):
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
        self.addAction(self.findAction)  # Make the shortcut work globally

    def handle_edit_action(self, action):
        editor = self.get_current_editor()
        if editor:
            if action == "cut":
                editor.cut()
            elif action == "copy":
                editor.copy()
            elif action == "paste":
                editor.paste()
            elif action == "undo":
                editor.undo()
            elif action == "redo":
                editor.redo()
            elif action == "select_all":
                editor.selectAll()

    def create_menubar(self):
        menubar = self.menuBar()

        # File Menu
        fileMenu = menubar.addMenu("File")
        fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addSeparator()
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

    def new_file(self):
        editor = CodeEditor()
        index = self.tabWidget.addTab(editor, "Untitled")
        self.tabWidget.setCurrentIndex(index)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*.*)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            editor = CodeEditor()
            editor.setText(text)
            index = self.tabWidget.addTab(editor, file_path.split('/')[-1])
            self.tabWidget.setCurrentIndex(index)
            editor.file_path = file_path

    def save_file(self):
        current_editor = self.get_current_editor()
        if current_editor is None:
            return

        if not hasattr(current_editor, 'file_path'):
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*.*)")
            if file_path:
                current_editor.file_path = file_path
            else:
                return

        try:
            with open(current_editor.file_path, 'w', encoding='utf-8') as f:
                f.write(current_editor.text())
            filename = current_editor.file_path.split('/')[-1]
            current_index = self.tabWidget.currentIndex()
            self.tabWidget.setTabText(current_index, filename)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot save file: {e}")

    def get_current_editor(self):
        current_index = self.tabWidget.currentIndex()
        if current_index == -1:
            return None
        editor = self.tabWidget.widget(current_index)
        return editor

    def close_tab(self, index):
        widget = self.tabWidget.widget(index)
        if widget:
            widget.deleteLater()
        self.tabWidget.removeTab(index)

    def about_app(self):
        QMessageBox.information(self, "About", "This is a Notepad++ style Text Editor, develop by Nghia Taarabt and Channel laptrinhdientu.com\nDebugger integration coming soon!")

    def show_find_dialog(self):
        if not self.find_dialog:
            self.find_dialog = FindDialog(self)
        
        # Get selected text if any
        editor = self.get_current_editor()
        if editor and editor.hasSelectedText():
            self.find_dialog.search_input.setText(editor.selectedText())
            self.find_dialog.search_input.selectAll()
        
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()
        self.find_dialog.search_input.setFocus()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

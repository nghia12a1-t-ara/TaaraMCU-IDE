from PyQt6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PyQt6.QtGui import QIcon
from pathlib import Path
from src.config.settings import ICONS_DIR
from src.ui.editor import CodeEditor
from src.ui.dialogs.find_dialog import FindDialog
from src.utils.file_handler import FileHandler
from src.utils.session import SessionManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_session()
        self.setup_connections()

    def setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Nghia Taarabt Notepad++")
        self.setGeometry(200, 100, 1000, 600)
        
        # Initialize TabWidget
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabWidget)

        # Optionally, add a new tab to start with
        self.new_file()  # Call this to create an initial empty tab

    def setup_connections(self):
        """Set up signal-slot connections."""
        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        # Add more connections as needed

    def on_tab_changed(self, index):
        """Handle tab change event."""
        # Logic for handling tab changes
        pass

    def close_tab(self, index):
        """Handle closing a tab."""
        # Logic for closing a tab
        pass

    def setup_session(self):
        """Load the session data."""
        self.session_manager = SessionManager(self)
        self.session_manager.load_session()

    def new_file(self):
        """Create a new empty file."""
        editor = CodeEditor()  # Assuming CodeEditor is defined correctly
        self.tabWidget.addTab(editor, "Untitled")
        self.tabWidget.setCurrentWidget(editor)
        
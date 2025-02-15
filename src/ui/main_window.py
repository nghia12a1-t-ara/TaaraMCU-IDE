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
        # UI setup code...
        pass

    def setup_session(self):
        self.session_manager = SessionManager(self)
        self.session_manager.load_session() 
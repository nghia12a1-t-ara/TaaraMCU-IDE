"""
CTags path configuration dialog
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal as Signal

from taara_ide.config import SettingsManager


class CtagsPathDialog(QDialog):
    """
    Dialog for setting the CTags executable path.
    
    Signals:
        path_set: Emitted when a valid path is set (path)
    """
    
    path_set = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsManager()
        
        self.setWindowTitle("CTags Path Settings")
        self.setMinimumWidth(400)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Instructions
        layout.addWidget(QLabel(
            "Please specify the path to the CTags executable.\n"
            "CTags is required for function list and symbol navigation."
        ))
        
        # Path input
        path_layout = QHBoxLayout()
        self._path_input = QLineEdit()
        self._path_input.setText(self._settings.get_ctags_path())
        path_layout.addWidget(self._path_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _browse(self) -> None:
        """Browse for CTags executable"""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select CTags Executable",
            "",
            "Executables (*.exe);;All Files (*)" if __import__('sys').platform == 'win32' else "All Files (*)"
        )
        if path:
            self._path_input.setText(path)
    
    def _save(self) -> None:
        """Validate and save the path"""
        path = self._path_input.text().strip()
        
        if not path:
            QMessageBox.warning(self, "Error", "Please enter a path.")
            return
        
        # Validate by trying to run ctags --version
        import subprocess
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise Exception("CTags returned error")
        except Exception as e:
            QMessageBox.warning(
                self, "Error", 
                f"Invalid CTags path or CTags not working:\n{e}"
            )
            return
        
        # Save the path
        self._settings.set_ctags_path(path)
        self.path_set.emit(path)
        QMessageBox.information(self, "Success", "CTags path saved successfully.")
        self.accept()

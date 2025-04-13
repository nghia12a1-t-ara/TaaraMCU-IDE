"""
STM32 Framework installation dialog
"""
import os
import subprocess
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QProgressBar, QTextEdit
)
from PyQt6.QtCore import pyqtSignal as Signal, QThread

from taara_ide.config import SettingsManager


class InstallWorker(QThread):
    """Worker thread for framework installation"""
    
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, target_path: str):
        super().__init__()
        self.target_path = target_path
    
    def run(self):
        try:
            framework_path = os.path.join(
                self.target_path, 
                "STM32_myDevelopment_Framework"
            )
            
            if os.path.exists(framework_path):
                self.finished.emit(False, "Framework directory already exists.")
                return
            
            os.makedirs(framework_path, exist_ok=True)
            
            self.progress.emit("Cloning repository...")
            
            result = subprocess.run(
                [
                    "git", "clone",
                    "https://github.com/nghia12a1-t-ara/STM32_myDevelopment_Framework.git",
                    framework_path
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.finished.emit(True, framework_path)
            else:
                self.finished.emit(False, result.stderr)
                
        except Exception as e:
            self.finished.emit(False, str(e))


class InstallFrameworkDialog(QDialog):
    """
    Dialog for installing the STM32 development framework.
    
    Signals:
        framework_installed: Emitted when framework is installed (path)
    """
    
    framework_installed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsManager()
        self._worker: Optional[InstallWorker] = None
        
        self.setWindowTitle("Install STM32 Framework")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._check_existing()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Instructions
        layout.addWidget(QLabel(
            "Install the TaaraFramework for STM32 development.\n"
            "This will clone the framework from GitHub."
        ))
        
        # Target directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Install to:"))
        
        self._dir_input = QLineEdit()
        self._dir_input.setPlaceholderText("Select installation directory...")
        dir_layout.addWidget(self._dir_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        dir_layout.addWidget(browse_btn)
        
        layout.addLayout(dir_layout)
        
        # Progress
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate
        self._progress.hide()
        layout.addWidget(self._progress)
        
        # Log output
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(100)
        self._log.hide()
        layout.addWidget(self._log)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._install_btn = QPushButton("Install")
        self._install_btn.clicked.connect(self._install)
        button_layout.addWidget(self._install_btn)
        
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._close_btn)
        
        layout.addLayout(button_layout)
    
    def _check_existing(self) -> None:
        """Check if framework is already installed"""
        path = self._settings.get("tools/stm32FrameworkPath")
        if path and os.path.exists(path):
            QMessageBox.information(
                self, "Already Installed",
                f"STM32 Framework is already installed at:\n{path}"
            )
            self._install_btn.setEnabled(False)
    
    def _browse(self) -> None:
        """Browse for installation directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Installation Directory"
        )
        if directory:
            self._dir_input.setText(directory)
    
    def _install(self) -> None:
        """Start installation"""
        target_path = self._dir_input.text().strip()
        
        if not target_path:
            QMessageBox.warning(self, "Error", "Please select an installation directory.")
            return
        
        # Check if git is available
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except Exception:
            QMessageBox.warning(
                self, "Error",
                "Git is not installed or not in PATH.\n"
                "Please install Git first."
            )
            return
        
        # Start installation
        self._install_btn.setEnabled(False)
        self._progress.show()
        self._log.show()
        
        self._worker = InstallWorker(target_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
    
    def _on_progress(self, message: str) -> None:
        """Handle progress update"""
        self._log.append(message)
    
    def _on_finished(self, success: bool, result: str) -> None:
        """Handle installation finished"""
        self._progress.hide()
        self._install_btn.setEnabled(True)
        
        if success:
            # Save framework path
            self._settings.set("tools/stm32FrameworkPath", result)
            
            self._log.append(f"Installation complete: {result}")
            QMessageBox.information(
                self, "Success",
                f"STM32 Framework installed successfully at:\n{result}"
            )
            self.framework_installed.emit(result)
            self.accept()
        else:
            self._log.append(f"Installation failed: {result}")
            QMessageBox.warning(
                self, "Error",
                f"Failed to install framework:\n{result}"
            )

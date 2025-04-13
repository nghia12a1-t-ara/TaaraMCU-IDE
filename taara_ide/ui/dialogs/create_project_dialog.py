"""
Create new project dialog
"""
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QComboBox, QMessageBox, QFormLayout, QWidget
)
from PyQt6.QtCore import pyqtSignal as Signal

from taara_ide.services import ProjectService
from taara_ide.config import SettingsManager


class CreateProjectDialog(QDialog):
    """
    Dialog for creating a new project.
    
    Signals:
        project_created: Emitted when project is created (project_path)
    """
    
    project_created = Signal(str)
    
    def __init__(
        self,
        project_service: ProjectService,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._project = project_service
        self._settings = SettingsManager()
        
        self.setWindowTitle("Create New Project")
        self.setMinimumWidth(450)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Project directory
        dir_layout = QHBoxLayout()
        self._dir_input = QLineEdit()
        self._dir_input.setPlaceholderText("Select project location...")
        dir_layout.addWidget(self._dir_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(browse_btn)
        
        form.addRow("Location:", dir_layout)
        
        # Project name
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("MyProject")
        form.addRow("Project Name:", self._name_input)
        
        # Target MCU
        self._mcu_combo = QComboBox()
        self._mcu_combo.setEditable(True)
        self._mcu_combo.addItems([
            "STM32F407VG",
            "STM32F103C8",
            "STM32F411CE",
            "STM32F746ZG",
            "STM32H743ZI"
        ])
        form.addRow("Target MCU:", self._mcu_combo)
        
        # Framework selection
        self._framework_combo = QComboBox()
        self._framework_combo.addItems([
            "None",
            "STM32 HAL (TaaraFramework)",
            "STM32 LL",
            "CMSIS Only"
        ])
        form.addRow("Framework:", self._framework_combo)
        
        layout.addLayout(form)
        
        # Use framework checkbox
        self._use_framework = QCheckBox("Use TaaraFramework template")
        self._use_framework.setChecked(True)
        self._use_framework.stateChanged.connect(self._on_framework_changed)
        layout.addWidget(self._use_framework)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self._create_project)
        button_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _browse_directory(self) -> None:
        """Browse for project directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Project Location"
        )
        if directory:
            self._dir_input.setText(directory)
    
    def _on_framework_changed(self, state: int) -> None:
        """Handle framework checkbox change"""
        self._framework_combo.setEnabled(state)
    
    def _create_project(self) -> None:
        """Create the project"""
        directory = self._dir_input.text().strip()
        name = self._name_input.text().strip()
        mcu = self._mcu_combo.currentText().strip()
        
        if not directory:
            QMessageBox.warning(self, "Error", "Please select a project location.")
            return
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a project name.")
            return
        
        # Determine framework
        framework = ""
        if self._use_framework.isChecked():
            idx = self._framework_combo.currentIndex()
            framework_map = {0: "", 1: "stm32-hal", 2: "stm32-ll", 3: "cmsis"}
            framework = framework_map.get(idx, "")
        
        # Create project path
        project_path = os.path.join(directory, name)
        
        # Check if already exists
        if os.path.exists(project_path):
            reply = QMessageBox.question(
                self, "Directory Exists",
                f"Directory '{project_path}' already exists. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Create project
        result = self._project.create_project(
            path=project_path,
            name=name,
            target_mcu=mcu,
            framework=framework
        )
        
        if result.success:
            QMessageBox.information(
                self, "Success",
                f"Project created successfully at:\n{project_path}"
            )
            self.project_created.emit(project_path)
            self.accept()
        else:
            QMessageBox.warning(
                self, "Error",
                f"Failed to create project:\n{result.error}"
            )

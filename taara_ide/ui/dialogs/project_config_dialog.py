"""
Project configuration dialog
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, 
    QFileDialog, QTabWidget, QWidget, QListWidget,
    QGroupBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal as Signal

from taara_ide.services import ProjectService
from taara_ide.config import SettingsManager


class ProjectConfigDialog(QDialog):
    """
    Project configuration dialog with tabbed interface.
    
    Signals:
        config_saved: Emitted when configuration is saved
    """
    
    config_saved = Signal()
    
    def __init__(
        self, 
        project_service: ProjectService,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._project = project_service
        self._settings = SettingsManager()
        
        self.setWindowTitle("Project Configuration")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Tab widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)
        
        # General tab
        self._tabs.addTab(self._create_general_tab(), "General")
        
        # Build tab
        self._tabs.addTab(self._create_build_tab(), "Build")
        
        # Paths tab
        self._tabs.addTab(self._create_paths_tab(), "Paths")
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_config)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Project name
        self._name_input = QLineEdit()
        layout.addRow("Project Name:", self._name_input)
        
        # Target MCU
        self._mcu_input = QLineEdit()
        layout.addRow("Target MCU:", self._mcu_input)
        
        # Framework
        self._framework_combo = QComboBox()
        self._framework_combo.addItems(["None", "STM32 HAL", "STM32 LL", "CMSIS"])
        layout.addRow("Framework:", self._framework_combo)
        
        return widget
    
    def _create_build_tab(self) -> QWidget:
        """Create build settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Optimization level
        self._optimize_combo = QComboBox()
        self._optimize_combo.addItems(["Debug (-Og)", "Release (-O2)", "Size (-Os)", "Speed (-O3)", "None (-O0)"])
        layout.addRow("Optimization:", self._optimize_combo)
        
        # Debug info
        self._debug_check = QCheckBox("Include debug information (-g)")
        self._debug_check.setChecked(True)
        layout.addRow("", self._debug_check)
        
        # Preprocessor defines
        self._defines_input = QLineEdit()
        self._defines_input.setPlaceholderText("e.g., STM32F407xx, USE_HAL_DRIVER")
        layout.addRow("Defines:", self._defines_input)
        
        # Extra compiler flags
        self._cflags_input = QLineEdit()
        self._cflags_input.setPlaceholderText("Additional compiler flags")
        layout.addRow("Compiler Flags:", self._cflags_input)
        
        # Extra linker flags
        self._ldflags_input = QLineEdit()
        self._ldflags_input.setPlaceholderText("Additional linker flags")
        layout.addRow("Linker Flags:", self._ldflags_input)
        
        return widget
    
    def _create_paths_tab(self) -> QWidget:
        """Create paths settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Source paths
        src_group = QGroupBox("Source Directories")
        src_layout = QVBoxLayout(src_group)
        self._src_list = QListWidget()
        src_layout.addWidget(self._src_list)
        src_btn_layout = QHBoxLayout()
        add_src_btn = QPushButton("Add")
        add_src_btn.clicked.connect(lambda: self._add_path(self._src_list))
        remove_src_btn = QPushButton("Remove")
        remove_src_btn.clicked.connect(lambda: self._remove_path(self._src_list))
        src_btn_layout.addWidget(add_src_btn)
        src_btn_layout.addWidget(remove_src_btn)
        src_btn_layout.addStretch()
        src_layout.addLayout(src_btn_layout)
        layout.addWidget(src_group)
        
        # Include paths
        inc_group = QGroupBox("Include Directories")
        inc_layout = QVBoxLayout(inc_group)
        self._inc_list = QListWidget()
        inc_layout.addWidget(self._inc_list)
        inc_btn_layout = QHBoxLayout()
        add_inc_btn = QPushButton("Add")
        add_inc_btn.clicked.connect(lambda: self._add_path(self._inc_list))
        remove_inc_btn = QPushButton("Remove")
        remove_inc_btn.clicked.connect(lambda: self._remove_path(self._inc_list))
        inc_btn_layout.addWidget(add_inc_btn)
        inc_btn_layout.addWidget(remove_inc_btn)
        inc_btn_layout.addStretch()
        inc_layout.addLayout(inc_btn_layout)
        layout.addWidget(inc_group)
        
        # Linker script
        ld_layout = QHBoxLayout()
        self._linker_script = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_linker_script)
        ld_layout.addWidget(QLabel("Linker Script:"))
        ld_layout.addWidget(self._linker_script)
        ld_layout.addWidget(browse_btn)
        layout.addLayout(ld_layout)
        
        return widget
    
    def _add_path(self, list_widget: QListWidget) -> None:
        """Add a path to the list"""
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            list_widget.addItem(path)
    
    def _remove_path(self, list_widget: QListWidget) -> None:
        """Remove selected path from list"""
        current = list_widget.currentRow()
        if current >= 0:
            list_widget.takeItem(current)
    
    def _browse_linker_script(self) -> None:
        """Browse for linker script"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Linker Script", "", "Linker Scripts (*.ld);;All Files (*)"
        )
        if path:
            self._linker_script.setText(path)
    
    def _load_config(self) -> None:
        """Load current project configuration"""
        if not self._project.config:
            return
        
        config = self._project.config
        
        # General
        self._name_input.setText(config.name)
        self._mcu_input.setText(config.target_mcu)
        
        # Find framework in combo
        framework_map = {"": 0, "stm32-hal": 1, "stm32-ll": 2, "cmsis": 3}
        self._framework_combo.setCurrentIndex(framework_map.get(config.framework, 0))
        
        # Build
        opt_map = {"Debug": 0, "Release": 1, "Size": 2, "Speed": 3, "None": 4}
        self._optimize_combo.setCurrentIndex(opt_map.get(config.optimization, 0))
        self._debug_check.setChecked(config.debug_info)
        self._defines_input.setText(", ".join(config.defines))
        self._cflags_input.setText(" ".join(config.compiler_flags))
        self._ldflags_input.setText(" ".join(config.linker_flags))
        
        # Paths
        self._src_list.clear()
        self._src_list.addItems(config.source_paths)
        self._inc_list.clear()
        self._inc_list.addItems(config.include_paths)
        self._linker_script.setText(config.linker_script)
    
    def _save_config(self) -> None:
        """Save configuration"""
        if not self._project.config:
            return
        
        # Parse optimization level
        opt_text = self._optimize_combo.currentText()
        opt_map = {
            "Debug (-Og)": "Debug",
            "Release (-O2)": "Release", 
            "Size (-Os)": "Size",
            "Speed (-O3)": "Speed",
            "None (-O0)": "None"
        }
        
        # Parse framework
        framework_map = {0: "", 1: "stm32-hal", 2: "stm32-ll", 3: "cmsis"}
        
        # Get paths from lists
        src_paths = [self._src_list.item(i).text() for i in range(self._src_list.count())]
        inc_paths = [self._inc_list.item(i).text() for i in range(self._inc_list.count())]
        
        # Parse defines
        defines_text = self._defines_input.text()
        defines = [d.strip() for d in defines_text.split(",") if d.strip()]
        
        # Update config
        self._project.update_config(
            name=self._name_input.text(),
            target_mcu=self._mcu_input.text(),
            framework=framework_map.get(self._framework_combo.currentIndex(), ""),
            optimization=opt_map.get(opt_text, "Debug"),
            debug_info=self._debug_check.isChecked(),
            defines=defines,
            compiler_flags=self._cflags_input.text().split(),
            linker_flags=self._ldflags_input.text().split(),
            source_paths=src_paths,
            include_paths=inc_paths,
            linker_script=self._linker_script.text()
        )
        
        # Save to file
        self._project.save_config()
        
        self.config_saved.emit()
        self.accept()

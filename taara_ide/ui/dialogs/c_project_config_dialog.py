"""
Dialog for editing C Project configuration (.cproject)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget,
    QComboBox, QCheckBox, QGroupBox, QFormLayout, QTextEdit,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

from taara_ide.core.compiler.c_project_config import CProjectConfig


class CProjectConfigDialog(QDialog):
    """Dialog for editing .cproject configuration"""
    
    def __init__(self, config: CProjectConfig, project_path: str, parent=None):
        super().__init__(parent)
        self.config = config
        self.project_path = project_path
        self.setWindowTitle(f"Project Configuration - {config.project_name}")
        self.resize(700, 600)
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_sources_tab(), "Sources")
        tabs.addTab(self._create_includes_tab(), "Includes")
        tabs.addTab(self._create_compiler_tab(), "Compiler")
        tabs.addTab(self._create_linker_tab(), "Linker")
        tabs.addTab(self._create_defines_tab(), "Defines")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.name_edit = QLineEdit()
        self.version_edit = QLineEdit()
        self.output_name_edit = QLineEdit()
        self.output_dir_edit = QLineEdit()
        self.output_type_combo = QComboBox()
        self.output_type_combo.addItems(["executable", "static_lib", "shared_lib"])
        
        self.active_config_combo = QComboBox()
        self.active_config_combo.addItems(["Debug", "Release"])
        
        layout.addRow("Project Name:", self.name_edit)
        layout.addRow("Version:", self.version_edit)
        layout.addRow("Output Name:", self.output_name_edit)
        layout.addRow("Output Directory:", self.output_dir_edit)
        layout.addRow("Output Type:", self.output_type_combo)
        layout.addRow("Active Configuration:", self.active_config_combo)
        
        return widget
    
    def _create_sources_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Source directories
        layout.addWidget(QLabel("Source Directories:"))
        self.source_dirs_list = QListWidget()
        layout.addWidget(self.source_dirs_list)
        
        btn_layout = QHBoxLayout()
        add_dir_btn = QPushButton("Add Directory")
        add_dir_btn.clicked.connect(lambda: self._add_to_list(self.source_dirs_list, "Select Source Directory", dir=True))
        remove_dir_btn = QPushButton("Remove")
        remove_dir_btn.clicked.connect(lambda: self._remove_from_list(self.source_dirs_list))
        btn_layout.addWidget(add_dir_btn)
        btn_layout.addWidget(remove_dir_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Source files
        layout.addWidget(QLabel("Additional Source Files:"))
        self.source_files_list = QListWidget()
        layout.addWidget(self.source_files_list)
        
        btn_layout2 = QHBoxLayout()
        add_file_btn = QPushButton("Add File")
        add_file_btn.clicked.connect(lambda: self._add_to_list(self.source_files_list, "Select Source File"))
        remove_file_btn = QPushButton("Remove")
        remove_file_btn.clicked.connect(lambda: self._remove_from_list(self.source_files_list))
        btn_layout2.addWidget(add_file_btn)
        btn_layout2.addWidget(remove_file_btn)
        btn_layout2.addStretch()
        layout.addLayout(btn_layout2)
        
        return widget
    
    def _create_includes_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Include Directories:"))
        self.include_dirs_list = QListWidget()
        layout.addWidget(self.include_dirs_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Directory")
        add_btn.clicked.connect(lambda: self._add_to_list(self.include_dirs_list, "Select Include Directory", dir=True))
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_from_list(self.include_dirs_list))
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def _create_compiler_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.compiler_combo = QComboBox()
        self.compiler_combo.addItems(["gcc", "g++", "clang", "clang++"])
        
        self.c_standard_combo = QComboBox()
        self.c_standard_combo.addItems(["c89", "c99", "c11", "c17"])
        
        self.cpp_standard_combo = QComboBox()
        self.cpp_standard_combo.addItems(["c++98", "c++11", "c++14", "c++17", "c++20"])
        
        self.optimization_combo = QComboBox()
        self.optimization_combo.addItems(["O0", "O1", "O2", "O3", "Os", "Og"])
        
        self.debug_symbols_check = QCheckBox()
        
        self.compiler_flags_edit = QTextEdit()
        self.compiler_flags_edit.setMaximumHeight(80)
        self.compiler_flags_edit.setPlaceholderText("One flag per line, e.g.:\n-Wall\n-Wextra\n-pedantic")
        
        layout.addRow("Compiler:", self.compiler_combo)
        layout.addRow("C Standard:", self.c_standard_combo)
        layout.addRow("C++ Standard:", self.cpp_standard_combo)
        layout.addRow("Optimization:", self.optimization_combo)
        layout.addRow("Debug Symbols:", self.debug_symbols_check)
        layout.addRow("Additional Flags:", self.compiler_flags_edit)
        
        return widget
    
    def _create_linker_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Libraries (e.g., m, pthread):"))
        self.libraries_list = QListWidget()
        layout.addWidget(self.libraries_list)
        
        btn_layout = QHBoxLayout()
        add_lib_btn = QPushButton("Add Library")
        add_lib_btn.clicked.connect(lambda: self._add_text_to_list(self.libraries_list, "Library Name"))
        remove_lib_btn = QPushButton("Remove")
        remove_lib_btn.clicked.connect(lambda: self._remove_from_list(self.libraries_list))
        btn_layout.addWidget(add_lib_btn)
        btn_layout.addWidget(remove_lib_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addWidget(QLabel("Linker Flags:"))
        self.linker_flags_edit = QTextEdit()
        self.linker_flags_edit.setMaximumHeight(80)
        self.linker_flags_edit.setPlaceholderText("One flag per line")
        layout.addWidget(self.linker_flags_edit)
        
        return widget
    
    def _create_defines_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Preprocessor Defines (e.g., DEBUG, USE_FEATURE):"))
        self.defines_list = QListWidget()
        layout.addWidget(self.defines_list)
        
        btn_layout = QHBoxLayout()
        add_def_btn = QPushButton("Add Define")
        add_def_btn.clicked.connect(lambda: self._add_text_to_list(self.defines_list, "Define Name"))
        remove_def_btn = QPushButton("Remove")
        remove_def_btn.clicked.connect(lambda: self._remove_from_list(self.defines_list))
        btn_layout.addWidget(add_def_btn)
        btn_layout.addWidget(remove_def_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def _load_config(self):
        """Load configuration into UI"""
        self.name_edit.setText(self.config.project_name)
        self.version_edit.setText(self.config.project_version)
        self.output_name_edit.setText(self.config.output_name)
        self.output_dir_edit.setText(self.config.output_dir)
        self.output_type_combo.setCurrentText(self.config.output_type)
        self.active_config_combo.setCurrentText(self.config.active_config)
        
        self.source_dirs_list.addItems(self.config.source_dirs)
        self.source_files_list.addItems(self.config.source_files)
        self.include_dirs_list.addItems(self.config.include_dirs)
        
        self.compiler_combo.setCurrentText(self.config.compiler)
        self.c_standard_combo.setCurrentText(self.config.c_standard)
        self.cpp_standard_combo.setCurrentText(self.config.cpp_standard)
        self.optimization_combo.setCurrentText(self.config.optimization_level)
        self.debug_symbols_check.setChecked(self.config.debug_symbols)
        self.compiler_flags_edit.setPlainText('\n'.join(self.config.compiler_flags))
        
        self.libraries_list.addItems(self.config.libraries)
        self.linker_flags_edit.setPlainText('\n'.join(self.config.linker_flags))
        
        self.defines_list.addItems(self.config.defines)
    
    def _save_config(self):
        """Save UI values to configuration"""
        self.config.project_name = self.name_edit.text()
        self.config.project_version = self.version_edit.text()
        self.config.output_name = self.output_name_edit.text()
        self.config.output_dir = self.output_dir_edit.text()
        self.config.output_type = self.output_type_combo.currentText()
        self.config.active_config = self.active_config_combo.currentText()
        
        self.config.source_dirs = [self.source_dirs_list.item(i).text() for i in range(self.source_dirs_list.count())]
        self.config.source_files = [self.source_files_list.item(i).text() for i in range(self.source_files_list.count())]
        self.config.include_dirs = [self.include_dirs_list.item(i).text() for i in range(self.include_dirs_list.count())]
        
        self.config.compiler = self.compiler_combo.currentText()
        self.config.c_standard = self.c_standard_combo.currentText()
        self.config.cpp_standard = self.cpp_standard_combo.currentText()
        self.config.optimization_level = self.optimization_combo.currentText()
        self.config.debug_symbols = self.debug_symbols_check.isChecked()
        
        flags_text = self.compiler_flags_edit.toPlainText().strip()
        self.config.compiler_flags = [f for f in flags_text.split('\n') if f.strip()]
        
        self.config.libraries = [self.libraries_list.item(i).text() for i in range(self.libraries_list.count())]
        
        linker_text = self.linker_flags_edit.toPlainText().strip()
        self.config.linker_flags = [f for f in linker_text.split('\n') if f.strip()]
        
        self.config.defines = [self.defines_list.item(i).text() for i in range(self.defines_list.count())]
    
    def _add_to_list(self, list_widget: QListWidget, title: str, dir: bool = False):
        """Add path to list"""
        import os
        if dir:
            path = QFileDialog.getExistingDirectory(self, title, self.project_path)
        else:
            path, _ = QFileDialog.getOpenFileName(self, title, self.project_path)
        
        if path:
            # Make relative to project if possible
            try:
                rel_path = os.path.relpath(path, self.project_path)
                list_widget.addItem(rel_path)
            except ValueError:
                list_widget.addItem(path)
    
    def _add_text_to_list(self, list_widget: QListWidget, prompt: str):
        """Add text item to list"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Add Item", f"{prompt}:")
        if ok and text:
            list_widget.addItem(text)
    
    def _remove_from_list(self, list_widget: QListWidget):
        """Remove selected items from list"""
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))
    
    def accept(self):
        """Save and close"""
        self._save_config()
        super().accept()

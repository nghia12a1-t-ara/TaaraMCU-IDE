"""
Debug Sidebar Panel - Debug controls and variable watch
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt
from PyQt6.QtGui import QIcon

from taara_ide.utils.resource import resource_path


class DebugSidebarPanel(QWidget):
    """Sidebar panel for debugging controls and watch"""
    
    # Signals
    start_debug = Signal()
    stop_debug = Signal()
    step_over = Signal()
    step_into = Signal()
    step_out = Signal()
    continue_debug = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the debug sidebar UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Run and Debug")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("Start")
        self._start_btn.clicked.connect(self.start_debug.emit)
        controls_layout.addWidget(self._start_btn)
        
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_debug.emit)
        controls_layout.addWidget(self._stop_btn)
        
        layout.addLayout(controls_layout)
        
        # Step controls
        step_layout = QHBoxLayout()
        
        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setEnabled(False)
        self._continue_btn.clicked.connect(self.continue_debug.emit)
        step_layout.addWidget(self._continue_btn)
        
        self._step_over_btn = QPushButton("Step Over")
        self._step_over_btn.setEnabled(False)
        self._step_over_btn.clicked.connect(self.step_over.emit)
        step_layout.addWidget(self._step_over_btn)
        
        layout.addLayout(step_layout)
        
        # Variables section
        var_label = QLabel("Variables")
        var_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(var_label)
        
        self._variables_tree = QTreeWidget()
        self._variables_tree.setHeaderLabels(["Name", "Value", "Type"])
        self._variables_tree.setColumnWidth(0, 100)
        self._variables_tree.setColumnWidth(1, 100)
        layout.addWidget(self._variables_tree)
        
        # Watch section
        watch_label = QLabel("Watch")
        watch_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(watch_label)
        
        self._watch_tree = QTreeWidget()
        self._watch_tree.setHeaderLabels(["Expression", "Value"])
        layout.addWidget(self._watch_tree)
        
        # Call stack section
        stack_label = QLabel("Call Stack")
        stack_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(stack_label)
        
        self._stack_tree = QTreeWidget()
        self._stack_tree.setHeaderHidden(True)
        layout.addWidget(self._stack_tree)
    
    def set_debugging(self, is_debugging: bool):
        """Update UI based on debug state"""
        self._start_btn.setEnabled(not is_debugging)
        self._stop_btn.setEnabled(is_debugging)
        self._continue_btn.setEnabled(is_debugging)
        self._step_over_btn.setEnabled(is_debugging)
    
    def update_variables(self, variables: list):
        """Update variables display"""
        self._variables_tree.clear()
        for var in variables:
            item = QTreeWidgetItem([
                var.get('name', ''),
                var.get('value', ''),
                var.get('type', '')
            ])
            self._variables_tree.addTopLevelItem(item)
    
    def update_call_stack(self, frames: list):
        """Update call stack display"""
        self._stack_tree.clear()
        for frame in frames:
            item = QTreeWidgetItem([f"{frame.get('function', '')} at {frame.get('file', '')}:{frame.get('line', '')}"])
            self._stack_tree.addTopLevelItem(item)

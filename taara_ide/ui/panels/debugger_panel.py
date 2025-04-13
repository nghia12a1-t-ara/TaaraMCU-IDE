"""
Debugger Panel - GDB debugging interface.
"""

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QTextEdit, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QLabel, QTreeWidget,
    QTreeWidgetItem, QSplitter, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal as Signal
from PyQt6.QtGui import QFont
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from taara_ide.core.debugger.gdb_controller import GDBController
    from taara_ide.services.debug_service import DebugService


class DebuggerPanel(QWidget):
    """
    GDB debugging panel with controls and output.
    
    Signals:
        breakpoint_added: Emitted when a breakpoint is added
        debug_started: Emitted when debugging session starts
        debug_stopped: Emitted when debugging session ends
    """
    
    breakpoint_added = Signal(str)  # location
    debug_started = Signal()
    debug_stopped = Signal()
    
    def __init__(self, debug_service: Optional['DebugService'] = None, parent=None):
        super().__init__(parent)
        self._debug_service = debug_service
        self._gdb: Optional['GDBController'] = None
        self._timer_id: Optional[int] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self._btn_start = QPushButton("Start")
        self._btn_stop = QPushButton("Stop")
        self._btn_continue = QPushButton("Continue")
        self._btn_step_over = QPushButton("Step Over")
        self._btn_step_into = QPushButton("Step Into")
        self._btn_step_out = QPushButton("Step Out")
        
        for btn in [self._btn_start, self._btn_stop, self._btn_continue,
                    self._btn_step_over, self._btn_step_into, self._btn_step_out]:
            controls_layout.addWidget(btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Breakpoint input
        bp_layout = QHBoxLayout()
        bp_layout.addWidget(QLabel("Breakpoint:"))
        self._bp_input = QLineEdit()
        self._bp_input.setPlaceholderText("e.g., main.c:42 or main")
        bp_layout.addWidget(self._bp_input)
        self._btn_add_bp = QPushButton("Add")
        bp_layout.addWidget(self._btn_add_bp)
        layout.addLayout(bp_layout)
        
        # Splitter for output and variables
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Output area
        output_group = QGroupBox("Debug Output")
        output_layout = QVBoxLayout(output_group)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Consolas", 10))
        output_layout.addWidget(self._output)
        splitter.addWidget(output_group)
        
        # Variables/Watch area
        vars_group = QGroupBox("Variables")
        vars_layout = QVBoxLayout(vars_group)
        self._vars_tree = QTreeWidget()
        self._vars_tree.setHeaderLabels(["Name", "Value", "Type"])
        vars_layout.addWidget(self._vars_tree)
        splitter.addWidget(vars_group)
        
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)
        
        # Initial state
        self._set_debug_state(False)
    
    def _connect_signals(self):
        """Connect button signals."""
        self._btn_start.clicked.connect(self._on_start)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_continue.clicked.connect(self._on_continue)
        self._btn_step_over.clicked.connect(self._on_step_over)
        self._btn_step_into.clicked.connect(self._on_step_into)
        self._btn_step_out.clicked.connect(self._on_step_out)
        self._btn_add_bp.clicked.connect(self._on_add_breakpoint)
        self._bp_input.returnPressed.connect(self._on_add_breakpoint)
    
    def _set_debug_state(self, debugging: bool):
        """Update UI based on debugging state."""
        self._btn_start.setEnabled(not debugging)
        self._btn_stop.setEnabled(debugging)
        self._btn_continue.setEnabled(debugging)
        self._btn_step_over.setEnabled(debugging)
        self._btn_step_into.setEnabled(debugging)
        self._btn_step_out.setEnabled(debugging)
    
    # Button handlers
    
    def _on_start(self):
        """Start debugging session."""
        if self._debug_service:
            result = self._debug_service.start_session()
            if result.success:
                self._gdb = self._debug_service._gdb
                self._set_debug_state(True)
                self._timer_id = self.startTimer(300)
                self.debug_started.emit()
                self._log("Debug session started")
            else:
                self._log(f"Error: {result.message}")
    
    def _on_stop(self):
        """Stop debugging session."""
        if self._debug_service:
            self._debug_service.stop_session()
        
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = None
        
        self._gdb = None
        self._set_debug_state(False)
        self.debug_stopped.emit()
        self._log("Debug session stopped")
    
    def _on_continue(self):
        """Continue execution."""
        if self._gdb:
            self._gdb.continue_exec()
    
    def _on_step_over(self):
        """Step over."""
        if self._gdb:
            self._gdb.step_over()
    
    def _on_step_into(self):
        """Step into."""
        if self._gdb:
            self._gdb.step_into()
    
    def _on_step_out(self):
        """Step out."""
        if self._gdb:
            self._gdb.step_out()
    
    def _on_add_breakpoint(self):
        """Add breakpoint."""
        location = self._bp_input.text().strip()
        if location:
            if self._gdb:
                self._gdb.set_breakpoint(location)
            self.breakpoint_added.emit(location)
            self._bp_input.clear()
            self._log(f"Breakpoint added: {location}")
    
    def timerEvent(self, event):
        """Poll GDB for output."""
        if self._gdb:
            responses = self._gdb.read_output()
            for r in responses:
                if r.get("type") != "console":
                    self._log(str(r))
    
    def _log(self, message: str):
        """Add message to output."""
        self._output.append(message)
    
    # Public API
    
    def set_debug_service(self, service: 'DebugService'):
        """Set the debug service."""
        self._debug_service = service
    
    def clear(self):
        """Clear output and variables."""
        self._output.clear()
        self._vars_tree.clear()

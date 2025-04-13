"""
Debug service
"""
import os
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.core.debugger import GDBController
from taara_ide.core.base import DebugStatus, BreakpointInfo, VariableInfo
from taara_ide.config import SettingsManager
from taara_ide.services.project_service import ProjectService


@dataclass
class DebugSession:
    """Debug session information"""
    executable: str
    target_address: str
    connected: bool = False
    current_file: str = ""
    current_line: int = 0


class DebugService(QObject):
    """
    Service for debugging operations.
    
    Signals:
        session_started: Emitted when debug session starts
        session_ended: Emitted when debug session ends
        execution_paused: Emitted when execution pauses (file, line, reason)
        execution_resumed: Emitted when execution continues
        breakpoint_added: Emitted when breakpoint is added
        breakpoint_removed: Emitted when breakpoint is removed
        variables_updated: Emitted when variables are updated
        output: Emitted for debugger output
        error: Emitted on error
    """
    
    session_started = Signal()
    session_ended = Signal()
    execution_paused = Signal(str, int, str)  # file, line, reason
    execution_resumed = Signal()
    breakpoint_added = Signal(BreakpointInfo)
    breakpoint_removed = Signal(int)  # breakpoint id
    variables_updated = Signal(list)
    output = Signal(str)
    error = Signal(str)
    
    def __init__(
        self,
        project_service: ProjectService,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._project = project_service
        self._settings = SettingsManager()
        self._debugger = GDBController(self)
        self._session: Optional[DebugSession] = None
        
        # Connect debugger signals
        self._debugger.connected.connect(self._on_connected)
        self._debugger.disconnected.connect(self._on_disconnected)
        self._debugger.stopped.connect(self._on_stopped)
        self._debugger.running.connect(self.execution_resumed.emit)
        self._debugger.output.connect(self.output.emit)
        self._debugger.error.connect(self.error.emit)
        self._debugger.variables_updated.connect(self.variables_updated.emit)
    
    @property
    def status(self) -> DebugStatus:
        return self._debugger.status
    
    @property
    def is_active(self) -> bool:
        return self._session is not None and self._session.connected
    
    @property
    def session(self) -> Optional[DebugSession]:
        return self._session
    
    def start_session(
        self,
        executable: Optional[str] = None,
        target_address: str = "localhost:3333"
    ) -> bool:
        """
        Start a debug session.
        
        Args:
            executable: Path to ELF file (uses project build output if None)
            target_address: GDB server address
        """
        if self.is_active:
            self.error.emit("Debug session already active")
            return False
        
        if not executable and self._project.is_open:
            # Use project's build output
            build_dir = os.path.join(self._project.path, "build")
            name = self._project.config.name.replace(" ", "_").lower()
            executable = os.path.join(build_dir, f"{name}.elf")
        
        if not executable or not os.path.exists(executable):
            self.error.emit("Executable not found. Build project first.")
            return False
        
        self._session = DebugSession(
            executable=executable,
            target_address=target_address
        )
        
        self.output.emit(f"Starting debug session: {executable}")
        
        success = self._debugger.connect(
            executable=executable,
            target_type="remote",
            target_address=target_address
        )
        
        return success
    
    def stop_session(self) -> None:
        """Stop current debug session"""
        if self._session:
            self._debugger.disconnect()
            self._session = None
    
    def run(self) -> None:
        """Start or continue execution"""
        if self.is_active:
            self._debugger.run()
    
    def pause(self) -> None:
        """Pause execution"""
        if self.is_active:
            self._debugger.pause()
    
    def step_over(self) -> None:
        """Step over"""
        if self.is_active:
            self._debugger.step_over()
    
    def step_into(self) -> None:
        """Step into"""
        if self.is_active:
            self._debugger.step_into()
    
    def step_out(self) -> None:
        """Step out"""
        if self.is_active:
            self._debugger.step_out()
    
    def add_breakpoint(
        self,
        file: str,
        line: int,
        condition: Optional[str] = None
    ) -> Optional[BreakpointInfo]:
        """Add a breakpoint"""
        bp = self._debugger.add_breakpoint(file, line, condition)
        if bp:
            self.breakpoint_added.emit(bp)
        return bp
    
    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """Remove a breakpoint"""
        success = self._debugger.remove_breakpoint(breakpoint_id)
        if success:
            self.breakpoint_removed.emit(breakpoint_id)
        return success
    
    def toggle_breakpoint(self, file: str, line: int) -> None:
        """Toggle breakpoint at location"""
        # Check if breakpoint exists at location
        for bp_id, bp in self._debugger._breakpoints.items():
            if bp.file == file and bp.line == line:
                self.remove_breakpoint(bp_id)
                return
        
        # Add new breakpoint
        self.add_breakpoint(file, line)
    
    def get_breakpoints(self) -> List[BreakpointInfo]:
        """Get all breakpoints"""
        return list(self._debugger._breakpoints.values())
    
    def evaluate(self, expression: str) -> None:
        """Evaluate an expression"""
        if self.is_active:
            self._debugger.evaluate(expression)
    
    def request_variables(self) -> None:
        """Request current variables"""
        if self.is_active:
            self._debugger.get_variables()
    
    def _on_connected(self) -> None:
        if self._session:
            self._session.connected = True
        self.session_started.emit()
        self.output.emit("Debug session connected")
    
    def _on_disconnected(self) -> None:
        self._session = None
        self.session_ended.emit()
        self.output.emit("Debug session ended")
    
    def _on_stopped(self, reason: str, file: str, line: int) -> None:
        if self._session:
            self._session.current_file = file
            self._session.current_line = line
        self.execution_paused.emit(file, line, reason)

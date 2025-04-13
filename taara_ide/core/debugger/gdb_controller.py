"""
GDB/MI debugger controller
"""
import os
import re
import subprocess
from typing import Optional, List, Dict, Callable
from threading import Thread
from queue import Queue, Empty

from PyQt6.QtCore import QObject, pyqtSignal as Signal, QTimer

from taara_ide.core.base import DebuggerBase, DebugStatus, BreakpointInfo, VariableInfo
from taara_ide.config.settings_manager import SettingsManager


class GDBController(DebuggerBase):
    """
    GDB debugger controller using MI (Machine Interface) protocol.
    """
    
    console_output = Signal(str)
    target_output = Signal(str)
    registers_updated = Signal(dict)
    memory_updated = Signal(int, bytes)
    stack_updated = Signal(list)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = SettingsManager()
        
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[Thread] = None
        self._running = False
        
        self._command_queue: Queue = Queue()
        self._response_callbacks: Dict[str, Callable] = {}
        self._token_counter = 0
        
        self._current_file: Optional[str] = None
        self._current_line: int = 0
    
    @property
    def gdb_path(self) -> str:
        return self._settings.get_gdb_path()
    
    def connect(
        self,
        executable: str,
        target_type: str = "remote",
        target_address: str = "localhost:3333",
        **kwargs
    ) -> bool:
        if self._process is not None:
            self.disconnect()
        
        self._status = DebugStatus.CONNECTING
        
        try:
            self._process = subprocess.Popen(
                [self.gdb_path, "--interpreter=mi3", executable],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self._running = True
            
            self._reader_thread = Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()
            
            if target_type == "remote":
                self._send_command(f"-target-select remote {target_address}")
            
            self._send_command("-file-symbol-file " + executable)
            
            self._status = DebugStatus.CONNECTED
            self.connected.emit()
            return True
            
        except Exception as e:
            self._status = DebugStatus.ERROR
            self.error.emit(str(e))
            return False
    
    def disconnect(self) -> None:
        if self._process:
            self._running = False
            self._send_command("-gdb-exit")
            
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            
            self._process = None
        
        self._status = DebugStatus.DISCONNECTED
        self.disconnected.emit()
    
    def run(self) -> None:
        if self._status == DebugStatus.CONNECTED:
            self._send_command("-exec-run")
        else:
            self._send_command("-exec-continue")
        self._status = DebugStatus.RUNNING
        self.running.emit()
    
    def pause(self) -> None:
        self._send_command("-exec-interrupt")
    
    def step_over(self) -> None:
        self._send_command("-exec-next")
    
    def step_into(self) -> None:
        self._send_command("-exec-step")
    
    def step_out(self) -> None:
        self._send_command("-exec-finish")
    
    def add_breakpoint(
        self,
        file: str,
        line: int,
        condition: Optional[str] = None
    ) -> Optional[BreakpointInfo]:
        location = f"{file}:{line}"
        cmd = f"-break-insert {location}"
        
        if condition:
            cmd = f"-break-insert -c \"{condition}\" {location}"
        
        self._send_command(cmd)
        
        bp = BreakpointInfo(
            id=len(self._breakpoints) + 1,
            file=file,
            line=line,
            enabled=True,
            condition=condition
        )
        self._breakpoints[bp.id] = bp
        return bp
    
    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        if breakpoint_id not in self._breakpoints:
            return False
        
        self._send_command(f"-break-delete {breakpoint_id}")
        del self._breakpoints[breakpoint_id]
        return True
    
    def get_variables(self, scope: str = "local") -> List[VariableInfo]:
        self._send_command("-stack-list-locals --simple-values")
        return []
    
    def evaluate(self, expression: str) -> Optional[str]:
        self._send_command(f"-data-evaluate-expression \"{expression}\"")
        return None
    
    def read_memory(self, address: int, size: int) -> None:
        self._send_command(f"-data-read-memory-bytes {hex(address)} {size}")
    
    def write_memory(self, address: int, data: bytes) -> None:
        hex_data = data.hex()
        self._send_command(f"-data-write-memory-bytes {hex(address)} {hex_data}")
    
    def get_registers(self) -> None:
        self._send_command("-data-list-register-values x")
    
    def get_backtrace(self) -> None:
        self._send_command("-stack-list-frames")
    
    def read_output(self) -> List[Dict]:
        """Read pending output (for compatibility with original API)"""
        results = []
        # Return empty list - output is handled via signals
        return results
    
    def set_breakpoint(self, location: str) -> None:
        """Set breakpoint at location (for compatibility)"""
        self._send_command(f"-break-insert {location}")
    
    def continue_exec(self) -> None:
        """Continue execution (for compatibility)"""
        self.run()
    
    def _send_command(self, command: str, callback: Optional[Callable] = None) -> int:
        if not self._process or not self._running:
            return -1
        
        token = self._token_counter
        self._token_counter += 1
        
        if callback:
            self._response_callbacks[str(token)] = callback
        
        full_command = f"{token}{command}\n"
        
        try:
            self._process.stdin.write(full_command)
            self._process.stdin.flush()
        except Exception as e:
            self.error.emit(f"Failed to send command: {e}")
        
        return token
    
    def _read_output(self) -> None:
        while self._running and self._process:
            try:
                line = self._process.stdout.readline()
                if not line:
                    break
                self._parse_output(line.strip())
            except Exception:
                break
        
        self._running = False
    
    def _parse_output(self, line: str) -> None:
        if not line:
            return
        
        if '^' in line:
            self._parse_result(line)
        elif line.startswith('*'):
            self._parse_async_exec(line)
        elif line.startswith('='):
            self._parse_async_notify(line)
        elif line.startswith('~'):
            text = self._extract_string(line[1:])
            self.console_output.emit(text)
        elif line.startswith('@'):
            text = self._extract_string(line[1:])
            self.target_output.emit(text)
        elif line.startswith('&'):
            text = self._extract_string(line[1:])
            self.output.emit(text)
    
    def _parse_result(self, line: str) -> None:
        match = re.match(r'(\d*)?\^(\w+)(?:,(.*))?', line)
        if match:
            token = match.group(1)
            status = match.group(2)
            data = match.group(3)
            
            if token and token in self._response_callbacks:
                callback = self._response_callbacks.pop(token)
                callback(status, data)
            
            if status == "error":
                error_msg = self._extract_value(data, "msg") if data else "Unknown error"
                self.error.emit(error_msg)
    
    def _parse_async_exec(self, line: str) -> None:
        match = re.match(r'\*(\w+)(?:,(.*))?', line)
        if match:
            status = match.group(1)
            data = match.group(2)
            
            if status == "stopped":
                self._status = DebugStatus.PAUSED
                reason = self._extract_value(data, "reason") if data else "unknown"
                
                frame_data = self._extract_value(data, "frame") if data else ""
                file = self._extract_value(frame_data, "fullname") or ""
                line_str = self._extract_value(frame_data, "line") or "0"
                
                self._current_file = file
                self._current_line = int(line_str) if line_str.isdigit() else 0
                
                self.stopped.emit(reason, file, self._current_line)
            
            elif status == "running":
                self._status = DebugStatus.RUNNING
                self.running.emit()
    
    def _parse_async_notify(self, line: str) -> None:
        pass
    
    def _extract_string(self, s: str) -> str:
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
    
    def _extract_value(self, data: str, key: str) -> Optional[str]:
        if not data:
            return None
        pattern = rf'{key}="([^"]*)"'
        match = re.search(pattern, data)
        return match.group(1) if match else None

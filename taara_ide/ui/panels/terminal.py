"""
Terminal Panel - Embedded terminal for command execution.
"""

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit
)
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal as Signal
import subprocess
import os
import queue
import shlex
from typing import Optional, Callable, List, TYPE_CHECKING

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class TerminalWorker(QThread):
    """Worker thread for executing shell commands."""
    
    result_ready = Signal(str, str)   # (log_type, message)
    command_finished = Signal(str)    # command string
    
    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self.command = command
    
    def run(self):
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if result.stdout:
                self.result_ready.emit("Info", result.stdout.strip())
            if result.stderr:
                self.result_ready.emit("Error", result.stderr.strip())
            if result.returncode != 0 and not result.stdout and not result.stderr:
                self.result_ready.emit("Error", f"Command failed with code {result.returncode}")
        except Exception as e:
            self.result_ready.emit("Error", str(e))
        finally:
            self.command_finished.emit(self.command)


class Terminal(QDockWidget):
    """
    Embedded terminal panel for executing commands.
    
    Features:
        - Command history navigation with up/down arrows
        - Async command execution
        - Command queue management
        - Built-in commands: cd, clear, help
    """
    
    def __init__(self, parent: Optional['MainWindow'] = None):
        super().__init__("Terminal", parent)
        self._parent = parent
        
        self._command_history: List[str] = []
        self._history_index: int = -1
        self._workers: List[TerminalWorker] = []
        self._command_queue: queue.Queue = queue.Queue()
        self._command_active: bool = False
        self._current_path: Optional[str] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setObjectName("TerminalDock")
        self.setMinimumHeight(100)
        self.setMaximumHeight(500)
        
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Output display
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Style output
        font = QFont("Consolas", 12)
        self._output.setFont(font)
        palette = self._output.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#1E1E1E"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#D4D4D4"))
        self._output.setPalette(palette)
        layout.addWidget(self._output)
        
        # Command input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter command here...")
        self._input.setFont(font)
        self._input.installEventFilter(self)
        layout.addWidget(self._input)
        
        self.setWidget(main_widget)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._input.returnPressed.connect(self._execute_input)
        self.visibilityChanged.connect(self._on_visibility_changed)
    
    def _on_visibility_changed(self, visible: bool):
        """Handle visibility change for action sync."""
        if self._parent and hasattr(self._parent, '_actions'):
            action = self._parent._actions.get('view.terminal')
            if action:
                action.setChecked(visible)
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for command history."""
        if obj == self._input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._navigate_history(1)
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._navigate_history(-1)
                return True
        return super().eventFilter(obj, event)
    
    def _navigate_history(self, direction: int):
        """Navigate command history."""
        new_index = self._history_index + direction
        if 0 <= new_index < len(self._command_history):
            self._history_index = new_index
            self._input.setText(self._command_history[new_index])
        elif new_index < 0:
            self._history_index = -1
            self._input.clear()
    
    def _get_prompt(self) -> str:
        """Get the current prompt string."""
        path = self._current_path or os.getcwd()
        return f"{path} >>> "
    
    # Public API
    
    def add_log(self, log_type: str, message: str):
        """
        Add a log entry to the terminal output.
        
        Args:
            log_type: One of "Debug", "Error", "Command", "Info"
            message: The message to display
        """
        colors = {
            "Debug": QColor("#00C0FF"),
            "Error": QColor("#FF6B6B"),
            "Command": QColor("#98C379"),
            "Info": QColor("#D4D4D4"),
        }
        
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._output.setTextCursor(cursor)
        
        # Prompt
        self._output.setTextColor(QColor("#E5C07B"))
        self._output.insertPlainText(self._get_prompt())
        
        # Message
        self._output.setTextColor(colors.get(log_type, QColor("#D4D4D4")))
        self._output.insertPlainText(f"{message}\n")
        self._output.ensureCursorVisible()
    
    def append_output(self, text: str):
        """Append text to terminal output."""
        self.add_log("Info", text)
    
    def run_command(self, command: str, on_finished: Optional[Callable] = None):
        """
        Execute a command asynchronously.
        
        Args:
            command: The command to execute
            on_finished: Optional callback when command completes
        """
        # Check for duplicate running commands
        if self._command_active and self._workers:
            running_cmd = self._workers[-1].command
            if running_cmd.strip() == command.strip():
                self.add_log("Debug", f"Ignored: '{command}' is already running.")
                return
        
        self._command_queue.put((command, on_finished))
        self._process_next_command()
    
    def _process_next_command(self):
        """Process the next command in queue."""
        if self._command_active or self._command_queue.empty():
            return
        
        command, on_finished = self._command_queue.get()
        self._command_active = True
        
        self.add_log("Command", command)
        
        worker = TerminalWorker(command)
        worker.result_ready.connect(self.add_log)
        
        def on_done(cmd):
            self._command_active = False
            self._command_queue.task_done()
            if on_finished:
                on_finished(cmd)
            self._process_next_command()
        
        worker.command_finished.connect(on_done)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()
    
    def execute(self, command: str):
        """Execute a command (alias for run_command)."""
        self.run_command(command)
    
    def _execute_input(self):
        """Execute command from input field."""
        command = self._input.text().strip()
        if not command:
            return
        
        # Add to history
        if not self._command_history or self._command_history[0] != command:
            self._command_history.insert(0, command)
        self._history_index = -1
        self._input.clear()
        
        # Handle built-in commands
        if self._handle_builtin(command):
            return
        
        self.run_command(command)
    
    def _handle_builtin(self, command: str) -> bool:
        """
        Handle built-in terminal commands.
        
        Returns:
            True if command was handled, False otherwise
        """
        parts = shlex.split(command)
        if not parts:
            return False
        
        cmd = parts[0].lower()
        
        if cmd == "clear":
            self._output.clear()
            return True
        elif cmd == "cd":
            if len(parts) > 1:
                path = parts[1]
                if os.path.isdir(path):
                    os.chdir(path)
                    self._current_path = os.getcwd()
                    self.add_log("Info", f"Changed directory to: {self._current_path}")
                else:
                    self.add_log("Error", f"Directory not found: {path}")
            else:
                self._current_path = os.path.expanduser("~")
                os.chdir(self._current_path)
                self.add_log("Info", f"Changed to home: {self._current_path}")
            return True
        elif cmd == "help":
            help_text = """
Built-in commands:
  clear  - Clear terminal output
  cd     - Change directory
  help   - Show this help message
            """
            self.add_log("Info", help_text.strip())
            return True
        
        return False
    
    def set_working_directory(self, path: str):
        """Set the current working directory."""
        if os.path.isdir(path):
            self._current_path = path
            os.chdir(path)
    
    def clear(self):
        """Clear terminal output."""
        self._output.clear()

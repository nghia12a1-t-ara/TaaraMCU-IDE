"""
Terminal Panel - Embedded terminal for command execution.
"""

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit
)
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal as Signal
import subprocess
import os
import queue
import shlex
import re
import sys
from typing import Optional, Callable, List, TYPE_CHECKING

from taara_ide.utils.process_utils import get_subprocess_flags

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class TerminalWorker(QThread):
    """Worker thread for executing shell commands."""
    
    result_ready = Signal(str, str)   # (log_type, message)
    command_finished = Signal(str)    # command string
    
    def __init__(self, command: str, working_dir: str = None, parent=None):
        super().__init__(parent)
        self.command = command
        self.working_dir = working_dir
    
    def run(self):
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.working_dir,
                **get_subprocess_flags()
            )
            if result.stdout:
                self.result_ready.emit("stdout", result.stdout)
            if result.stderr:
                self.result_ready.emit("stderr", result.stderr)
            if result.returncode != 0 and not result.stdout and not result.stderr:
                self.result_ready.emit("error", f"Command failed with code {result.returncode}")
            elif result.returncode == 0:
                self.result_ready.emit("success", "")
        except Exception as e:
            self.result_ready.emit("error", str(e))
        finally:
            self.command_finished.emit(self.command)


class TerminalColors:
    """Color scheme for terminal output - Git and shell colors."""
    
    # Base colors
    BACKGROUND = "#1E1E1E"
    TEXT = "#D4D4D4"
    PROMPT_PATH = "#569CD6"      # Blue for path
    PROMPT_SYMBOL = "#DCDCAA"    # Yellow for >>>
    
    # Log type colors
    COMMAND = "#98C379"          # Green for commands
    ERROR = "#F44747"            # Red for errors
    WARNING = "#FFCC00"          # Yellow for warnings
    SUCCESS = "#4EC9B0"          # Cyan for success
    INFO = "#D4D4D4"             # Gray for info
    DEBUG = "#9CDCFE"            # Light blue for debug
    
    # Git-specific colors
    GIT_BRANCH = "#C586C0"       # Purple for branch names
    GIT_ADD = "#98C379"          # Green for additions
    GIT_DELETE = "#F44747"       # Red for deletions
    GIT_MODIFIED = "#DCDCAA"     # Yellow for modified
    GIT_UNTRACKED = "#808080"    # Gray for untracked
    GIT_COMMIT = "#CE9178"       # Orange for commit hashes
    GIT_REMOTE = "#4FC1FF"       # Bright blue for remote
    GIT_TAG = "#D7BA7D"          # Gold for tags
    GIT_HEAD = "#569CD6"         # Blue for HEAD
    GIT_AUTHOR = "#9CDCFE"       # Light blue for author
    GIT_DATE = "#808080"         # Gray for dates
    
    # File colors
    FILE_HEADER = "#569CD6"      # Blue for file headers (diff)
    LINE_NUMBER = "#858585"      # Gray for line numbers


class Terminal(QDockWidget):
    """
    Embedded terminal panel for executing commands.
    
    Features:
        - Command history navigation with up/down arrows
        - Async command execution
        - Command queue management
        - Built-in commands: cd, clear, help
        - Syntax highlighting for git commands
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
        self._last_command: str = ""
        
        self._setup_ui()
        self._connect_signals()
        self._compile_git_patterns()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setObjectName("TerminalDock")
        self.setMinimumHeight(100)
        self.setMaximumHeight(500)
        
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Output display
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # Style output
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._output.setFont(font)
        
        self._output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {TerminalColors.BACKGROUND};
                color: {TerminalColors.TEXT};
                border: none;
                selection-background-color: #264F78;
                selection-color: #FFFFFF;
            }}
            QScrollBar:vertical {{
                background-color: #2D2D2D;
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #5A5A5A;
                min-height: 20px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #787878;
            }}
        """)
        layout.addWidget(self._output)
        
        # Command input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter command here...")
        self._input.setFont(font)
        self._input.installEventFilter(self)
        
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2D2D2D;
                color: {TerminalColors.TEXT};
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                padding: 6px 10px;
                selection-background-color: #264F78;
            }}
            QLineEdit:focus {{
                border-color: #007ACC;
            }}
        """)
        layout.addWidget(self._input)
        
        self.setWidget(main_widget)
    
    def _compile_git_patterns(self):
        """Compile regex patterns for git output highlighting."""
        self._git_patterns = [
            # Branch names
            (re.compile(r'\b(main|master|develop|feature/\S+|bugfix/\S+|hotfix/\S+|release/\S+)\b'), TerminalColors.GIT_BRANCH),
            (re.compile(r"^\* (.+)$", re.MULTILINE), TerminalColors.GIT_BRANCH),  # Current branch
            
            # Commit hashes
            (re.compile(r'\b([a-f0-9]{7,40})\b'), TerminalColors.GIT_COMMIT),
            
            # Remote references
            (re.compile(r'\b(origin|upstream|remote)/\S+'), TerminalColors.GIT_REMOTE),
            
            # Tags
            (re.compile(r'\btag:\s*(\S+)'), TerminalColors.GIT_TAG),
            (re.compile(r'^v?\d+\.\d+\.\d+', re.MULTILINE), TerminalColors.GIT_TAG),
            
            # HEAD reference
            (re.compile(r'\bHEAD\b'), TerminalColors.GIT_HEAD),
            
            # Git status patterns
            (re.compile(r'^(\+.*)$', re.MULTILINE), TerminalColors.GIT_ADD),
            (re.compile(r'^(-.*)$', re.MULTILINE), TerminalColors.GIT_DELETE),
            (re.compile(r'^\s*M\s+(.+)$', re.MULTILINE), TerminalColors.GIT_MODIFIED),
            (re.compile(r'^\?\?\s+(.+)$', re.MULTILINE), TerminalColors.GIT_UNTRACKED),
            (re.compile(r'^\s*A\s+(.+)$', re.MULTILINE), TerminalColors.GIT_ADD),
            (re.compile(r'^\s*D\s+(.+)$', re.MULTILINE), TerminalColors.GIT_DELETE),
            
            # Modified/new file in status
            (re.compile(r'modified:\s+(.+)$', re.MULTILINE), TerminalColors.GIT_MODIFIED),
            (re.compile(r'new file:\s+(.+)$', re.MULTILINE), TerminalColors.GIT_ADD),
            (re.compile(r'deleted:\s+(.+)$', re.MULTILINE), TerminalColors.GIT_DELETE),
            (re.compile(r'renamed:\s+(.+)$', re.MULTILINE), TerminalColors.GIT_MODIFIED),
            
            # Author and date
            (re.compile(r'^Author:\s*(.+)$', re.MULTILINE), TerminalColors.GIT_AUTHOR),
            (re.compile(r'^Date:\s*(.+)$', re.MULTILINE), TerminalColors.GIT_DATE),
            
            # Diff headers
            (re.compile(r'^diff --git .+$', re.MULTILINE), TerminalColors.FILE_HEADER),
            (re.compile(r'^@@.+@@', re.MULTILINE), TerminalColors.GIT_BRANCH),
            (re.compile(r'^index [a-f0-9]+\.\.[a-f0-9]+', re.MULTILINE), TerminalColors.LINE_NUMBER),
        ]
    
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
        # Shorten path if too long
        if len(path) > 50:
            parts = path.split(os.sep)
            if len(parts) > 3:
                path = os.sep.join(['...'] + parts[-2:])
        return path
    
    def _is_git_command(self, command: str) -> bool:
        """Check if command is a git command."""
        return command.strip().startswith('git ')
    
    def _format_with_colors(self, text: str, base_color: str, apply_git_colors: bool = False):
        """
        Format text with syntax highlighting.
        
        Args:
            text: Text to format
            base_color: Base color for text
            apply_git_colors: Whether to apply git-specific coloring
        """
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if not apply_git_colors:
            # Simple colored text
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(base_color))
            cursor.insertText(text, fmt)
        else:
            # Apply git patterns
            self._apply_git_highlighting(cursor, text, base_color)
        
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()
    
    def _apply_git_highlighting(self, cursor: QTextCursor, text: str, base_color: str):
        """Apply git-specific syntax highlighting to text."""
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if i > 0:
                cursor.insertText('\n')
            
            if not line:
                continue
            
            # Determine line color based on patterns
            line_color = base_color
            
            # Check for diff additions/deletions
            if line.startswith('+') and not line.startswith('+++'):
                line_color = TerminalColors.GIT_ADD
            elif line.startswith('-') and not line.startswith('---'):
                line_color = TerminalColors.GIT_DELETE
            elif line.startswith('@@'):
                line_color = TerminalColors.GIT_BRANCH
            elif line.startswith('commit '):
                line_color = TerminalColors.GIT_COMMIT
            elif line.startswith('Author:'):
                line_color = TerminalColors.GIT_AUTHOR
            elif line.startswith('Date:'):
                line_color = TerminalColors.GIT_DATE
            elif line.startswith('diff --git'):
                line_color = TerminalColors.FILE_HEADER
            elif line.startswith('index '):
                line_color = TerminalColors.LINE_NUMBER
            elif 'modified:' in line:
                line_color = TerminalColors.GIT_MODIFIED
            elif 'new file:' in line:
                line_color = TerminalColors.GIT_ADD
            elif 'deleted:' in line:
                line_color = TerminalColors.GIT_DELETE
            elif line.startswith('* '):
                line_color = TerminalColors.GIT_BRANCH
            elif line.strip().startswith('M ') or line.strip().startswith('A ') or line.strip().startswith('D '):
                # git status short format
                status = line.strip()[0]
                if status == 'M':
                    line_color = TerminalColors.GIT_MODIFIED
                elif status == 'A':
                    line_color = TerminalColors.GIT_ADD
                elif status == 'D':
                    line_color = TerminalColors.GIT_DELETE
            elif line.strip().startswith('??'):
                line_color = TerminalColors.GIT_UNTRACKED
            
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(line_color))
            cursor.insertText(line, fmt)
    
    def _write_prompt(self):
        """Write the prompt to output."""
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Path in blue
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(TerminalColors.PROMPT_PATH))
        cursor.insertText(self._get_prompt(), fmt)
        
        # Separator in yellow
        fmt.setForeground(QColor(TerminalColors.PROMPT_SYMBOL))
        cursor.insertText(" >>> ", fmt)
        
        self._output.setTextCursor(cursor)
    
    # Public API
    
    def add_log(self, log_type: str, message: str):
        """
        Add a log entry to the terminal output.
        
        Args:
            log_type: One of "stdout", "stderr", "error", "success", "command", "info", "debug", "warning"
            message: The message to display
        """
        if not message:
            return
        
        is_git = self._is_git_command(self._last_command)
        
        color_map = {
            "stdout": TerminalColors.INFO,
            "stderr": TerminalColors.ERROR,
            "error": TerminalColors.ERROR,
            "success": TerminalColors.SUCCESS,
            "command": TerminalColors.COMMAND,
            "info": TerminalColors.INFO,
            "debug": TerminalColors.DEBUG,
            "warning": TerminalColors.WARNING,
            "Error": TerminalColors.ERROR,
            "Info": TerminalColors.INFO,
            "Debug": TerminalColors.DEBUG,
            "Command": TerminalColors.COMMAND,
        }
        
        base_color = color_map.get(log_type, TerminalColors.INFO)
        
        # For commands, write prompt first
        if log_type in ("command", "Command"):
            self._write_prompt()
            self._format_with_colors(message + "\n", base_color, apply_git_colors=False)
        else:
            # Apply git coloring if this is git output
            self._format_with_colors(message + "\n", base_color, apply_git_colors=is_git)
    
    def append_output(self, text: str):
        """Append text to terminal output."""
        self.add_log("info", text)
    
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
                self.add_log("debug", f"Ignored: '{command}' is already running.")
                return
        
        self._command_queue.put((command, on_finished))
        self._process_next_command()
    
    def _process_next_command(self):
        """Process the next command in queue."""
        if self._command_active or self._command_queue.empty():
            return
        
        command, on_finished = self._command_queue.get()
        self._command_active = True
        self._last_command = command
        
        self.add_log("command", command)
        
        worker = TerminalWorker(command, self._current_path)
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
        
        if cmd == "clear" or cmd == "cls":
            self._output.clear()
            return True
        elif cmd == "cd":
            self._last_command = command
            self.add_log("command", command)
            if len(parts) > 1:
                path = parts[1]
                # Expand ~ and environment variables
                path = os.path.expanduser(os.path.expandvars(path))
                if not os.path.isabs(path):
                    path = os.path.join(self._current_path or os.getcwd(), path)
                path = os.path.normpath(path)
                
                if os.path.isdir(path):
                    os.chdir(path)
                    self._current_path = os.getcwd()
                    self.add_log("success", f"Changed directory to: {self._current_path}")
                else:
                    self.add_log("error", f"Directory not found: {path}")
            else:
                self._current_path = os.path.expanduser("~")
                os.chdir(self._current_path)
                self.add_log("success", f"Changed to home: {self._current_path}")
            return True
        elif cmd == "pwd":
            self._last_command = command
            self.add_log("command", command)
            self.add_log("info", self._current_path or os.getcwd())
            return True
        elif cmd == "help":
            self._last_command = command
            self.add_log("command", command)
            help_text = """Built-in commands:
  clear, cls  - Clear terminal output
  cd <path>   - Change directory
  pwd         - Print working directory
  help        - Show this help message

Shortcuts:
  Ctrl+T      - Toggle terminal
  Up/Down     - Navigate command history
  Enter       - Execute command"""
            self.add_log("info", help_text)
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
    
    def focus_input(self):
        """Focus the command input field."""
        self._input.setFocus()
        self.show()
        self.raise_()

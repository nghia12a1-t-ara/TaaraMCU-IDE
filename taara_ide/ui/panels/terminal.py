"""
Terminal Panel - Embedded terminal for command execution.
"""

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QComboBox, QPushButton,
    QLabel, QToolBar, QSplitter
)
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat, QIcon
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal as Signal
import subprocess
import os
import queue
import shlex
import re
import sys
from typing import Optional, Callable, List, TYPE_CHECKING

from taara_ide.utils.process_utils import get_subprocess_flags
from taara_ide.ui.panels.serial_port_manager import SerialPortManager
from taara_ide.ui.panels.terminal_log_filter import TerminalLogFilter, TerminalSearchHelper
from taara_ide.ui.panels.terminal_color_config import TerminalColorConfig

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class TerminalColors:
    """Color scheme for terminal output - Git and shell colors."""
    
    _colors = TerminalColorConfig.get_colors_from_settings()
    
    # Base colors
    BACKGROUND = _colors.get("background", "#1E1E1E")
    TEXT = _colors.get("text", "#D4D4D4")
    PROMPT_PATH = _colors.get("prompt_path", "#569CD6")
    PROMPT_SYMBOL = _colors.get("prompt_symbol", "#DCDCAA")
    
    # Log type colors
    COMMAND = _colors.get("command", "#98C379")
    ERROR = _colors.get("error", "#F44747")
    WARNING = _colors.get("warning", "#FFCC00")
    SUCCESS = _colors.get("success", "#4EC9B0")
    INFO = _colors.get("info", "#D4D4D4")
    DEBUG = _colors.get("debug", "#9CDCFE")
    
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
    
    @classmethod
    def reload_colors(cls):
        """Reload colors from settings."""
        cls._colors = TerminalColorConfig.get_colors_from_settings()
        cls.BACKGROUND = cls._colors.get("background", "#1E1E1E")
        cls.TEXT = cls._colors.get("text", "#D4D4D4")
        cls.PROMPT_PATH = cls._colors.get("prompt_path", "#569CD6")
        cls.PROMPT_SYMBOL = cls._colors.get("prompt_symbol", "#DCDCAA")
        cls.COMMAND = cls._colors.get("command", "#98C379")
        cls.ERROR = cls._colors.get("error", "#F44747")
        cls.WARNING = cls._colors.get("warning", "#FFCC00")
        cls.SUCCESS = cls._colors.get("success", "#4EC9B0")
        cls.INFO = cls._colors.get("info", "#D4D4D4")
        cls.DEBUG = cls._colors.get("debug", "#9CDCFE")


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


class Terminal(QDockWidget):
    """
    Embedded terminal panel for executing commands.
    
    Features:
        - Command history navigation with up/down arrows
        - Async command execution
        - Command queue management
        - Built-in commands: cd, clear, help
        - Syntax highlighting for git commands
        - Serial port communication (COM port)
        - Log filtering and search
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
        
        self._serial_manager = SerialPortManager(self)
        self._serial_mode = False  # Toggle between terminal and serial mode
        
        self._log_buffer = []  # Store all log entries for filtering
        self._active_filter = {'log_types': {'all'}, 'custom_pattern': ''}
        self._search_helper = None
        
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
        
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        self._filter_widget = TerminalLogFilter()
        self._filter_widget.setVisible(False)  # Hidden by default
        layout.addWidget(self._filter_widget)
        
        # Output display
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        self._search_helper = TerminalSearchHelper(self._output)
        
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
    
    def _create_toolbar(self) -> QWidget:
        """Create compact toolbar with mode on left, settings on right."""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(8)
        
        # Left side: Mode selection
        mode_label = QLabel("Mode:")
        toolbar_layout.addWidget(mode_label)
        
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Terminal", "Serial Port"])
        self._mode_combo.setMinimumWidth(100)
        toolbar_layout.addWidget(self._mode_combo)
        
        toolbar_layout.addStretch()  # Push settings to the right
        
        # Right side: Serial port settings (hidden by default)
        self._serial_settings_widget = QWidget()
        serial_settings_layout = QHBoxLayout(self._serial_settings_widget)
        serial_settings_layout.setContentsMargins(0, 0, 0, 0)
        serial_settings_layout.setSpacing(6)
        
        # Port selection with info
        port_label = QLabel("Port:")
        serial_settings_layout.addWidget(port_label)
        
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)
        serial_settings_layout.addWidget(self._port_combo)
        
        # Refresh ports button
        self._refresh_ports_btn = QPushButton()
        self._refresh_ports_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self._refresh_ports_btn.setToolTip("Refresh available ports")
        self._refresh_ports_btn.setMaximumWidth(28)
        serial_settings_layout.addWidget(self._refresh_ports_btn)
        
        # Separator
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #555;")
        serial_settings_layout.addWidget(sep1)
        
        # Baud rate
        baud_label = QLabel("Baud:")
        serial_settings_layout.addWidget(baud_label)
        
        self._baud_combo = QComboBox()
        self._baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self._baud_combo.setCurrentText("115200")
        self._baud_combo.setMinimumWidth(80)
        serial_settings_layout.addWidget(self._baud_combo)
        
        # Separator
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #555;")
        serial_settings_layout.addWidget(sep2)
        
        # Connect/Disconnect button
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setMinimumWidth(80)
        serial_settings_layout.addWidget(self._connect_btn)
        
        # Clear button
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(lambda: self._output.clear())
        serial_settings_layout.addWidget(self._clear_btn)
        
        # Color config button
        self._color_config_btn = QPushButton()
        self._color_config_btn.setIcon(QIcon.fromTheme("preferences-desktop-color"))
        self._color_config_btn.setToolTip("Customize terminal colors")
        self._color_config_btn.setMaximumWidth(28)
        serial_settings_layout.addWidget(self._color_config_btn)
        
        self._serial_settings_widget.setVisible(False)  # Hidden initially
        toolbar_layout.addWidget(self._serial_settings_widget)
        
        # Style toolbar
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #2D2D2D;
                border-radius: 4px;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
            }
            QComboBox {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #4C4C4C;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QComboBox:hover {
                border-color: #007ACC;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #CCCCCC;
                margin-right: 5px;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #4C4C4C;
                color: #808080;
            }
        """)
        
        return toolbar_widget

    def _connect_signals(self):
        """Connect internal signals."""
        self._input.returnPressed.connect(self._execute_input)
        
        self._serial_manager.data_received.connect(self._on_serial_data_received)
        self._serial_manager.error_occurred.connect(self._on_serial_error)
        self._serial_manager.connection_changed.connect(self._on_serial_connection_changed)
        
        # Terminal action buttons
        self._clear_btn.clicked.connect(self._clear_terminal)
        self._color_config_btn.clicked.connect(self._show_color_config)
        
        # Mode switching
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        
        # Serial port controls
        self._refresh_ports_btn.clicked.connect(self._refresh_ports)
        self._connect_btn.clicked.connect(self._toggle_serial_connection)
        
        # TerminalLogFilter widget handles its own signals internally

    def eventFilter(self, obj, event):
        """Handle key events for command history navigation"""
        if obj == self._input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            
            # Navigate command history with Up/Down arrows
            if key == Qt.Key.Key_Up:
                if self._command_history and self._history_index < len(self._command_history) - 1:
                    self._history_index += 1
                    self._input.setText(self._command_history[self._history_index])
                return True
            elif key == Qt.Key.Key_Down:
                if self._history_index > 0:
                    self._history_index -= 1
                    self._input.setText(self._command_history[self._history_index])
                elif self._history_index == 0:
                    self._history_index = -1
                    self._input.clear()
                return True
        
        return super().eventFilter(obj, event)

    def _on_mode_changed(self, mode: str):
        """Handle mode change between Terminal and Serial Port."""
        self._serial_mode = (mode == "Serial Port")
        self._serial_settings_widget.setVisible(self._serial_mode)
        self._filter_widget.setVisible(self._serial_mode)
        
        if self._serial_mode:
            self._refresh_ports()
            self._input.setPlaceholderText("Type and press Enter to send...")
        else:
            self._input.setPlaceholderText("Enter command here...")

    def _refresh_ports(self):
        """Refresh the list of available COM ports."""
        self._port_combo.clear()
        ports = self._serial_manager.get_available_ports()
        
        if not ports:
            self._port_combo.addItem("No COM Port")
            self._connect_btn.setEnabled(False)
        else:
            for port in ports:
                # Format: "COM3 - USB Serial Port (STMicroelectronics)"
                display_text = f"{port['name']}"
                if port['description']:
                    display_text += f" - {port['description']}"
                if port['manufacturer'] and port['manufacturer'] != 'Unknown':
                    display_text += f" ({port['manufacturer']})"
                
                self._port_combo.addItem(display_text, port['name'])  # Store actual name in data
            
            self._connect_btn.setEnabled(True)

    def _toggle_serial_connection(self):
        """Toggle serial port connection."""
        if self._serial_manager.is_connected():
            self._serial_manager.disconnect_port()
        else:
            if self._port_combo.count() == 0 or self._port_combo.currentText() == "No COM Port":
                self._append_output("[Terminal] No COM port available\n", TerminalColors.ERROR)
                return
            
            port_name = self._port_combo.currentData()  # Get stored port name
            if not port_name:
                port_name = self._port_combo.currentText().split(' ')[0]  # Fallback to parsing
            
            baud_rate = int(self._baud_combo.currentText())
            
            if self._serial_manager.connect_port(port_name, baud_rate):
                self._connect_btn.setText("Disconnect")
                self._connect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #C5000B;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #E81123;
                    }
                """)
                self._append_output(f"[Terminal] Connected to {port_name} at {baud_rate} baud\n", TerminalColors.SUCCESS)
            else:
                self._append_output(f"[Terminal] Failed to connect to {port_name}\n", TerminalColors.ERROR)
    
    def _on_serial_connection_changed(self, is_connected: bool):
        """Handle serial connection status change."""
        if not is_connected:
            self._connect_btn.setText("Connect")
            self._connect_btn.setStyleSheet("")  # Reset to default style

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
    
    def _execute_input(self):
        """Execute command from input field."""
        command = self._input.text().strip()
        if not command:
            return
        
        self._input.clear()
        
        if not self._command_history or self._command_history[0] != command:
            self._command_history.insert(0, command)
        self._history_index = -1
        
        if self._serial_mode and self._serial_manager.is_connected():
            # Send data via serial port
            if self._serial_manager.send_text(command):
                self.add_log("command", f"TX: {command}")
            else:
                self.add_log("error", "Failed to send data")
            return

        # Handle built-in commands
        if self._handle_builtin(command):
            return
        
        self.run_command(command)
    
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
        
        log_entry = {
            'type': log_type,
            'message': message,
            'is_git': is_git
        }
        self._log_buffer.append(log_entry)
        
        # Only display if it passes the filter
        if self._should_show_log(log_entry):
            self._display_log_entry(log_entry)
    
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
        self._log_buffer.clear()
        self._search_helper.clear()
    
    def focus_input(self):
        """Focus the command input field."""
        self._input.setFocus()
        self.show()
        self.raise_()
    
    def _open_color_config(self):
        """Open color configuration dialog."""
        dialog = TerminalColorConfig(self)
        dialog.colors_changed.connect(self._apply_custom_colors)
        dialog.exec()
    
    def _apply_custom_colors(self, colors: dict):
        """Apply custom colors to terminal."""
        # Reload color class
        TerminalColors.reload_colors()
        
        # Update output stylesheet
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
        
        # Re-render all logs with new colors
        self._apply_filter()

    def _on_serial_data_received(self, data: bytes):
        """Handle data received from serial port."""
        try:
            text = data.decode('utf-8', errors='replace')
            self.add_log("info", text.rstrip())
        except Exception as e:
            self.add_log("error", f"Error decoding data: {str(e)}")
    
    def _on_serial_error(self, error_message: str):
        """Handle serial port error."""
        self.add_log("error", error_message)
    
    def _append_output(self, text: str, color: str):
        """Append text to terminal output with specified color."""
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(text, fmt)
        
        self._output.setTextCursor(cursor)
        self._output.ensureCursorVisible()

    def _clear_terminal(self):
        """Clear terminal output."""
        self._output.clear()
        self._log_buffer.clear()
        self._search_helper.clear()
    
    def _show_color_config(self):
        """Open color configuration dialog."""
        dialog = TerminalColorConfig(self)
        dialog.colors_changed.connect(self._apply_custom_colors)
        dialog.exec()
    
    def _apply_filter(self):
        """Apply current filter to log buffer and refresh display."""
        self._output.clear()
        
        for log_entry in self._log_buffer:
            if self._should_show_log(log_entry):
                self._display_log_entry(log_entry)
    
    def _clear_filter(self):
        """Clear the current filter."""
        self._active_filter = {'log_types': {'all'}, 'custom_pattern': ''}
        self._apply_filter()
    
    def _display_log_entry(self, log_entry: dict):
        """Display a single log entry."""
        log_type = log_entry['type']
        message = log_entry['message']
        is_git = log_entry.get('is_git', False)
        
        color_map = {
            "stdout": TerminalColors.INFO,
            "stderr": TerminalColors.ERROR,
            "error": TerminalColors.ERROR,
            "success": TerminalColors.SUCCESS,
            "command": TerminalColors.COMMAND,
            "info": TerminalColors.INFO,
            "debug": TerminalColors.DEBUG,
            "warning": TerminalColors.WARNING,
        }
        
        base_color = color_map.get(log_type, TerminalColors.INFO)
        
        if log_type in ("command", "Command"):
            self._write_prompt()
            self._format_with_colors(message + "\n", base_color, apply_git_colors=False)
        else:
            self._format_with_colors(message + "\n", base_color, apply_git_colors=is_git)
    
    def _should_show_log(self, log_entry: dict) -> bool:
        """
        Check if a log entry should be displayed based on current filters.
        
        Args:
            log_entry: The log entry to check
            
        Returns:
            True if the log should be displayed, False otherwise
        """
        # Check log type filter
        log_types = self._active_filter.get('log_types', {'all'})
        if 'all' not in log_types:
            log_type = log_entry['type']
            # Map log types to filter categories
            type_mapping = {
                'error': 'errors',
                'stderr': 'errors',
                'warning': 'warnings',
                'info': 'info',
                'stdout': 'info',
                'success': 'info',
                'command': 'commands',
                'debug': 'info'
            }
            filter_type = type_mapping.get(log_type, 'info')
            if filter_type not in log_types:
                return False
        
        # Check custom pattern filter
        custom_pattern = self._active_filter.get('custom_pattern', '')
        if custom_pattern:
            message = log_entry['message']
            try:
                if not re.search(custom_pattern, message, re.IGNORECASE):
                    return False
            except re.error:
                # Invalid regex, treat as literal text
                if custom_pattern.lower() not in message.lower():
                    return False
        
        return True

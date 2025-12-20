"""
Terminal Panel - Embedded terminal for command execution.
"""

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QComboBox, QPushButton,
    QLabel, QToolBar, QSplitter
)
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QTextCharFormat, QIcon
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal as Signal, QTimer
import subprocess
import os
import queue
import shlex
import re
import sys
from typing import Optional, Callable, List, TYPE_CHECKING
from datetime import datetime

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
        
        self._serial_buffer = bytearray()
        
        self._log_buffer = []  # Store all log entries for filtering
        self._max_log_buffer_size = 10000  # Limit to prevent memory issues
        self._auto_scroll = True
        
        self._active_filter = {'log_types': {'all'}, 'custom_pattern': ''}
        self._search_helper = None  # Will be initialized after UI setup
        
        self._serial_hex_mode = False
        
        self._auto_reconnect_enabled = False
        
        self._setup_ui()
        self._connect_signals()
        self._compile_git_patterns()
        
        self._search_helper = TerminalSearchHelper(self._output)
    
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
        
        self._auto_scroll_btn = QPushButton("Auto Scroll: ON")
        self._auto_scroll_btn.setCheckable(True)
        self._auto_scroll_btn.setChecked(True)
        self._auto_scroll_btn.setToolTip("Toggle auto-scrolling to bottom")
        self._auto_scroll_btn.clicked.connect(self._toggle_auto_scroll)
        serial_settings_layout.addWidget(self._auto_scroll_btn)
        
        # Color config button
        self._color_config_btn = QPushButton()
        self._color_config_btn.setIcon(QIcon.fromTheme("preferences-desktop-color"))
        self._color_config_btn.setToolTip("Customize terminal colors")
        self._color_config_btn.setMaximumWidth(28)
        serial_settings_layout.addWidget(self._color_config_btn)
        
        self._serial_settings_widget.setVisible(False)  # Hidden initially
        toolbar_layout.addWidget(self._serial_settings_widget)
        
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
            QComboBox QAbstractItemView {
                background-color: #2D2D2D;
                color: #CCCCCC;
                selection-background-color: #007ACC;
                selection-color: #FFFFFF;
                border: 1px solid #4C4C4C;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3C3C3C;
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
            QPushButton:checked {
                background-color: #16825D;
            }
            QPushButton:checked:hover {
                background-color: #1E9670;
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
        
        self._filter_widget.filter_changed.connect(self._on_filter_changed)
        self._filter_widget.search_requested.connect(self._on_search_requested)
        self._filter_widget.search_next.connect(lambda: self._search_helper.next_match() if self._search_helper else None)
        self._filter_widget.search_previous.connect(lambda: self._search_helper.previous_match() if self._search_helper else None)

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
        """Compile regex patterns for git output formatting with optimization."""
        self._git_combined_pattern = re.compile(r'''
            (?P<branch>\b(?:main|master|develop|release/\S+|feature/\S+|bugfix/\S+|hotfix/\S+)\b)|
            (?P<commit>\b[a-f0-9]{7,40}\b)|
            (?P<remote>origin/\S+)|
            (?P<tag>v\d+\.\d+\.\d+)|
            (?P<add>^\+(?!\+\+).*$)|
            (?P<delete>^-(?!--).*$)|
            (?P<file_header>^(?:diff|index|---|\+\+\+)\s)|
            (?P<hunk_header>^@@.*@@)|
            (?P<status>^\s*(?:modified|deleted|added|renamed|copied):)
        ''', re.VERBOSE | re.MULTILINE)
    
    def _format_git_output(self, cursor: QTextCursor, text: str):
        """Format text with git syntax highlighting using combined pattern."""
        last_pos = 0
        for match in self._git_combined_pattern.finditer(text):
            start, end = match.span()
            
            # Insert text before the match with default color
            if start > last_pos:
                span_text = text[last_pos:start]
                cursor.insertHtml(f'<span style="color: {TerminalColors.TEXT};">{self._escape_html(span_text)}</span>')
            
            # Insert matched text with its specific color
            for group_name, group_value in match.groupdict().items():
                if group_value:
                    color = TerminalColors.TEXT  # Default if not specifically mapped
                    if group_name == 'branch': color = TerminalColors.GIT_BRANCH
                    elif group_name == 'commit': color = TerminalColors.GIT_COMMIT
                    elif group_name == 'remote': color = TerminalColors.GIT_REMOTE
                    elif group_name == 'tag': color = TerminalColors.GIT_TAG
                    elif group_name == 'add': color = TerminalColors.GIT_ADD
                    elif group_name == 'delete': color = TerminalColors.GIT_DELETE
                    elif group_name == 'file_header': color = TerminalColors.FILE_HEADER
                    elif group_name == 'hunk_header': color = TerminalColors.GIT_BRANCH
                    elif group_name == 'status': color = TerminalColors.GIT_MODIFIED # Default for status
                    
                    cursor.insertHtml(f'<span style="color: {color};">{self._escape_html(group_value)}</span>')
                    break # Only apply color for the first matched group
            
            last_pos = end
        
        # Insert remaining text after the last match
        if last_pos < len(text):
            cursor.insertHtml(f'<span style="color: {TerminalColors.TEXT};">{self._escape_html(text[last_pos:])}</span>')
        
        cursor.insertHtml("<br>") # Newline after each log entry
    
    def _get_log_color(self, log_type: str) -> str:
        """Get color based on log type."""
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
        return color_map.get(log_type, TerminalColors.INFO)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

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
        Add a log entry to the terminal.
        
        Args:
            log_type: Type of log (stdout, stderr, error, warning, info, command, success)
            message: Log message text
        """
        is_git = self._is_git_command()
        
        log_entry = {
            'type': log_type,
            'message': message,
            'is_git': is_git,
            'timestamp': datetime.now().isoformat()
        }
        
        self._log_buffer.append(log_entry)
        if len(self._log_buffer) > self._max_log_buffer_size:
            self._log_buffer.pop(0)  # Remove oldest entry
        
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
    
    def _show_color_config(self):
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
            self._serial_buffer.extend(data)
            
            # Process complete lines
            while b'\n' in self._serial_buffer:
                line, self._serial_buffer = self._serial_buffer.split(b'\n', 1)
                text = line.decode('utf-8', errors='replace').rstrip()
                
                if text:
                    if self._serial_hex_mode:
                        hex_str = ' '.join(f'{b:02X}' for b in line)
                        self.add_log("info", f"RX (HEX): {hex_str}")
                        self.add_log("info", f"RX (ASCII): {text}")
                    else:
                        self.add_log("info", f"RX: {text}")
        except Exception as e:
            self.add_log("error", f"Error decoding serial data: {str(e)}")
            self._serial_buffer.clear()
    
    def _on_serial_error(self, error_message: str):
        """Handle serial port errors."""
        self.add_log("error", f"Serial error: {error_message}")
        
        if "disconnected" in error_message.lower() or "lost" in error_message.lower():
            if self._auto_reconnect_enabled and not self._serial_manager.is_connected():
                self.add_log("warning", "Attempting auto-reconnect in 2 seconds...")
                QTimer.singleShot(2000, self._attempt_reconnect)

    def _on_filter_changed(self, filter_data: dict):
        """Handle filter changes from TerminalLogFilter widget."""
        self._active_filter = filter_data
        self._apply_filter()
    
    def _on_search_requested(self, text: str, case_sensitive: bool, use_regex: bool):
        """Handle search request from TerminalLogFilter widget."""
        if not self._search_helper:
            return
        
        total = self._search_helper.search(text, case_sensitive, use_regex)
        current = self._search_helper.get_current_match()
        self._filter_widget.update_match_count(current, total)

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
            if log_type not in log_types:
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
        """Display a single log entry in the output."""
        log_type = log_entry['type']
        message = log_entry['message']
        is_git = log_entry.get('is_git', False)
        
        cursor = self._output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        if is_git:
            self._format_git_output(cursor, message)
        else:
            color = self._get_log_color(log_type)
            cursor.insertHtml(f'<span style="color: {color};">{self._escape_html(message)}</span><br>')
        
        if self._auto_scroll:
            self._output.ensureCursorVisible()

    def _is_git_command(self) -> bool:
        """Check if the last command was a git command."""
        return self._last_command.strip().startswith('git ')
    
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
    
    def _get_prompt(self) -> str:
        """Get the current prompt string."""
        path = self._current_path or os.getcwd()
        # Shorten path if too long
        if len(path) > 50:
            parts = path.split(os.sep)
            if len(parts) > 3:
                path = os.sep.join(['...'] + parts[-2:])
        return path
    
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
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to serial port."""
        if not self._serial_manager.is_connected():
            self.add_log("info", "Attempting to reconnect...")
            try:
                self._toggle_serial_connection()
            except Exception as e:
                self.add_log("error", f"Reconnection failed: {str(e)}")
    
    def export_logs(self, filepath: str):
        """
        Export current logs to file.
        
        Args:
            filepath: Path to export file
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self._log_buffer:
                    timestamp = entry.get('timestamp', '')
                    log_type = entry['type']
                    message = entry['message']
                    f.write(f"[{timestamp}] [{log_type.upper()}] {message}\n")
            self.add_log("success", f"Logs exported to {filepath}")
        except Exception as e:
            self.add_log("error", f"Failed to export logs: {str(e)}")
    
    def set_auto_scroll(self, enabled: bool):
        """Enable or disable auto-scrolling."""
        self._auto_scroll = enabled
        self._auto_scroll_btn.setChecked(enabled)
        self._auto_scroll_btn.setText(f"Auto Scroll: {'ON' if enabled else 'OFF'}")
    
    def set_hex_view_mode(self, enabled: bool):
        """Enable or disable hex view mode for serial data."""
        self._serial_hex_mode = enabled
    
    def set_auto_reconnect(self, enabled: bool):
        """Enable or disable auto-reconnect for serial port."""
        self._auto_reconnect_enabled = enabled

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

    def _toggle_auto_scroll(self):
        """Toggle auto-scrolling on/off."""
        self._auto_scroll = self._auto_scroll_btn.isChecked()
        if self._auto_scroll:
            self._auto_scroll_btn.setText("Auto Scroll: ON")
            # Scroll to bottom immediately
            scrollbar = self._output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            self._auto_scroll_btn.setText("Auto Scroll: OFF")

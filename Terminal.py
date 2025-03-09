from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QScrollBar
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor
from PyQt6.QtCore import Qt, QEvent
import subprocess
import os

class Terminal(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Terminal", parent)
        self.parent = parent

        # Main widget for QDockWidget
        main_widget = QWidget()
        self.setObjectName("TerminalDock")
        layout = QVBoxLayout(main_widget)

        # Create QTextEdit to display log/output with black background
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # Enable smooth scrolling
        scroll_bar = self.output_display.verticalScrollBar()
        scroll_bar.setSingleStep(1)
        scroll_bar.setPageStep(10)

        # Set black background and default text color
        palette = self.output_display.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#C0C0C0"))
        self.output_display.setPalette(palette)

        # Set font (Consolas or Lucida Console)
        font = QFont("Consolas", 12)
        self.output_display.setFont(font)

        layout.addWidget(self.output_display)

        # Create QLineEdit for command input
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command here (type 'help' for commands)...")
        self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.installEventFilter(self)
        layout.addWidget(self.command_input)

        self.setWidget(main_widget)
        self.setMinimumHeight(100)
        self.setMaximumHeight(500)

        self.command_history = []
        self.history_index = -1

        self.visibilityChanged.connect(self.on_terminal_visibility_changed)

    def on_terminal_visibility_changed(self, visible):
        """Handle when Terminal is hidden/shown (including clicking the 'X' button)."""
        if hasattr(self.parent, 'toggleterminalAction'):
            self.parent.toggleterminalAction.setChecked(visible)

    def get_prompt(self):
        """Tạo dấu nhắc lệnh với thư mục hiện tại và ký hiệu >>>."""
        cwd = os.getcwd()
        return f"{cwd} >>> "

    def append_colored_text(self, text, color):
        """Thêm văn bản với màu sắc vào QTextEdit."""
        self.output_display.setTextColor(color)
        self.output_display.append(text)
        self.output_display.ensureCursorVisible()

    def eventFilter(self, obj, event):
        """Catch the Up/Down key event to browse command history."""
        if obj == self.command_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                if self.history_index + 1 < len(self.command_history):
                    self.history_index += 1
                    self.command_input.setText(self.command_history[self.history_index])
                return True
            elif event.key() == Qt.Key.Key_Down:
                if self.history_index >= 0:
                    self.history_index -= 1
                    if self.history_index == -1:
                        self.command_input.clear()
                    else:
                        self.command_input.setText(self.command_history[self.history_index])
                return True
        return super().eventFilter(obj, event)

    def add_log(self, log_type, message, prefix=True):
        """Add a log or output to the terminal with color based on log type."""
        # Get the current directory as a prompt
        prompt = self.get_prompt() if prefix else ""

        # Format log: Prompt + Message
        log_message = f"{prompt}{message}"

        # Set color based on log type
        if log_type == "Debug":
            color = QColor("#00C0FF")  # Light blue
        elif log_type == "Error":
            color = QColor("#FF0000")  # Red
        elif log_type == "Info":
            color = QColor("#C0C0C0")  # Light gray
        elif log_type == "Command":
            color = QColor("#00FF00")  # Green
        else:
            color = QColor("#808080")  # Gray for undefined type

        # Display prompt in yellow, message in specified color
        self.output_display.setTextColor(QColor("#FFFF00"))  # Yellow for prompt
        self.output_display.insertPlainText(prompt)
        self.output_display.setTextColor(color)
        self.output_display.insertPlainText(f"{message}\n")
        self.output_display.ensureCursorVisible()

    def clear_log(self):
        """Clear all content in the terminal."""
        self.output_display.clear()

    def execute_command(self):
        """Execute the user's command entered in QLineEdit."""
        command = self.command_input.text().strip()
        if not command:
            return

        # Add command to history
        if not self.command_history or self.command_history[0] != command:
            self.command_history.insert(0, command)
        self.history_index = -1

        # Display the command with prompt in green
        self.add_log("Command", command)

        command_parts = command.split()
        cmd = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []

        if cmd == "clear":
            self.clear_log()
        elif cmd == "help":
            help_text = (
                "Available commands:\n"
                "  help - Show this help message\n"
                "  clear - Clear the terminal\n"
                "  open <file_path> - Open a file in the editor\n"
                "  project - Show current project directory\n"
                "  cd <dir> - Change current working directory\n"
                "  cd. - Change to current opened file directory\n"
                "  dir/ls - List files in current directory\n"
                "  (Other system commands like 'echo', 'type' are also supported)"
            )
            self.add_log("Info", help_text, prefix=False)
        elif cmd == "cd.":
            # Get current editor and its file path
            current_editor = self.parent.get_current_editor()
            if current_editor and hasattr(current_editor, 'file_path'):
                try:
                    new_dir = os.path.dirname(current_editor.file_path)
                    os.chdir(new_dir)
                    self.add_log("Info", f"Changed directory to: {os.getcwd()}", prefix=False)
                except Exception as e:
                    self.add_log("Error", f"Failed to change directory: {str(e)}", prefix=False)
            else:
                self.add_log("Error", "No file currently open or file has not been saved", prefix=False)
        elif cmd == "cd":
            if not args:
                self.add_log("Error", "Usage: cd <directory>", prefix=False)
            else:
                try:
                    new_dir = args[0]
                    os.chdir(new_dir)
                    self.add_log("Info", f"Changed directory to: {os.getcwd()}", prefix=False)
                except Exception as e:
                    self.add_log("Error", f"Failed to change directory: {str(e)}", prefix=False)
        elif cmd in ["ls", "dir"]:
            try:
                # Get the target directory (current directory if no args provided)
                target_dir = args[0] if args else "."
                
                # Get list of all items in directory
                items = os.listdir(target_dir)
                
                # Sort items (directories first, then files)
                dirs = []
                files = []
                for item in items:
                    full_path = os.path.join(target_dir, item)
                    if os.path.isdir(full_path):
                        dirs.append(f"{item}/")  # Add / to indicate directories
                    else:
                        files.append(item)
                
                # Combine and sort the lists
                sorted_items = sorted(dirs) + sorted(files)
                
                # Format the output in columns
                if sorted_items:
                    output = "  ".join(sorted_items)  # Simple space-separated output
                    self.add_log("Info", output, prefix=False)
                else:
                    self.add_log("Info", "Directory is empty", prefix=False)
            except Exception as e:
                self.add_log("Error", f"Error listing directory: {str(e)}", prefix=False)
        elif cmd == "open":
            if not args:
                self.add_log("Error", "Usage: open <file_path>", prefix=False)
            else:
                try:
                    self.parent.open_file(args[0])
                    self.add_log("Info", f"Opened file: {args[0]}", prefix=False)
                except Exception as e:
                    self.add_log("Error", f"Failed to open file {args[0]}: {str(e)}", prefix=False)
        else:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                if result.stdout:
                    self.add_log("Info", result.stdout.rstrip(), prefix=False)
                if result.stderr:
                    self.add_log("Error", result.stderr.rstrip(), prefix=False)
                if result.returncode != 0 and not result.stdout and not result.stderr:
                    self.add_log("Error", f"Command failed with return code {result.returncode}", prefix=False)
            except Exception as e:
                self.add_log("Error", f"Failed to execute system command: {str(e)}", prefix=False)

        self.command_input.clear()

    def exe_first_cmd(self):
        """Execute first command - cd."""
        current_editor = self.parent.get_current_editor()
        if current_editor and hasattr(current_editor, 'file_path'):
            try:
                new_dir = os.path.dirname(current_editor.file_path)
                os.chdir(new_dir)
                self.add_log("Info", f"Changed directory to: {os.getcwd()}", prefix=False)
            except Exception as e:
                self.add_log("Error", f"Failed to change directory: {str(e)}", prefix=False)
        else:
            self.add_log("Error", "No file currently open or file has not been saved", prefix=False)

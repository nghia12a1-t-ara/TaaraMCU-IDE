from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QScrollBar
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor
from PyQt6.QtCore import Qt, QEvent
import subprocess
import os
import pyte

class Console(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Console", parent)
        self.parent = parent

        # Initialize pyte screen and stream with larger buffer
        self.screen = pyte.Screen(120, 10000)  # Increased width and much larger height
        self.stream = pyte.Stream(self.screen)
        self.history_buffer = []  # Store command output history
        
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

        # Set black background and font similar to Command Prompt
        palette = self.output_display.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#C0C0C0"))
        self.output_display.setPalette(palette)

        # Set font (Consolas or Lucida Console)
        font = QFont("Consolas", 10)
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
        self.setMaximumHeight(500)  # Increased maximum height

        self.command_history = []
        self.history_index = -1

    def update_display(self):
        """Update the display with the current screen content and history"""
        # Combine history buffer with current screen content
        display_text = ""
        
        # Add history buffer
        for line in self.history_buffer:
            display_text += line + "\n"
            
        # Add current screen content
        for line in self.screen.display:
            if line.strip():  # Only add non-empty lines
                display_text += line + "\n"
                
        # Update the display
        self.output_display.setText(display_text.rstrip())
        
        # Move cursor to end and scroll to bottom
        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_display.setTextCursor(cursor)
        self.output_display.ensureCursorVisible()

    def process_output(self, output):
        """Process output through pyte and update display"""
        # Add current screen content to history before processing new output
        for line in self.screen.display:
            if line.strip():  # Only store non-empty lines
                self.history_buffer.append(line)
        
        # Keep history buffer size reasonable (last 1000 lines)
        if len(self.history_buffer) > 1000:
            self.history_buffer = self.history_buffer[-1000:]
            
        # Process new output
        self.stream.feed(output)
        self.update_display()

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
        """Add a log or output to the console with color based on log type."""
        # Get the current directory as a prefix
        cwd = os.getcwd()
        prompt = f"{cwd}> " if prefix else ""

        # Format log: Prefix + Message
        log_message = f"{prompt}{message}"

        # Set color based on log type (good contrast on black background)
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

        # Set color for text
        self.output_display.setTextColor(color)
        # Add log to QTextEdit
        self.output_display.append(log_message)
        # Scroll to the last line
        self.output_display.ensureCursorVisible()

    def clear_log(self):
        """Clear all content in the console."""
        self.screen.reset()
        self.history_buffer = []  # Clear history buffer
        self.update_display()

    def execute_command(self):
        """Execute the user's command entered in QLineEdit."""
        command = self.command_input.text().strip()
        if not command:
            return

        if not self.command_history or self.command_history[0] != command:
            self.command_history.insert(0, command)
        self.history_index = -1

        # Feed the command to pyte
        self.stream.feed(f"{os.getcwd()}> {command}\r\n")

        command_parts = command.split()
        cmd = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []

        if cmd == "clear":
            self.screen.reset()
            self.update_display()
        elif cmd == "help":
            help_text = (
                "Available commands:\r\n"
                "  help - Show this help message\r\n"
                "  clear - Clear the console\r\n"
                "  open <file_path> - Open a file in the editor\r\n"
                "  project - Show current project directory\r\n"
                "  cd <dir> - Change current working directory\r\n"
                "  cd. - Change to current opened file directory\r\n"
                "  dir/ls - List files in current directory\r\n"
                "  (Other system commands like 'echo', 'type' are also supported)\r\n"
            )
            self.stream.feed(help_text)
            self.update_display()
        elif cmd == "cd.":
            # Get current editor and its file path
            current_editor = self.parent.get_current_editor()
            if current_editor and hasattr(current_editor, 'file_path'):
                try:
                    new_dir = os.path.dirname(current_editor.file_path)
                    os.chdir(new_dir)
                    self.stream.feed(f"Changed directory to: {os.getcwd()}\r\n")
                except Exception as e:
                    self.stream.feed(f"\x1b[31mFailed to change directory: {str(e)}\x1b[0m\r\n")
            else:
                self.stream.feed("\x1b[31mNo file currently open or file has not been saved\x1b[0m\r\n")
            self.update_display()
        elif cmd == "cd":
            if not args:
                self.stream.feed("Error: Usage: cd <directory>\r\n")
            else:
                try:
                    new_dir = args[0]
                    os.chdir(new_dir)
                    self.stream.feed(f"Changed directory to: {os.getcwd()}\r\n")
                except Exception as e:
                    self.stream.feed(f"Error: Failed to change directory: {str(e)}\r\n")
            self.update_display()
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
                        dirs.append(f"\x1b[36m{item}/\x1b[0m")  # Blue color for directories
                    else:
                        files.append(f"\x1b[37m{item}\x1b[0m")  # White color for files
                
                # Combine and sort the lists
                sorted_items = sorted(dirs) + sorted(files)
                
                # Format the output in columns
                if sorted_items:
                    # Calculate the maximum width needed
                    max_width = max(len(item) + 2 for item in sorted_items)  # +2 for spacing
                    term_width = self.screen.columns
                    cols = max(1, term_width // max_width)
                    
                    # Create the formatted output
                    output = ""
                    for i, item in enumerate(sorted_items):
                        output += f"{item:<{max_width}}"
                        if (i + 1) % cols == 0:
                            output += "\r\n"
                    output += "\r\n"
                    
                    self.stream.feed(output)
                else:
                    self.stream.feed("Directory is empty\r\n")
                    
            except Exception as e:
                self.stream.feed(f"\x1b[31mError listing directory: {str(e)}\x1b[0m\r\n")
            self.update_display()
        elif cmd == "open":
            if not args:
                self.stream.feed("Error: Usage: open <file_path>\r\n")
            else:
                try:
                    self.parent.open_file(args[0])
                    self.stream.feed(f"Opened file: {args[0]}\r\n")
                except Exception as e:
                    self.stream.feed(f"Error: Failed to open file {args[0]}: {str(e)}\r\n")
            self.update_display()
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
                    self.stream.feed(result.stdout)
                if result.stderr:
                    self.stream.feed(f"\x1b[31m{result.stderr}\x1b[0m")  # Red color for errors
                if result.returncode != 0 and not result.stdout and not result.stderr:
                    self.stream.feed(f"\x1b[31mCommand failed with return code {result.returncode}\x1b[0m\r\n")
                self.update_display()
            except Exception as e:
                self.stream.feed(f"\x1b[31mFailed to execute system command: {str(e)}\x1b[0m\r\n")
                self.update_display()

        self.command_input.clear()

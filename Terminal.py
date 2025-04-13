from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor
from PyQt6.QtCore import Qt, QEvent, QThread, pyqtSignal
import subprocess
import os
import queue
import shlex

class TerminalWorker(QThread):
    resultReady = pyqtSignal(str, str)   # (log_type, message)
    finishedCommand = pyqtSignal(str)    # command string

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
                self.resultReady.emit("Info", result.stdout.strip())
            if result.stderr:
                self.resultReady.emit("Error", result.stderr.strip())
            if result.returncode != 0 and not result.stdout and not result.stderr:
                self.resultReady.emit("Error", f"Command failed with code {result.returncode}")
        except Exception as e:
            self.resultReady.emit("Error", str(e))
        finally:
            self.finishedCommand.emit(self.command)


class Terminal(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Terminal", parent)
        self.parent = parent

        self.setObjectName("TerminalDock")
        self.setMinimumHeight(100)
        self.setMaximumHeight(500)

        self.command_history = []
        self.history_index = -1
        self.workers = []

        self.command_queue = queue.Queue()
        self.command_thread_active = False

        self.current_path = None

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.output_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        font = QFont("Consolas", 12)
        self.output_display.setFont(font)
        palette = self.output_display.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#C0C0C0"))
        self.output_display.setPalette(palette)

        layout.addWidget(self.output_display)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command here...")
        self.command_input.returnPressed.connect(self.execute_input_command)
        self.command_input.installEventFilter(self)
        layout.addWidget(self.command_input)

        self.setWidget(main_widget)
        self.visibilityChanged.connect(self.on_terminal_visibility_changed)

    def on_terminal_visibility_changed(self, visible):
        if hasattr(self.parent, 'toggleterminalAction'):
            self.parent.toggleterminalAction.setChecked(visible)

    def eventFilter(self, obj, event):
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

    def get_prompt(self):
        return f"{os.getcwd()} >>> "

    def add_log(self, log_type, message):
        prompt = self.get_prompt()
        color = QColor("#C0C0C0")
        if log_type == "Debug":
            color = QColor("#00C0FF")
        elif log_type == "Error":
            color = QColor("#FF0000")
        elif log_type == "Command":
            color = QColor("#00FF00")

        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_display.setTextCursor(cursor)

        self.output_display.setTextColor(QColor("#FFFF00"))
        self.output_display.insertPlainText(prompt)
        self.output_display.setTextColor(color)
        self.output_display.insertPlainText(f"{message}\n")
        self.output_display.ensureCursorVisible()

    def run_command(self, command: str, on_finished=None):
        # If a command is already running, ignore the new command
        if self.command_thread_active:
            running_cmd = self.workers[-1].command if self.workers else None
            if running_cmd and running_cmd.strip() == command.strip():
                self.add_log("Debug", f"Ignored: '{command}' is already running.")
                return

        # If the command is the same as the last one in the queue, ignore it
        if not self.command_queue.empty():
            last_cmd, _ = self.command_queue.queue[-1]
            if last_cmd.strip() == command.strip():
                self.add_log("Debug", f"Ignored duplicate queued command: {command}")
                return

        # If the command is not a duplicate, add it to the queue
        self.command_queue.put((command, on_finished))
        self.process_next_command()

    def process_next_command(self):
        if self.command_thread_active or self.command_queue.empty():
            return

        command, on_finished = self.command_queue.get()
        self.command_thread_active = True

        self.add_log("Command", command)
        worker = TerminalWorker(command)
        worker.resultReady.connect(self.add_log)

        def on_command_done(cmd):
            self.command_thread_active = False
            self.command_queue.task_done()
            if on_finished:
                on_finished(cmd)
            self.process_next_command()

        worker.finishedCommand.connect(on_command_done)
        worker.finished.connect(lambda: self.workers.remove(worker))
        self.workers.append(worker)
        worker.start()

    def execute_specific_command(self, cmd, args=None, on_finished=None):
        if args is None:
            args = []

        if cmd == "clear":
            self.clear_log()
            return
        elif cmd == "help":
            self.add_log("Info", "Available commands: make clean, make build, cd, clear, etc.")
            return
        elif cmd == "cd":
            try:
                if args[0] == '.':
                    self.add_log("Info", "Current directory unchanged.")
                elif args[0] == '..':
                    self.current_path = os.path.dirname(self.current_path)
                elif not os.path.isabs(args[0]):
                    self.current_path = os.path.join(self.current_path, args[0])
                else:
                    self.current_path = args[0]

                if args[0] != '.' and os.path.exists(self.current_path):
                    os.chdir(self.current_path)
                    self.add_log("Info", f"Changed to: {self.current_path}")
                else:
                    return
            except Exception as e:
                self.add_log("Error", str(e))
            return

        full_cmd = " ".join([cmd] + args)
        self.run_command(full_cmd, on_finished=on_finished)

    def execute_input_command(self):
        command = self.command_input.text().strip()
        if not command:
            return

        if not self.command_history or self.command_history[0] != command:
            self.command_history.insert(0, command)
        self.history_index = -1
        self.command_input.clear()

        cmd, args = self.parse_command(command)
        self.execute_specific_command(cmd, args)

    def parse_command(self, command_str):
        tokens = shlex.split(command_str)
        if not tokens:
            return None, []
        cmd = tokens[0]
        args = tokens[1:]
        return cmd, args

    def clear_log(self):
        self.output_display.clear()

    def exe_first_cmd(self, current_file_path):
        self.current_path = current_file_path
        def on_ready(_):
            self.add_log("Info", "Welcome to Taara Embedded Terminal!")
        self.execute_specific_command("cd", [f"{current_file_path}"], on_finished=on_ready)

from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton
from PyQt6.QtGui import QColor, QPalette, QFont
from PyQt6.QtCore import Qt, QEvent
from datetime import datetime
import subprocess
import os

class Console(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Console", parent)
        self.parent = parent

        # Main widget cho QDockWidget
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # Tạo QTextEdit để hiển thị log/output với nền màu đen
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)  # Chỉ đọc
        self.output_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)  # Không xuống dòng tự động

        # Đặt nền màu đen và font giống Command Prompt
        palette = self.output_display.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))  # Nền màu đen
        palette.setColor(QPalette.ColorRole.Text, QColor("#C0C0C0"))  # Văn bản màu xám nhạt
        self.output_display.setPalette(palette)

        # Đặt font (Consolas hoặc Lucida Console)
        font = QFont("Consolas", 10)  # Kích thước font 10pt, giống Command Prompt
        self.output_display.setFont(font)

        layout.addWidget(self.output_display)

        # Tạo QLineEdit để nhập lệnh
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command here (type 'help' for commands)...")
        self.command_input.returnPressed.connect(self.execute_command)  # Thực thi lệnh khi nhấn Enter
        # Cài đặt event filter để bắt phím Lên/Xuống
        self.command_input.installEventFilter(self)
        layout.addWidget(self.command_input)

        # Nút Clear để xóa log
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_log)
        layout.addWidget(clear_button)

        # Đặt widget vào QDockWidget
        self.setWidget(main_widget)

        # Đặt kích thước tối thiểu và tối đa (tùy chọn)
        self.setMinimumHeight(100)
        self.setMaximumHeight(300)

        # Khởi tạo lịch sử lệnh
        self.command_history = []  # Danh sách lưu lịch sử lệnh
        self.history_index = -1  # Vị trí hiện tại trong lịch sử (-1: không duyệt)

    def eventFilter(self, obj, event):
        """Bắt sự kiện phím Lên/Xuống để duyệt lịch sử lệnh."""
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
        """Thêm một log hoặc output vào console với màu sắc dựa trên loại log."""
        # Lấy thư mục hiện tại làm tiền tố
        cwd = os.getcwd()
        prompt = f"{cwd}> " if prefix else ""

        # Định dạng log: Tiền tố + Thông điệp
        log_message = f"{prompt}{message}"

        # Đặt màu sắc dựa trên loại log (tương phản tốt trên nền đen)
        if log_type == "Debug":
            color = QColor("#00C0FF")  # Xanh dương nhạt
        elif log_type == "Error":
            color = QColor("#FF0000")  # Đỏ
        elif log_type == "Info":
            color = QColor("#C0C0C0")  # Xám nhạt
        elif log_type == "Command":
            color = QColor("#00FF00")  # Xanh lá
        else:
            color = QColor("#808080")  # Xám cho loại không xác định

        # Đặt màu cho văn bản
        self.output_display.setTextColor(color)
        # Thêm log vào QTextEdit
        self.output_display.append(log_message)
        # Cuộn xuống dòng cuối cùng
        self.output_display.ensureCursorVisible()

    def clear_log(self):
        """Xóa toàn bộ nội dung trong console."""
        self.output_display.clear()

    def execute_command(self):
        """Thực thi lệnh người dùng nhập trong QLineEdit."""
        command = self.command_input.text().strip()
        if not command:
            return  # Không làm gì nếu lệnh rỗng

        # Thêm lệnh vào lịch sử (nếu không trùng với lệnh trước đó)
        if not self.command_history or self.command_history[0] != command:
            self.command_history.insert(0, command)
        self.history_index = -1  # Reset chỉ số lịch sử

        # Hiển thị lệnh người dùng nhập với tiền tố
        self.add_log("Command", f">{command}")

        # Phân tách lệnh thành phần chính và đối số
        command_parts = command.split()
        cmd = command_parts[0].lower()  # Lệnh chính (ví dụ: "cd", "dir", "open")
        args = command_parts[1:] if len(command_parts) > 1 else []  # Đối số (nếu có)

        # Xử lý lệnh nội bộ trước
        if cmd == "help":
            self.add_log("Info", "Available commands:", prefix=False)
            self.add_log("Info", "  help - Show this help message", prefix=False)
            self.add_log("Info", "  clear - Clear the console", prefix=False)
            self.add_log("Info", "  open <file_path> - Open a file in the editor", prefix=False)
            self.add_log("Info", "  project - Show current project directory", prefix=False)
            self.add_log("Info", "  cd <dir> - Change current working directory", prefix=False)
            self.add_log("Info", "  dir/ls - List files in current directory", prefix=False)
            self.add_log("Info", "  (Other system commands like 'echo', 'type' are also supported)", prefix=False)
        elif cmd == "clear":
            self.clear_log()
        elif cmd == "open":
            if not args:
                self.add_log("Error", "Usage: open <file_path>")
            else:
                file_path = args[0]
                try:
                    self.parent.open_file(file_path)  # Gọi phương thức open_file từ MainWindow
                    self.add_log("Info", f"Opened file: {file_path}")
                except Exception as e:
                    self.add_log("Error", f"Failed to open file {file_path}: {str(e)}")
        elif cmd == "project":
            if hasattr(self.parent, 'project_view'):
                project_dir = self.parent.project_view.get_project_directory()
                self.add_log("Info", f"Current project directory: {project_dir}")
            else:
                self.add_log("Error", "ProjectView not available")
        # Xử lý lệnh hệ thống
        elif cmd == "cd":
            if not args:
                self.add_log("Error", "Usage: cd <directory>")
            else:
                try:
                    new_dir = args[0]
                    os.chdir(new_dir)  # Thay đổi thư mục làm việc
                    self.add_log("Info", f"Changed directory to: {os.getcwd()}")
                except Exception as e:
                    self.add_log("Error", f"Failed to change directory: {str(e)}")
        else:
            # Chạy lệnh hệ thống bằng subprocess
            try:
                # Chạy lệnh với shell=True để hỗ trợ các lệnh như dir, echo, type, v.v.
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                # Hiển thị kết quả stdout (nếu có)
                if result.stdout:
                    self.add_log("Info", result.stdout.strip(), prefix=False)
                # Hiển thị lỗi stderr (nếu có)
                if result.stderr:
                    self.add_log("Error", result.stderr.strip())
                # Nếu lệnh không trả về gì (như dir trên Windows), kiểm tra return code
                if result.returncode != 0 and not result.stdout and not result.stderr:
                    self.add_log("Error", f"Command failed with return code {result.returncode}")
            except Exception as e:
                self.add_log("Error", f"Failed to execute system command: {str(e)}")

        # Xóa nội dung trong QLineEdit sau khi thực thi
        self.command_input.clear()
        
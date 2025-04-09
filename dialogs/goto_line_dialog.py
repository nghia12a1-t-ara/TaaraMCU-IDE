from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout

class GoToLineDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Go To...")

        # Create layout
        layout = QVBoxLayout()

        # Current line label
        self.current_line_label = QLabel(f"You are here: Line {parent.get_current_editor().getCursorPosition()[0] + 1}")
        layout.addWidget(self.current_line_label)

        # Line number input
        self.line_input = QLineEdit()
        layout.addWidget(QLabel("You want to go to:"))
        layout.addWidget(self.line_input)

        # Buttons
        button_layout = QHBoxLayout()
        go_button = QPushButton("Go")
        go_button.clicked.connect(self.go_to_line)
        button_layout.addWidget(go_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def go_to_line(self):
        """Navigate to the specified line number."""
        line_number = self.line_input.text()
        if not line_number.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid line number.")
            return

        line_number = int(line_number) - 1  # Convert to zero-based index
        editor = self.parent().get_current_editor()

        if editor:
            total_lines = editor.lines()
            if line_number < 0 or line_number >= total_lines:
                QMessageBox.warning(self, "Out of Range", f"You can't go further than: {total_lines}")
                return

            editor.setCursorPosition(line_number, 0)  # Move cursor to the specified line
            self.accept()  # Close the dialog

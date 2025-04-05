import subprocess
import os, sys
from PyQt6.QtWidgets import QMessageBox, QDialog, QLabel, QLineEdit, QVBoxLayout, QPushButton, QFileDialog, QApplication
from pathlib import Path

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class CtagsHandler:
    ctags_path = None  # Class-level variable to store the ctags path

    def __init__(self, editor):
        self.editor = editor  # Reference to the editor instance
        if CtagsHandler.ctags_path is None:  # Check if ctags_path has not been set
            QMessageBox.information(self.editor, "CTags Path", "CTags path not set. Please set the path to the ctags executable.")

    def generate_ctags(self):
        """Generate CTags for the current file, only for supported source files."""
        if not self.editor.file_path:
            return False

        # Create a .tags file name based on file_path
        tags_file = f"{self.editor.file_path}.tags"  # Example: Queue.c.tags

        # Check write permission in the directory containing the file
        target_dir = Path(self.editor.file_path).parent
        if not os.access(target_dir, os.W_OK):
            QMessageBox.warning(self.editor, "CTags Error", f"No write permission in directory: {target_dir}")
            return False

        try:
            # Command to generate CTags for the current file
            ctags_cmd = [CtagsHandler.ctags_path, "--fields=+n", "--kinds-C=+d", "-o", tags_file, self.editor.file_path]
            result = subprocess.run(ctags_cmd, capture_output=True, text=True, shell=True)

            if result.returncode == 0:
                return True
            else:
                # Display detailed error from stdout/stderr
                error_message = result.stderr or result.stdout or "Unknown error occurred."
                QMessageBox.warning(self.editor, "CTags Error", f"Failed to generate tags file:\n{error_message}")
                return False
        except Exception as e:
            QMessageBox.warning(self.editor, "CTags Error", f"Exception occurred while generating tags:\n{str(e)}")
            return False

    def remove_ctags(self):
        """Remove the .tags file associated with the current editor's file."""
        if hasattr(self.editor, 'file_path') and self.editor.file_path:
            tags_file_path = f"{self.editor.file_path}.tags"
            if os.path.exists(tags_file_path):
                try:
                    os.remove(tags_file_path)
                except Exception as e:
                    QMessageBox.warning(self.editor, "CTags Error", f"Failed to remove tags file:\n{str(e)}")

    def update_ctags(self):
        """Update CTags for the current editor's file."""
        self.generate_ctags()  # Simply regenerate CTags

class CtagsPathDialog(QDialog):
    def __init__(self, setting_man, current_path=None):
        super().__init__()
        self.setWindowTitle("Select CTags Path")
        self.setFixedWidth(400)
        layout = QVBoxLayout()

        self.setting_man = setting_man

        # Label and text field for displaying the current path
        self.label = QLabel("Current CTags Path:")
        self.path_input = QLineEdit()
        self.path_input.setText(current_path if current_path else "")
        # self.path_input.setReadOnly(True)     # Make it read-only

        # Button to browse for the ctags.exe file
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_ctags)

        # Button to save the path
        self.save_button = QPushButton("Save Path")
        self.save_button.clicked.connect(self.save_path)

        layout.addWidget(self.label)
        layout.addWidget(self.path_input)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        # Connect the rejected signal to exit the application
        self.rejected.connect(self.exit_application)

    def browse_ctags(self):
        """Open a file dialog to select the ctags.exe file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CTags Executable", "", "Executable Files (*.exe)")
        if file_path:
            self.path_input.setText(file_path)

    def save_path(self):
        """Save the selected path and check its version."""
        path = self.path_input.text()
        if os.path.exists(path):
            # Check the version of ctags
            if self.check_ctags_version(path):
                # Save the path to the settings manager
                self.setting_man.set_ctags_path(path)
                # QMessageBox.information(self, "Success", "CTags path saved successfully.")
                self.accept()   # Close the dialog
            else:
                QMessageBox.warning(self, "CTags Error", "The selected CTags executable is not valid or does not support the required features.")
        else:
            QMessageBox.warning(self, "Error", "The selected path does not exist.")

    def check_ctags_version(self, path):
        """Check if the ctags executable is valid and supports the required features."""
        try:
            result = subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            # You can add specific version checks here if needed
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def exit_application(self):
        """Exit the application when the dialog is closed."""
        sys.exit(1)  # Exit the application

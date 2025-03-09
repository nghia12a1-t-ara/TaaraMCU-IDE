import subprocess
import os
from PyQt6.QtWidgets import QMessageBox
from pathlib import Path

class CtagsHandler:
    def __init__(self, editor):
        self.editor = editor  # Reference to the editor instance
        # Find the absolute path to ctags.exe
        self.ctags_path = self.get_ctags_path()

    def get_ctags_path(self):
        """Find the absolute path to ctags.exe."""
        # Assuming ctags.exe is located in the 'ctags' directory within the source code directory
        script_dir = Path(__file__).parent
        ctags_path = script_dir / "ctags" / "ctags.exe"
        if not ctags_path.exists():
            return None
        return str(ctags_path)

    def is_ctags_available(self):
        """Check if ctags is available."""
        if not self.ctags_path:
            return False
        try:
            subprocess.run([self.ctags_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def generate_ctags(self):
        """Generate CTags for the current file, only for supported source files."""
        if not self.editor.file_path:
            return False

        # Check if ctags is available
        if not self.is_ctags_available():
            QMessageBox.warning(self.editor, "CTags Error", "CTags executable not found at the specified path!")
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
            ctags_cmd = [self.ctags_path, "--fields=+n", "--kinds-C=+d", "-o", tags_file, self.editor.file_path]
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

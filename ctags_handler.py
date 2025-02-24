
import subprocess
import os
from PyQt6.QtWidgets import QMessageBox

class CtagsHandler:
    def __init__(self, editor):
        self.editor = editor  # Reference to the editor instance

    def is_ctags_available():
        try:
            subprocess.run(['ctags', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except FileNotFoundError:
            return False

    def generate_ctags(self):
        """Generate CTags for the current editor's file."""
        if hasattr(self.editor, 'file_path') and os.path.isfile(self.editor.file_path):
            try:
                tags_file_path = f"{self.editor.file_path}.tags"
                
                # Dùng full path cho ctags nếu cần
                ctags_cmd = [r".\ctags\ctags.exe", "--fields=+n", "-f", tags_file_path, self.editor.file_path]

                # Chạy subprocess với shell=True để hoạt động tốt trong PyQt6
                result = subprocess.run(
                    ctags_cmd, capture_output=True, text=True, shell=True
                )

                if result.returncode == 0:
                    return True
                else:
                    return False
            except Exception as e:
                QMessageBox.warning(self.editor.parent(), "CTags Error", f"Could not generate CTags: {str(e)}")

    def update_ctags(self):
        """Update CTags for the current editor's file."""
        self.generate_ctags()  # Simply regenerate CTags

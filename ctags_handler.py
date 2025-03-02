
import subprocess
import os, shutil
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
        if not hasattr(self.editor, 'file_path') or not os.path.isfile(self.editor.file_path):
            return False
        try:
            tags_file_path = f"{self.editor.file_path}.tags"
            ctags_path = shutil.which("ctags") or r".\ctags\ctags.exe"  # Tìm trong PATH trước
            if not os.path.exists(ctags_path):
                QMessageBox.warning(self.editor.parent(), "CTags Error", "CTags executable not found!")
                return False
            ctags_cmd = [ctags_path, "--fields=+n", "-f", tags_file_path, self.editor.file_path]
            result = subprocess.run(ctags_cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            return False
        
    def remove_ctags(self):
        """Remove the .tags file associated with the current editor's file."""
        if hasattr(self.editor, 'file_path'):
            tags_file_path = f"{self.editor.file_path}.tags"
            if os.path.exists(tags_file_path):
                os.remove(tags_file_path)
        
    def update_ctags(self):
        """Update CTags for the current editor's file."""
        self.generate_ctags()  # Simply regenerate CTags

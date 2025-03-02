import subprocess
import os, shutil
from PyQt6.QtWidgets import QMessageBox

class CtagsHandler:
    def __init__(self, editor):
        self.editor = editor  # Reference to the editor instance

    @staticmethod
    def is_ctags_available():
        try:
            subprocess.run(['ctags', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except FileNotFoundError:
            return False

    def generate_ctags(self):
        """Generate CTags for the current file, only for supported source files."""
        if not self.editor.file_path:
            return False

        # Create a .tags file name based on file_path
        tags_file = f"{self.editor.file_path}.tags"  # Example: Queue.c.tags
        try:
            # Command to generate CTags for the current file
            ctags_cmd = [r".\ctags\ctags.exe", "--fields=+n", "--kinds-C=+d", "-o", tags_file, self.editor.file_path]
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

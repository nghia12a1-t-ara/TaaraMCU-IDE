# C Compiler
import json
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel
import subprocess
import shutil
from pathlib import Path

class CompilerHandler:
    def __init__(self, editor, compiler_path=None):
        self.editor = editor
        self.compiler_path = compiler_path or self.get_default_compiler_path()
        self.output_file = None

    def get_default_compiler_path(self):
        """Finds the default path to gcc."""
        # Assuming gcc is in PATH or in the compilers directory
        script_dir = Path(__file__).parent
        possible_paths = [
            "gcc",  # If gcc is already in PATH
            str(script_dir / "compilers" / "gcc" / "bin" / "gcc.exe")  # Local path
        ]
        for path in possible_paths:
            if Path(path).exists() or shutil.which(path):
                return path
        return None

    def is_compiler_available(self):
        """Checks if gcc is available."""
        if not self.compiler_path:
            return False
        try:
            subprocess.run([self.compiler_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def compile(self, output_dir=None, flags=None):
        """Compiles the current C file using gcc."""
        if not self.editor.file_path:
            QMessageBox.warning(self.editor, "Compile Error", "No file path available for compilation!")
            return False

        if not self.is_compiler_available():
            QMessageBox.warning(self.editor, "Compile Error", "GCC not found at the specified path!")
            return False

        # Creates the output directory if it doesn't exist
        output_dir = output_dir or Path(self.editor.file_path).parent / "build"
        output_dir.mkdir(exist_ok=True)

        # Creates the output file name (e.g., main.c -> main.exe)
        base_name = Path(self.editor.file_path).stem
        self.output_file = output_dir / f"{base_name}.exe"

        # Configures default flags
        default_flags = ["-Wall", "-o", str(self.output_file)]
        if flags:
            default_flags.extend(flags)

        try:
            # Compilation command
            compile_cmd = [self.compiler_path, self.editor.file_path] + default_flags

            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                cwd=str(output_dir)
            )

            if result.returncode == 0:
                self.editor.GUI.terminal.add_log("Info", f"Compilation successful: {self.output_file}", prefix=False)
                QMessageBox.information(self.editor, "Compile Success", f"Compiled to {self.output_file}")
                return True
            else:
                error_message = result.stderr or result.stdout or "Unknown error occurred."
                self.editor.GUI.terminal.add_log("Error", f"Compilation failed:\n{error_message}", prefix=False)
                QMessageBox.warning(self.editor, "Compile Error", f"Compilation failed:\n{error_message}")
                return False
        except Exception as e:
            self.editor.GUI.terminal.add_log("Error", f"Exception during compilation:\n{str(e)}", prefix=False)
            QMessageBox.warning(self.editor, "Compile Error", f"Exception during compilation:\n{str(e)}")
            return False
        
    def compile_project(self, project_manager):
        """Compile the entire project."""
        if not self.is_compiler_available():
            QMessageBox.warning(self.editor, "Compile Error", "GCC not found!")
            return False

        build_cmd = project_manager.get_build_command(self.compiler_path)
        if not build_cmd:
            QMessageBox.warning(self.editor, "Compile Error", "No source files in project!")
            return False

        build_dir = Path(self.editor.file_path).parent / "build"
        build_dir.mkdir(exist_ok=True)

        try:
            result = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                cwd=str(build_dir)
            )

            if result.returncode == 0:
                self.editor.GUI.terminal.add_log("Info", f"Project compilation successful: {project_manager.output_file}", prefix=False)
                QMessageBox.information(self.editor, "Compile Success", f"Compiled project to {build_dir / project_manager.output_file}")
                return True
            else:
                error_message = result.stderr or result.stdout or "Unknown error occurred."
                self.editor.GUI.terminal.add_log("Error", f"Compilation failed:\n{error_message}", prefix=False)
                QMessageBox.warning(self.editor, "Compile Error", f"Compilation failed:\n{error_message}")
                return False
        except Exception as e:
            self.editor.GUI.terminal.add_log("Error", f"Exception during compilation:\n{str(e)}", prefix=False)
            return False
    
    def run(self):
        """Runs the compiled file (optional)."""
        if not self.output_file or not self.output_file.exists():
            QMessageBox.warning(self.editor, "Run Error", "No compiled file available!")
            return False
        try:
            result = subprocess.run(
                [str(self.output_file)],
                capture_output=True,
                text=True,
                cwd=Path(self.output_file).parent
            )
            self.editor.GUI.terminal.add_log("Output", result.stdout, prefix=False)
            if result.stderr:
                self.editor.GUI.terminal.add_log("Error", result.stderr, prefix=False)
            return True
        except Exception as e:
            self.editor.GUI.terminal.add_log("Error", f"Exception during run:\n{str(e)}", prefix=False)
            return False
        
class ProjectManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.project_file = None
        self.source_files = []
        self.output_file = "output.exe"
        self.compile_flags = ["-Wall"]
        self.load_default_config()

    def load_default_config(self):
        """Loads the default configuration if no project."""
        self.source_files = []
        self.output_file = "output.exe"
        self.compile_flags = ["-Wall"]

    def create_project(self, project_path):
        """Creates a new project."""
        self.project_file = Path(project_path) / "project.taaraproject"
        self.source_files = []
        self.save_project()
        QMessageBox.information(self.main_window, "Project Created", f"Project created at {self.project_file}")

    def open_project(self, project_path):
        """Opens an existing project."""
        self.project_file = Path(project_path)
        if self.project_file.exists():
            with open(self.project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.source_files = data.get("source_files", [])
                self.output_file = data.get("output_file", "output.exe")
                self.compile_flags = data.get("compile_flags", ["-Wall"])
            return True
        QMessageBox.warning(self.main_window, "Project Error", "Project file not found!")
        return False

    def save_project(self):
        """Saves project information to a JSON file."""
        if self.project_file:
            data = {
                "source_files": self.source_files,
                "output_file": self.output_file,
                "compile_flags": self.compile_flags
            }
            with open(self.project_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

    def add_file(self, file_path):
        """Adds a file to the project."""
        if file_path not in self.source_files and Path(file_path).suffix.lower() == ".c":
            self.source_files.append(file_path)
            self.save_project()
            return True
        return False

    def remove_file(self, file_path):
        """Removes a file from the project."""
        if file_path in self.source_files:
            self.source_files.remove(file_path)
            self.save_project()
            return True
        return False

    def get_build_command(self, compiler_path):
        """Creates the build command for the entire project."""
        if not self.source_files:
            return None
        build_dir = self.project_file.parent / "build"
        build_dir.mkdir(exist_ok=True)
        output_path = build_dir / self.output_file
        cmd = [compiler_path] + self.compile_flags + self.source_files + ["-o", str(output_path)]
        return cmd

class ProjectConfigDialog(QDialog):
    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.setWindowTitle("Project Configuration")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # File List
        file_layout = QHBoxLayout()
        self.file_list = QListWidget()
        self.file_list.addItems(project_manager.source_files)
        file_layout.addWidget(QLabel("Source Files:"))
        file_layout.addWidget(self.file_list)

        # Add File Button
        add_button = QPushButton("Add File")
        add_button.clicked.connect(self.add_file)
        file_layout.addWidget(add_button)

        # Remove File Button
        remove_button = QPushButton("Remove File")
        remove_button.clicked.connect(self.remove_file)
        file_layout.addWidget(remove_button)

        layout.addLayout(file_layout)

        # Output File
        output_layout = QHBoxLayout()
        output_label = QLabel("Output File:")
        self.output_input = QLineEdit(project_manager.output_file)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)

        layout.addLayout(output_layout)

        # Flags
        flags_layout = QHBoxLayout()
        flags_label = QLabel("Compile Flags:")
        self.flags_input = QLineEdit(" ".join(project_manager.compile_flags))
        flags_layout.addWidget(flags_label)
        flags_layout.addWidget(self.flags_input)

        layout.addLayout(flags_layout)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Add Source File", "", "C Files (*.c)")
        if file_path and self.project_manager.add_file(file_path):
            self.file_list.addItem(file_path)

    def remove_file(self):
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            if self.project_manager.remove_file(item.text()):
                self.file_list.takeItem(self.file_list.row(item))

    def save_config(self):
        self.project_manager.output_file = self.output_input.text()
        self.project_manager.compile_flags = self.flags_input.text().split()
        self.project_manager.save_project()
        self.accept()

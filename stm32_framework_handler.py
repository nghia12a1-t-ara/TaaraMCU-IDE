import os, json, shutil
import subprocess
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog

class STM32FrameworkHandler:
    """Class to handle the STM32 framework and project operations."""
    def __init__(self, settings_manager, terminal):
        """Initialize the STM32FrameworkHandler."""
        self.settings_manager = settings_manager
        self.terminal = terminal
        self.framework_path = self.load_framework_path()
        self.framework_installed = self.check_framework_status()
        self.project_path = None
        self.project_name = None
        self.framework_makefile_path = None
        self.project_makefile_path = None
        self.framework_content = None
        self.makefile_header = "PROJECT         := USER\n"
        self.project_available = False

    def set_framework_path(self, path):
        """Set the framework path."""
        if os.path.exists(path):
            self.framework_path = path
            self.settings_manager.set_stm32_framework_path(path)
            QMessageBox.information(None, "Success", "STM32 Framework path set successfully.")
        else:
            QMessageBox.warning(None, "Error", "The specified path does not exist.")

    def load_framework_path(self):
        """Load the framework path from the settings manager."""
        return self.settings_manager.get_stm32_framework_path()

    def check_framework_status(self):
        """Check if the framework is installed."""
        return bool(self.framework_path and os.path.exists(self.framework_path))

    def load_project_parameters(self, project_dir):
        """Load project parameters when opening a project and change directory to project path."""
        if not os.path.exists(project_dir):
            QMessageBox.warning(None, "Error", "Project directory does not exist.")
            return

        project_file_path = os.path.join(project_dir, ".taara_project")
        if not os.path.exists(project_file_path):
            QMessageBox.warning(None, "Error", "Project file does not exist.")
            return

        with open(project_file_path, 'r') as project_file:
            project_params = json.load(project_file)

        self.project_path               = project_params.get("project_dir", None)
        self.framework_makefile_path    = project_params.get("framework_makefile_path", None)
        self.project_makefile_path      = project_params.get("project_makefile_path", None)
        self.framework_content          = project_params.get("framework_content", None)
        self.project_name               = project_params.get("project_name", None)  # Load project_name
        self.project_available = True

        # Change directory to project path and log the action
        self.terminal.execute_specific_command("cd", [self.project_path])
        self.terminal.add_log("Info", "Loaded the STM32 Project follow the Taara-Framework!")

    def clean_project(self):
        """Clean the project."""
        if not os.path.exists(self.project_path):
            self.terminal.add_log("Error", "Project directory does not exist")
            return

        def on_clean_finished(_):
            self.terminal.add_log("Info", "Clean finished")

        self.terminal.run_command("make clean", on_finished=on_clean_finished)

    def build_project(self):
        """Build the project."""
        if not os.path.exists(self.project_path):
            self.terminal.add_log("Error", "Project directory does not exist")
            return

        def on_build_finished(_):
            self.terminal.add_log("Info", "Build finished")

        self.terminal.run_command("make build", on_finished=on_build_finished)

    def flash_project(self):
        """Flash the project."""
        bin_path = os.path.join(self.project_path, "output", f"{self.project_name}.hex")
        if not os.path.exists(bin_path):
            self.terminal.add_log("Error", "Binary file not found. Please build the project first.")
            return

        self.terminal.add_log("Info", f"Flash the Binary File: {bin_path}")

        def on_flash_finished(_):
            self.terminal.add_log("Info", "Flash finished")

        self.terminal.run_command("make run", on_finished=on_flash_finished)

    def project_action(self, action):
        """Perform an action on the project."""
        if not self.project_available:
            self.terminal.add_log("Error", "No project loaded.")
            return

        if action == "clean":
            self.clean_project()
        elif action == "build":
            self.build_project()
        elif action == "flash":
            self.flash_project()
        elif action == "clean_build":
            self.clean_project()
            self.build_project()
        else:
            self.terminal.add_log("Error", f"Unknown action: {action}")

    def create_project(self, project_dir, project_name):
        """Create a new STM32 project using the framework template"""
        if not self.framework_path:
            raise Exception("Framework path is not set")
            
        # Create project directory
        self.project_name = project_name + '_TaaraFramework'
        self.project_path = os.path.join(project_dir, self.project_name).replace('\\', '/')
        if not os.path.exists(self.project_path):
            os.makedirs(self.project_path)
        
        # Copy template files from framework
        if not os.path.exists(self.framework_path):
            raise Exception(f"Template directory {self.framework_path} not found")
                
        # Update project name in Makefile
        project_settings = {
            "project_dir": self.project_path,
            "project_name": self.project_name,
            "use_framework": "TRUE",
            "source_files": [],
            "include_directories": [],
            "compiler_optimize_level": "O2",
            "preprocessor": "-DSTM32F4",
            "linker_options": "-lstdc++ -lm",
            "mcu": "STM32F4",
            "compiler_dir": os.path.join(project_dir, "compiler"),
        }

        project_settings_file = os.path.join(self.project_path, ".taara_project")
        with open(project_settings_file, 'w') as file:
            json.dump(project_settings, file)

        # Create STM32 Project Need File
        # Create available file/folder
        src_folder = os.path.join(self.project_path, "src")
        os.makedirs(src_folder, exist_ok=True)
        main_c_file = os.path.join(src_folder, "main.c")
        with open(main_c_file, 'w') as file:
            file.write("#include <stdint.h>\n\nint main() {\n    // Your code here\n    return 0;\n}")

        # Create Makefile from Framework
        self.framework_makefile_path    =   os.path.join(self.framework_path, "STM32F4_Framework", "Makefile").replace('\\', '/')
        self.project_makefile_path      =   os.path.join(self.project_path, "Makefile").replace('\\', '/')

        shutil.copy(self.framework_makefile_path, self.project_makefile_path)
        with open(self.framework_makefile_path, 'r') as file:
            self.framework_content = file.read()

        # Update Makefile Header to Project Makefile
        self.makefile_header = self.makefile_header + f"PROJECT_DIR     := {self.project_path}\n"
        self.makefile_header = self.makefile_header + f"FRAMEWORK_DIR   := {self.framework_path}/STM32F4_Framework\n"
        self.makefile_header = self.makefile_header + f"SRC_DIRS        += $(PROJECT_DIR)/src\n"
        self.makefile_header = self.makefile_header + f"MODULE_LIST     := BASE CLOCK\n"
        self.makefile_header = self.makefile_header + f"PROJ_NAME       := {self.project_name}\n"

        with open(self.project_makefile_path, 'w') as file:
            file.write(self.makefile_header + self.framework_content)
        self.project_available = True

        # Change directory to project path and log the action
        self.terminal.execute_specific_command("cd", [self.project_path])
        
        return self.project_path
    
    def makefile_add_head(self, string):
        """Add string data to the header of the makefile."""
        self.makefile_header = self.makefile_header + string
        with open(self.project_makefile_path, 'w') as file:
            file.write(self.makefile_header + self.framework_content)

    def close_project(self):
        """Close the current project."""
        self.project_available = False
        pass

class CreateProjectDialog(QDialog):
    """Dialog to create a new STM32 project."""
    def __init__(self, stm32_handler, parent=None):
        """Initialize the CreateProjectDialog."""
        super().__init__(parent)
        self.stm32_handler = stm32_handler
        self.setWindowTitle("Create STM32 Project")
        self.setFixedWidth(400)
        layout = QVBoxLayout()

        self.isProjectCreated = False

        # Project Directory
        self.dir_label = QLabel("Project Directory:")
        self.dir_input = QLineEdit()
        self.dir_browse = QPushButton("Browse")
        self.dir_browse.clicked.connect(self.browse_directory)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_browse)
        
        # Project Name
        self.name_label = QLabel("Project Name:")
        self.name_input = QLineEdit()

        # Use Framework Checkbox
        self.use_framework = QCheckBox("Use TaaraFramework")
        self.use_framework.setChecked(True)
        self.use_framework.stateChanged.connect(self.check_framework_availability)

        # Create Button
        self.create_button = QPushButton("Create Project")
        self.create_button.clicked.connect(self.create_project)

        # Add widgets to layout
        layout.addWidget(self.dir_label)
        layout.addLayout(dir_layout)
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.use_framework)
        layout.addWidget(self.create_button)

        self.setLayout(layout)
        self.check_framework_availability()

    def browse_directory(self):
        """Open a file dialog to select the project directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if directory:
            self.dir_input.setText(directory)

    def check_framework_availability(self):
        """Check if framework is available and update UI accordingly."""
        if self.use_framework.isChecked() and not self.stm32_handler.framework_installed:
            QMessageBox.warning(self, "Warning", 
                "TaaraFramework is not available. Please install it first.")
            self.use_framework.setChecked(False)

    def create_project(self):
        """Handle project creation."""
        project_dir = self.dir_input.text()
        project_name = self.name_input.text()
        use_framework = self.use_framework.isChecked()

        if not project_dir or not project_name:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return

        try:
            if use_framework:
                project_path = self.stm32_handler.create_project(project_dir, project_name)
            else:
                project_path = os.path.join(project_dir, project_name)
                os.makedirs(project_path, exist_ok=True)
            
            QMessageBox.information(self, "Success", 
                f"Project created successfully at:\n{project_path}")
            self.accept()
            
            self.isProjectCreated = True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create project:\n{str(e)}")

class InstallFrameworkDialog(QDialog):
    """Dialog to install the STM32 framework."""
    def __init__(self, settings_manager, terminal):
        """Initialize the InstallFrameworkDialog."""
        super().__init__()
        self.settings_manager = settings_manager
        self.stm32_handler = STM32FrameworkHandler(settings_manager, terminal)  # Create an instance of STM32FrameworkHandler
        self.setWindowTitle("Install STM32 Framework")
        self.setFixedWidth(400)
        layout = QVBoxLayout()

        # Label and text field for the framework path
        self.label = QLabel("Framework Directory:")
        self.path_input = QLineEdit()
        layout.addWidget(self.label)
        layout.addWidget(self.path_input)

        # Button to browse for the framework directory
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_directory)
        layout.addWidget(self.browse_button)

        # Button to install the framework
        self.install_button = QPushButton("Install Framework")
        self.install_button.clicked.connect(self.install_framework)
        layout.addWidget(self.install_button)

        # Use the new check_framework_status method
        self.status = not self.stm32_handler.framework_installed
        if self.stm32_handler.framework_installed:
            QMessageBox.information(None, "Success", 
                f"STM32 Framework is already installed at {self.stm32_handler.framework_path}")

        self.setLayout(layout)

    def browse_directory(self):
        """Open a file dialog to select the framework directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Framework Directory")
        if directory:
            self.path_input.setText(directory)

    def install_framework(self):
        """Clone the STM32 framework from GitHub."""
        framework_path = self.path_input.text() + "/STM32_myDevelopment_Framework"
        
        if not os.path.exists(framework_path):
            os.makedirs(framework_path)  # Create the directory if it doesn't exist
        else:
            QMessageBox.warning(self, "Warning", "The SDK/Framework already exists. Please choose a different directory.")
            return

        # Clone the framework from GitHub at the specified framework_path
        clone_command = f"git clone https://github.com/nghia12a1-t-ara/STM32_myDevelopment_Framework.git {framework_path}"
        result = subprocess.run(clone_command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            QMessageBox.information(self, "Success", "STM32 Framework installed successfully.")
            self.stm32_handler.set_framework_path(framework_path)  # Save the path using the handler
            self.accept()  # Close the dialog
        else:
            QMessageBox.warning(self, "Error", f"Failed to install STM32 Framework:\n{result.stderr}")
    def getstatus(self):
        return self.status

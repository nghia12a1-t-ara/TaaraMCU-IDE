"""
STM32 Framework Handler - Implements FrameworkBase for STM32 development.
"""
import os
import json
import shutil
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path

from PyQt6.QtCore import QObject

from taara_ide.frameworks.base import FrameworkBase, FrameworkInfo, ProjectTemplate
from taara_ide.utils.resource import Result


class STM32Handler(FrameworkBase):
    """
    Framework handler for STM32 development with TaaraFramework.
    
    Supports:
        - STM32F4 series (more can be added)
        - Project creation from templates
        - Build/Clean/Flash operations
        - Framework installation from GitHub
    """
    
    FRAMEWORK_REPO = "https://github.com/nghia12a1-t-ara/STM32_myDevelopment_Framework.git"
    SUPPORTED_MCUS = [
        "STM32F401", "STM32F405", "STM32F407", "STM32F410",
        "STM32F411", "STM32F412", "STM32F413", "STM32F415",
        "STM32F417", "STM32F423", "STM32F427", "STM32F429",
        "STM32F437", "STM32F439", "STM32F446", "STM32F469",
        "STM32F479"
    ]
    
    def __init__(self, settings_manager=None, terminal=None, parent=None):
        super().__init__(settings_manager, terminal, parent)
        
        # Project state
        self._project_path: Optional[str] = None
        self._project_name: Optional[str] = None
        self._project_config: Optional[Dict[str, Any]] = None
        self._framework_path: Optional[str] = None
        self._makefile_header: str = ""
        self._framework_content: str = ""
        
        # Load saved framework path
        self._load_framework_path()
    
    @property
    def info(self) -> FrameworkInfo:
        """Get framework information."""
        return FrameworkInfo(
            id="stm32-taara",
            name="STM32 TaaraFramework",
            version="1.0.0",
            description="STM32 development framework with HAL support",
            supported_mcus=self.SUPPORTED_MCUS,
            installed=self.is_installed(),
            install_path=self._framework_path or ""
        )
    
    def _load_framework_path(self):
        """Load framework path from settings."""
        if self._settings:
            self._framework_path = self._settings.get_stm32_framework_path()
    
    def is_installed(self) -> bool:
        """Check if framework is installed."""
        return bool(self._framework_path and os.path.exists(self._framework_path))
    
    def get_install_path(self) -> Optional[str]:
        """Get the framework installation path."""
        return self._framework_path
    
    def set_install_path(self, path: str) -> Result:
        """Set/update the framework installation path."""
        if not os.path.exists(path):
            return Result(success=False, message="Path does not exist")
        
        self._framework_path = path
        if self._settings:
            self._settings.set_stm32_framework_path(path)
        
        return Result(success=True)
    
    def install(self, target_path: str) -> Result:
        """
        Install framework by cloning from GitHub.
        
        Args:
            target_path: Directory to install framework
            
        Returns:
            Result indicating success or failure
        """
        self.install_started.emit()
        
        framework_path = os.path.join(target_path, "STM32_myDevelopment_Framework")
        
        if os.path.exists(framework_path):
            self.install_finished.emit(False)
            return Result(
                success=False, 
                message="Framework already exists at this location"
            )
        
        try:
            os.makedirs(framework_path, exist_ok=True)
            self.install_progress.emit("Cloning repository...", 50)
            
            result = subprocess.run(
                f"git clone {self.FRAMEWORK_REPO} {framework_path}",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.install_finished.emit(False)
                return Result(success=False, message=result.stderr)
            
            # Save path
            self._framework_path = framework_path
            if self._settings:
                self._settings.set_stm32_framework_path(framework_path)
            
            self.install_progress.emit("Installation complete", 100)
            self.install_finished.emit(True)
            
            return Result(success=True, data=framework_path)
            
        except Exception as e:
            self.install_finished.emit(False)
            return Result(success=False, message=str(e))
    
    def uninstall(self) -> Result:
        """Uninstall framework (remove path reference, not files)."""
        self._framework_path = None
        if self._settings:
            self._settings.set_stm32_framework_path("")
        return Result(success=True)
    
    def get_templates(self) -> List[ProjectTemplate]:
        """Get available project templates."""
        return [
            ProjectTemplate(
                id="default",
                name="Basic STM32 Project",
                description="Minimal STM32 project with main.c",
                files={
                    "src/main.c": self._get_main_template()
                }
            ),
            ProjectTemplate(
                id="blinky",
                name="LED Blink Example",
                description="Simple LED blinking example",
                files={
                    "src/main.c": self._get_blinky_template()
                }
            )
        ]
    
    def create_project(
        self,
        project_path: str,
        project_name: str,
        template_id: str = "default",
        mcu: str = "STM32F407",
        options: Optional[Dict[str, Any]] = None
    ) -> Result:
        """
        Create a new STM32 project.
        
        Args:
            project_path: Base directory for the project
            project_name: Name of the project
            template_id: Template to use
            mcu: Target MCU
            options: Additional options
            
        Returns:
            Result with project path on success
        """
        if not self._framework_path:
            return Result(success=False, message="Framework path is not set")
        
        options = options or {}
        
        # Create project directory
        self._project_name = f"{project_name}_TaaraFramework"
        self._project_path = os.path.join(project_path, self._project_name).replace('\\', '/')
        
        try:
            os.makedirs(self._project_path, exist_ok=True)
            
            # Create src folder and main.c
            src_folder = os.path.join(self._project_path, "src")
            os.makedirs(src_folder, exist_ok=True)
            
            # Get template files
            templates = {t.id: t for t in self.get_templates()}
            template = templates.get(template_id, templates["default"])
            
            for file_path, content in template.files.items():
                full_path = os.path.join(self._project_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
            
            # Create project config
            self._project_config = {
                "project_dir": self._project_path,
                "project_name": self._project_name,
                "mcu": mcu,
                "use_framework": True,
                "framework_path": self._framework_path,
                "source_files": [],
                "include_directories": [],
                "compiler_optimize_level": options.get("optimize", "O2"),
                "preprocessor": f"-D{mcu[:7]}",
                "linker_options": "-lstdc++ -lm",
            }
            
            # Save project config
            config_file = os.path.join(self._project_path, ".taara_project")
            with open(config_file, 'w') as f:
                json.dump(self._project_config, f, indent=2)
            
            # Create Makefile
            self._create_makefile(mcu, options)
            
            # Change terminal directory
            if self._terminal:
                self._terminal.execute_command("cd", [self._project_path])
            
            self.project_created.emit(self._project_path)
            self.log("Info", f"Created STM32 project: {self._project_name}")
            
            return Result(success=True, data=self._project_path)
            
        except Exception as e:
            return Result(success=False, message=str(e))
    
    def _create_makefile(self, mcu: str, options: Dict[str, Any]):
        """Create project Makefile from framework template."""
        framework_makefile = os.path.join(
            self._framework_path, "STM32F4_Framework", "Makefile"
        ).replace('\\', '/')
        
        project_makefile = os.path.join(
            self._project_path, "Makefile"
        ).replace('\\', '/')
        
        # Read framework Makefile template
        if os.path.exists(framework_makefile):
            with open(framework_makefile, 'r') as f:
                self._framework_content = f.read()
        
        # Create Makefile header
        modules = options.get("modules", ["BASE", "CLOCK"])
        self._makefile_header = f"""PROJECT         := USER
PROJECT_DIR     := {self._project_path}
FRAMEWORK_DIR   := {self._framework_path}/STM32F4_Framework
SRC_DIRS        += $(PROJECT_DIR)/src
MODULE_LIST     := {' '.join(modules)}
PROJ_NAME       := {self._project_name}
"""
        
        # Write combined Makefile
        with open(project_makefile, 'w') as f:
            f.write(self._makefile_header + self._framework_content)
    
    def load_project(self, project_path: str) -> Result:
        """
        Load an existing STM32 project.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Result indicating success or failure
        """
        if not os.path.exists(project_path):
            return Result(success=False, message="Project directory does not exist")
        
        config_file = os.path.join(project_path, ".taara_project")
        if not os.path.exists(config_file):
            return Result(success=False, message="Project config file not found")
        
        try:
            with open(config_file, 'r') as f:
                self._project_config = json.load(f)
            
            self._project_path = self._project_config.get("project_dir", project_path)
            self._project_name = self._project_config.get("project_name", "")
            
            # Change terminal directory
            if self._terminal:
                self._terminal.execute_command("cd", [self._project_path])
            
            self.log("Info", "Loaded STM32 project from TaaraFramework")
            
            return Result(success=True, data=self._project_path)
            
        except Exception as e:
            return Result(success=False, message=str(e))
    
    def build_project(self) -> Result:
        """Build the current project."""
        if not self._project_path or not os.path.exists(self._project_path):
            self.log("Error", "Project directory does not exist")
            return Result(success=False, message="No project loaded")
        
        def on_finished(_):
            self.log("Info", "Build finished")
        
        if self._terminal:
            self._terminal.run_command("make build", on_finished=on_finished)
        
        return Result(success=True)
    
    def clean_project(self) -> Result:
        """Clean the current project."""
        if not self._project_path or not os.path.exists(self._project_path):
            self.log("Error", "Project directory does not exist")
            return Result(success=False, message="No project loaded")
        
        def on_finished(_):
            self.log("Info", "Clean finished")
        
        if self._terminal:
            self._terminal.run_command("make clean", on_finished=on_finished)
        
        return Result(success=True)
    
    def flash_project(self) -> Result:
        """Flash the project to target device."""
        if not self._project_path:
            self.log("Error", "No project loaded")
            return Result(success=False, message="No project loaded")
        
        hex_path = os.path.join(
            self._project_path, "output", f"{self._project_name}.hex"
        )
        
        if not os.path.exists(hex_path):
            self.log("Error", "Binary file not found. Please build first.")
            return Result(success=False, message="Binary not found")
        
        self.log("Info", f"Flashing: {hex_path}")
        
        def on_finished(_):
            self.log("Info", "Flash finished")
        
        if self._terminal:
            self._terminal.run_command("make run", on_finished=on_finished)
        
        return Result(success=True)
    
    def add_makefile_header(self, content: str):
        """Add content to Makefile header."""
        self._makefile_header += content
        
        if self._project_path:
            makefile_path = os.path.join(self._project_path, "Makefile")
            with open(makefile_path, 'w') as f:
                f.write(self._makefile_header + self._framework_content)
    
    def close_project(self):
        """Close the current project."""
        self._project_path = None
        self._project_name = None
        self._project_config = None
        self.log("Info", "Closed STM32 project")
    
    def get_defines(self, mcu: str) -> List[str]:
        """Get preprocessor defines for MCU."""
        # Extract series from MCU name (e.g., STM32F407 -> STM32F4)
        if mcu.startswith("STM32"):
            series = mcu[:7]
            return [series]
        return []
    
    def get_include_paths(self, project_path: str) -> List[str]:
        """Get include paths for framework."""
        paths = []
        if self._framework_path:
            framework_inc = os.path.join(
                self._framework_path, "STM32F4_Framework", "inc"
            )
            if os.path.exists(framework_inc):
                paths.append(framework_inc)
        return paths
    
    # Template content methods
    
    def _get_main_template(self) -> str:
        """Get default main.c template."""
        return '''/**
 * @file main.c
 * @brief Main application entry point
 */

#include <stdint.h>

int main(void)
{
    /* System initialization */
    
    /* Main loop */
    while (1)
    {
        /* Application code */
    }
    
    return 0;
}
'''
    
    def _get_blinky_template(self) -> str:
        """Get LED blink template."""
        return '''/**
 * @file main.c
 * @brief LED Blink Example
 */

#include <stdint.h>

/* Simple delay function */
void delay(volatile uint32_t count)
{
    while (count--);
}

int main(void)
{
    /* TODO: Configure GPIO for LED */
    
    /* Main loop */
    while (1)
    {
        /* Toggle LED */
        
        /* Delay */
        delay(1000000);
    }
    
    return 0;
}
'''

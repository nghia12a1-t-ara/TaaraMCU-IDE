"""
Build Controller - Manages all build-related operations
Refactored from MainWindow to keep concerns separated
"""

import os
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from taara_ide.core.compiler import LanguageDetector, Language, NativeCCompiler, PythonExecutor
from taara_ide.core.compiler.c_project_config import CProjectConfigManager
from taara_ide.services.build_service import BuildService, BuildResult


class BuildController(QObject):
    """
    Controller for handling all build operations (compile, run, flash)
    Separates build logic from MainWindow
    """
    
    # Signals
    build_output = pyqtSignal(str)  # Build output text
    build_finished = pyqtSignal(object)  # BuildResult
    status_message = pyqtSignal(str, int)  # Message, timeout
    
    def __init__(self, parent, build_service: BuildService, 
                 project_service, project_view, editor_manager, terminal):
        super().__init__(parent)
        
        self._build_service = build_service
        self._project_service = project_service
        self._project_view = project_view
        self._editor_manager = editor_manager
        self._terminal = terminal
        
        self._pending_run_after_build = False
        
        # Connect build service signals
        self._build_service.build_output.connect(self.build_output.emit)
        self._build_service.build_finished.connect(self._on_build_service_finished)
    
    def clean(self) -> None:
        """Clean build artifacts"""
        self._build_service.clean()
    
    def compile(self, run_after_build: bool = False) -> None:
        """
        Compile current project or file
        
        Args:
            run_after_build: If True, run executable after successful build
        """
        self._pending_run_after_build = run_after_build
        
        # Show terminal in Terminal mode
        self._show_terminal()
        
        if not self._project_service.is_open:
            # Try to find .cproject in current directory
            current_dir = self._get_current_directory()
            
            if current_dir:
                cproject_path = os.path.join(current_dir, ".cproject")
                if os.path.exists(cproject_path):
                    # Build C project using .cproject
                    self._compile_c_project(current_dir)
                    return
            
            # No .cproject found, try to compile current file
            editor = self._editor_manager.get_current_editor()
            if editor and editor.file_path:
                self._compile_single_file(editor.file_path)
            else:
                self.status_message.emit("No project or file to compile", 3000)
        else:
            # Build using BuildService
            self._build_service.build()
    
    def flash(self) -> None:
        """Flash compiled program to target device"""
        if not self._project_service.is_open:
            QMessageBox.warning(
                self.parent(),
                "No Project",
                "Please open or create a project before flashing."
            )
            return
        
        project_config = self._project_service.get_current_project()
        if not project_config:
            return
        
        # Show terminal
        self._show_terminal()
        
        # Use BuildService to flash
        self._build_service.flash(project_config.root_path)
    
    def _compile_c_project(self, project_path: str) -> None:
        """Compile C project using .cproject configuration"""
        # Load .cproject
        c_config = CProjectConfigManager.load(project_path)
        if not c_config:
            self.status_message.emit("Failed to load .cproject", 3000)
            return
        
        # Create compiler and connect signals
        compiler = NativeCCompiler(self)
        compiler.compile_output.connect(self.build_output.emit)
        
        def on_finished(success, errors):
            output_file = None
            if success and hasattr(compiler, '_worker') and compiler._worker:
                output_file = compiler._worker.output_path
            
            result = BuildResult(
                success=success,
                output_file=output_file,
                errors=[e for e in errors if e.is_error],
                warnings=[e for e in errors if not e.is_error],
                duration_ms=0
            )
            
            self.status_message.emit(
                "Build successful" if success else "Build failed",
                3000
            )
            
            self._on_build_finished(result)
        
        compiler.compile_finished.connect(on_finished)
        
        # Start compilation
        self.status_message.emit("Building C project...", 0)
        compiler.compile_project(project_path, c_config)
    
    def _compile_single_file(self, file_path: str) -> None:
        """Compile a single file without a project"""
        lang = LanguageDetector.detect(file_path)
        
        if lang == Language.PYTHON:
            self._execute_python_file(file_path)
        elif lang in (Language.C, Language.CPP):
            self._compile_native_c_file(file_path)
        else:
            self.status_message.emit(f"Cannot compile {lang.value} files", 3000)
    
    def _execute_python_file(self, file_path: str) -> None:
        """Execute Python file"""
        executor = PythonExecutor(self)
        executor.compile_output.connect(self.build_output.emit)
        
        def on_finished(success, errors):
            result = BuildResult(
                success=success,
                output_file=file_path if success else None,
                errors=errors,
                warnings=[],
                duration_ms=0
            )
            self.status_message.emit(
                "Execution finished" if success else "Execution failed", 
                3000
            )
            self._on_build_finished(result)
        
        executor.compile_finished.connect(on_finished)
        executor.compile([file_path], "", {})
    
    def _compile_native_c_file(self, file_path: str) -> None:
        """Compile native C/C++ file"""
        compiler = NativeCCompiler(self)
        compiler.compile_output.connect(self.build_output.emit)
        
        def on_finished(success, errors):
            output_file = None
            if success and hasattr(compiler, '_worker') and compiler._worker:
                output_file = compiler._worker.output_path
            
            result = BuildResult(
                success=success,
                output_file=output_file,
                errors=[e for e in errors if e.is_error],
                warnings=[e for e in errors if not e.is_error],
                duration_ms=0
            )
            self.status_message.emit(
                "Build successful" if success else "Build failed", 
                3000
            )
            self._on_build_finished(result)
        
        compiler.compile_finished.connect(on_finished)

        build_dir = os.path.join(os.path.dirname(file_path), "build")
        output_name = os.path.splitext(os.path.basename(file_path))[0]
        
        import platform
        if platform.system() == "Windows":
            output_path = os.path.join(build_dir, f"{output_name}.exe")
        else:
            output_path = os.path.join(build_dir, output_name)
        
        options = {
            "build_dir": build_dir,
            "optimization": "-O2",
            "debug_info": True,
            "defines": [],
            "include_paths": [],
            "compiler_flags": [],
            "linker_flags": []
        }
        
        compiler.compile([file_path], output_path, options)
    
    def _on_build_service_finished(self, result: BuildResult) -> None:
        """Handle build finished from BuildService"""
        self._on_build_finished(result)
    
    def _on_build_finished(self, result: BuildResult) -> None:
        """
        Unified handler for all build finished events
        Handles both regular build and compile-and-run
        """
        if result.success and result.output_file:
            self._terminal.append_output_with_color(f"Build finished result: {result.output_file}\n", "#00FF00")
            if self._pending_run_after_build:
                self._pending_run_after_build = False
                self._run_executable(result.output_file)
        elif not result.success:
            if self._terminal:
                self._terminal.append_output_with_color("\nBuild failed. Cannot run executable.\n", "#FF5555")
        
        # Emit build finished signal
        self.build_finished.emit(result)
    
    def _run_executable(self, exe_path: str) -> None:
        """Run the compiled executable in terminal"""
        if not self._terminal:
            return
        
        # Make sure terminal is visible and in terminal mode
        self._show_terminal()
        
        # Execute the file
        self._terminal.append_output_with_color(f"\n{'='*60}\n", "#00AAFF")
        self._terminal.append_output_with_color(f"Running: {os.path.basename(exe_path)}\n", "#00FF00")
        self._terminal.append_output_with_color(f"{'='*60}\n", "#00AAFF")
        
        # Use raw path if no spaces, otherwise quote it properly
        if ' ' in exe_path:
            # For paths with spaces, use proper Windows quoting
            import sys
            if sys.platform == "win32":
                # Windows needs special handling for paths with spaces
                command = exe_path  # Let cmd.exe handle the quoting
            else:
                command = f'"{exe_path}"'
        else:
            command = exe_path
        
        # Run the executable
        self._terminal.execute_command(command)
    
    def _show_terminal(self) -> None:
        """Show terminal in Terminal mode"""
        if self._terminal:
            if not self._terminal.isVisible():
                self._terminal.show()
                # Terminal's parent is the dock widget
                if self._terminal.parent():
                    self._terminal.parent().show()
            self._terminal.set_terminal_mode()
    
    def _get_current_directory(self) -> Optional[str]:
        """Get current project directory from ProjectView"""
        if self._project_view:
            return self._project_view.get_project_directory()
        return None

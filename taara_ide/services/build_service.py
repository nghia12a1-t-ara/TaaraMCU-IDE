"""
Build system service
"""
import os
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.core.compiler import GCCCompiler, NativeCCompiler, PythonExecutor
from taara_ide.core.compiler import LanguageDetector, Language
from taara_ide.core.compiler.c_project_config import CProjectConfig, CProjectConfigManager
from taara_ide.core.base import BuildStatus, CompileError
from taara_ide.config import SettingsManager
from taara_ide.services.project_service import ProjectService, ProjectConfig


@dataclass
class BuildResult:
    """Result of a build operation"""
    success: bool
    output_file: Optional[str] = None
    errors: List[CompileError] = None
    warnings: List[CompileError] = None
    duration_ms: int = 0
    
    def __post_init__(self):
        self.errors = self.errors or []
        self.warnings = self.warnings or []


class BuildService(QObject):
    """
    Service for build operations.
    
    Signals:
        build_started: Emitted when build starts
        build_progress: Emitted with progress (message, percentage)
        build_finished: Emitted when build finishes (BuildResult)
        build_output: Emitted for build output lines
    """
    
    build_started = Signal()
    build_progress = Signal(str, int)
    build_finished = Signal(object)  # BuildResult
    build_output = Signal(str)
    
    def __init__(
        self,
        project_service: ProjectService,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._project = project_service
        self._settings = SettingsManager()
        
        self._gcc_compiler = GCCCompiler(self)
        self._native_compiler = NativeCCompiler(self)
        self._python_executor = PythonExecutor(self)
        self._current_compiler = None
        
        self._start_time: int = 0
        
    def _select_compiler(self) -> Optional[Any]:
        """Select appropriate compiler based on project type and files"""
        if not self._project.is_open:
            return None
        
        project_config = self._project.config
        
        # Check project type
        if project_config.project_type == "python":
            return self._python_executor
        elif project_config.project_type == "native":
            return self._native_compiler
        elif project_config.project_type == "embedded":
            return self._gcc_compiler
        
        # Auto-detect from files
        source_files = self._project.get_source_files()
        if source_files:
            first_file = source_files[0]
            lang = LanguageDetector.detect(first_file)
            
            if lang == Language.PYTHON:
                return self._python_executor
            elif lang in (Language.C, Language.CPP):
                # Check if it's embedded (has ARM-specific code or MCU set)
                if project_config.target_mcu:
                    return self._gcc_compiler
                else:
                    return self._native_compiler
        
        # Default to GCC for embedded
        return self._gcc_compiler
    
    def _connect_compiler_signals(self, compiler):
        """Connect compiler signals"""
        # Disconnect previous compiler if any
        if self._current_compiler:
            try:
                self._current_compiler.compile_started.disconnect()
                self._current_compiler.compile_progress.disconnect()
                self._current_compiler.compile_output.disconnect()
                self._current_compiler.compile_finished.disconnect()
            except:
                pass
        
        # Connect new compiler
        compiler.compile_started.connect(self.build_started.emit)
        compiler.compile_progress.connect(self.build_progress.emit)
        compiler.compile_output.connect(self.build_output.emit)
        compiler.compile_finished.connect(self._on_compile_finished)
        
        self._current_compiler = compiler
    
    @property
    def status(self) -> BuildStatus:
        if self._current_compiler:
            return self._current_compiler.status
        return BuildStatus.IDLE
    
    @property
    def is_building(self) -> bool:
        if self._current_compiler:
            return self._current_compiler.status == BuildStatus.COMPILING
        return False
    
    def build(self, config_override: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start a build.
        
        Args:
            config_override: Optional dict to override project config settings
            
        Returns:
            True if build was started successfully
        """
        if not self._project.is_open:
            self.build_output.emit("Error: No project open")
            return False
        
        compiler = self._select_compiler()
        if not compiler:
            self.build_output.emit("Error: No suitable compiler found")
            return False
        
        self._connect_compiler_signals(compiler)
        
        if self.is_building:
            self.build_output.emit("Error: Build already in progress")
            return False
        
        import time
        self._start_time = int(time.time() * 1000)
        
        project_config = self._project.config
        project_path = self._project.path
        
        if compiler == self._python_executor:
            return self._build_python(project_config, project_path, config_override)
        
        # C/C++ compilation - check for .cproject first
        c_config = CProjectConfigManager.load(project_path)
        if c_config and compiler == self._native_compiler:
            return self._build_c_project(c_config, project_path, config_override)
        
        # Fall back to standard build
        return self._build_c_cpp(compiler, project_config, project_path, config_override)
    
    def _build_c_project(self, c_config: CProjectConfig, project_path: str, config_override) -> bool:
        """Build C/C++ project using .cproject configuration"""
        self.build_output.emit("=" * 60)
        self.build_output.emit(f"Building C Project: {c_config.project_name}")
        self.build_output.emit("=" * 60)
        
        # Apply config overrides
        if config_override:
            if "optimization_level" in config_override:
                c_config.optimization_level = config_override["optimization_level"]
            if "active_config" in config_override:
                c_config.active_config = config_override["active_config"]
        
        return self._native_compiler.compile_project(project_path, c_config)
    
    def _build_python(self, project_config, project_path, config_override) -> bool:
        """Execute Python script"""
        source_files = self._project.get_source_files()
        if not source_files:
            self.build_output.emit("Error: No Python files found")
            return False
        
        # Use first .py file or main.py if exists
        main_file = None
        for f in source_files:
            if f.endswith('main.py'):
                main_file = f
                break
        
        if not main_file:
            main_file = source_files[0]
        
        self.build_output.emit(f"Executing {os.path.basename(main_file)}...")
        
        options = {
            "args": project_config.python_args if hasattr(project_config, 'python_args') else []
        }
        
        if config_override:
            options.update(config_override)
        
        return self._current_compiler.compile([main_file], "", options)
    
    def _build_c_cpp(self, compiler, project_config, project_path, config_override) -> bool:
        """Build C/C++ project"""
        # Collect source files
        source_files = self._project.get_source_files()
        if not source_files:
            self.build_output.emit("Error: No source files found")
            return False
        
        # Build output path
        build_dir = os.path.join(project_path, "build")
        output_name = project_config.name.replace(" ", "_").lower()
        
        # Different extension for different platforms
        if compiler == self._native_compiler:
            import platform
            if platform.system() == "Windows":
                output_ext = ".exe"
            else:
                output_ext = ""
        else:
            output_ext = ".elf"
        
        output_path = os.path.join(build_dir, f"{output_name}{output_ext}")
        
        # Prepare compiler options
        options = {
            "build_dir": build_dir,
            "optimization": self._get_optimization_flag(project_config.optimization),
            "debug_info": project_config.debug_info,
            "defines": project_config.defines.copy(),
            "include_paths": self._project.get_include_paths(),
            "compiler_flags": project_config.compiler_flags.copy(),
            "linker_flags": project_config.linker_flags.copy(),
        }
        
        # Add embedded-specific options
        if compiler == self._gcc_compiler:
            options["target_mcu"] = self._get_mcu_core(project_config.target_mcu)
            
            # Add linker script if specified
            if project_config.linker_script:
                ld_path = os.path.join(project_path, project_config.linker_script)
                if os.path.exists(ld_path):
                    options["linker_script"] = ld_path
        
        # Apply overrides
        if config_override:
            options.update(config_override)
        
        self.build_output.emit(f"Building {project_config.name}...")
        self.build_output.emit(f"Compiler: {compiler.get_toolchain_info().name if compiler.get_toolchain_info() else 'Unknown'}")
        self.build_output.emit(f"Source files: {len(source_files)}")
        
        return compiler.compile(source_files, output_path, options)
    
    def clean(self) -> bool:
        """Clean build artifacts"""
        if not self._project.is_open:
            return False
        
        build_dir = os.path.join(self._project.path, "build")
        success = self._current_compiler.clean(build_dir) if self._current_compiler else False
        
        if success:
            self.build_output.emit("Clean completed")
        else:
            self.build_output.emit("Clean failed")
        
        return success
    
    def rebuild(self) -> bool:
        """Clean and rebuild"""
        self.clean()
        return self.build()
    
    def cancel(self) -> None:
        """Cancel current build"""
        if self._current_compiler:
            self._current_compiler.cancel()
    
    def _on_compile_finished(self, success: bool, errors: list):
        import time
        duration = int(time.time() * 1000) - self._start_time
        
        # Separate errors and warnings
        error_list = [e for e in errors if e.is_error]
        warning_list = [e for e in errors if not e.is_error]
        
        output_file = None
        if success and self._current_compiler:
            if hasattr(self._current_compiler, '_worker') and self._current_compiler._worker:
                output_file = self._current_compiler._worker.output_path
        
        result = BuildResult(
            success=success,
            output_file=output_file,
            errors=error_list,
            warnings=warning_list,
            duration_ms=duration
        )
        
        if success:
            self.build_output.emit(f"Build successful ({duration}ms)")
            if output_file:
                self.build_output.emit(f"Output: {output_file}")
        else:
            self.build_output.emit(f"Build failed with {len(error_list)} error(s)")
        
        self.build_finished.emit(result)
    
    def _get_optimization_flag(self, level: str) -> str:
        """Convert optimization level name to flag"""
        levels = {
            "Debug": "-Og",
            "Release": "-O2",
            "Size": "-Os",
            "Speed": "-O3",
            "None": "-O0"
        }
        return levels.get(level, "-Og")
    
    def _get_mcu_core(self, mcu: str) -> str:
        """Extract core type from MCU name"""
        mcu_upper = mcu.upper()
        
        # STM32 family detection
        if "STM32F0" in mcu_upper:
            return "cortex-m0"
        elif "STM32F1" in mcu_upper or "STM32F2" in mcu_upper:
            return "cortex-m3"
        elif "STM32F3" in mcu_upper or "STM32F4" in mcu_upper:
            return "cortex-m4"
        elif "STM32F7" in mcu_upper or "STM32H7" in mcu_upper:
            return "cortex-m7"
        elif "STM32L0" in mcu_upper:
            return "cortex-m0plus"
        elif "STM32L4" in mcu_upper or "STM32G4" in mcu_upper:
            return "cortex-m4"
        
        return "cortex-m4"  # Default

"""
Build system service
"""
import os
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.core.compiler import GCCCompiler
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
        self._compiler = GCCCompiler(self)
        
        # Connect compiler signals
        self._compiler.compile_started.connect(self.build_started.emit)
        self._compiler.compile_progress.connect(self.build_progress.emit)
        self._compiler.compile_output.connect(self.build_output.emit)
        self._compiler.compile_finished.connect(self._on_compile_finished)
        
        self._start_time: int = 0
    
    @property
    def status(self) -> BuildStatus:
        return self._compiler.status
    
    @property
    def is_building(self) -> bool:
        return self._compiler.status == BuildStatus.COMPILING
    
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
        
        if self.is_building:
            self.build_output.emit("Error: Build already in progress")
            return False
        
        import time
        self._start_time = int(time.time() * 1000)
        
        project_config = self._project.config
        project_path = self._project.path
        
        # Collect source files
        source_files = self._project.get_source_files()
        if not source_files:
            self.build_output.emit("Error: No source files found")
            return False
        
        # Build output path
        build_dir = os.path.join(project_path, "build")
        output_name = project_config.name.replace(" ", "_").lower()
        output_path = os.path.join(build_dir, f"{output_name}.elf")
        
        # Prepare compiler options
        options = {
            "build_dir": build_dir,
            "optimization": self._get_optimization_flag(project_config.optimization),
            "debug_info": project_config.debug_info,
            "defines": project_config.defines.copy(),
            "include_paths": self._project.get_include_paths(),
            "compiler_flags": project_config.compiler_flags.copy(),
            "linker_flags": project_config.linker_flags.copy(),
            "target_mcu": self._get_mcu_core(project_config.target_mcu),
        }
        
        # Add linker script if specified
        if project_config.linker_script:
            ld_path = os.path.join(project_path, project_config.linker_script)
            if os.path.exists(ld_path):
                options["linker_script"] = ld_path
        
        # Apply overrides
        if config_override:
            options.update(config_override)
        
        self.build_output.emit(f"Building {project_config.name}...")
        self.build_output.emit(f"Source files: {len(source_files)}")
        
        return self._compiler.compile(source_files, output_path, options)
    
    def clean(self) -> bool:
        """Clean build artifacts"""
        if not self._project.is_open:
            return False
        
        build_dir = os.path.join(self._project.path, "build")
        success = self._compiler.clean(build_dir)
        
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
        self._compiler.cancel()
    
    def _on_compile_finished(self, success: bool, errors: list):
        import time
        duration = int(time.time() * 1000) - self._start_time
        
        # Separate errors and warnings
        error_list = [e for e in errors if e.is_error]
        warning_list = [e for e in errors if not e.is_error]
        
        result = BuildResult(
            success=success,
            output_file=None,  # TODO: Get from compiler
            errors=error_list,
            warnings=warning_list,
            duration_ms=duration
        )
        
        if success:
            self.build_output.emit(f"Build successful ({duration}ms)")
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

"""
GCC-based compiler implementation for ARM targets
"""
import os
import re
import subprocess
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal as Signal

from taara_ide.core.base import CompilerBase, BuildStatus, ToolchainInfo, CompileError
from taara_ide.utils.process_utils import ProcessUtils
from taara_ide.utils.resource import Result
from taara_ide.config.settings_manager import SettingsManager


@dataclass
class BuildOptions:
    """Build configuration options"""
    optimization: str = "-Og"
    debug_info: bool = True
    defines: List[str] = None
    include_paths: List[str] = None
    compiler_flags: List[str] = None
    linker_flags: List[str] = None
    linker_script: Optional[str] = None
    target_mcu: str = ""
    
    def __post_init__(self):
        self.defines = self.defines or []
        self.include_paths = self.include_paths or []
        self.compiler_flags = self.compiler_flags or []
        self.linker_flags = self.linker_flags or []


class CompileWorker(QThread):
    """Worker thread for compilation"""
    
    progress = Signal(str, int)
    output = Signal(str)
    finished_signal = Signal(bool, list)
    
    def __init__(
        self,
        gcc_path: str,
        source_files: List[str],
        output_path: str,
        options: BuildOptions,
        build_dir: str
    ):
        super().__init__()
        self.gcc_path = gcc_path
        self.source_files = source_files
        self.output_path = output_path
        self.options = options
        self.build_dir = build_dir
        self._cancelled = False
        self._errors: List[CompileError] = []
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            os.makedirs(self.build_dir, exist_ok=True)
            
            total_files = len(self.source_files)
            object_files = []
            
            for i, source in enumerate(self.source_files):
                if self._cancelled:
                    self.finished_signal.emit(False, [])
                    return
                
                basename = os.path.basename(source)
                obj_file = os.path.join(
                    self.build_dir, 
                    os.path.splitext(basename)[0] + ".o"
                )
                
                self.progress.emit(f"Compiling {basename}...", int((i / total_files) * 80))
                
                if not self._compile_file(source, obj_file):
                    self.finished_signal.emit(False, self._errors)
                    return
                
                object_files.append(obj_file)
            
            self.progress.emit("Linking...", 85)
            if not self._link(object_files):
                self.finished_signal.emit(False, self._errors)
                return
            
            self.progress.emit("Generating outputs...", 95)
            self._generate_outputs()
            
            self.progress.emit("Build complete", 100)
            self.finished_signal.emit(True, [])
            
        except Exception as e:
            self._errors.append(CompileError(
                file="", line=0, column=0,
                message=str(e), is_error=True
            ))
            self.finished_signal.emit(False, self._errors)
    
    def _compile_file(self, source: str, output: str) -> bool:
        """Compile a single source file"""
        cmd = [self.gcc_path]
        
        if self.options.target_mcu:
            cmd.extend(["-mcpu=" + self.options.target_mcu, "-mthumb"])
        
        cmd.append(self.options.optimization)
        
        if self.options.debug_info:
            cmd.append("-g3")
        
        cmd.extend(["-Wall", "-fdata-sections", "-ffunction-sections"])
        
        for define in self.options.defines:
            cmd.append(f"-D{define}")
        
        for inc in self.options.include_paths:
            cmd.extend([f"-I{inc}"])
        
        cmd.extend(self.options.compiler_flags)
        cmd.extend(["-c", source, "-o", output])
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.stdout:
            self.output.emit(process.stdout)
        if process.stderr:
            self.output.emit(process.stderr)
            self._parse_errors(process.stderr)
        
        return process.returncode == 0
    
    def _link(self, object_files: List[str]) -> bool:
        """Link object files"""
        cmd = [self.gcc_path]
        
        if self.options.target_mcu:
            cmd.extend(["-mcpu=" + self.options.target_mcu, "-mthumb"])
        
        cmd.extend(object_files)
        
        if self.options.linker_script:
            cmd.extend(["-T", self.options.linker_script])
        
        cmd.extend(["-Wl,--gc-sections", "-Wl,-Map=" + self.output_path + ".map"])
        cmd.extend(self.options.linker_flags)
        cmd.extend(["-o", self.output_path])
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.stdout:
            self.output.emit(process.stdout)
        if process.stderr:
            self.output.emit(process.stderr)
            self._parse_errors(process.stderr)
        
        return process.returncode == 0
    
    def _generate_outputs(self):
        """Generate HEX and BIN files"""
        objcopy = self.gcc_path.replace("gcc", "objcopy")
        size = self.gcc_path.replace("gcc", "size")
        
        subprocess.run([
            objcopy, "-O", "ihex",
            self.output_path,
            self.output_path.replace(".elf", ".hex")
        ], capture_output=True)
        
        subprocess.run([
            objcopy, "-O", "binary",
            self.output_path,
            self.output_path.replace(".elf", ".bin")
        ], capture_output=True)
        
        result = subprocess.run([size, self.output_path], capture_output=True, text=True)
        if result.stdout:
            self.output.emit("\n" + result.stdout)
    
    def _parse_errors(self, output: str):
        """Parse GCC error output"""
        pattern = r'([^:]+):(\d+):(\d+):\s*(error|warning):\s*(.+)'
        
        for match in re.finditer(pattern, output):
            self._errors.append(CompileError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                message=match.group(5),
                is_error=match.group(4) == "error"
            ))


class GCCCompiler(CompilerBase):
    """GCC-based compiler for ARM targets"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsManager()
        self._worker: Optional[CompileWorker] = None
    
    @property
    def gcc_path(self) -> str:
        return self._settings.get_gcc_path()
    
    def compile(
        self,
        source_files: List[str],
        output_path: str,
        options: Dict[str, Any]
    ) -> bool:
        """Start async compilation"""
        if self._status == BuildStatus.COMPILING:
            return False
        
        self._status = BuildStatus.COMPILING
        self._cancelled = False
        self.compile_started.emit()
        
        build_opts = BuildOptions(
            optimization=options.get("optimization", "-Og"),
            debug_info=options.get("debug_info", True),
            defines=options.get("defines", []),
            include_paths=options.get("include_paths", []),
            compiler_flags=options.get("compiler_flags", []),
            linker_flags=options.get("linker_flags", []),
            linker_script=options.get("linker_script"),
            target_mcu=options.get("target_mcu", "cortex-m4")
        )
        
        build_dir = options.get("build_dir", "build")
        
        self._worker = CompileWorker(
            self.gcc_path, source_files, output_path, build_opts, build_dir
        )
        
        self._worker.progress.connect(self.compile_progress.emit)
        self._worker.output.connect(self.compile_output.emit)
        self._worker.finished_signal.connect(self._on_compile_finished)
        
        self._worker.start()
        return True
    
    def _on_compile_finished(self, success: bool, errors: list):
        self._status = BuildStatus.SUCCESS if success else BuildStatus.FAILED
        self.compile_finished.emit(success, errors)
        self._worker = None
    
    def cancel(self):
        super().cancel()
        if self._worker:
            self._worker.cancel()
    
    def clean(self, build_dir: str) -> bool:
        """Clean build directory"""
        import shutil
        try:
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
            return True
        except OSError:
            return False
    
    def get_toolchain_info(self) -> Optional[ToolchainInfo]:
        """Get GCC toolchain information"""
        try:
            result = subprocess.run(
                [self.gcc_path, "--version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                first_line = result.stdout.split('\n')[0]
                version_match = re.search(r'(\d+\.\d+\.\d+)', first_line)
                version = version_match.group(1) if version_match else "unknown"
                
                return ToolchainInfo(
                    name="ARM GCC",
                    version=version,
                    path=self.gcc_path,
                    target="arm-none-eabi"
                )
        except Exception:
            pass
        
        return None

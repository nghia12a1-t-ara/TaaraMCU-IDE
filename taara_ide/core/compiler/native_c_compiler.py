"""
Native C/C++ compiler for host system (Windows/Linux/Mac)
Supports standard GCC/Clang/MSVC compilation for development and testing
"""
import os
import subprocess
import platform
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal as Signal

from taara_ide.core.base import CompilerBase, BuildStatus, ToolchainInfo, CompileError
from taara_ide.core.compiler.gcc_compiler import BuildOptions
from taara_ide.core.compiler.c_project_config import CProjectConfig, CProjectConfigManager

class NativeCCompileWorker(QThread):
    """Worker thread for native C/C++ compilation"""
    
    progress = Signal(str, int)
    output = Signal(str)
    finished_signal = Signal(bool, list)
    
    def __init__(
        self,
        compiler_path: str,
        source_files: List[str],
        output_path: str,
        options: BuildOptions,
        build_dir: str
    ):
        super().__init__()
        self.compiler_path = compiler_path
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
            
            self.progress.emit("Compiling native C/C++ program...", 10)
            
            cmd = [self.compiler_path]
            
            # Add optimization
            cmd.append(self.options.optimization)
            
            # Add debug info
            if self.options.debug_info:
                cmd.append("-g")
            
            # Add warning flags
            cmd.extend(["-Wall", "-Wextra"])
            
            # Add defines
            for define in self.options.defines:
                cmd.append(f"-D{define}")
            
            # This allows header files in the same directory to be found
            for source in self.source_files:
                source_dir = os.path.dirname(os.path.abspath(source))
                if source_dir not in self.options.include_paths:
                    cmd.extend([f"-I{source_dir}"])
            
            # Add include paths
            for inc in self.options.include_paths:
                cmd.extend([f"-I{inc}"])
            
            # Add custom compiler flags
            cmd.extend(self.options.compiler_flags)
            
            # Add source files
            cmd.extend(self.source_files)
            
            # Add output
            cmd.extend(["-o", self.output_path])
            
            # Add linker flags
            cmd.extend(self.options.linker_flags)
            
            self.output.emit(f"Command: {' '.join(cmd)}\n")
            
            self.progress.emit("Compiling...", 50)
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=self.build_dir)
            
            if process.stdout:
                self.output.emit(process.stdout)
            if process.stderr:
                self.output.emit(process.stderr)
                self._parse_errors(process.stderr)
            
            if process.returncode == 0:
                self.progress.emit("Build successful", 100)
                self.finished_signal.emit(True, [])
            else:
                self.progress.emit("Build failed", 100)
                self.finished_signal.emit(False, self._errors)
                
        except Exception as e:
            self._errors.append(CompileError(
                file="", line=0, column=0,
                message=str(e), is_error=True
            ))
            self.finished_signal.emit(False, self._errors)
    
    def _parse_errors(self, output: str):
        """Parse compiler error output"""
        import re
        # GCC/Clang error format: file:line:column: error/warning: message
        pattern = r'([^:]+):(\d+):(\d+):\s*(error|warning):\s*(.+)'
        
        for match in re.finditer(pattern, output):
            self._errors.append(CompileError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                message=match.group(5),
                is_error=match.group(4) == "error"
            ))


class NativeCCompiler(CompilerBase):
    """Native C/C++ compiler for host system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[NativeCCompileWorker] = None
        self._compiler_path = self._detect_compiler()
    
    def _detect_compiler(self) -> str:
        """Detect available C compiler on the system"""
        system = platform.system()
        
        # Try GCC first (most common)
        for compiler in ['gcc', 'g++', 'clang', 'clang++']:
            try:
                result = subprocess.run(
                    [compiler, '--version'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return compiler
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # On Windows, try MSVC
        if system == 'Windows':
            try:
                result = subprocess.run(
                    ['cl.exe', '/?'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return 'cl.exe'
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Default fallback
        return 'gcc'
    
    def compile(
        self,
        source_files: List[str],
        output_path: str,
        options: Dict[str, Any]
    ) -> bool:
        """Start async native compilation"""
        if self._status == BuildStatus.COMPILING:
            return False
        
        self._status = BuildStatus.COMPILING
        self._cancelled = False
        self.compile_started.emit()
        
        build_opts = BuildOptions(
            optimization=options.get("optimization", "-O2"),
            debug_info=options.get("debug_info", True),
            defines=options.get("defines", []),
            include_paths=options.get("include_paths", []),
            compiler_flags=options.get("compiler_flags", []),
            linker_flags=options.get("linker_flags", []),
            linker_script=None,  # Not used for native
            target_mcu=""  # Not used for native
        )
        
        build_dir = options.get("build_dir", "build")
        
        self._worker = NativeCCompileWorker(
            self._compiler_path, source_files, output_path, build_opts, build_dir
        )
        
        self._worker.progress.connect(self.compile_progress.emit)
        self._worker.output.connect(self.compile_output.emit)
        self._worker.finished_signal.connect(self._on_compile_finished)
        
        self._worker.start()
        return True
    
    def compile_project(
        self,
        project_path: str,
        c_config: Optional[CProjectConfig] = None
    ) -> bool:
        """
        Compile a C project using .cproject configuration
        
        Args:
            project_path: Path to project directory
            c_config: Optional CProjectConfig, will load from .cproject if not provided
        """
        if self._status == BuildStatus.COMPILING:
            return False
        
        # Load or use provided config
        if c_config is None:
            c_config = CProjectConfigManager.load(project_path)
            if c_config is None:
                self.compile_output.emit("Error: No .cproject file found")
                return False
        
        # Merge with active build configuration
        config = c_config.merge_with_active_config()
        
        # Collect source files
        source_files = CProjectConfigManager.collect_source_files(project_path, config)
        if not source_files:
            self.compile_output.emit("Error: No source files found")
            return False
        
        self.compile_output.emit(f"Found {len(source_files)} source file(s)")
        for src in source_files:
            self.compile_output.emit(f"  - {os.path.basename(src)}")
        
        # Prepare output path
        output_dir = os.path.join(project_path, config.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        output_name = config.output_name or config.project_name.lower().replace(" ", "_")
        
        # Add extension based on output type and platform
        if config.output_type == "executable":
            if platform.system() == "Windows":
                output_ext = ".exe"
            else:
                output_ext = ""
        elif config.output_type == "static_lib":
            output_ext = ".a"
        else:  # shared_lib
            if platform.system() == "Windows":
                output_ext = ".dll"
            else:
                output_ext = ".so"
        
        output_path = os.path.join(output_dir, f"{output_name}{output_ext}")
        
        # Resolve include paths
        include_paths = CProjectConfigManager.resolve_include_paths(project_path, config)
        
        # Prepare compiler flags
        compiler_flags = config.compiler_flags.copy()
        
        # Add C/C++ standard
        if any(f.endswith(('.cpp', '.cc', '.cxx')) for f in source_files):
            compiler_flags.append(f"-std={config.cpp_standard}")
            compiler_flags.extend(config.cpp_flags)
        else:
            compiler_flags.append(f"-std={config.c_standard}")
        
        # Prepare linker flags
        linker_flags = config.linker_flags.copy()
        
        # Add libraries
        for lib in config.libraries:
            linker_flags.append(f"-l{lib}")
        
        # Add library paths
        for lib_path in config.library_paths:
            if not os.path.isabs(lib_path):
                lib_path = os.path.join(project_path, lib_path)
            linker_flags.append(f"-L{lib_path}")
        
        # Add preprocessor defines
        defines = config.defines.copy()
        for key, value in config.preprocessor_defs.items():
            defines.append(f"{key}={value}")
        
        # Build options
        options = {
            "build_dir": output_dir,
            "optimization": f"-{config.optimization_level}",
            "debug_info": config.debug_symbols,
            "defines": defines,
            "include_paths": include_paths,
            "compiler_flags": compiler_flags,
            "linker_flags": linker_flags,
        }
        
        self.compile_output.emit(f"\nBuilding project: {config.project_name}")
        self.compile_output.emit(f"Configuration: {config.active_config}")
        self.compile_output.emit(f"Optimization: {config.optimization_level}")
        self.compile_output.emit(f"Output: {output_path}\n")
        
        return self.compile(source_files, output_path, options)
    
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
        """Get native compiler information"""
        try:
            result = subprocess.run(
                [self._compiler_path, '--version'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                first_line = result.stdout.split('\n')[0]
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', first_line)
                version = version_match.group(1) if version_match else "unknown"
                
                return ToolchainInfo(
                    name=f"Native {self._compiler_path.upper()}",
                    version=version,
                    path=self._compiler_path,
                    target=platform.machine()
                )
        except Exception:
            pass
        
        return None

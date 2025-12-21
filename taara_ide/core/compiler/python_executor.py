"""
Python script executor
Executes Python files with proper output capture and error handling
"""
import os
import sys
import subprocess
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal as Signal

from taara_ide.core.base import CompilerBase, BuildStatus, ToolchainInfo, CompileError


class PythonExecutorWorker(QThread):
    """Worker thread for Python script execution"""
    
    progress = Signal(str, int)
    output = Signal(str)
    finished_signal = Signal(bool, list)
    
    def __init__(
        self,
        python_path: str,
        script_file: str,
        working_dir: str,
        args: List[str]
    ):
        super().__init__()
        self.python_path = python_path
        self.script_file = script_file
        self.working_dir = working_dir
        self.args = args
        self._cancelled = False
        self._process: Optional[subprocess.Popen] = None
    
    def cancel(self):
        self._cancelled = True
        if self._process:
            self._process.terminate()
    
    def run(self):
        try:
            self.progress.emit(f"Executing {os.path.basename(self.script_file)}...", 10)
            
            cmd = [self.python_path, self.script_file] + self.args
            
            self.output.emit(f"Command: {' '.join(cmd)}\n")
            self.output.emit(f"Working directory: {self.working_dir}\n")
            self.output.emit("-" * 60 + "\n")
            
            self.progress.emit("Running...", 50)
            
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.working_dir,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output line by line
            for line in self._process.stdout:
                if self._cancelled:
                    self._process.terminate()
                    self.finished_signal.emit(False, [])
                    return
                self.output.emit(line)
            
            self._process.wait()
            
            self.output.emit("\n" + "-" * 60 + "\n")
            
            if self._process.returncode == 0:
                self.output.emit(f"Process finished with exit code 0\n")
                self.progress.emit("Execution successful", 100)
                self.finished_signal.emit(True, [])
            else:
                self.output.emit(f"Process finished with exit code {self._process.returncode}\n")
                self.progress.emit("Execution failed", 100)
                errors = [CompileError(
                    file=self.script_file,
                    line=0,
                    column=0,
                    message=f"Python script exited with code {self._process.returncode}",
                    is_error=True
                )]
                self.finished_signal.emit(False, errors)
                
        except Exception as e:
            error = CompileError(
                file=self.script_file,
                line=0,
                column=0,
                message=str(e),
                is_error=True
            )
            self.output.emit(f"Error: {str(e)}\n")
            self.finished_signal.emit(False, [error])


class PythonExecutor(CompilerBase):
    """Python script executor (acts as a compiler for consistency)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[PythonExecutorWorker] = None
        self._python_path = self._detect_python()
    
    def _detect_python(self) -> str:
        """Detect Python interpreter"""
        # Try current Python first
        current_python = sys.executable
        if current_python and os.path.exists(current_python):
            return current_python
        
        # Try common names
        for name in ['python', 'python3', 'python.exe', 'python3.exe']:
            try:
                result = subprocess.run(
                    [name, '--version'],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return name
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return 'python'
    
    def compile(
        self,
        source_files: List[str],
        output_path: str,
        options: Dict[str, Any]
    ) -> bool:
        """Execute Python script (compile interface for consistency)"""
        if self._status == BuildStatus.COMPILING:
            return False
        
        if not source_files:
            return False
        
        script_file = source_files[0]
        
        if not os.path.exists(script_file):
            self.compile_output.emit(f"Error: File not found: {script_file}\n")
            return False
        
        self._status = BuildStatus.COMPILING
        self._cancelled = False
        self.compile_started.emit()
        
        working_dir = os.path.dirname(script_file) or os.getcwd()
        args = options.get("args", [])
        
        self._worker = PythonExecutorWorker(
            self._python_path,
            script_file,
            working_dir,
            args
        )
        
        self._worker.progress.connect(self.compile_progress.emit)
        self._worker.output.connect(self.compile_output.emit)
        self._worker.finished_signal.connect(self._on_execution_finished)
        
        self._worker.start()
        return True
    
    def _on_execution_finished(self, success: bool, errors: list):
        self._status = BuildStatus.SUCCESS if success else BuildStatus.FAILED
        self.compile_finished.emit(success, errors)
        self._worker = None
    
    def cancel(self):
        super().cancel()
        if self._worker:
            self._worker.cancel()
    
    def clean(self, build_dir: str) -> bool:
        """Clean __pycache__ directories"""
        import shutil
        try:
            for root, dirs, files in os.walk(build_dir):
                if '__pycache__' in dirs:
                    pycache_path = os.path.join(root, '__pycache__')
                    shutil.rmtree(pycache_path)
            return True
        except OSError:
            return False
    
    def get_toolchain_info(self) -> Optional[ToolchainInfo]:
        """Get Python interpreter information"""
        try:
            result = subprocess.run(
                [self._python_path, '--version'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                version_line = result.stdout or result.stderr
                import re
                version_match = re.search(r'Python (\d+\.\d+\.\d+)', version_line)
                version = version_match.group(1) if version_match else "unknown"
                
                return ToolchainInfo(
                    name="Python",
                    version=version,
                    path=self._python_path,
                    target="interpreted",
                    supported_languages=["python"]
                )
        except Exception:
            pass
        
        return None

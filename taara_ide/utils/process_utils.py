"""
Process and subprocess utilities
"""
import subprocess
import os
import signal
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from taara_ide.utils.resource import Result


@dataclass
class ProcessResult:
    """Result of a subprocess execution"""
    return_code: int
    stdout: str
    stderr: str
    
    @property
    def success(self) -> bool:
        return self.return_code == 0


class ProcessUtils:
    """Utility class for subprocess operations"""
    
    @staticmethod
    def run_command(
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        shell: bool = False
    ) -> Result:
        """
        Run a command and capture output.
        
        Args:
            command: Command and arguments as list
            cwd: Working directory
            env: Environment variables (merged with current env)
            timeout: Timeout in seconds
            shell: Whether to run through shell
        """
        try:
            # Merge environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
            
            process = subprocess.run(
                command,
                cwd=cwd,
                env=run_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell
            )
            
            result = ProcessResult(
                return_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr
            )
            
            if result.success:
                return Result.ok(result)
            else:
                return Result.fail(result.stderr or f"Command failed with code {result.return_code}")
                
        except subprocess.TimeoutExpired:
            return Result.fail("Command timed out")
        except FileNotFoundError:
            return Result.fail(f"Command not found: {command[0]}")
        except Exception as e:
            return Result.fail(str(e))
    
    @staticmethod
    def run_command_async(
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
        shell: bool = False
    ) -> subprocess.Popen:
        """
        Start a command asynchronously.
        
        Returns Popen object for process control.
        """
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            shell=shell
        )
    
    @staticmethod
    def kill_process_tree(pid: int) -> None:
        """Kill a process and all its children"""
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], 
                             capture_output=True)
            else:  # Unix
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass  # Process already terminated

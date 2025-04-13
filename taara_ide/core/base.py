"""
Abstract base classes for core components.
These define the interfaces that concrete implementations must follow.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal as Signal


class BuildStatus(Enum):
    """Build process status"""
    IDLE = "idle"
    COMPILING = "compiling"
    LINKING = "linking"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DebugStatus(Enum):
    """Debugger status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ToolchainInfo:
    """Information about a toolchain"""
    name: str
    version: str
    path: str
    target: str  # e.g., "arm-none-eabi"
    supported_languages: List[str] = field(default_factory=lambda: ["c", "cpp", "asm"])


@dataclass
class CompileError:
    """Represents a compilation error or warning"""
    file: str
    line: int
    column: int
    message: str
    is_error: bool = True  # False for warnings
    
    def __str__(self) -> str:
        severity = "error" if self.is_error else "warning"
        return f"{self.file}:{self.line}:{self.column}: {severity}: {self.message}"


@dataclass 
class BreakpointInfo:
    """Breakpoint information"""
    id: int
    file: str
    line: int
    enabled: bool = True
    condition: Optional[str] = None
    hit_count: int = 0


@dataclass 
class VariableInfo:
    """Variable information from debugger"""
    name: str
    value: str
    type: str
    children: List['VariableInfo'] = field(default_factory=list)


class CompilerBase(QObject):
    """
    Abstract base class for compilers.
    
    Signals:
        compile_started: Emitted when compilation starts
        compile_progress: Emitted with progress updates (message, percentage)
        compile_finished: Emitted when compilation finishes (success, errors)
        compile_output: Emitted for build output lines
    """
    
    compile_started = Signal()
    compile_progress = Signal(str, int)  # message, percentage
    compile_finished = Signal(bool, list)  # success, errors
    compile_output = Signal(str)  # output line
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._status = BuildStatus.IDLE
        self._cancelled = False
    
    @property
    def status(self) -> BuildStatus:
        return self._status
    
    @abstractmethod
    def compile(
        self,
        source_files: List[str],
        output_path: str,
        options: Dict[str, Any]
    ) -> bool:
        """
        Compile source files.
        
        Args:
            source_files: List of source file paths
            output_path: Path for output binary
            options: Compiler options (flags, defines, includes, etc.)
            
        Returns:
            True if compilation succeeded
        """
        pass
    
    @abstractmethod
    def clean(self, build_dir: str) -> bool:
        """Clean build artifacts"""
        pass
    
    @abstractmethod
    def get_toolchain_info(self) -> Optional[ToolchainInfo]:
        """Get information about the toolchain"""
        pass
    
    def cancel(self) -> None:
        """Request compilation cancellation"""
        self._cancelled = True
        self._status = BuildStatus.CANCELLED


class DebuggerBase(QObject):
    """
    Abstract base class for debuggers.
    
    Signals:
        connected: Emitted when connected to target
        disconnected: Emitted when disconnected
        stopped: Emitted when execution stops (reason, file, line)
        running: Emitted when execution continues
        breakpoint_hit: Emitted when breakpoint is hit
        output: Emitted for debugger output
        error: Emitted on error
    """
    
    connected = Signal()
    disconnected = Signal()
    stopped = Signal(str, str, int)  # reason, file, line
    running = Signal()
    breakpoint_hit = Signal(object)  # BreakpointInfo
    output = Signal(str)
    error = Signal(str)
    variables_updated = Signal(list)  # List[VariableInfo]
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._status = DebugStatus.DISCONNECTED
        self._breakpoints: Dict[int, BreakpointInfo] = {}
    
    @property
    def status(self) -> DebugStatus:
        return self._status
    
    @property
    def is_connected(self) -> bool:
        return self._status not in (DebugStatus.DISCONNECTED, DebugStatus.ERROR)
    
    @abstractmethod
    def connect(self, executable: str, **kwargs) -> bool:
        """Connect to debug target"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from target"""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Start/continue execution"""
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """Pause execution"""
        pass
    
    @abstractmethod
    def step_over(self) -> None:
        """Step over (next line)"""
        pass
    
    @abstractmethod
    def step_into(self) -> None:
        """Step into function"""
        pass
    
    @abstractmethod
    def step_out(self) -> None:
        """Step out of function"""
        pass
    
    @abstractmethod
    def add_breakpoint(self, file: str, line: int, condition: Optional[str] = None) -> Optional[BreakpointInfo]:
        """Add a breakpoint"""
        pass
    
    @abstractmethod
    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """Remove a breakpoint"""
        pass
    
    @abstractmethod
    def get_variables(self, scope: str = "local") -> List[VariableInfo]:
        """Get variables in scope"""
        pass
    
    @abstractmethod
    def evaluate(self, expression: str) -> Optional[str]:
        """Evaluate an expression"""
        pass


class IndexerBase(QObject):
    """
    Abstract base class for code indexers (ctags, LSP, etc.)
    
    Signals:
        indexing_started: Emitted when indexing starts
        indexing_finished: Emitted when indexing finishes
        symbols_updated: Emitted when symbols are updated
    """
    
    indexing_started = Signal()
    indexing_finished = Signal(bool)  # success
    symbols_updated = Signal(str, list)  # file, symbols
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
    
    @abstractmethod
    def index_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Index a single file and return symbols"""
        pass
    
    @abstractmethod
    def index_project(self, project_path: str) -> bool:
        """Index entire project"""
        pass
    
    @abstractmethod
    def find_definition(self, symbol: str, context_file: str) -> Optional[tuple]:
        """Find symbol definition, returns (file, line) or None"""
        pass
    
    @abstractmethod
    def find_references(self, symbol: str, project_path: str) -> List[tuple]:
        """Find all references to symbol, returns list of (file, line)"""
        pass

"""
Resource path utilities and common result types
"""
import sys
import os
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum

from pathlib import Path
import sys

def _get_project_root() -> Path:
    """
    Resolve real project root directory in all modes:
    - Dev mode (python run.py)
    - Nuitka standalone
    - Launcher + dependencies
    - PyInstaller (_MEIPASS)
    """
    # 1. PyInstaller mode
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()

    exe_path = Path(sys.argv[0]).resolve()
    base_dir = exe_path.parent

    # 2. If running from dependencies/
    if base_dir.name == "dependencies":
        return base_dir.parent

    # 3. If launcher exe in ROOT (current shape)
    if (base_dir / "dependencies").exists():
        return base_dir

    # 4. Dev mode fallback (based on package structure)
    return Path(__file__).resolve().parents[1]

def resource_path(relative_path: str) -> str:
    """
    Create absolute resource path relative to project ROOT.
    Example:
        resource_path("icons/logo.ico")
        resource_path("themes/dark.json")
    """
    root = _get_project_root()
    return str(root / "taara_ide" / relative_path)

class ResultStatus(Enum):
    """Status codes for operation results"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    CANCELLED = "cancelled"

@dataclass
class Result:
    """
    Generic result wrapper for operations that can fail.
    Attributes:
        success: Whether the operation succeeded
        data: The result data if successful
        error: Error message if failed
        status: Detailed status code
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status: ResultStatus = ResultStatus.SUCCESS
    
    @classmethod
    def ok(cls, data: Any = None) -> 'Result':
        """Create a successful result"""
        return cls(success=True, data=data, status=ResultStatus.SUCCESS)
    
    @classmethod
    def fail(cls, error: str) -> 'Result':
        """Create a failed result"""
        return cls(success=False, error=error, status=ResultStatus.ERROR)
    
    @classmethod
    def cancelled(cls) -> 'Result':
        """Create a cancelled result"""
        return cls(success=False, status=ResultStatus.CANCELLED)
    
    def __bool__(self) -> bool:
        return self.success

"""
Resource path utilities and common result types
"""
import sys
import os
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    return os.path.join(base_path, relative_path)


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

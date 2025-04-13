"""
UI Panels module - Contains dock panels for the IDE.
"""

from .project_view import ProjectView
from .function_list import FunctionList
from .terminal import Terminal, TerminalWorker
from .debugger_panel import DebuggerPanel

__all__ = [
    'ProjectView',
    'FunctionList', 
    'Terminal',
    'TerminalWorker',
    'DebuggerPanel',
]

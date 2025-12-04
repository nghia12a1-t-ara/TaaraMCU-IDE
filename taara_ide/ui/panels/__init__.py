"""
UI Panels module - Contains dock panels for the IDE.
"""

from .project_view import ProjectView
from .function_list import FunctionList
from .terminal import Terminal, TerminalWorker
from .debugger_panel import DebuggerPanel
from .search_panel import SearchPanel
from .git_panel import GitPanel
from .extensions_panel import ExtensionsPanel
from .debug_sidebar import DebugSidebarPanel

__all__ = [
    'ProjectView',
    'FunctionList', 
    'Terminal',
    'TerminalWorker',
    'DebuggerPanel',
    'SearchPanel',
    'GitPanel',
    'ExtensionsPanel',
    'DebugSidebarPanel',
]

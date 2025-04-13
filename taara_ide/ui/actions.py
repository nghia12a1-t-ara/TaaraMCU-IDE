"""
Centralized action definitions for the application.
This module defines all QActions used in menus and toolbars.
"""
from typing import Optional, Dict, Callable
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from taara_ide.utils import resource_path


class ActionDefinition:
    """Definition for a single action"""
    def __init__(
        self,
        id: str,
        text: str,
        shortcut: Optional[str] = None,
        icon: Optional[str] = None,
        checkable: bool = False,
        tooltip: Optional[str] = None
    ):
        self.id = id
        self.text = text
        self.shortcut = shortcut
        self.icon = icon
        self.checkable = checkable
        self.tooltip = tooltip or text


# Define all application actions
ACTION_DEFINITIONS = {
    # File actions
    "file.new": ActionDefinition("file.new", "New File", "Ctrl+N", "icons/new.svg"),
    "file.new_project": ActionDefinition("file.new_project", "New STM32 Project", None, "icons/open_proj.svg"),
    "file.open": ActionDefinition("file.open", "Open...", "Ctrl+O", "icons/open.svg"),
    "file.open_project": ActionDefinition("file.open_project", "Open Project...", None, "icons/open_proj.svg"),
    "file.save": ActionDefinition("file.save", "Save", "Ctrl+S", "icons/save.svg"),
    "file.save_as": ActionDefinition("file.save_as", "Save As...", "Ctrl+Shift+S"),
    "file.close_tab": ActionDefinition("file.close_tab", "Close Tab", "Ctrl+F4"),
    "file.reopen": ActionDefinition("file.reopen", "Reopen Last Closed", "Ctrl+H"),
    "file.exit": ActionDefinition("file.exit", "Exit", "Alt+F4"),
    
    # Edit actions
    "edit.undo": ActionDefinition("edit.undo", "Undo", "Ctrl+Z"),
    "edit.redo": ActionDefinition("edit.redo", "Redo", "Ctrl+Y"),
    "edit.cut": ActionDefinition("edit.cut", "Cut", "Ctrl+X"),
    "edit.copy": ActionDefinition("edit.copy", "Copy", "Ctrl+C"),
    "edit.paste": ActionDefinition("edit.paste", "Paste", "Ctrl+V"),
    "edit.select_all": ActionDefinition("edit.select_all", "Select All", "Ctrl+A"),
    "edit.find": ActionDefinition("edit.find", "Find...", "Ctrl+F"),
    "edit.replace": ActionDefinition("edit.replace", "Replace...", "Ctrl+R"),
    "edit.goto_line": ActionDefinition("edit.goto_line", "Go To Line...", "Ctrl+G"),
    "edit.comment": ActionDefinition("edit.comment", "Comment/Uncomment", "Ctrl+Q"),
    
    # View actions
    "view.word_wrap": ActionDefinition("view.word_wrap", "Word Wrap", "Ctrl+W", "icons/word-wrap.svg", checkable=True),
    "view.show_all_chars": ActionDefinition("view.show_all_chars", "Show All Characters", "Ctrl+J", "icons/show_all_char.svg", checkable=True),
    "view.project_panel": ActionDefinition("view.project_panel", "Project Panel", checkable=True),
    "view.function_list": ActionDefinition("view.function_list", "Function List", checkable=True),
    "view.terminal": ActionDefinition("view.terminal", "Terminal", checkable=True),
    "view.debugger": ActionDefinition("view.debugger", "Debugger", checkable=True),
    
    # Build actions
    "build.clean": ActionDefinition("build.clean", "Clean", "F8"),
    "build.compile": ActionDefinition("build.compile", "Compile", "F9"),
    "build.compile_run": ActionDefinition("build.compile_run", "Compile && Run", "F10"),
    "build.flash": ActionDefinition("build.flash", "Flash Programming", "F12"),
    
    # Debug actions
    "debug.start": ActionDefinition("debug.start", "Start Debugging", "F5"),
    "debug.stop": ActionDefinition("debug.stop", "Stop Debugging", "Shift+F5"),
    "debug.step_over": ActionDefinition("debug.step_over", "Step Over", "F10"),
    "debug.step_into": ActionDefinition("debug.step_into", "Step Into", "F11"),
    "debug.step_out": ActionDefinition("debug.step_out", "Step Out", "Shift+F11"),
    "debug.toggle_breakpoint": ActionDefinition("debug.toggle_breakpoint", "Toggle Breakpoint", "F9"),
    
    # Settings actions
    "settings.ctags_path": ActionDefinition("settings.ctags_path", "CTags Path Settings"),
    "settings.stm32_framework": ActionDefinition("settings.stm32_framework", "STM32 Framework Path"),
    "settings.project_config": ActionDefinition("settings.project_config", "Project Configuration"),
    
    # Language actions
    "lang.c": ActionDefinition("lang.c", "C"),
    "lang.cpp": ActionDefinition("lang.cpp", "C++"),
    "lang.python": ActionDefinition("lang.python", "Python"),
    
    # Help actions
    "help.about": ActionDefinition("help.about", "About"),
    "help.install_framework": ActionDefinition("help.install_framework", "STM32 Framework Installation"),
}


class ActionManager:
    """
    Manages all application actions.
    Creates, stores, and provides access to QAction instances.
    """
    
    def __init__(self, parent: QWidget):
        self._parent = parent
        self._actions: Dict[str, QAction] = {}
        self._create_actions()
    
    def _create_actions(self) -> None:
        """Create all actions from definitions"""
        for action_id, definition in ACTION_DEFINITIONS.items():
            action = QAction(definition.text, self._parent)
            
            if definition.shortcut:
                action.setShortcut(QKeySequence(definition.shortcut))
            
            if definition.icon:
                try:
                    icon_path = resource_path(definition.icon)
                    action.setIcon(QIcon(icon_path))
                except Exception:
                    pass
            
            if definition.checkable:
                action.setCheckable(True)
            
            if definition.tooltip:
                action.setToolTip(definition.tooltip)
            
            action.setObjectName(action_id)
            self._actions[action_id] = action
    
    def get(self, action_id: str) -> Optional[QAction]:
        """Get an action by its ID"""
        return self._actions.get(action_id)
    
    def __getitem__(self, action_id: str) -> QAction:
        """Get an action by its ID using [] syntax"""
        action = self._actions.get(action_id)
        if action is None:
            raise KeyError(f"Action '{action_id}' not found")
        return action
    
    def connect(self, action_id: str, handler: Callable) -> None:
        """Connect an action's triggered signal to a handler"""
        action = self.get(action_id)
        if action:
            action.triggered.connect(handler)
    
    def connect_many(self, connections: Dict[str, Callable]) -> None:
        """Connect multiple actions to handlers"""
        for action_id, handler in connections.items():
            self.connect(action_id, handler)
    
    def set_enabled(self, action_id: str, enabled: bool) -> None:
        """Enable or disable an action"""
        action = self.get(action_id)
        if action:
            action.setEnabled(enabled)
    
    def set_checked(self, action_id: str, checked: bool) -> None:
        """Set checked state of a checkable action"""
        action = self.get(action_id)
        if action and action.isCheckable():
            action.setChecked(checked)
    
    def all_actions(self) -> Dict[str, QAction]:
        """Get all actions"""
        return self._actions.copy()

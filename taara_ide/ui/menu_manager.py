"""
Menu and toolbar management for MainWindow.
Separates menu/toolbar creation from MainWindow logic.
"""
from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QMenuBar, QToolBar, QMenu

if TYPE_CHECKING:
    from .main_window import MainWindow
    from .actions import ActionManager


class MenuManager:
    """
    Manages menu bar and toolbar creation.
    Keeps MainWindow clean by handling all menu-related logic here.
    """
    
    def __init__(self, main_window: 'MainWindow', actions: 'ActionManager'):
        self._window = main_window
        self._actions = actions
        self._menubar: QMenuBar = None
        self._toolbar: QToolBar = None
    
    def setup_menus(self) -> None:
        """Create and populate menu bar"""
        self._menubar = self._window.menuBar()
        
        self._create_file_menu()
        self._create_edit_menu()
        self._create_view_menu()
        self._create_build_menu()
        self._create_debug_menu()
        self._create_settings_menu()
        self._create_help_menu()
    
    def setup_toolbar(self) -> None:
        """Create and populate main toolbar"""
        self._toolbar = QToolBar("Main Toolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setObjectName("MainToolbar")
        self._window.addToolBar(self._toolbar)
        
        # File actions
        self._toolbar.addAction(self._actions["file.new"])
        self._toolbar.addAction(self._actions["file.open"])
        self._toolbar.addAction(self._actions["file.save"])
        self._toolbar.addSeparator()
        
        # Build actions
        self._toolbar.addAction(self._actions["build.compile"])
        self._toolbar.addAction(self._actions["build.flash"])
        self._toolbar.addSeparator()
        
        # Debug actions
        self._toolbar.addAction(self._actions["debug.start"])
        self._toolbar.addAction(self._actions["debug.stop"])
        self._toolbar.addSeparator()
        
        # View toggles
        self._toolbar.addAction(self._actions["view.word_wrap"])
        self._toolbar.addAction(self._actions["view.show_all_chars"])
    
    def _create_file_menu(self) -> None:
        """Create File menu"""
        menu = self._menubar.addMenu("&File")
        
        # New submenu
        new_menu = QMenu("New", self._window)
        new_menu.addAction(self._actions["file.new"])
        new_menu.addAction(self._actions["file.new_project"])
        menu.addMenu(new_menu)
        
        menu.addAction(self._actions["file.open"])
        menu.addAction(self._actions["file.open_project"])
        menu.addAction(self._actions["file.save"])
        menu.addAction(self._actions["file.save_as"])
        menu.addSeparator()
        
        menu.addAction(self._actions["file.close_tab"])
        menu.addAction(self._actions["file.reopen"])
        menu.addSeparator()
        
        menu.addAction(self._actions["file.exit"])
    
    def _create_edit_menu(self) -> None:
        """Create Edit menu"""
        menu = self._menubar.addMenu("&Edit")
        
        menu.addAction(self._actions["edit.undo"])
        menu.addAction(self._actions["edit.redo"])
        menu.addSeparator()
        
        menu.addAction(self._actions["edit.cut"])
        menu.addAction(self._actions["edit.copy"])
        menu.addAction(self._actions["edit.paste"])
        menu.addSeparator()
        
        menu.addAction(self._actions["edit.find"])
        menu.addAction(self._actions["edit.replace"])
        menu.addAction(self._actions["edit.goto_line"])
        menu.addSeparator()
        
        menu.addAction(self._actions["edit.select_all"])
        menu.addAction(self._actions["edit.comment"])
    
    def _create_view_menu(self) -> None:
        """Create View menu"""
        menu = self._menubar.addMenu("&View")
        
        # Panels submenu
        panels_menu = QMenu("Panels", self._window)
        panels_menu.addAction(self._actions["view.project_panel"])
        panels_menu.addAction(self._actions["view.function_list"])
        panels_menu.addAction(self._actions["view.terminal"])
        panels_menu.addAction(self._actions["view.debugger"])
        menu.addMenu(panels_menu)
        
        menu.addSeparator()
        menu.addAction(self._actions["view.word_wrap"])
        menu.addAction(self._actions["view.show_all_chars"])
    
    def _create_build_menu(self) -> None:
        """Create Build menu"""
        menu = self._menubar.addMenu("&Build")
        
        menu.addAction(self._actions["build.clean"])
        menu.addAction(self._actions["build.compile"])
        menu.addAction(self._actions["build.compile_run"])
        menu.addSeparator()
        menu.addAction(self._actions["build.flash"])
    
    def _create_debug_menu(self) -> None:
        """Create Debug menu"""
        menu = self._menubar.addMenu("&Debug")
        
        menu.addAction(self._actions["debug.start"])
        menu.addAction(self._actions["debug.stop"])
        menu.addSeparator()
        menu.addAction(self._actions["debug.step_over"])
        menu.addAction(self._actions["debug.step_into"])
        menu.addAction(self._actions["debug.step_out"])
        menu.addSeparator()
        menu.addAction(self._actions["debug.toggle_breakpoint"])
    
    def _create_settings_menu(self) -> None:
        """Create Settings menu"""
        menu = self._menubar.addMenu("&Settings")
        
        menu.addAction(self._actions["settings.project_config"])
        menu.addSeparator()
        
        # Tools submenu
        tools_menu = QMenu("Tool Paths", self._window)
        tools_menu.addAction(self._actions["settings.ctags_path"])
        tools_menu.addAction(self._actions["settings.stm32_framework"])
        menu.addMenu(tools_menu)
        
        # Language submenu
        lang_menu = QMenu("Set Language", self._window)
        lang_menu.addAction(self._actions["lang.c"])
        lang_menu.addAction(self._actions["lang.cpp"])
        lang_menu.addAction(self._actions["lang.python"])
        menu.addMenu(lang_menu)
    
    def _create_help_menu(self) -> None:
        """Create Help menu"""
        menu = self._menubar.addMenu("&Help")
        
        menu.addAction(self._actions["help.about"])
        menu.addSeparator()
        menu.addAction(self._actions["help.install_framework"])

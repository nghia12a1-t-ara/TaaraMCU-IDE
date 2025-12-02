"""
Main application window - refactored version
"""
import os
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QDockWidget,
    QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QCloseEvent, QIcon

from taara_ide.ui.actions import ActionManager
from taara_ide.ui.menu_manager import MenuManager
from taara_ide.ui.status_bar import StatusBarManager
from taara_ide.ui.dialogs import (
    FindDialog, GoToLineDialog, ProjectConfigDialog,
    CtagsPathDialog, CreateProjectDialog, InstallFrameworkDialog
)
from taara_ide.ui.editor.editor_manager import EditorManager

from taara_ide.config import SettingsManager, AppConstants
from taara_ide.services import ProjectService, BuildService, DebugService
from taara_ide.utils import resource_path


class MainWindow(QMainWindow):
    """
    Main application window for Taara IDE.
    
    This is a refactored version that delegates responsibilities to:
    - ActionManager: Handles all QActions
    - MenuManager: Creates menus and toolbars
    - StatusBarManager: Manages status bar
    - EditorManager: Manages editor tabs
    - Services: Handle business logic
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize services
        self._settings = SettingsManager()
        self._project_service = ProjectService(self)
        self._build_service = BuildService(self._project_service, self)
        self._debug_service = DebugService(self._project_service, self)
        
        # Initialize UI managers
        self._actions = ActionManager(self)
        self._menu_manager = MenuManager(self, self._actions)
        
        # UI components (will be set up later)
        self._project_view = None
        self._function_list = None
        self._terminal = None
        self._debugger_panel = None
        
        self._setup_window()
        self._setup_ui()
        
        self._editor_manager = EditorManager(self, self._tab_widget)
        self._connect_editor_manager()
        
        self._connect_actions()
        self._connect_services()
        self._restore_state()
        
        self._editor_manager.new_editor()
    
    def _setup_window(self) -> None:
        """Configure main window properties"""
        self.setWindowTitle(f"{AppConstants.APP_NAME} - {AppConstants.VERSION}")
        self.setMinimumSize(1024, 768)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon(resource_path("icons/app_icon.png")))
        except Exception:
            pass
    
    def _setup_ui(self) -> None:
        """Set up the main UI layout"""
        # Create menus and toolbar
        self._menu_manager.setup_menus()
        self._menu_manager.setup_toolbar()
        
        # Create status bar
        self._status_manager = StatusBarManager(self.statusBar())
        
        # Create central splitter
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self._main_splitter)
        
        # Left panel (project view + function list)
        self._left_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.addWidget(self._left_splitter)
        
        # Center (editor area)
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._main_splitter.addWidget(self._tab_widget)
        self._tab_widget.tabBar().setStyleSheet("""
            QTabBar::tab {
                background: #d8dded;
                padding: 7px 16px;
                border: 1px solid #111;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #e9edd8;
                font-weight: bold;
                border: 1px solid #0259bf;
            }
            QTabBar::tab:hover {
                background: #cfd6b2;
            }
            QTabBar::tab:!selected {
                margin-top: 3px;
            }
            QTabBar::tab:selected:!active {
                background: #2a2a2a;
            }
        """)

        # Set splitter sizes
        self._main_splitter.setSizes([250, 750])
        
        # Create dock widgets
        self._setup_dock_widgets()
    
    def _setup_dock_widgets(self) -> None:
        """Set up dock widgets for panels"""
        # Terminal dock
        self._terminal_dock = QDockWidget("Terminal", self)
        self._terminal_dock.setObjectName("TerminalDock")
        self._terminal_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._terminal_dock)
        
        # Debugger dock
        self._debugger_dock = QDockWidget("Debugger", self)
        self._debugger_dock.setObjectName("DebuggerDock")
        self._debugger_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._debugger_dock)
        self._debugger_dock.hide()
    
    def _toggle_dock(self, dock: QDockWidget) -> None:
        """Toggle dock widget visibility"""
        dock.setVisible(not dock.isVisible())
    
    def _connect_editor_manager(self) -> None:
        """Connect EditorManager signals"""
        self._editor_manager.current_editor_changed.connect(self._on_editor_changed)
        self._editor_manager.file_saved.connect(
            lambda path: self._status_manager.set_message(f"Saved: {path}", 3000)
        )
        self._editor_manager.file_opened.connect(self._on_file_opened)
        self._editor_manager.content_modified.connect(self.update_status_bar)
        
        # Connect CTags handler signals
        self._editor_manager.ctags_handler.ctags_path_required.connect(
            self._show_ctags_dialog
        )
        self._editor_manager.ctags_handler.symbols_updated.connect(
            self._on_symbols_updated
        )
    
    def _on_editor_changed(self, editor) -> None:
        """Handle editor tab change"""
        self.update_status_bar()
        print("_on_editor_changed")
        
        # Update function list if available
        if self._function_list and editor:
            file_path = self._editor_manager.get_current_filepath()
            if file_path:
                self._editor_manager.ctags_handler.index_file_async(file_path)
    
    def _on_file_opened(self, file_path: str) -> None:
        """Handle file opened"""
        self._status_manager.set_message(f"Opened: {file_path}", 3000)
    
    def _on_symbols_updated(self, file_path: str, symbols: list) -> None:
        """Handle symbols updated from CTags"""
        if self._function_list:
            # Update function list with new symbols
            self._function_list.update_symbols(symbols)
    
    def _connect_actions(self) -> None:
        """Connect actions to handlers"""
        # File actions - Use EditorManager methods
        self._actions.connect_many({
            "file.new": self._editor_manager.new_editor,
            "file.new_project": self._new_project,
            "file.open": self._editor_manager.open_editor,
            "file.open_project": self._open_project,
            "file.save": self._editor_manager.save_editor,
            "file.save_as": self._editor_manager.save_editor_as,
            "file.close_tab": lambda: self._editor_manager.close_editor(
                self._tab_widget.currentIndex()
            ),
            "file.reopen": self._editor_manager.reopen_last_closed,
            "file.exit": self.close,
        })
        
        # Edit actions - Use EditorManager methods
        self._actions.connect_many({
            "edit.undo": self._editor_manager.undo,
            "edit.redo": self._editor_manager.redo,
            "edit.cut": self._editor_manager.cut,
            "edit.copy": self._editor_manager.copy,
            "edit.paste": self._editor_manager.paste,
            "edit.select_all": self._editor_manager.select_all,
            "edit.find": self._show_find_dialog,
            "edit.goto_line": self._show_goto_line_dialog,
            "edit.comment": self._editor_manager.comment_lines,
        })
        
        # View actions - Use EditorManager methods
        self._actions.connect_many({
            "view.word_wrap": self._editor_manager.toggle_word_wrap,
            "view.show_all_chars": self._editor_manager.toggle_whitespace,
            "view.terminal": lambda: self._toggle_dock(self._terminal_dock),
            "view.debugger": lambda: self._toggle_dock(self._debugger_dock),
        })
        
        # Build actions
        self._actions.connect_many({
            "build.clean": self._clean,
            "build.compile": self._compile,
            "build.compile_run": self._compile_and_run,
            "build.flash": self._flash,
        })
        
        # Debug actions
        self._actions.connect_many({
            "debug.start": self._start_debug,
            "debug.stop": self._stop_debug,
            "debug.step_over": self._debug_service.step_over,
            "debug.step_into": self._debug_service.step_into,
            "debug.step_out": self._debug_service.step_out,
        })
        
        # Settings actions
        self._actions.connect_many({
            "settings.ctags_path": self._show_ctags_dialog,
            "settings.project_config": self._show_project_config,
        })
        
        # Help actions
        self._actions.connect_many({
            "help.about": self._show_about,
            "help.install_framework": self._show_install_framework,
        })
    
    def _connect_services(self) -> None:
        """Connect service signals"""
        # Project service
        self._project_service.project_opened.connect(self._on_project_opened)
        self._project_service.project_closed.connect(self._on_project_closed)
        
        # Build service
        self._build_service.build_started.connect(
            lambda: self._status_manager.set_message("Building...")
        )
        self._build_service.build_progress.connect(
            lambda msg, pct: self._status_manager.set_message(f"Building: {msg}")
        )
        self._build_service.build_output.connect(self._on_build_output)
        self._build_service.build_finished.connect(self._on_build_finished)
        
        # Debug service
        self._debug_service.session_started.connect(self._on_debug_started)
        self._debug_service.session_ended.connect(self._on_debug_ended)
        self._debug_service.execution_paused.connect(self._on_debug_paused)
    
    # ========== File Operations ==========
    
    def _new_project(self) -> None:
        """Show create project dialog"""
        dialog = CreateProjectDialog(self._project_service, self)
        dialog.project_created.connect(self._on_project_opened)
        dialog.exec()
    
    def _open_project(self) -> None:
        """Open project dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Open Project"
        )
        if directory:
            result = self._project_service.open_project(directory)
            if not result.success:
                QMessageBox.warning(self, "Error", f"Failed to open project: {result.message}")
    
    # ========== Edit Operations ==========
    
    def _show_find_dialog(self) -> None:
        """Show find dialog"""
        dialog = FindDialog(self)
        dialog.find_requested.connect(self._do_find)
        dialog.replace_requested.connect(self._do_replace)
        dialog.replace_all_requested.connect(self._do_replace_all)
        dialog.show()
    
    def _do_find(self, text: str, options: dict) -> None:
        """Perform find operation"""
        found = self._editor_manager.find_text(
            text,
            case_sensitive=options.get('case_sensitive', False),
            whole_word=options.get('whole_word', False),
            forward=options.get('forward', True)
        )
        if not found:
            self._status_manager.set_message("Text not found", 2000)
    
    def _do_replace(self, find_text: str, replace_text: str, options: dict) -> None:
        """Perform replace operation"""
        self._editor_manager.replace_text(
            find_text, replace_text,
            case_sensitive=options.get('case_sensitive', False),
            whole_word=options.get('whole_word', False)
        )
    
    def _do_replace_all(self, find_text: str, replace_text: str, options: dict) -> None:
        """Perform replace all operation"""
        count = self._editor_manager.replace_all(
            find_text, replace_text,
            case_sensitive=options.get('case_sensitive', False),
            whole_word=options.get('whole_word', False)
        )
        self._status_manager.set_message(f"Replaced {count} occurrence(s)", 3000)
    
    def _show_goto_line_dialog(self) -> None:
        """Show go to line dialog"""
        max_line = self._editor_manager.get_current_line_count()
        line, col = self._editor_manager.get_current_cursor_position()
        
        dialog = GoToLineDialog(self, current_line=line + 1, max_line=max_line)
        dialog.line_selected.connect(self._editor_manager.goto_line)
        dialog.exec()
    
    # ========== Build Operations ==========
    
    def _clean(self) -> None:
        """Clean build"""
        self._build_service.clean()
    
    def _compile(self) -> None:
        """Compile project"""
        self._build_service.build()
    
    def _compile_and_run(self) -> None:
        """Compile and run/flash"""
        self._build_service.build()
        # TODO: Flash after build
    
    def _flash(self) -> None:
        """Flash to target"""
        # TODO: Implement flash
        pass
    
    def _on_build_output(self, output: str) -> None:
        """Handle build output"""
        if self._terminal:
            self._terminal.append_output(output)
    
    def _on_build_finished(self, result) -> None:
        """Handle build finished"""
        if result.success:
            self._status_manager.set_message("Build successful", 5000)
        else:
            self._status_manager.set_message(
                f"Build failed: {len(result.errors)} error(s)", 
                5000
            )
    
    # ========== Debug Operations ==========
    
    def _start_debug(self) -> None:
        """Start debug session"""
        self._debug_service.start_session()
    
    def _stop_debug(self) -> None:
        """Stop debug session"""
        self._debug_service.stop_session()
    
    def _on_debug_started(self) -> None:
        """Handle debug session started"""
        self._status_manager.set_message("Debug session started")
        self._debugger_dock.show()
    
    def _on_debug_ended(self) -> None:
        """Handle debug session ended"""
        self._status_manager.set_message("Debug session ended")
    
    def _on_debug_paused(self, file: str, line: int, reason: str) -> None:
        """Handle debug execution paused"""
        self._status_manager.set_message(f"Paused at {file}:{line} ({reason})")
        # TODO: Navigate to file:line in editor
    
    # ========== Project Events ==========
    
    def _on_project_opened(self, path: str) -> None:
        """Handle project opened"""
        self.setWindowTitle(
            f"{self._project_service.name} - {AppConstants.APP_NAME}"
        )
        self._status_manager.set_message(f"Opened project: {path}")
        
        # Update project view
        if self._project_view:
            self._project_view.set_project_path(path)
    
    def _on_project_closed(self) -> None:
        """Handle project closed"""
        self.setWindowTitle(f"{AppConstants.APP_NAME} - {AppConstants.VERSION}")
    
    # ========== Settings Dialogs ==========
    
    def _show_ctags_dialog(self) -> None:
        """Show CTags path dialog"""
        dialog = CtagsPathDialog(self)
        dialog.exec()
    
    def _show_project_config(self) -> None:
        """Show project configuration dialog"""
        if not self._project_service.is_open:
            QMessageBox.warning(self, "Error", "No project is open.")
            return
        
        dialog = ProjectConfigDialog(self._project_service, self)
        dialog.exec()
    
    def _show_install_framework(self) -> None:
        """Show framework installation dialog"""
        dialog = InstallFrameworkDialog(self)
        dialog.exec()
    
    def _show_about(self) -> None:
        """Show about dialog"""
        QMessageBox.about(
            self,
            f"About {AppConstants.APP_NAME}",
            f"{AppConstants.APP_NAME} v{AppConstants.VERSION}\n\n"
            "An IDE for embedded development with STM32 microcontrollers.\n\n"
            "Built with PyQt6 and Python."
        )
    
    # ========== State Management ==========
    
    def _restore_state(self) -> None:
        """Restore window state from settings"""
        geometry = self._settings.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self._settings.get_window_state()
        if state:
            self.restoreState(state)
        
        # Restore last project
        last_project = self._settings.get_last_project()
        if last_project and os.path.exists(last_project):
            self._project_service.open_project(last_project)
    
    def _save_state(self) -> None:
        """Save window state to settings"""
        self._settings.set_window_geometry(self.saveGeometry())
        self._settings.set_window_state(self.saveState())
        self._settings.sync()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close"""
        if self._editor_manager.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.SaveAll |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.SaveAll:
                if not self._editor_manager.save_all():
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        self._save_state()
        
        # Close project
        if self._project_service.is_open:
            self._project_service.close_project()
        
        event.accept()
    
    # ========== Public API ==========
    
    @property
    def editor_manager(self) -> EditorManager:
        """Get the editor manager"""
        return self._editor_manager
    
    @property
    def project_view(self):
        """Get the project view panel"""
        return self._project_view
    
    @property
    def tabWidget(self) -> QTabWidget:
        """Get the tab widget (compatibility property)"""
        return self._tab_widget
    
    def open_file(self, file_path: str):
        """Open a file (compatibility method)"""
        return self._editor_manager.open_editor(file_path)
    
    def update_status_bar(self) -> None:
        """Update status bar with current editor info"""
        editor = self._editor_manager.get_current_editor()
        if not editor:
            self._status_manager.set_cursor_position(0, 0)
            return
        
        line, col = self._editor_manager.get_current_cursor_position()
        self._status_manager.set_cursor_position(line, col)
        
        # Update file path
        file_path = self._editor_manager.get_current_filepath()
        if file_path:
            self._status_manager.set_message(file_path)

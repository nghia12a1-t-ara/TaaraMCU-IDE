"""
Main application window - refactored version
"""
import os

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QTabWidget
from PyQt6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut

from taara_ide.ui.actions import ActionManager
from taara_ide.ui.menu_manager import MenuManager
from taara_ide.ui.status_bar import StatusBarManager
from taara_ide.ui.layout_manager import LayoutManager
from taara_ide.ui.editor.editor_manager import EditorManager
from taara_ide.ui.controllers import BuildController

from taara_ide.config import SettingsManager, AppConstants
from taara_ide.services import ProjectService, BuildService, DebugService, LspService
from taara_ide.extensions import ExtensionManager
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
        self._settings_manager = SettingsManager()
        self._project_service = ProjectService(self)
        self._build_service = BuildService(self._project_service, self)
        self._debug_service = DebugService(self._project_service, self)
        self._lsp_service = LspService(self)
        self._extension_manager = ExtensionManager(self._settings_manager, self)
        
        # Initialize UI managers
        self._actions = ActionManager(self)
        self._menu_manager = MenuManager(self, self._actions)
        
        self._saved_sidebar_width = 250
        self._saved_right_panel_width = 200

        self._setup_window()

        # Menus / toolbar / status bar (must happen before layout)
        self._menu_manager.setup_menus()
        self._menu_manager.setup_toolbar()
        self._status_manager = StatusBarManager(self.statusBar())

        # Build the entire widget tree via LayoutManager
        self._layout = LayoutManager()
        self._layout.build(self, self._settings_manager, self._debug_service)

        # Assign widget references from layout
        self._activity_bar    = self._layout.activity_bar
        self._sidebar_stack   = self._layout.sidebar_stack
        self._project_view    = self._layout.project_view
        self._search_panel    = self._layout.search_panel
        self._git_panel       = self._layout.git_panel
        self._debug_sidebar   = self._layout.debug_sidebar
        self._extensions_panel = self._layout.extensions_panel
        self._main_splitter   = self._layout.main_splitter
        self._center_splitter = self._layout.center_splitter
        self._tab_widget      = self._layout.tab_widget
        self._breadcrumb_bar  = self._layout.breadcrumb_bar
        self._right_panel     = self._layout.right_panel
        self._function_list   = self._layout.function_list
        self._terminal        = self._layout.terminal
        self._terminal_dock   = self._layout.terminal_dock
        self._debugger_panel  = self._layout.debugger_panel
        self._debugger_dock   = self._layout.debugger_dock

        # Wire signals that need MainWindow handlers
        self._activity_bar.panel_changed.connect(self._on_activity_panel_changed)
        self._search_panel.file_requested.connect(self._on_search_file_requested)
        self._search_panel.search_term_changed.connect(self._on_search_term_changed)
        self._breadcrumb_bar.symbol_clicked.connect(self._on_breadcrumb_symbol_clicked)
        self._breadcrumb_bar.file_open_requested.connect(self._on_breadcrumb_file_requested)
        self._actions.set_checked("view.function_list",
                                  self._settings_manager.get_right_panel_width() != 0)

        self._editor_manager = EditorManager(self, self._tab_widget)
        self._connect_editor_manager()
        self._setup_shortcuts()

        # Flag to indicate if a run is pending after build completion
        self._pending_run_after_build = False
        self._build_controller = BuildController(
            self, 
            self._build_service,
            self._project_service,
            self._project_view,
            self._editor_manager,
            self._terminal
        )
        
        self._connect_actions()
        self._connect_services() # Changed from _connect_signals to _connect_services
        self._restore_state()

        # Connect build controller signals
        self._build_controller.build_output.connect(self._on_build_output)
        self._build_controller.build_finished.connect(self._on_build_finished)
        self._build_controller.status_message.connect(
            lambda msg, timeout: self._status_manager.set_message(msg, timeout)
        )

        # Wire extension panel and activate enabled extensions
        self._extensions_panel.set_extension_manager(self._extension_manager)
        self._extension_manager.panel_widget_ready.connect(self._on_extension_panel_ready)
        self._extension_manager.load_all(self)

        # Finish deferred heavy widgets (ProjectView) after window is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._finish_deferred)
    
    def _setup_window(self) -> None:
        """Configure main window properties"""
        self.setWindowTitle(f"{AppConstants.APP_NAME} - {AppConstants.VERSION}")
        self.setMinimumSize(1024, 768)
        self.setWindowIcon(QIcon(resource_path("icons/logoIcon.ico")))
    
    def _on_extension_panel_ready(self, ext_id: str, widget) -> None:
        """Add an extension's sidebar panel to the activity bar / sidebar stack."""
        panel_id = f"ext_{ext_id}"
        idx = self._sidebar_stack.addWidget(widget)
        self._activity_bar.add_button(panel_id, "extensions", ext_id.replace("-", " ").title())
        # Map the new panel_id to the new stack index via a direct connection
        self._activity_bar.panel_changed.connect(
            lambda pid, _idx=idx: (
                self._sidebar_stack.setCurrentIndex(_idx)
                if pid == panel_id else None
            )
        )

    def _on_activity_panel_changed(self, panel_id: str):
        """Handle activity bar panel change"""
        from taara_ide.ui.activity_bar import ActivityBar as _AB
        if not panel_id:
            self._sidebar_stack.hide()
            return
        self._sidebar_stack.show()
        panel_map = {
            _AB.PANEL_PROJECT: 0,
            _AB.PANEL_SEARCH: 1,
            _AB.PANEL_GIT: 2,
            _AB.PANEL_DEBUG: 3,
            _AB.PANEL_EXTENSIONS: 4,
        }
        self._sidebar_stack.setCurrentIndex(panel_map.get(panel_id, 0))

    def _on_search_file_requested(self, file_path: str, line_num: int):
        """Handle search result double click"""
        if hasattr(self, '_editor_manager'):
            self._editor_manager.open_file_at_line(file_path, line_num, 0)

    def _on_search_term_changed(self, term: str, case_sensitive: bool, whole_word: bool, use_regex: bool):
        """Highlight search matches in current editor"""
        editor = self._editor_manager.get_current_editor()
        if editor:
            editor.highlight_search_matches(term, case_sensitive, whole_word, use_regex)
        self._current_search_term = term
        self._current_search_case = case_sensitive
        self._current_search_word = whole_word
        self._current_search_regex = use_regex
    
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
        
        # project_view signals wired in _finish_deferred (it's built lazily)

        if self._function_list:
            self._function_list.symbol_selected.connect(self._editor_manager.open_file_at_line)
        
        self._editor_manager.cursor_position_changed.connect(self._on_cursor_position_changed)
    
    def _on_editor_changed(self, editor) -> None:
        """Handle editor tab change"""
        # print("_on_editor_changed")
        
        file_path = None
        if editor and hasattr(self, '_editor_manager'):
            editor_info = self._editor_manager.editors.get(editor)
            if editor_info:
                file_path = editor_info.get("file_path")
        
        # Update window title
        if file_path:
            self.setWindowTitle(f"{os.path.basename(file_path)} - {AppConstants.APP_NAME}")
            if hasattr(self, '_breadcrumb_bar') and self._breadcrumb_bar:
                self._breadcrumb_bar.set_file(file_path)
        else:
            self.setWindowTitle(AppConstants.APP_NAME)
            if hasattr(self, '_breadcrumb_bar') and self._breadcrumb_bar:
                self._breadcrumb_bar.set_file(None)
        
        # Update status bar
        self.update_status_bar()
        
        # Function list is updated via symbols_updated signal from ctags_handler
        # (already triggered by editor_manager on open/save — no duplicate call needed)
        
        if hasattr(self, '_current_search_term') and self._current_search_term:
            editor.highlight_search_matches(
                self._current_search_term,
                getattr(self, '_current_search_case', False),
                getattr(self, '_current_search_word', False),
                getattr(self, '_current_search_regex', False)
            )

        # Propagate "show all chars" state to newly created editors
        if getattr(self, '_show_all_chars', False):
            from PyQt6.Qsci import QsciScintilla
            editor.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsVisible)
            editor.setEolVisibility(True)
    
    def _on_file_opened(self, file_path: str) -> None:
        """Handle file opened"""
        self._status_manager.set_message(f"Opened: {file_path}", 3000)
    
    def _on_symbols_updated(self, file_path: str, symbols: list) -> None:
        """Handle symbols updated from CTags"""
        if self._function_list:
            # Update function list with new symbols
            self._function_list.update_symbols(symbols)
    
    def _connect_actions(self) -> None:
        """Connect actions to their handlers"""
        # File actions - Use EditorManager methods
        self._actions.connect_many({
            "file.new": self._editor_manager.new_editor,
            "file.new_project": self._new_project,
            "file.open": self._editor_manager.open_editor,
            "file.open_folder": self._open_folder,
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
        
        self._actions.connect_many({
            "view.word_wrap": self._toggle_word_wrap,
            "view.show_all_chars": self._toggle_whitespace,
            "view.project_panel": self._toggle_project_panel,
            "view.function_list": self._toggle_function_list,
            "view.terminal": self._toggle_terminal,
            "view.debugger": self._toggle_debugger,
        })
        
        self._actions.set_checked("view.project_panel", self._sidebar_stack.isVisible())
        self._actions.set_checked("view.function_list", self._right_panel.isVisible())
        self._actions.set_checked("view.terminal", self._terminal.isVisible())
        self._actions.set_checked("view.debugger", self._debugger_dock.isVisible())
        
        # Build actions - Use build controller for build actions
        self._actions.connect_many({
            "build.clean": self._build_controller.clean,
            "build.compile": lambda: self._build_controller.compile(run_after_build=False),
            "build.compile_run": lambda: self._build_controller.compile(run_after_build=True),
            "build.flash": self._build_controller.flash,
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
            "settings.c_project_config": self._show_c_project_config,  # Add C project config action
        })
        
        # Help actions
        self._actions.connect_many({
            "help.about": self._show_about,
            "help.install_framework": self._show_install_framework,
        })
    
    def _connect_services(self) -> None: # Renamed from _connect_signals
        """Connect service signals"""
        # Project service
        self._project_service.project_opened.connect(self._on_project_opened)
        self._project_service.project_closed.connect(self._on_project_closed)
        
        # Build service signals
        self._build_service.build_progress.connect(
            lambda msg, _pct: self._status_manager.set_message(f"Building: {msg}")
        )
        # Note: build_output and build_finished now handled by BuildController
    
    # ========== File Operations ==========
    
    def _new_project(self) -> None:
        """Show create project dialog"""
        from taara_ide.ui.dialogs import CreateProjectDialog
        dialog = CreateProjectDialog(self._project_service, self)
        dialog.project_created.connect(self._on_project_opened)
        dialog.exec()
    
    def _open_project(self) -> None:
        """Open STM32 project dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Open STM32 Project"
        )
        if directory:
            result = self._project_service.open_project(directory)
            if not result.success:
                QMessageBox.warning(self, "Error", f"Failed to open project: {result.message}")
    
    def _open_folder(self) -> None:
        """Open a generic folder (not STM32 project)"""
        directory = QFileDialog.getExistingDirectory(
            self, "Open Folder"
        )
        if directory:
            # Set folder in project view for browsing
            self._project_view.set_project_directory(directory)
            
            if self._search_panel:
                self._search_panel.set_project_path(directory)
            
            # Index folder with CTags for code navigation (runs in background)
            if hasattr(self, '_editor_manager') and hasattr(self._editor_manager, 'ctags_handler'):
                self._status_manager.set_message("Indexing project…")
                ch = self._editor_manager.ctags_handler
                ch.indexing_finished.connect(self._on_project_index_done)
                ch.index_project(directory)
            
            # Save as last opened folder
            self._settings_manager.set_last_project(directory)

            # Update window title
            folder_name = os.path.basename(directory)
            self.setWindowTitle(f"{folder_name} - {AppConstants.APP_NAME} - {AppConstants.VERSION}")

            self._start_lsp(directory)

    # ========== Edit Operations ==========
    
    def _show_find_dialog(self) -> None:
        """Show find dialog"""
        from taara_ide.ui.dialogs import FindDialog
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
        
        from taara_ide.ui.dialogs import GoToLineDialog
        dialog = GoToLineDialog(self, current_line=line + 1, max_line=max_line)
        dialog.line_selected.connect(self._editor_manager.goto_line)
        dialog.exec()
    
    # ========== Build Operations ==========
    # _compile_c_project, _compile_and_run, _flash, _run_executable, _on_unified_build_finished)
    # They are now in BuildController
    
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
    
    def _start_lsp(self, root_path: str) -> None:
        """Start (or restart) clangd for the given root."""
        clangd_exe = self._settings_manager.value("clangd/path", "clangd")
        if self._lsp_service.start(root_path, clangd_exe):
            self._lsp_service.started.connect(
                lambda: self._status_manager.set_message("clangd ready", 3000)
            )
            # Attach LSP to all currently open editors
            for editor in self._editor_manager.editors:
                editor.lsp_client.attach(self._lsp_service)
            # Also attach to future editors
            self._editor_manager.editor_created.connect(
                lambda ed: ed.lsp_client.attach(self._lsp_service)
            )

    def _on_project_opened(self, path: str) -> None:
        """Handle project opened"""
        self.setWindowTitle(
            f"{self._project_service.name} - {AppConstants.APP_NAME}"
        )
        self._status_manager.set_message(f"Opened project: {path}")

        # Update project view
        if self._project_view:
            self._project_view.set_project_directory(path)

        if self._search_panel:
            self._search_panel.set_project_path(path)

        self._start_lsp(path)
    
    def _on_project_closed(self) -> None:
        """Handle project closed"""
        if hasattr(self, '_editor_manager') and hasattr(self._editor_manager, 'ctags_handler'):
            project_path = self._project_service.path
            if project_path:
                self._editor_manager.ctags_handler.cleanup_project_tags(project_path)
        
        self.setWindowTitle(f"{AppConstants.APP_NAME} - {AppConstants.VERSION}")
    
    # ========== Settings Dialogs ==========
    
    def _show_ctags_dialog(self) -> None:
        """Show CTags path dialog"""
        from taara_ide.ui.dialogs import CtagsPathDialog
        dialog = CtagsPathDialog(self)
        dialog.exec()
    
    def _show_project_config(self) -> None:
        """Show project config dialog"""
        if not self._project_service.is_open:
            QMessageBox.warning(self, "Error", "No project is open.")
            return
        
        from taara_ide.ui.dialogs import ProjectConfigDialog
        dialog = ProjectConfigDialog(self._project_service, self)
        dialog.exec()
    
    def _show_c_project_config(self) -> None:
        """Show C project configuration dialog"""
        project_path = None
        project_name = "Untitled"
        
        # Try to get path from project service first
        if self._project_service.is_open:
            project_path = self._project_service.path
            project_name = self._project_service.name
        # Fall back to project view's current directory
        elif self._project_view and self._project_view.get_project_directory():
            project_path = self._project_view.get_project_directory()
            project_name = os.path.basename(project_path)
        
        if not project_path:
            QMessageBox.warning(
                self, 
                "No Directory", 
                "Please open a folder in Project View first.\n\n"
                "Use File > Open Folder to browse to your C project directory."
            )
            return
        
        # Load or create .cproject config
        from taara_ide.core.compiler.c_project_config import CProjectConfigManager
        c_config = CProjectConfigManager.load(project_path)
        if c_config is None:
            # Create default config
            c_config = CProjectConfigManager.create_default(project_path, project_name)
            
            # Show info message for first-time setup
            QMessageBox.information(
                self,
                "New C Project Configuration",
                f"Creating new .cproject configuration for:\n{project_path}\n\n"
                "Configure your source files, include paths, and build settings."
            )
        
        # Show dialog
        from taara_ide.ui.dialogs import CProjectConfigDialog
        dialog = CProjectConfigDialog(c_config, project_path, self)
        if dialog.exec():
            # Save configuration
            if CProjectConfigManager.save(project_path, c_config):
                self._status_manager.set_message("C project configuration saved", 3000)
                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    f"C project configuration has been saved to:\n{os.path.join(project_path, '.cproject')}"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Save Failed",
                    "Failed to save C project configuration."
                )
    
    def _show_install_framework(self) -> None:
        """Show framework installation dialog"""
        from taara_ide.ui.dialogs import InstallFrameworkDialog
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
        
        geometry = self._settings_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self._settings_manager.get_window_state()
        if state:
            self.restoreState(state)
        
        self._saved_sidebar_width = self._settings_manager.get_sidebar_width()
        self._saved_right_panel_width = self._settings_manager.get_right_panel_width()
        
        main_sizes = self._settings_manager.get_main_splitter_sizes()
        if main_sizes and len(main_sizes) == 2:
            self._main_splitter.setSizes(main_sizes)
            # Update sidebar visibility based on actual size
            if main_sizes[0] == 0:
                self._sidebar_stack.setVisible(False)
        else:
            # Default sizes if not saved
            self._main_splitter.setSizes([self._saved_sidebar_width, 750])
        
        center_sizes = self._settings_manager.get_right_splitter_sizes()
        if center_sizes and len(center_sizes) == 2:
            self._center_splitter.setSizes(center_sizes)
            # Update right panel visibility based on actual size
            right_panel_visible = center_sizes[1] > 0
            self._right_panel.setVisible(right_panel_visible)
            self._actions.set_checked("view.function_list", right_panel_visible)
        else:
            # Default sizes if not saved
            if self._saved_right_panel_width > 0:
                self._center_splitter.setSizes([600, self._saved_right_panel_width])
                self._right_panel.setVisible(True)
                self._actions.set_checked("view.function_list", True)
            else:
                self._center_splitter.setSizes([800, 0])
                self._right_panel.setVisible(False)
                self._actions.set_checked("view.function_list", False)
        
        last_project = self._settings_manager.get_last_project()
        if last_project and os.path.exists(last_project):
            # project_view not yet built — set title now, directory set in _finish_deferred
            if self._search_panel:
                self._search_panel.set_project_path(last_project)
            folder_name = os.path.basename(last_project)
            self.setWindowTitle(f"{folder_name} - {AppConstants.APP_NAME} - {AppConstants.VERSION}")

        # Defer tab restoration until after the window is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._restore_tabs)
    
    def _finish_deferred(self) -> None:
        """Complete heavy widget init deferred from __init__ (runs after show)."""
        self._layout.finish_deferred(self)
        self._project_view = self._layout.project_view

        # Wire signals that depend on project_view
        self._project_view.file_requested.connect(self._editor_manager.open_editor)
        self._project_view.index_requested.connect(self._on_index_requested)

        # Re-apply last project to the now-real project view
        last_project = self._settings_manager.get_last_project()
        if last_project and os.path.exists(last_project):
            self._project_view.set_project_directory(last_project)

    def _restore_tabs(self) -> None:
        """Restore previously open editor tabs (called deferred after show)."""
        open_tabs = self._settings_manager.get_open_tabs()
        active_index = self._settings_manager.get_active_tab_index()

        tabs_restored = 0
        for file_path in open_tabs:
            if os.path.exists(file_path):
                self._editor_manager.open_editor(file_path)
                tabs_restored += 1

        if tabs_restored > 0 and 0 <= active_index < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(active_index)

        # Open a blank editor if nothing was restored
        if self._tab_widget.count() == 0:
            self._editor_manager.new_editor()

    def _save_state(self) -> None:
        """Save window state to settings"""
        self._settings_manager.set_window_geometry(self.saveGeometry())
        self._settings_manager.set_window_state(self.saveState())
        
        self._settings_manager.set_main_splitter_sizes(self._main_splitter.sizes())
        self._settings_manager.set_right_splitter_sizes(self._center_splitter.sizes())
        
        self._settings_manager.set_sidebar_width(self._saved_sidebar_width)
        self._settings_manager.set_right_panel_width(self._saved_right_panel_width)
        
        if hasattr(self, '_editor_manager'):
            open_tabs = self._editor_manager.get_open_file_paths()
            self._settings_manager.set_open_tabs(open_tabs)
            
            active_index = self._tab_widget.currentIndex()
            self._settings_manager.set_active_tab_index(active_index)

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
            else:
                self._editor_manager.discard_all_changes()
        
        if hasattr(self, '_editor_manager') and hasattr(self._editor_manager, 'ctags_handler'):
            print("[main_window] Cleaning up all CTags files...")
            self._editor_manager.ctags_handler.cleanup_all_tags()

        if self._lsp_service.is_running():
            self._lsp_service.stop()

        self._extension_manager.shutdown()

        self._save_state()
        
        # Close project
        if self._project_service.is_open:
            self._project_service.close_project()
        
        event.accept()
    
    # ========== View Toggle Operations ==========
    
    def _toggle_word_wrap(self, checked: bool = None) -> None:
        """Toggle word wrap for current editor"""
        editor = self._editor_manager.get_current_editor()
        if editor:
            from PyQt6.Qsci import QsciScintilla
            if checked is not None:
                wrap_mode = QsciScintilla.WrapMode.WrapWord if checked else QsciScintilla.WrapMode.WrapNone
            else:
                current_mode = editor.wrapMode()
                wrap_mode = QsciScintilla.WrapMode.WrapNone if current_mode == QsciScintilla.WrapMode.WrapWord else QsciScintilla.WrapMode.WrapWord
            editor.setWrapMode(wrap_mode)
            is_wrapped = wrap_mode == QsciScintilla.WrapMode.WrapWord
            self._actions.set_checked("view.word_wrap", is_wrapped)
    
    def _toggle_whitespace(self, checked: bool = None) -> None:
        """Toggle whitespace/EOL visibility for all open editors.

        When enabled:
          - Spaces shown as middle dots (·)
          - Tabs shown as long arrows (→) with a tinted background
          - EOL markers shown (↵ / ¶)
        Mirrors VS Code / Notepad++ "Show All Characters" behaviour.
        """
        from PyQt6.Qsci import QsciScintilla

        if checked is None:
            # Derive from current editor state
            editor = self._editor_manager.get_current_editor()
            if editor:
                checked = editor.whitespaceVisibility() == QsciScintilla.WhitespaceVisibility.WsInvisible
            else:
                checked = False

        ws_mode = (QsciScintilla.WhitespaceVisibility.WsVisible
                   if checked else
                   QsciScintilla.WhitespaceVisibility.WsInvisible)

        # Apply to every open editor so switching tabs stays consistent
        for editor in self._editor_manager.editors:
            editor.setWhitespaceVisibility(ws_mode)
            editor.setEolVisibility(checked)   # show ↵ / ¶ markers

        # Remember for editors opened later
        self._show_all_chars = checked

        self._actions.set_checked("view.show_all_chars", checked)
    
    def _toggle_project_panel(self, checked: bool = None) -> None:
        """Toggle project panel visibility"""
        if checked is None:
            checked = not self._sidebar_stack.isVisible()
        
        if checked:
            # Show sidebar
            self._sidebar_stack.setVisible(True)
            sizes = self._main_splitter.sizes()
            total = sum(sizes)
            self._main_splitter.setSizes([self._saved_sidebar_width, total - self._saved_sidebar_width])
        else:
            # Hide sidebar
            sizes = self._main_splitter.sizes()
            if sizes[0] > 0:
                self._saved_sidebar_width = sizes[0]
            self._sidebar_stack.setVisible(False)
            self._main_splitter.setSizes([0, sum(sizes)])
        
        self._actions.set_checked("view.project_panel", checked)

    def _toggle_function_list(self, checked: bool = None) -> None:
        """Toggle function list panel visibility"""
        if checked is None:
            checked = not self._right_panel.isVisible()
        
        if checked:
            # Show function list
            self._right_panel.setVisible(True)
            sizes = self._center_splitter.sizes()
            total = sum(sizes)
            self._center_splitter.setSizes([total - self._saved_right_panel_width, self._saved_right_panel_width])
        else:
            # Hide function list
            sizes = self._center_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                self._saved_right_panel_width = sizes[1]
            self._right_panel.setVisible(False)
            self._center_splitter.setSizes([sum(sizes), 0])
        
        self._actions.set_checked("view.function_list", checked)
    
    def _toggle_terminal(self, checked: bool = None) -> None:
        """Toggle terminal dock visibility"""
        if checked is not None:
            visible = checked
        else:
            visible = not self._terminal_dock.isVisible() # Check dock visibility
        self._terminal_dock.setVisible(visible) # Set dock visibility
        self._actions.set_checked("view.terminal", visible)
        if visible and hasattr(self._terminal, 'focus_input'):
            self._terminal.focus_input()
    
    def _toggle_debugger(self, checked: bool = None) -> None:
        """Toggle debugger dock visibility"""
        if checked is not None:
            visible = checked
        else:
            visible = not self._debugger_dock.isVisible()
        self._debugger_dock.setVisible(visible)
        self._actions.set_checked("view.debugger", visible)
    
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
    
    # ========== CTags Indexing Handler ==========
    
    def _on_project_index_done(self, success: bool) -> None:
        """Handle async project indexing completion."""
        if success:
            self._status_manager.set_message("Project indexed successfully", 3000)
        else:
            self._status_manager.set_message("CTags indexing failed — check CTags path in Settings", 5000)
        # Disconnect to avoid repeated calls on future indexing_finished signals
        try:
            self._editor_manager.ctags_handler.indexing_finished.disconnect(self._on_project_index_done)
        except RuntimeError:
            pass

    def _on_index_requested(self, directory: str) -> None:
        """Handle project indexing request from ProjectView (runs in background)."""
        self._status_manager.set_message(f"Indexing {os.path.basename(directory)}…")
        ch = self._editor_manager.ctags_handler
        ch.indexing_finished.connect(self._on_project_index_done)
        ch.index_project(directory)
    
    # ========== Breadcrumb Bar Handler ==========
    
    def _on_cursor_position_changed(self, line: int, column: int) -> None:
        """Handle cursor position change to update breadcrumb"""
        # Get current symbols from function list
        if hasattr(self._function_list, '_symbols'):
            self._breadcrumb_bar.update_from_cursor(line, self._function_list._symbols)
        
        # Update status bar cursor position
        self._status_manager.update_cursor_position(line + 1, column + 1)
    
    def _on_breadcrumb_symbol_clicked(self, symbol_name: str, line: int) -> None:
        """Handle symbol click in breadcrumb bar"""
        if self._editor_manager:
            self._editor_manager.goto_line(line)
    
    def _on_breadcrumb_file_requested(self, file_path: str):
        """Handle file open request from breadcrumb dropdown"""
        if self._editor_manager and os.path.isfile(file_path):
            self._editor_manager.open_editor(file_path)

    # ========== Shortcut Alt Left/Right Setup ==========
    def _navigate_back(self):
        if self.editor_manager.can_navigate_back():
            self.statusBar().showMessage("Navigated back", 2000)
            self.editor_manager.navigate_back()
        else:
            self.statusBar().showMessage("No more back history", 2000)
    
    def _navigate_forward(self):
        if self.editor_manager.can_navigate_forward():
            self.statusBar().showMessage("Navigated forward", 2000)
            self.editor_manager.navigate_forward()
        else:
            self.statusBar().showMessage("No more forward history", 2000)
    
    def _setup_shortcuts(self):
        back_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        forward_shortcut = QShortcut(QKeySequence("Alt+Right"), self)
        back_shortcut.activated.connect(self._navigate_back)
        forward_shortcut.activated.connect(self._navigate_forward)

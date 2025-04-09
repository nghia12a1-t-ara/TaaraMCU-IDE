import os
import chardet
import subprocess
from pathlib            import Path
from PyQt6.Qsci         import (
    QsciScintilla,
)
from PyQt6.QtWidgets    import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar, QLabel, QMessageBox,
    QFileDialog, QWidget, QMenu, QDialog
)
from PyQt6.QtGui        import QIcon, QAction
from PyQt6.QtCore       import Qt

from code_editor        import CodeEditor
from dialogs.find_dialog        import FindDialog
from dialogs.goto_line_dialog   import GoToLineDialog
from Terminal           import Terminal
from settings_manager   import SettingsManager
from project_view       import ProjectView, FunctionList
from stm32_framework_handler    import STM32FrameworkHandler, InstallFrameworkDialog, CreateProjectDialog
from ctags_handler      import CtagsHandler, CtagsPathDialog
from utils.resource     import resource_path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nghia Taarabt Notepad++")
        self.setGeometry(200, 100, 1000, 600)

        # Set window icon
        icon_path = "icons\\logoIcon.ico"
        self.setWindowIcon(QIcon(resource_path(icon_path)))

        # Initialize find dialog
        self.find_dialog = None

        # UI Manager Variables
        self._showallchar   = False
        self._wordwrap      = False
        self.ctags_handler  = None
        self.current_tab_index = -1

        # Initialize SettingsManager
        self.settings_manager = SettingsManager()
        # Check for existing ctags path
        self.check_ctags_path()

        # Create Terminal
        self.terminal = Terminal(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.terminal)

        # STM32 Framework Setting
        self.stm32_handler = STM32FrameworkHandler(self.settings_manager, self.terminal)
        # Check framework status
        if self.stm32_handler.framework_installed:
            self.statusBar().showMessage("TaaraFramework detected", 3000)

        # Add Function List
        self.function_list = FunctionList(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.function_list)

        # Initialize TabWidget with custom styling
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.close_file)
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        # Update Function List when switching tabs
        self.tabWidget.currentChanged.connect(self.update_function_list)

        # Add Project View
        self.project_view = ProjectView(self)

        # Install event filter for right mouse click on tabs
        self.tabWidget.tabBar().installEventFilter(self)

        self.setCentralWidget(self.tabWidget)

        # Set the tab style
        self.set_tab_style()

        # Create actions, menu and toolbar
        self.control_shorcut_actions()
        self.create_menubar()
        self.create_toolbar()

        # Load session from SettingsManager instead of session.json
        self.settings_manager.restore_session(self)
        self.settings_manager.restore_layout(self)

        # If no files were restored, create a new file
        if self.tabWidget.count() == 0:
            self.new_file()

        # Initialize a list to keep track of closed files
        self.closed_files = []

        # Create a status bar
        self.mainStatusBar = QStatusBar()
        self.setStatusBar(self.mainStatusBar)

        # Create labels for status information
        self.length_label = QLabel("length: 0")
        self.lines_label = QLabel("lines: 0")
        self.cursor_label = QLabel("Ln: 1   Col: 1   Pos: 0")
        self.line_endings_label = QLabel("Windows (CR LF)")
        self.encoding_label = QLabel("UTF-8")
        self.mode_label = QLabel("INS")

        # Add labels to the status bar
        self.mainStatusBar.addPermanentWidget(self.length_label)
        self.mainStatusBar.addPermanentWidget(self.lines_label)
        self.mainStatusBar.addPermanentWidget(self.cursor_label)
        self.mainStatusBar.addPermanentWidget(self.line_endings_label)
        self.mainStatusBar.addPermanentWidget(self.encoding_label)
        self.mainStatusBar.addPermanentWidget(self.mode_label)

        self.length_label.setFixedWidth(80)   # Fix the width to 80px
        self.lines_label.setFixedWidth(80)
        self.cursor_label.setFixedWidth(200)
        self.line_endings_label.setFixedWidth(120)
        self.encoding_label.setFixedWidth(80)
        self.mode_label.setFixedWidth(50)

        # Connect right-click event on encoding label
        self.encoding_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.encoding_label.customContextMenuRequested.connect(self.show_encoding_menu)
        self.line_endings_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.line_endings_label.customContextMenuRequested.connect(self.show_line_end_menu)

        # Initialize status bar fields
        self.update_status_bar()
        self.terminal.exe_first_cmd()

        # Connect the cursor position change to update the status bar
        self.tabWidget.currentChanged.connect(self.update_status_bar)

        # Update the Project View Status follow the STM32 Framework Project
        project_directory = self.project_view.get_project_directory()
        if project_directory and os.path.isfile(os.path.join(project_directory, ".taara_project")):
            self.stm32_handler.load_project_parameters(project_directory)

    def set_tab_style(self):
        """Set the style for tabs"""
        # Style for the tab widget
        self.tabWidget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background: #F0F0F0;
            }
            QTabBar::tab {
                background: #E1E1E1;
                border: 1px solid #C4C4C3;
                padding: 5px 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #dcffbd;  /* Moccasin color for selected tab */
                border-bottom: none;
                margin-bottom: -1px;
                font-weight: bold;
            }
            QTabBar::tab:!selected {
                background: #F0F0F0;
            }
            QTabBar::tab:!selected:hover {
                background: #E8E8E8;
            }
            QTabBar::close-button {
                image: url(icons/close.png);
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background: #FFA07A;  /* Light salmon color for close button hover */
                border-radius: 2px;
            }
        """)

    def on_tab_changed(self, index):
        """Handle tab change event"""
        current_editor = self.get_current_editor()

        # Update the UI to reflect the current tab
        if index >= 0:
            # You can add additional handling here if needed
            current_index_file_status = "saved" if not current_editor.isModified() else "changed"
            self.set_tab_background_color(index, current_index_file_status)
            self.tabWidget.setCurrentIndex(index)
            self.current_tab_index = index

    def control_shorcut_actions(self):
        # File actions
        self.newAction = QAction("New File", self)
        self.newAction.setShortcut("Ctrl+N")
        self.newAction.triggered.connect(self.new_file)

        self.openAction = QAction("Open...", self)
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.triggered.connect(self.open_file)

        self.saveAction = QAction("Save", self)
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.triggered.connect(self.save_file)

        self.exitAction = QAction("Exit", self)
        self.exitAction.setShortcut("Alt+F4")
        self.exitAction.triggered.connect(self.close)

        # Edit actions
        self.undoAction = QAction("Undo", self)
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.triggered.connect(lambda: self.handle_edit_action("undo"))

        self.redoAction = QAction("Redo", self)
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.triggered.connect(lambda: self.handle_edit_action("redo"))

        self.cutAction = QAction("Cut", self)
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.triggered.connect(lambda: self.handle_edit_action("cut"))

        self.copyAction = QAction("Copy", self)
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.triggered.connect(lambda: self.handle_edit_action("copy"))

        self.pasteAction = QAction("Paste", self)
        self.pasteAction.setShortcut("Ctrl+V")
        self.pasteAction.triggered.connect(lambda: self.handle_edit_action("paste"))

        self.selectAllAction = QAction("Select All", self)
        self.selectAllAction.setShortcut("Ctrl+A")
        self.selectAllAction.triggered.connect(lambda: self.handle_edit_action("select_all"))

        # Clean & Compile Execute Action
        self.cleanAction = QAction("Clean", self)
        self.cleanAction.setShortcut("F8")
        self.cleanAction.triggered.connect(self.clean_handle)
        self.addAction(self.cleanAction)

        self.compileAction = QAction("Compile", self)
        self.compileAction.setShortcut("F9")
        self.compileAction.triggered.connect(self.compile_handle)
        self.addAction(self.compileAction)

        self.compilerunAction = QAction("Compile & Run", self)
        self.compilerunAction.setShortcut("F10")
        self.compilerunAction.triggered.connect(self.compile_run_handle)
        self.addAction(self.compilerunAction)

        self.flashAction = QAction("Flash Programming", self)
        self.flashAction.setShortcut("F12")
        self.flashAction.triggered.connect(self.flash_handle)
        self.addAction(self.flashAction)

        # ctags setting action
        self.ctagsSettingAction = QAction("ctags Path Settings", self)
        self.ctagsSettingAction.triggered.connect(self.check_ctags_path)
        self.addAction(self.ctagsSettingAction)

        # STM32 Framework Action
        self.setSTM32FrameworkPath = QAction("Set STM32 Framework Path", self)
        self.setSTM32FrameworkPath.triggered.connect(self.STM32FrameworkPath)
        self.addAction(self.setSTM32FrameworkPath)

        # Add Find action
        self.findAction = QAction("Find", self)
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.triggered.connect(self.show_find_dialog)
        self.addAction(self.findAction)     # Make the shortcut work globally

        # Add action for reopening the last closed file
        self.reopenAction = QAction("Reopen Last Closed File", self)
        self.reopenAction.setShortcut("Ctrl+H")
        self.reopenAction.triggered.connect(self.reopen_last_closed_file)
        self.addAction(self.reopenAction)   # Make the shortcut work globally

        # Add action for closing the current tab
        self.closeTabAction = QAction("Close Tab", self)
        self.closeTabAction.setShortcut("Ctrl+F4")
        self.closeTabAction.triggered.connect(self.close_current_tab)
        self.addAction(self.closeTabAction)  # Make the shortcut work globally

        # Add action for Go To Line
        self.goToLineAction = QAction("Go To Line", self)
        self.goToLineAction.setShortcut("Ctrl+G") # Change to a unique shortcut
        self.goToLineAction.triggered.connect(self.show_go_to_line_dialog)
        self.addAction(self.goToLineAction)             # Make the shortcut work globally

        # Add shortcut for commenting/uncommenting
        self.commentAction = QAction("Comment/Uncomment", self)
        self.commentAction.setShortcut("Ctrl+Q")
        self.commentAction.triggered.connect(lambda: self.handle_edit_action("comment"))
        self.addAction(self.commentAction)

        # Add Word Wrap action
        self.wordWrapAction = QAction("Word Wrap", self)
        self.wordWrapAction.setCheckable(True)  # Make it checkable
        self.wordWrapAction.setShortcut("Ctrl+W")  # Optional shortcut
        self.wordWrapAction.triggered.connect(self.toggle_word_wrap)
        self.addAction(self.wordWrapAction)  # Make the shortcut work globally

        # Add Show All Characters action
        self.ShowAllCharAction = QAction("Show All Characters", self)
        self.ShowAllCharAction.setCheckable(True)  # Make it checkable
        self.ShowAllCharAction.setShortcut("Ctrl+J")  # Optional shortcut
        self.ShowAllCharAction.triggered.connect(self.toggle_show_all_char)
        self.addAction(self.ShowAllCharAction)  # Make the shortcut work globally

        # Add action to change language
        self.setPythonAction = QAction("Set Python Language", self)
        self.setPythonAction.triggered.connect(lambda: self.set_editor_language("Python"))
        self.setCPPAction = QAction("Set C++ Language", self)
        self.setCPPAction.triggered.connect(lambda: self.set_editor_language("CPP"))
        self.addAction(self.setPythonAction)
        self.addAction(self.setCPPAction)

        # Create New STM32 Framework Action
        self.newSTM32FrameworkPrjAction = QAction("New STM32 Framework Project", self)
        # self.newSTM32FrameworkPrjAction.setShortcut("Ctrl+Shift+P")
        self.newSTM32FrameworkPrjAction.triggered.connect(self.create_stm32_project)
        self.addAction(self.newSTM32FrameworkPrjAction)

        # Add action to open project directory
        self.openprojectAction = QAction("Open Project", self)
        self.openprojectAction.setShortcut("Ctrl+Shift+P")
        self.openprojectAction.triggered.connect(self.open_project_directory)
        self.addAction(self.openprojectAction)

        # Create actions for project view and function list
        self.projectviewAction = QAction(QIcon(resource_path("icons/project.svg")), "Project Explore", self)
        self.projectviewAction.setCheckable(True)
        self.projectviewAction.setChecked(True)
        self.projectviewAction.toggled.connect(self.toggle_project_view)

        # Function List Action
        self.functionlistAction = QAction(QIcon(resource_path("icons/function_list.svg")), "Function List", self)
        self.functionlistAction.setCheckable(True)
        self.functionlistAction.setChecked(True)
        self.functionlistAction.toggled.connect(self.toggle_function_list)

        self.toggleterminalAction = QAction("Terminal", self)
        self.toggleterminalAction.setCheckable(True)
        self.toggleterminalAction.setChecked(True)
        self.toggleterminalAction.setShortcut("Ctrl+B")
        self.toggleterminalAction.triggered.connect(self.toggle_terminal)

    def handle_edit_action(self, action):
        current_editor = self.get_current_editor()
        if current_editor:
            if action == "cut":
                current_editor.cut()
            elif action == "copy":
                current_editor.copy()
            elif action == "paste":
                current_editor.paste()
            elif action == "undo":
                current_editor.undo()
            elif action == "redo":
                current_editor.redo()
            elif action == "select_all":
                current_editor.selectAll()
            elif action == "comment":
                current_editor.comment_lines()

    def create_menubar(self):
        menubar = self.menuBar()

        # File Menu
        fileMenu = menubar.addMenu("File")
        new_menu = QMenu("New Menu", self)
        fileMenu.addMenu(new_menu)
        new_menu.addAction(self.newAction)
        new_menu.addAction(self.newSTM32FrameworkPrjAction)


        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.openprojectAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.reopenAction)  # Add the reopen action to the menu
        fileMenu.addAction(self.exitAction)

        # Edit Menu
        editMenu = menubar.addMenu("Edit")
        editMenu.addAction(self.undoAction)
        editMenu.addAction(self.redoAction)
        editMenu.addSeparator()
        editMenu.addAction(self.cutAction)
        editMenu.addAction(self.copyAction)
        editMenu.addAction(self.pasteAction)
        editMenu.addSeparator()
        editMenu.addAction(self.findAction)
        editMenu.addAction(self.selectAllAction)
        
        # Execute Menu
        execMenu = menubar.addMenu("Execute")
        execMenu.addAction(self.cleanAction)
        execMenu.addAction(self.compileAction)
        execMenu.addAction(self.compilerunAction)
        execMenu.addSeparator()
        execMenu.addAction(self.flashAction)
        # execMenu.addSeparator()
        # execMenu.addAction(self.cleanAction)
        # execMenu.addAction(self.debugAction)

        # Settings Menu
        SettingMenu = menubar.addMenu("Settings")
        
        specsetting_menu    = QMenu("Special Settings", self)
        languageMenu        = QMenu("Set Language", self)
        stm32frameworkMenu  = QMenu("STM32 Framework Path", self)
        SettingMenu.addMenu(specsetting_menu)
        SettingMenu.addMenu(stm32frameworkMenu)
        SettingMenu.addMenu(languageMenu)

        # Action of Setting Menu
        specsetting_menu.addAction(self.ctagsSettingAction)
        languageMenu.addAction(self.setSTM32FrameworkPath)
        languageMenu.addAction(self.setPythonAction)
        languageMenu.addAction(self.setCPPAction)

        # Add Window Toolbar
        windowMenu = menubar.addMenu("Window")
        show_view_menu = QMenu("Show View", self)
        windowMenu.addMenu(show_view_menu)
        show_view_menu.addAction(self.projectviewAction)
        show_view_menu.addAction(self.functionlistAction)
        show_view_menu.addAction(self.toggleterminalAction)
        
        # Help Menu
        helpMenu = menubar.addMenu("Help")
        aboutAction = QAction("About", self)
        aboutAction.triggered.connect(self.about_app)
        STM32FrameworkInstallAction = QAction("STM32 Framework Installation", self)
        STM32FrameworkInstallAction.triggered.connect(self.open_install_framework_dialog)
        helpMenu.addAction(aboutAction)
        helpMenu.addAction(STM32FrameworkInstallAction)

    def check_ctags_path(self):
        """Check if the ctags path is already set."""
        path = self.settings_manager.get_ctags_path()
        if path and os.path.exists(path):
            # Set the ctags path in the handler
            CtagsHandler.ctags_path = path
            self.ctags_handler = CtagsHandler(self)
            self.ctags_handler.ctags_path = path
            return

        # If no valid path is found, show the dialog
        dialog = CtagsPathDialog(self.settings_manager)
        if dialog.exec() != QDialog.accepted:
            QMessageBox.warning(self, "CTags Path", "CTags path must be set to use this feature.")
            self.close()        # Close this dialog if the user cancels

    def open_install_framework_dialog(self):
        dialog = InstallFrameworkDialog(self.settings_manager, self.terminal)
        if dialog.getstatus():
            dialog.exec()

    def create_stm32_project(self):
        """Create a new STM32 project and generate ctags."""
        projdialog = CreateProjectDialog(self.stm32_handler)
        projdialog.exec()
        if projdialog.isProjectCreated:
            projdialog.isProjectCreated = False
            self.project_view.set_project_directory(self.stm32_handler.project_path)

    def STM32FrameworkPath(self):
        # @TODO - implement STM32 Framework Path Setting
        pass

    def open_project_directory(self):
        """Select project directory and update Project View."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if directory:
            self.project_view.set_project_directory(directory)

    def set_editor_language(self, language):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.set_language(language)

    def toggle_project_view(self, checked):
        """Toggle visibility of Project View."""
        self.project_view.project_dock.setVisible(checked)

    def toggle_function_list(self, checked):
        """Toggle visibility of Function List."""
        self.function_list.setVisible(checked)

    def toggle_terminal(self, checked):
        """Toggle Terminal."""
        if checked:
            self.terminal.show()
        else:
            self.terminal.hide()

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.setObjectName("MainToolbar")

        # Add icons to actions
        self.newAction.setIcon(QIcon(resource_path("icons/new.svg")))
        self.newSTM32FrameworkPrjAction.setIcon(QIcon(resource_path("icons/open_proj.svg")))
        self.openAction.setIcon(QIcon(resource_path("icons/open.svg")))
        self.openprojectAction.setIcon(QIcon(resource_path("icons/open_proj.svg")))
        self.saveAction.setIcon(QIcon(resource_path("icons/save.svg")))
        self.wordWrapAction.setIcon(QIcon(resource_path("icons/word-wrap.svg")))
        self.ShowAllCharAction.setIcon(QIcon(resource_path("icons/show_all_char.svg")))

        # Add actions to toolbar
        toolbar.addAction(self.newAction)
        toolbar.addAction(self.openAction)
        toolbar.addAction(self.openprojectAction)
        toolbar.addAction(self.saveAction)
        toolbar.addAction(self.wordWrapAction)
        toolbar.addAction(self.ShowAllCharAction)
        toolbar.addAction(self.functionlistAction)

    def new_file(self):
        """Create a new empty file"""
        editor = CodeEditor(self)  # Ensure self is passed as the parent
        editor.textChanged.connect(self.on_editor_text_changed)  # Connect the signal
        self.add_editor(editor)
        self.tabWidget.addTab(editor, "Untitled")
        self.tabWidget.setCurrentWidget(editor)  # Set the new editor as the current widget

    def open_file(self, file_path=None, cursor_pos=(0, 0)):
        """Open a file in a new tab, generating CTags only for source code files."""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open File",
                "",
                "All Files (*.*)"
            )

        if file_path:
            # Check if file is already open
            for i in range(self.tabWidget.count()):
                editor = self.tabWidget.widget(i)
                if hasattr(editor, 'file_path') and editor.file_path == file_path:
                    self.tabWidget.setCurrentIndex(i)
                    return

            try:
                # Detect file encoding
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']

                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()

                editor = CodeEditor(self)
                editor.textChanged.connect(self.on_editor_text_changed)
                editor.setText(text)
                editor.file_path = file_path
                editor.setModified(False)
                self.add_editor(editor)

                # Restore cursor position
                editor.setCursorPosition(*cursor_pos)
                editor.horizontalScrollBar().setValue(0)  # Set to leftmost position

                filename = Path(file_path).name
                index = self.tabWidget.addTab(editor, filename)
                self.tabWidget.setCurrentIndex(index)
                
                # Update Function List after opening a file
                self.update_function_list()

                # Define recognized source code extensions
                SOURCE_EXTENSIONS = ('.c', '.cpp', '.h', '.hpp', '.py')  # Add more as needed

                # Only generate CTags for source code files
                file_suffix = Path(file_path).suffix.lower()
                if file_suffix in SOURCE_EXTENSIONS:
                    self.ctags_handler = CtagsHandler(editor)
                    self.ctags_handler.generate_ctags()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        current_editor = self.get_current_editor()
        if current_editor is None:
            return
        self.set_tab_background_color(self.current_tab_index, "saved")

        if not hasattr(current_editor, 'file_path'):
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*.*)")
            if file_path:
                current_editor.file_path = file_path
            else:
                return
        try:
            with open(current_editor.file_path, 'w', encoding='utf-8') as f:
                f.write(current_editor.text())

            # Mark the editor as not modified
            current_editor.setModified(False)

            # Update Tab Color Background
            self.set_tab_background_color(self.current_tab_index, "saved")

            # Update the tab title to the file name
            self.tabWidget.setTabText(
                self.current_tab_index,
                Path(current_editor.file_path).name
            )
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
            return False

    def close_file(self, index):
        """Handle closing a tab"""
        editor = self.tabWidget.widget(index)
        if editor.isModified():
            filename = self.tabWidget.tabText(index)
            reply = QMessageBox.question(
                self,
                "Save Changes",
                f"Do you want to save changes to {filename}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file(editor):
                    return  # Don't close if save was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return  # Don't close if user cancelled

        # Store the closed file information
        if hasattr(editor, 'file_path'):
            self.closed_files.append((editor.file_path, editor.text(), editor.getCursorPosition()))

        # Remove ctags file
        self.ctags_handler = CtagsHandler(editor)
        self.ctags_handler.remove_ctags()

        # Remove the tab
        self.tabWidget.removeTab(index)

        # Create a new tab if this was the last one
        if self.tabWidget.count() == 0:
            self.new_file()

    def about_app(self):
        QMessageBox.information(self, "About", "This is a Notepad++ style Text Editor, develop by Nghia Taarabt and Channel laptrinhdientu.com\nDebugger integration coming soon!")

    def set_tab_background_color(self, index, hex_color):
        """Set the background color of a specific tab"""
        if 0 <= index < self.tabWidget.count():
            if hex_color == "changed":
                self.tabWidget.setStyleSheet("""
                    QTabWidget::pane {
                        border: 1px solid #C2C7CB;
                        background: #F0F0F0;
                    }
                    QTabBar::tab {
                        background: #E1E1E1;
                        border: 1px solid #C4C4C3;
                        padding: 5px 10px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background: #edd19d;  /* Moccasin color for selected tab */
                        border-bottom: none;
                        margin-bottom: -1px;
                        font-weight: bold;
                    }
                    QTabBar::tab:!selected {
                        background: #F0F0F0;
                    }
                    QTabBar::tab:!selected:hover {
                        background: #E8E8E8;
                    }
                    QTabBar::close-button {
                        image: url(icons/close.png);
                        subcontrol-position: right;
                    }
                    QTabBar::close-button:hover {
                        background: #FFA07A;  /* Light salmon color for close button hover */
                        border-radius: 2px;
                    }
                """)
            elif hex_color == "saved":
                self.tabWidget.setStyleSheet("""
                    QTabWidget::pane {
                        border: 1px solid #C2C7CB;
                        background: #F0F0F0;
                    }
                    QTabBar::tab {
                        background: #E1E1E1;
                        border: 1px solid #C4C4C3;
                        padding: 5px 10px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background: #dcffbd;  /* Moccasin color for selected tab */
                        border-bottom: none;
                        margin-bottom: -1px;
                        font-weight: bold;
                    }
                    QTabBar::tab:!selected {
                        background: #F0F0F0;
                    }
                    QTabBar::tab:!selected:hover {
                        background: #E8E8E8;
                    }
                    QTabBar::close-button {
                        image: url(icons/close.png);
                        subcontrol-position: right;
                    }
                    QTabBar::close-button:hover {
                        background: #FFA07A;  /* Light salmon color for close button hover */
                        border-radius: 2px;
                    }
                """)
            #self.tabWidget.tabBar().setTabData(index, {"background-color": hex_color})

    def set_tabtext_color(self, index, hex_color):
        """Set the text color of a specific tab"""
        if 0 <= index < self.tabWidget.count():
            self.tabWidget.tabBar().setStyleSheet(f"QTabBar::tab::selected {{ color: {hex_color}; }}")

    def get_current_editor(self):
        """Return the currently active editor"""
        current_index = self.tabWidget.currentIndex()
        if current_index != -1:
            return self.tabWidget.widget(current_index)
        return None

    def show_find_dialog(self):
        if not self.find_dialog:
            self.find_dialog = FindDialog(self)

        # Get selected text if any
        editor = self.get_current_editor()
        if editor and editor.hasSelectedText():
            self.find_dialog.find_input.setText(editor.selectedText())
            self.find_dialog.find_input.selectAll()

        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()
        self.find_dialog.find_input.setFocus()

    def save_file_for_editor(self, editor):
        """Save the specified editor's content"""
        if not hasattr(editor, 'file_path') or not editor.file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*.*)")
            if file_path:
                editor.file_path = file_path
            else:
                return False  # Người dùng hủy lưu

        try:
            with open(editor.file_path, 'w', encoding='utf-8') as f:
                f.write(editor.text())
            editor.setModified(False)
            # Cập nhật tên tab
            tab_index = self.tabWidget.indexOf(editor)
            if tab_index != -1:
                self.tabWidget.setTabText(tab_index, Path(editor.file_path).name)
                self.set_tab_background_color(tab_index, "saved")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
            return False

    def closeEvent(self, event):
        """Handle application close event."""
        modified_saved_files = []
        for i in range(self.tabWidget.count()):
            editor = self.tabWidget.widget(i)
            if editor.isModified() and hasattr(editor, 'file_path') and editor.file_path:
                if editor.text().strip():
                    modified_saved_files.append((i, editor, self.tabWidget.tabText(i)))

        if modified_saved_files:
            tabs_to_remove = []
            for index, editor, filename in modified_saved_files:
                reply = QMessageBox.question(
                    self, "Save Changes", f"Do you want to save changes to {filename}?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                )
                if reply == QMessageBox.StandardButton.Save:
                    if not self.save_file_for_editor(editor):
                        event.ignore()
                        return
                elif reply == QMessageBox.StandardButton.Discard:
                    tabs_to_remove.append(index)

            for index in sorted(tabs_to_remove, reverse=True):
                self.tabWidget.removeTab(index)

        # Remove .tags files for all open files
        for i in range(self.tabWidget.count()):
            editor = self.tabWidget.widget(i)
            if hasattr(editor, 'file_path'):
                self.ctags_handler = CtagsHandler(editor)
                self.ctags_handler.remove_ctags()

        # Remove .tags file for current project
        if hasattr(self, 'project_view') and self.project_view.current_project_directory:
            project_tags = Path(self.project_view.current_project_directory) / 'project.tags'
            if project_tags.exists():
                project_tags.unlink()

        # Lưu session và layout qua SettingsManager
        self.settings_manager.save_session(self)
        self.settings_manager.save_layout(self)
        event.accept()

    def hideEvent(self, event):
        """Save state when minimized."""
        self.settings_manager.save_layout(self)
        super().hideEvent(event)

    def showEvent(self, event):
        """Restore state when shown again."""
        self.settings_manager.restore_layout(self)
        super().showEvent(event)

    def eventFilter(self, obj, event):
        """Handle right mouse click on tabs and middle mouse button click to close tabs"""
        if obj is self.tabWidget.tabBar():
            if event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.MiddleButton:  # Middle mouse button
                    tab_index = obj.tabAt(event.pos())
                    if tab_index != -1:  # Valid tab clicked
                        self.close_file(tab_index)  # Close the tab
                        return True
                elif event.button() == Qt.MouseButton.RightButton:
                    tab_index = obj.tabAt(event.pos())
                    if tab_index != -1:  # Valid tab clicked
                        # Use mapToGlobal to get the global position
                        self.show_tab_context_menu(tab_index, obj.mapToGlobal(event.pos()))
                        return True
        return super().eventFilter(obj, event)

    def copy_full_file_path(self, editor):
        """Copy the full file path to the clipboard"""
        if hasattr(editor, 'file_path') and editor.file_path:
            clipboard = QApplication.clipboard()
            clipboard.setText(editor.file_path)

    def open_containing_folder(self, editor):
        """Open the containing folder of the file in Explorer"""
        if hasattr(editor, 'file_path') and editor.file_path:
            folder_path = Path(editor.file_path).parent
            if folder_path.exists():
                subprocess.Popen(f'explorer "{folder_path}"')

    def show_tab_context_menu(self, tab_index, pos):
        """Show context menu for tab actions"""
        menu = QMenu(self)

        # Get the editor associated with the tab
        editor = self.tabWidget.widget(tab_index)

        # Close File action
        close_action = QAction("Close File", self)
        close_action.triggered.connect(lambda: self.close_file(tab_index))
        menu.addAction(close_action)

        # Copy Full File Path action
        copy_path_action = QAction("Copy Full File Path", self)
        copy_path_action.triggered.connect(lambda: self.copy_full_file_path(editor))
        menu.addAction(copy_path_action)

        # Open Containing Folder in Explorer action
        open_folder_action = QAction("Open Containing Folder in Explorer", self)
        open_folder_action.triggered.connect(lambda: self.open_containing_folder(editor))
        menu.addAction(open_folder_action)

        # Show the context menu
        menu.exec(pos)

    def on_editor_text_changed(self):
        """Handle text changes in the editor"""
        current_editor = self.get_current_editor()
        if current_editor:
            current_index = self.tabWidget.indexOf(current_editor)
            self.set_tab_background_color(current_index, "changed")
            self.update_status_bar()  # Update status bar on text change

    def reopen_last_closed_file(self):
        """Reopen the last closed file"""
        if self.closed_files:
            file_path, content, cursor_pos = self.closed_files.pop()  # Get the last closed file info
            self.open_file(file_path, cursor_pos)  # Open the file with the saved cursor position
            editor = self.get_current_editor()
            if editor:
                editor.setText(content)     # Restore the content
                editor.setModified(False)   # Mark as saved
                self.set_tab_background_color(self.tabWidget.indexOf(editor), "saved")

    def close_current_tab(self):
        """Close the currently active tab."""
        current_index = self.tabWidget.currentIndex()
        if current_index != -1:
            self.close_file(current_index)  # Call the existing close_file method

    def show_go_to_line_dialog(self):
        """Show the Go To Line dialog."""
        dialog = GoToLineDialog(self)
        dialog.exec()

    def toggle_word_wrap(self):
        """Toggle word wrap in the current editor."""
        current_editor = self.get_current_editor()
        if current_editor:
            # Check the current wrap mode and toggle accordingly
            if current_editor.wrapMode() == QsciScintilla.WrapMode.WrapWord:
                current_editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)  # Disable wrap
                self.wordWrapAction.setChecked(False)  # Update UI action
            else:
                current_editor.setWrapMode(QsciScintilla.WrapMode.WrapWord)  # Enable word wrap
                self.wordWrapAction.setChecked(True)  # Update UI action

    def show_all_char(self, isShowed):
        current_editor = self.get_current_editor()
        current_editor.setEolVisibility(isShowed)
        self.ShowAllCharAction.setChecked(isShowed)  # Update UI action

    def toggle_show_all_char(self):
        """Toggle show all character in the current editor."""
        current_editor = self.get_current_editor()
        self._showallchar = not self._showallchar
        current_editor.setEolVisibility(self._showallchar)
        self.ShowAllCharAction.setChecked(self._showallchar)

    def add_editor(self, editor):
        """Add a new editor and connect signals for real-time updates."""
        editor.textChanged.connect(self.on_editor_text_changed)  # Update on text change
        editor.cursorPositionChanged.connect(self.update_status_bar)  # Update on cursor position change

    def update_status_bar(self):
        """Update the status bar with current editor information."""
        editor = self.get_current_editor()
        if editor:
            # Chặn tín hiệu để tránh tác dụng phụ
            editor.blockSignals(True)
            try:
                text = editor.text()
                length = len(text)
                lines = editor.SendScintilla(QsciScintilla.SCI_GETLINECOUNT)
                cursor_line, cursor_col = editor.getCursorPosition()
                cursor_pos = editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

                # Determine line endings based on the text content
                eol_mode = editor.eolMode()

                if eol_mode == QsciScintilla.EolMode.EolWindows:
                    line_endings = "Windows (CRLF)"
                elif eol_mode == QsciScintilla.EolMode.EolUnix:
                    line_endings = "Unix (LF)"
                elif eol_mode == QsciScintilla.EolMode.EolMac:
                    line_endings = "Mac (CR)"
                else:
                    line_endings = "Unknown EOL"

                encoding = "UTF-8"  # You can implement detection if needed
                mode = "INS" if editor.SendScintilla(QsciScintilla.SCI_GETOVERTYPE) == 0 else "OVR"

                # Update the status labels
                if hasattr(self, 'mainStatusBar'):
                    self.length_label.setText(f"length: {length}")
                    self.lines_label.setText(f"MaxLine: {lines}")
                    self.cursor_label.setText(f"Line: {cursor_line + 1}   Col: {cursor_col + 1}   Pos: {cursor_pos}")
                    self.line_endings_label.setText(line_endings)
                    self.encoding_label.setText(encoding)
                    self.mode_label.setText(mode)
            finally:
                # Khôi phục tín hiệu
                editor.blockSignals(False)

    def show_encoding_menu(self, pos):
        """Show context menu for encoding options."""
        menu = QMenu(self)

        # Define encoding options
        encodings = ["UTF-8", "ISO-8859-1", "ASCII", "UTF-16", "UTF-32"]
        for encoding in encodings:
            action = QAction(encoding, self)
            action.triggered.connect(lambda checked, enc=encoding: self.change_encoding(enc))
            menu.addAction(action)

        # Show the menu at the cursor position
        menu.exec(self.encoding_label.mapToGlobal(pos))

    def change_encoding(self, new_enc):
        """Change the encoding of the current file."""
        current_editor = self.get_current_editor()
        if current_editor and hasattr(current_editor, 'file_path'):
            try:
                # Read the current content
                coding1 = "utf-8"
                coding2 = "gb18030"

                f = open(current_editor.file_path, 'rb')
                content = unicode(f.read(), coding2)
                f.close()
                f = open(current_editor.file_path, 'wb')
                f.write(content.encode(new_enc))
                f.close()

                # Save the current cursor position
                # cursor_pos = current_editor.getCursorPosition()

                # Write the content with the new encoding
                # with open(current_editor.file_path, 'wb') as f:
                #     f.write(content.encode(new_enc))

                # Update the encoding label
                self.encoding_label.setText(new_enc)

                # Restore the cursor position
                current_editor.setCursorPosition(*cursor_pos)

                QMessageBox.information(self, "Encoding Changed", f"File encoding changed to {new_enc}.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not change encoding: {str(e)}")

    def show_line_end_menu(self, pos):
        """Show context menu for encoding options."""
        menu = QMenu(self)

        # Define encoding options
        line_end_list = ["Windows (CRLF)", "Unix (LF)", "Mac (CR)"]
        for line_end in line_end_list:
            action = QAction(line_end, self)
            action.triggered.connect(lambda checked, type=line_end: self.change_line_end(type))
            menu.addAction(action)

        # Show the menu at the cursor position
        menu.exec(self.line_endings_label.mapToGlobal(pos))

    def change_line_end(self, new_line_end):
        """Change the encoding of the current file."""
        current_editor = self.get_current_editor()
        if current_editor and hasattr(current_editor, 'file_path'):
            try:
                if new_line_end == "Windows (CRLF)":
                    current_editor.setEolMode(QsciScintilla.EolMode.EolWindows)
                elif new_line_end == "Unix (LF)":
                    current_editor.setEolMode(QsciScintilla.EolMode.EolUnix)
                elif new_line_end == "Mac (CR)":
                    current_editor.setEolMode(QsciScintilla.EolMode.EolMac)

                # Save the current cursor position
                cursor_pos = current_editor.getCursorPosition()

                # Update the encoding label
                self.line_endings_label.setText(new_line_end)

                # Restore the cursor position
                current_editor.setCursorPosition(*cursor_pos)

                QMessageBox.information(self, "Line Ending Changed", f"File Line Ending changed to {new_line_end}.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not change line endings: {str(e)}")

    def enable_folding(editor: QsciScintilla):
        # Set the width of the second margin to display folding indicators
        editor.setMarginWidth(2, 15)
        # Set the folding display style to boxed tree fold style
        editor.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)
    
    """ Function List Item Handle Functions """
    def update_function_list(self):
        """Update the function list when switching tabs or opening a file."""
        current_editor = self.get_current_editor()
        self.function_list.update_function_list(current_editor)

    def on_item_double_clicked(self, item, column):
        """Handle double-click event on a function list item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            file_path, line_info = data
            editor = self.parent.get_current_editor()
            if editor:
                # Extract line number and column position from line info
                line_number = None
                column_position = 0
                symbol = item.text(0)

                if line_info.startswith("/^") and line_info.endswith("$/;\""):
                    pattern = line_info[2:-4].strip()
                    try:
                        with open(file_path, 'r', encoding='utf-8') as source_file:
                            for i, source_line in enumerate(source_file, 1):
                                if pattern in source_line.strip():
                                    line_number = i
                                    column_position = source_line.find(symbol)
                                    break
                    except Exception as e:
                        return
                elif line_info.isdigit():
                    line_number = int(line_info)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as source_file:
                            for i, source_line in enumerate(source_file, 1):
                                if i == line_number:
                                    column_position = source_line.find(symbol)
                                    break
                    except Exception as e:
                        return

                if line_number is not None:
                    # Open the file and place the cursor at the symbol position
                    editor.open_file_at_line(file_path, line_number, column_position)
    
    ########## Compile and Execute Handle #############
    def clean_handle(self):
        # STM32 Framework Handle
        if self.stm32_handler.project_available:
            self.stm32_handler.project_action("clean")
        else:
            pass

    def compile_handle(self):
        # STM32 Framework Handle
        if self.stm32_handler.project_available:
            self.stm32_handler.project_action("clean_build")
        else:
            # Programming Language Handle
            editor = self.get_current_editor()
            file_suffix = Path(editor.file_path).suffix.lower()
            file_path = str(Path(editor.file_path).resolve())

            if '.py' == file_suffix:
                self.terminal.add_log("Command", f"python {file_path}")
                if self.terminal.execute_specific_command(f"python {file_path}"):
                    self.terminal.add_log("Info", "Python program is executed!")
            if '.c' == file_suffix:    
                output_path = str(Path(file_path).with_suffix('.exe'))
                current_dir = str(Path(file_path).parent)
                self.terminal.add_log("Command", f"gcc -o {output_path} {file_path} -I {current_dir}")
                if self.terminal.execute_specific_command(f"gcc -o {output_path} {file_path} -I {current_dir}"):
                    if Path(output_path).exists():
                        # Get modification times
                        exe_mtime = os.path.getmtime(output_path)
                        src_mtime = os.path.getmtime(file_path)
                        
                        if exe_mtime >= src_mtime:
                            self.terminal.add_log("Info", "Executable is up to date")
                        else:
                            self.terminal.add_log("Info", "Source file has changed, recompiling...")
                    else:
                        self.terminal.add_log("Info", "C program is executed!")

    def compile_run_handle(self):
        self.compile_handle()
        editor = self.get_current_editor()
        file_path = str(Path(editor.file_path).resolve())
        exe_path = str(Path(file_path).with_suffix('.exe'))
        
        if Path(exe_path).exists():
            self.terminal.add_log("Command", exe_path)
            self.terminal.execute_specific_command(exe_path)

    def flash_handle(self):
        # STM32 Framework Handle
        if self.stm32_handler.project_available:
            self.stm32_handler.project_action("flash")
        else:
            pass
    ##################### STM32 Handler ###########################

# editor_manager.py
from PyQt6.QtWidgets    import QMessageBox, QFileDialog
from code_editor        import CodeEditor
from pathlib            import Path
from ctags_handler      import CtagsHandler

class EditorManager:
    def __init__(self, parent, tab_widget):
        self.parent = parent            # MainWindow
        self.tab_widget = tab_widget    # QTabWidget to display editors
        self.editors = {}               # {editor: {"index": int, "file_path": str, "modified": bool}}
        
        # Connect tab_widget events
        self.tab_widget.tabCloseRequested.connect(self.close_editor)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def new_editor(self):
        """Create a new editor"""
        editor = CodeEditor(self.parent)
        editor.textChanged.connect(self.on_text_changed)
        editor.cursorPositionChanged.connect(self.parent.update_status_bar)
        
        index = self.tab_widget.addTab(editor, "Untitled")
        self.editors[editor] = {"index": index, "file_path": None, "modified": False}
        self.tab_widget.setCurrentWidget(editor)
        return editor

    def open_editor(self, file_path=None):
        """Open a file in a new editor"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self.parent, "Open File", "", "All Files (*.*)")
        if not file_path:
            return None

        # Check if the file is already open
        for editor, info in self.editors.items():
            if info["file_path"] == file_path:
                self.tab_widget.setCurrentIndex(info["index"])
                return editor

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            editor = CodeEditor(self.parent)
            editor.setText(text)
            editor.file_path = file_path
            editor.setModified(False)
            
            editor.textChanged.connect(self.on_text_changed)
            editor.cursorPositionChanged.connect(self.parent.update_status_bar)
            
            index = self.tab_widget.addTab(editor, Path(file_path).name)
            self.editors[editor] = {"index": index, "file_path": file_path, "modified": False}
            self.tab_widget.setCurrentIndex(index)
            return editor
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Could not open file: {str(e)}")
            return None

    def save_editor(self, editor=None):
        """Save the current editor or the specified editor"""
        editor = editor or self.get_current_editor()
        if not editor:
            return False
        
        if not hasattr(editor, 'file_path') or not editor.file_path:
            file_path, _ = QFileDialog.getSaveFileName(self.parent, "Save File", "", "All Files (*.*)")
            if not file_path:
                return False
            editor.file_path = file_path
            self.editors[editor]["file_path"] = file_path

        try:
            with open(editor.file_path, 'w', encoding='utf-8') as f:
                f.write(editor.text())
            editor.setModified(False)
            self.editors[editor]["modified"] = False
            self.tab_widget.setTabText(self.editors[editor]["index"], Path(editor.file_path).name)
            self.update_tab_style(editor, "saved")
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Could not save file: {str(e)}")
            return False

    def close_editor(self, index):
        """Close the editor at index"""
        editor = self.tab_widget.widget(index)
        if not editor or editor not in self.editors:
            return
        
        if editor.isModified():
            reply = QMessageBox.question(
                self.parent, "Save Changes",
                f"Do you want to save changes to {self.tab_widget.tabText(index)}?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_editor(editor):
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        # Remove ctags if any
        if hasattr(self.parent, 'ctags_handler'):
            self.parent.ctags_handler = CtagsHandler(editor)
            self.parent.ctags_handler.remove_ctags()

        self.tab_widget.removeTab(index)
        del self.editors[editor]
        
        if self.tab_widget.count() == 0:
            self.new_editor()

    def get_current_editor(self):
        """Get the current editor"""
        current_index = self.tab_widget.currentIndex()
        if current_index != -1:
            editor = self.tab_widget.widget(current_index)
            if editor in self.editors:
                return editor
        return None
    
    def get_current_filepath(self):
        """Get the file path of the current editor"""
        current_editor = self.get_current_editor()
        if current_editor:
            return self.editors[current_editor]["file_path"]
        return None

    def on_text_changed(self):
        """Handle when text in the editor changes"""
        editor = self.parent.sender()
        if editor in self.editors:
            self.editors[editor]["modified"] = True
            self.update_tab_style(editor, "changed")
            self.parent.update_status_bar()

    def on_tab_changed(self, index):
        """Handle when tab is changed"""
        editor = self.tab_widget.widget(index)
        if editor in self.editors:
            self.update_tab_style(editor, "changed" if self.editors[editor]["modified"] else "saved")
            self.parent.current_tab_index = index

    def update_tab_style(self, editor, state):
        """Update the style for the tab"""
        index = self.editors[editor]["index"]
        if state == "changed":
            self.tab_widget.setTabText(index, f"{Path(self.editors[editor]['file_path']).name if self.editors[editor]['file_path'] else 'Untitled'}*")
            self.parent.set_tab_background_color(index, "changed")
        elif state == "saved":
            self.tab_widget.setTabText(index, Path(self.editors[editor]['file_path']).name if self.editors[editor]['file_path'] else "Untitled")
            self.parent.set_tab_background_color(index, "saved")

    def get_all_editors(self):
        """Get the list of all editors"""
        return list(self.editors.keys())

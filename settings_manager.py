# settings_manager.py
from PyQt6.QtCore import QSettings
from pathlib import Path
import json
import os
from datetime import datetime

class SettingsManager:
    def __init__(self, organization="Taara", application="Debugger"):
        """Initialize SettingsManager with QSettings."""
        self.settings = QSettings(organization, application)
        self.app_dir = Path(__file__).parent
        self.backup_dir = self.app_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def save_layout(self, main_window):
        """Save the state of the MainWindow interface."""
        self.settings.setValue("MainWindow/State", main_window.saveState())
        self.settings.setValue("MainWindow/Geometry", main_window.saveGeometry())

    def restore_layout(self, main_window):
        """Restore the state of the MainWindow interface."""
        if self.settings.value("MainWindow/State"):
            main_window.restoreState(self.settings.value("MainWindow/State"))
            main_window.restoreGeometry(self.settings.value("MainWindow/Geometry"))

    def save_session(self, main_window):
        """Save session information instead of session.json."""
        session_data = {
            'open_files': [],
            'unsaved_files': [],
            'current_tab': main_window.tabWidget.currentIndex(),
            'project_directory': main_window.project_view.get_project_directory()
        }

        # Handle each open tab
        for i in range(main_window.tabWidget.count()):
            editor = main_window.tabWidget.widget(i)
            cursor_pos = editor.getCursorPosition()
            content = editor.text()

            # Save saved files
            if hasattr(editor, 'file_path') and editor.file_path and not editor.isModified():
                session_data['open_files'].append({
                    'path': editor.file_path,
                    'cursor': list(cursor_pos)  # Convert tuple to list for JSON storage
                })

            # Save unsaved or modified files
            if editor.isModified() or not hasattr(editor, 'file_path'):
                if content.strip():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if hasattr(editor, 'file_path') and editor.file_path:
                        original_name = Path(editor.file_path).stem
                        backup_name = f"{original_name}_{timestamp}.txt"
                    else:
                        backup_name = f"unsaved_{timestamp}_{i}.txt"
                    backup_path = str(self.backup_dir / backup_name)

                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    session_data['unsaved_files'].append({
                        'backup_path': backup_path,
                        'cursor': list(cursor_pos),
                        'original_path': getattr(editor, 'file_path', None),
                        'tab_name': main_window.tabWidget.tabText(i),
                        'timestamp': timestamp
                    })

        # Save session_data to QSettings
        self.settings.setValue("Session/Data", json.dumps(session_data))

    def restore_session(self, main_window):
        """Restore session information from QSettings."""
        session_json = self.settings.value("Session/Data")
        if not session_json:
            return

        try:
            session_data = json.loads(session_json)

            # Restore saved files
            for file_info in session_data.get('open_files', []):
                file_path = file_info['path']
                cursor_pos = tuple(file_info['cursor'])
                if Path(file_path).exists():
                    main_window.open_file(file_path, cursor_pos)

            # Restore unsaved files from backup
            for unsaved in session_data.get('unsaved_files', []):
                backup_path = unsaved['backup_path']
                if Path(backup_path).exists():
                    editor = main_window.open_file(backup_path, tuple(unsaved['cursor']))
                    if editor:
                        editor.setModified(True)
                else:
                    editor = CodeEditor(main_window)
                    editor.setCursorPosition(*tuple(unsaved['cursor']))
                    editor.setModified(True)
                    tab_name = unsaved.get('tab_name', Path(backup_path).stem)
                    main_window.tabWidget.addTab(editor, tab_name)

            # Restore the current tab
            current_tab = session_data.get('current_tab', 0)
            if main_window.tabWidget.count() > current_tab:
                main_window.tabWidget.setCurrentIndex(current_tab)

            # Restore the project directory
            project_dir = session_data.get('project_directory', '')
            if project_dir and os.path.isdir(project_dir):
                main_window.project_view.set_project_directory(project_dir)

        except Exception as e:
            print(f"Error restoring session: {str(e)}")

    def clear_session(self):
        """Clear session information."""
        self.settings.remove("Session/Data")

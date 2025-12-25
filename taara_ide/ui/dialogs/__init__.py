"""
Dialog components for Taara IDE
"""
from .find_dialog import FindDialog
from .goto_line_dialog import GoToLineDialog
from .project_config_dialog import ProjectConfigDialog
from .ctags_path_dialog import CtagsPathDialog
from .create_project_dialog import CreateProjectDialog
from .install_framework_dialog import InstallFrameworkDialog
from .c_project_config_dialog import CProjectConfigDialog
from .serial_settings_dialog import SerialSettingsDialog

__all__ = [
    'FindDialog',
    'GoToLineDialog', 
    'ProjectConfigDialog',
    'CtagsPathDialog',
    'CreateProjectDialog',
    'InstallFrameworkDialog',
    'CProjectConfigDialog',
    'SerialSettingsDialog'
]

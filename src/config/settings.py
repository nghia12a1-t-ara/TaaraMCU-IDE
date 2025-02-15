from pathlib import Path

# Application paths
APP_DIR = Path(__file__).parent.parent.parent
BACKUP_DIR = APP_DIR / "backups"
RESOURCES_DIR = APP_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
THEMES_DIR = RESOURCES_DIR / "themes"

# Editor settings
DEFAULT_FONT = "Consolas"
DEFAULT_FONT_SIZE = 16
MARGIN_FONT_SIZE = 18
DEFAULT_THEME = "Khaki"

# File settings
BACKUP_FILE_PREFIX = "backup_"
SESSION_FILENAME = "session.json" 
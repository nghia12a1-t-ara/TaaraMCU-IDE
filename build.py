import PyInstaller.__main__
import os
from pathlib import Path

# Get the current directory
current_dir = Path(__file__).parent

# Define icon path
icon_path = str(current_dir / "icons" / "logoIcon.ico")

PyInstaller.__main__.run([
    'main.py',
    '--name=Taara_Notepad++',
    '--onefile',
    f'--icon={icon_path}',
    '--noconsole',
    '--add-data=themes/khaki.json;themes',
    f'--distpath={current_dir}'
]) 
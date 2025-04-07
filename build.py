import PyInstaller.__main__
import os
import sys
import shutil
import winshell
from win32com.client import Dispatch

def create_shortcut(exe_path, working_dir):
    desktop = winshell.desktop()
    shortcut_path = os.path.join(desktop, "Taara_IDE.lnk")
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = exe_path
    shortcut.WorkingDirectory = working_dir
    shortcut.IconLocation = os.path.join(working_dir, "icons", "logoIcon.ico")  # Explicitly use .ico
    shortcut.save()
    print(f"Shortcut created at: {shortcut_path} with icon {shortcut.IconLocation}")

def clean_up():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    items_to_remove = ["Taara_IDE.spec", "build", "dist", "backups", "test"]
    for item in items_to_remove:
        item_path = os.path.join(current_dir, item)
        if os.path.exists(item_path):
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
            print(f"Removed: {item_path}")

def build_exe():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    files = [
        "main.py",
        "ctags_handler.py",
        "project_view.py",
        "settings_manager.py",
        "Terminal.py",
        "stm32_framework_handler.py",
    ]
    files = [os.path.join(current_dir, f) for f in files]

    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist.")
            sys.exit(1)

    svg_folder = os.path.join(current_dir, "icons")
    themes_folder = os.path.join(current_dir, "themes")
    session_file = os.path.join(current_dir, "session.json")
    icon_file = os.path.join(current_dir, "icons", "logoIcon.ico")

    for path, desc in [(svg_folder, "Icons folder"), (themes_folder, "Themes folder"), (icon_file, "Icon file")]:
        if not os.path.exists(path):
            print(f"Error: {desc} {path} does not exist.")
            sys.exit(1)

    svg_files = [os.path.join(svg_folder, f) for f in os.listdir(svg_folder) if f.endswith(".svg")]
    json_theme_files = [os.path.join(themes_folder, f) for f in os.listdir(themes_folder) if f.endswith(".json")]

    pyinstaller_args = [
        "--onefile",
        "--clean",
        "--noconsole",
        "--noupx",
        "--name", "Taara_IDE",
        "--icon", icon_file,
        "--uac-admin",
        "--distpath", current_dir,
    ]
    for svg_file in svg_files:
        pyinstaller_args.append(f"--add-data={svg_file}{os.pathsep}icons")
    for json_file in json_theme_files:
        pyinstaller_args.append(f"--add-data={json_file}{os.pathsep}themes")
    if os.path.exists(session_file):
        pyinstaller_args.append(f"--add-data={session_file}{os.pathsep}.")
    pyinstaller_args.extend(files)
    pyinstaller_args.append(f"--add-data={icon_file}{os.pathsep}icons")

    try:
        print(f"Building with icon: {icon_file}")
        PyInstaller.__main__.run(pyinstaller_args)
        print(f"Build completed: {os.path.join(current_dir, 'Taara_IDE.exe')}")

        print("Cleaning up...")
        clean_up()

        print("Creating shortcut...")
        exe_path = os.path.join(current_dir, "Taara_IDE.exe")
        create_shortcut(exe_path, current_dir)

    except Exception as e:
        print(f"Build failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe()

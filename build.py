import PyInstaller.__main__
import os
import sys
import shutil
import winshell  # Library to create shortcuts on Windows
from win32com.client import Dispatch

def create_shortcut(exe_path, working_dir):
    """Creates a shortcut on the Desktop with a specific working directory"""
    desktop = winshell.desktop()  # Get the path to the Desktop
    shortcut_path = os.path.join(desktop, 'Taara_Notepad++.lnk')  # Name of the shortcut
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = exe_path  # Path to the exe file
    shortcut.WorkingDirectory = working_dir  # Working directory
    shortcut.IconLocation = exe_path  # Use the icon of the exe file itself
    shortcut.save()

def clean_up():
    """Cleans up unnecessary files and directories after building"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    items_to_remove = [
        os.path.join(current_dir, 'Taara_Notepad++.exe.spec'),  # .spec file
        os.path.join(current_dir, 'Taara_Notepad++.spec'),      # .spec file
        os.path.join(current_dir, 'build'),      # build directory
        os.path.join(current_dir, 'backups'),    # backups directory
        os.path.join(current_dir, 'dist'),       # dist directory
        os.path.join(current_dir, 'test'),       # test directory
    ]
    
    for item in items_to_remove:
        if os.path.exists(item):
            if os.path.isfile(item):
                os.remove(item)
            elif os.path.isdir(item):
                shutil.rmtree(item)

def build_exe():
    # Path to the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Python files to be built
    files = [
        os.path.join(current_dir, 'main.py'),
        os.path.join(current_dir, 'ctags_handler.py'),
        os.path.join(current_dir, 'project_view.py'),
    ]
    
    # Check if the Python files exist
    for file_path in files:
        if not os.path.exists(file_path):
            sys.exit(1)

    # Path to the directory containing SVG files (the 'icons' directory)
    svg_folder = os.path.join(current_dir, 'icons')
    themes_folder = os.path.join(current_dir, 'themes')

    # Check the icons directory
    if not os.path.exists(svg_folder):
        sys.exit(1)

    # Get all .svg files in the icons directory
    svg_files = [f for f in os.listdir(svg_folder) if f.endswith('.svg')]

    # Get all .json files in the themes directory
    json_theme_files = [f for f in os.listdir(themes_folder) if f.endswith('.json')]

    # Path to the session.json file
    json_file = os.path.join(current_dir, 'session.json')

    # PyInstaller command configuration
    pyinstaller_args = [
        '--onefile',            # Build into a single exe file
        '--clean',              # Clean up temporary files before building
        '--noconsole',          # Do not display a console when running
        '--noupx',              # Do not use UPX to compress
        '-F',                   # Similar to --onefile
        '-n', 'Taara_IDE.exe',        # Name of the output exe file
        '--icon', 'icons/logoIcon.ico',    # Full path to the icon
        '--uac-admin',
        '--distpath', '.',      # Output directory
    ]
    
    # Add all .svg files as data
    for svg_file in svg_files:
        svg_path = os.path.join(svg_folder, svg_file)
        pyinstaller_args.append(f'--add-data={svg_path}:icons')  # Correct the syntax

    # Add all .json files in the themes directory as data
    for json_theme_file in json_theme_files:
        json_theme_path = os.path.join(themes_folder, json_theme_file)
        pyinstaller_args.append(f'--add-data={json_theme_path}:themes')

    # Add the session.json file as data
    pyinstaller_args.append(f'--add-data={json_file}:.')  # Place in the root when unpacked

    # Add all Python files to the command
    pyinstaller_args.extend(files)
    
    try:
        print("Building the exe file...")
        print(f"Found {len(svg_files)} SVG files: {svg_files}")
        PyInstaller.__main__.run(pyinstaller_args)
        print(f"Build completed! The exe file is created in the directory '{current_dir}'")
        
        # Clean up after building
        print("Cleaning up unnecessary files and directories...")
        clean_up()

        # Create a shortcut on the Desktop
        print("Creating a shortcut on the Desktop...")
        create_shortcut(f"{current_dir}/Taara_Notepad++.exe", current_dir)
        
    except Exception as e:
        print(f"Build failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    build_exe()
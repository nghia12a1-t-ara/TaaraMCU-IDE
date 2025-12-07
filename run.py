#!/usr/bin/env python3
"""
Taara IDE Runner Script - Deployment Safe Version
"""

import sys
import os
import ctypes
from pathlib import Path

# ===============================
# WINDOWS: TASKBAR APP ID
# ===============================
if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TaaraMCU.IDE")

# ===============================
# PATH SETUP FOR NUITKA LAYOUT
# ===============================
def setup_runtime_paths():
    exe_path = Path(sys.argv[0]).resolve()
    base_dir = exe_path.parent

    # dependencies/
    deps_dir = base_dir / "dependencies"

    # Dev mode fallback
    if not deps_dir.exists():
        deps_dir = base_dir

    # Add DLL search path (Windows 10+)
    if sys.platform == "win32":
        try:
            os.add_dll_directory(str(deps_dir))
        except AttributeError:
            pass

    # Ensure DLLs + Python libs are found
    os.environ["PATH"] = f"{deps_dir};" + os.environ.get("PATH", "")

    # Change working dir so Qt can find plugins
    os.chdir(deps_dir)

    # Ensure Python can import local packages
    sys.path.insert(0, str(deps_dir))
    sys.path.insert(0, str(base_dir))

setup_runtime_paths()

# ===============================
# START APPLICATION
# ===============================
from taara_ide.main import main

if __name__ == "__main__":
    main()

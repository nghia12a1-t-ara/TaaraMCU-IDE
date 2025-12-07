#!/usr/bin/env python3
"""
Taara IDE - Fully Automated Nuitka Builder
Output Layout:
    TaaraMCU-IDE.exe
    dependencies/
"""

import sys
import shutil
import subprocess
from pathlib import Path
import os

# ===============================
# CONFIG
# ===============================

APP_NAME = "TaaraMCU-IDE"
ENTRY_FILE = "run.py"

ROOT = Path(__file__).parent.resolve()
DIST_FOLDER = ROOT / f"{ENTRY_FILE.replace('.py', '')}.dist"
FINAL_DEPS = ROOT / "dependencies"
FINAL_EXE = ROOT / f"{APP_NAME}.exe"

ICON = ROOT / "taara_ide" / "icons" / "logoIcon.ico"


# ===============================
# UTILS
# ===============================

def clean():
    for p in [FINAL_DEPS, DIST_FOLDER]:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    if FINAL_EXE.exists():
        FINAL_EXE.unlink()

def run(cmd):
    print(">>>", " ".join(cmd))
    subprocess.check_call(cmd)

def create_shortcut():
    try:
        import win32com.client
    except ImportError:
        print("[!] pywin32 is not installed. Please setup: pip install pywin32")
        return
    shell = win32com.client.Dispatch("WScript.Shell")
    root = str(ROOT)
    target = os.path.join(root, "dependencies", f"{APP_NAME}.exe")
    shortcut_path = os.path.join(root, f"{APP_NAME}.lnk")

    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = os.path.dirname(target)
    shortcut.IconLocation = target
    shortcut.save()

    print(f"[OK] Shortcut created: {shortcut_path}")

# ===============================
# BUILD
# ===============================

def build():
    clean()

    cmd = [
        sys.executable, "-m", "nuitka",
        ENTRY_FILE,

        "--standalone",
        "--enable-plugin=pyqt6",
        "--assume-yes-for-downloads",
        "--windows-disable-console",
        f"--windows-icon-from-ico={ICON}",
        "--remove-output",
        f"--output-dir={ROOT}",
        f"--output-filename={APP_NAME}.exe",
    ]

    run(cmd)

    # ---- POST PROCESS ----
    if DIST_FOLDER.exists():
        if FINAL_DEPS.exists():
            shutil.rmtree(FINAL_DEPS, ignore_errors=True)
        DIST_FOLDER.rename(FINAL_DEPS)
        print("[OK] .dist renamed to dependencies/")


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    print("=====================================")
    print("   Building TaaraMCU IDE - FULL AUTO")
    print("=====================================")
    build()
    create_shortcut()

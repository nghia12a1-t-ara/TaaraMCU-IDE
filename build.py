import subprocess
import sys
import shutil
from pathlib import Path

# =========================
# CONFIG
# =========================

APP_NAME = "TaaraMCU-IDE"
ENTRY_FILE = "run.py"

PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUT_EXE = PROJECT_ROOT / f"{APP_NAME}.exe"

ICON_FILE = PROJECT_ROOT / "taara_ide" / "icons" / "logoIcon.ico"
THEME_DIR = PROJECT_ROOT / "taara_ide" / "themes"
ICON_DIR = PROJECT_ROOT / "taara_ide" / "icons"

# =========================
# UTILS
# =========================

def run(cmd):
    print(">>>", " ".join(cmd))
    subprocess.check_call(cmd)

def clean():
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    if OUTPUT_EXE.exists():
        OUTPUT_EXE.unlink()

# =========================
# BUILD
# =========================

def build():
    clean()

    cmd = [
        sys.executable, "-m", "nuitka",

        # ===== MODE =====
        "--standalone",
        "--onefile",
        "--assume-yes-for-downloads",
        
        "--follow-imports",

        # ===== QT PLUGIN =====
        "--enable-plugin=pyqt6",
        
        # ===== INCLUDE PROJECT MODULES EXPLICITLY =====
        "--include-package=taara_ide",
        "--include-package=taara_ide.config",
        "--include-package=taara_ide.core",
        "--include-package=taara_ide.core.compiler",
        "--include-package=taara_ide.core.debugger",
        "--include-package=taara_ide.core.indexer",
        "--include-package=taara_ide.frameworks",
        "--include-package=taara_ide.frameworks.stm32",
        "--include-package=taara_ide.services",
        "--include-package=taara_ide.ui",
        "--include-package=taara_ide.ui.dialogs",
        "--include-package=taara_ide.ui.editor",
        "--include-package=taara_ide.ui.panels",
        "--include-package=taara_ide.utils",
        
        # ===== INCLUDE PYQT6 MODULES =====
        "--include-module=PyQt6.QtCore",
        "--include-module=PyQt6.QtGui",
        "--include-module=PyQt6.QtWidgets",
        "--include-module=PyQt6.QtPrintSupport",
        "--include-module=PyQt6.QtSvg",
        "--include-module=PyQt6.Qsci",
        
        # ===== INCLUDE STANDARD LIBRARY MODULES =====
        "--include-module=json",
        "--include-module=os",
        "--include-module=sys",
        "--include-module=pathlib",
        "--include-module=subprocess",
        "--include-module=hashlib",
        "--include-module=re",
        "--include-module=dataclasses",
        "--include-module=typing",
        "--include-module=functools",
        "--include-module=shutil",
        
        # ===== ENCODING (prevent lag on startup) =====
        "--include-module=encodings",
        "--include-module=encodings.utf_8",
        "--include-module=encodings.ascii",
        "--include-module=encodings.latin_1",
        "--include-module=encodings.cp1252",
        "--include-module=codecs",

        # ===== BLOCK HEAVY/UNUSED QT MODULES =====
        "--nofollow-import-to=PyQt6.QtBluetooth",
        "--nofollow-import-to=PyQt6.QtNfc",
        "--nofollow-import-to=PyQt6.QtQuick",
        "--nofollow-import-to=PyQt6.QtQuickWidgets",
        "--nofollow-import-to=PyQt6.QtMultimedia",
        "--nofollow-import-to=PyQt6.QtOpenGL",
        "--nofollow-import-to=PyQt6.QtOpenGLWidgets",
        "--nofollow-import-to=PyQt6.QtWebSockets",
        "--nofollow-import-to=PyQt6.QtWebEngine",
        "--nofollow-import-to=PyQt6.QtWebEngineWidgets",
        "--nofollow-import-to=PyQt6.QtPdf",
        "--nofollow-import-to=PyQt6.QtPdfWidgets",
        "--nofollow-import-to=PyQt6.QtSensors",
        "--nofollow-import-to=PyQt6.QtPositioning",
        "--nofollow-import-to=PyQt6.QtSerialPort",
        "--nofollow-import-to=PyQt6.QtTest",
        "--nofollow-import-to=PyQt6.QtDesigner",
        "--nofollow-import-to=PyQt6.QtHelp",
        "--nofollow-import-to=PyQt6.Qt3DCore",
        "--nofollow-import-to=PyQt6.Qt3DRender",
        "--nofollow-import-to=PyQt6.Qt3DInput",
        "--nofollow-import-to=PyQt6.Qt3DLogic",
        "--nofollow-import-to=PyQt6.Qt3DAnimation",
        "--nofollow-import-to=PyQt6.Qt3DExtras",
        
        # ===== BLOCK OTHER UNUSED MODULES =====
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=test",
        "--nofollow-import-to=distutils",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=pip",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=matplotlib",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=PIL",
        "--nofollow-import-to=cv2",

        # ===== OUTPUT =====
        f"--output-filename={OUTPUT_EXE.name}",
        f"--output-dir={PROJECT_ROOT}",

        # ===== WINDOWS OPTIONS =====
        f"--windows-icon-from-ico={ICON_FILE}",
        "--windows-disable-console",
        
        # ===== COMPANY INFO =====
        "--windows-company-name=Taara",
        "--windows-product-name=TaaraMCU IDE",
        "--windows-file-version=1.0.0.0",
        "--windows-product-version=1.0.0.0",
        "--windows-file-description=TaaraMCU IDE - Embedded Development Environment",

        # ===== DATA FILES =====
        f"--include-data-dir={ICON_DIR}=taara_ide/icons",
        f"--include-data-dir={THEME_DIR}=taara_ide/themes",

        # ===== OPTIMIZATION =====
        "--lto=yes",
        "--jobs=4",

        ENTRY_FILE
    ]

    run(cmd)

    # Clean up build artifacts
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    print("\n" + "=" * 60)
    print("  BUILD SUCCESS!")
    print(f"  Output: {OUTPUT_EXE}")
    print("=" * 60)

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    print("=" * 60)
    print("  Building TaaraMCU IDE - PRODUCTION BUILD")
    print("=" * 60)
    build()

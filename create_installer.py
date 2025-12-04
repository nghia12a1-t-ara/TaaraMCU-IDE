#!/usr/bin/env python3
"""
Create Windows installer for Taara IDE using Inno Setup
Automatically builds the app and creates installer
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_step(message):
    print(f"\n{GREEN}==>{RESET} {message}")

def print_error(message):
    print(f"{RED}Error:{RESET} {message}")

def print_warning(message):
    print(f"{YELLOW}Warning:{RESET} {message}")

def check_inno_setup():
    """Check if Inno Setup is installed"""
    print_step("Checking for Inno Setup...")
    
    # Common Inno Setup installation paths
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  Found Inno Setup at: {path}")
            return path
    
    print_error("Inno Setup not found!")
    print("\nPlease download and install Inno Setup from:")
    print("  https://jrsoftware.org/isdl.php")
    print("\nAfter installation, run this script again.")
    return None

def build_app():
    """Build the application with Nuitka"""
    print_step("Building application with Nuitka...")
    
    if not os.path.exists("build.py"):
        print_error("build.py not found!")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, "build.py"],
            check=True,
            capture_output=False
        )
        print("  Build successful!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Build failed: {e}")
        return False

def verify_build_output():
    """Verify that build output exists"""
    print_step("Verifying build output...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print_error("dist/ directory not found!")
        return False
    
    exe_file = dist_dir / "TaaraIDE.exe"
    if not exe_file.exists():
        print_error("TaaraIDE.exe not found in dist/!")
        return False
    
    print(f"  Found: {exe_file}")
    print(f"  Size: {exe_file.stat().st_size / (1024*1024):.1f} MB")
    return True

def create_installer(iscc_path):
    """Create installer using Inno Setup"""
    print_step("Creating installer with Inno Setup...")
    
    if not os.path.exists("installer.iss"):
        print_error("installer.iss not found!")
        return False
    
    try:
        result = subprocess.run(
            [iscc_path, "installer.iss"],
            check=True,
            capture_output=True,
            text=True
        )
        print("  Installer created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Installer creation failed: {e}")
        if e.output:
            print(e.output)
        return False

def main():
    print(f"""
{GREEN}╔═══════════════════════════════════════╗
║   Taara IDE Installer Creator         ║
╚═══════════════════════════════════════╝{RESET}
""")
    
    # Step 1: Check for Inno Setup
    iscc_path = check_inno_setup()
    if not iscc_path:
        return 1
    
    # Step 2: Build the application
    print("\nDo you want to rebuild the application? (y/n): ", end="")
    rebuild = input().strip().lower()
    
    if rebuild == 'y':
        if not build_app():
            return 1
    else:
        print_warning("Skipping build step. Using existing dist/ folder.")
    
    # Step 3: Verify build output
    if not verify_build_output():
        return 1
    
    # Step 4: Create installer
    if not create_installer(iscc_path):
        return 1
    
    # Success!
    print(f"\n{GREEN}✓ Success!{RESET}")
    
    installer_output = Path("installer_output")
    if installer_output.exists():
        installer_files = list(installer_output.glob("*.exe"))
        if installer_files:
            installer_file = installer_files[0]
            size_mb = installer_file.stat().st_size / (1024*1024)
            print(f"\n  Installer created: {installer_file}")
            print(f"  Size: {size_mb:.1f} MB")
            print(f"\n  You can now distribute this single .exe file!")
            print(f"  Users just need to run it - no Python or dependencies required.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

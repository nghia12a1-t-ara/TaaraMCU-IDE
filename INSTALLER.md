# Creating Windows Installer for Taara IDE

This guide explains how to create a single-file Windows installer that bundles the application with all required DLLs.

## Prerequisites

### 1. Install Inno Setup

Download and install Inno Setup from:
- **Official Website**: https://jrsoftware.org/isdl.php
- **Direct Download**: https://jrsoftware.org/download.php/is.exe

Choose the default installation location.

### 2. Build Requirements

Make sure you have all build dependencies:
\`\`\`bash
pip install -r requirements.txt
pip install nuitka ordered-set zstandard
\`\`\`

## Quick Start

### Option 1: Automated (Recommended)

Run the automated installer creation script:

\`\`\`bash
python create_installer.py
\`\`\`

This script will:
1. Check if Inno Setup is installed
2. Build the application with Nuitka (optional)
3. Create the installer
4. Output: `installer_output/TaaraIDE-1.0.0-Setup.exe`

### Option 2: Manual Steps

1. **Build the application**:
   \`\`\`bash
   python build.py
   \`\`\`

2. **Compile installer** (if Inno Setup is in PATH):
   \`\`\`bash
   iscc installer.iss
   \`\`\`
   
   Or use the GUI:
   - Open `installer.iss` in Inno Setup Compiler
   - Click "Compile" or press F9

3. **Find the installer**:
   - Location: `installer_output/TaaraIDE-1.0.0-Setup.exe`

## Customization

### Change App Version

Edit `installer.iss`:
```iss
#define MyAppVersion "1.0.0"  ; Change this

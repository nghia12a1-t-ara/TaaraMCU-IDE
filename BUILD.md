# Building Taara IDE

This document explains how to build Taara IDE into a standalone executable.

## Prerequisites

1. **Python 3.8+**
2. **PyQt6** and dependencies installed
   ```bash
   pip install -r taara_ide/requirements.txt
   ```

3. **C Compiler** (Nuitka requirement)
   - **Windows**: Install Microsoft Visual C++ Build Tools or MinGW-w64
   - **Linux**: GCC (usually pre-installed)
   - **macOS**: Xcode Command Line Tools

## Building

### Production Build (Recommended)

Creates a single optimized executable file:

```bash
python build.py
```

The executable will be in the `dist/` folder.

**Features:**
- Single executable file
- Maximum optimization
- Small size (modules excluded)
- No console window (Windows)

**Build time:** ~10-15 minutes (first build)

### Development Build (Faster)

For quick testing during development:

```bash
python build_dev.py
```

**Features:**
- Folder mode (faster to build)
- No optimization
- Console window enabled
- Includes debug info

**Build time:** ~3-5 minutes

## Customization

Edit `build.py` to customize:

- **App metadata**: Lines 17-23 (name, version, copyright)
- **Icon**: Line 37 (provide your own `.ico` file)
- **Optimization**: Lines 32-33
- **Included packages**: Lines 39-43
- **Excluded modules**: Lines 51-60

## Common Issues

### Nuitka not found
The build script will offer to install Nuitka automatically.
Manual install:
```bash
pip install nuitka ordered-set
```

### C Compiler not found
Install a C compiler for your platform (see Prerequisites).

### Build too large
Adjust `EXCLUDE_MODULES` in `build.py` to exclude more unused packages.

### Build errors
- Check all dependencies are installed: `pip install -r taara_ide/requirements.txt`
- Ensure icon file exists if specified
- Try development build first for faster debugging

## Distribution

After building:

1. Test the executable on your platform
2. For Windows: Consider signing the executable
3. Create installer (NSIS, Inno Setup, etc.) if needed
4. Distribute the `dist/` folder or single `.exe` file

## Platform-Specific Notes

### Windows
- Includes Windows metadata (version, description, company)
- Uses icon from `taara_ide/icons/app.ico`
- Console disabled by default for clean UI

### Linux
- May require `AppImage` or package manager integration
- Check executable permissions: `chmod +x dist/TaaraMCU-IDE`

### macOS  
- May need code signing for distribution
- Consider creating `.app` bundle for native feel

## Advanced: Custom Builds

For advanced customization, see Nuitka documentation:
https://nuitka.net/doc/user-manual.html

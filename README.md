# Taara IDE

**Taara IDE** is a professional embedded development IDE for microcontrollers, specifically designed for STM32 development with support for C/C++ projects.

## Features

- **Modern UI**: Activity Bar, breadcrumb navigation, and customizable panels
- **Code Intelligence**: 
  - Syntax highlighting with QScintilla
  - Auto-completion powered by CTags
  - Go-to-definition (Ctrl+Click)
  - Function list sidebar
- **Project Management**:
  - Open files, folders, or STM32 projects
  - Project tree view with file browser
  - Search in files with regex support
- **Build & Debug**: Integrated terminal, debugger panel (WIP)
- **Customizable**:
  - Multiple themes (Dark, Light, Khaki, Monokai)
  - Adjustable font and editor settings
  - Panel layouts persist between sessions

## Quick Start

### For Users (Windows)

Download the latest installer from [Releases](../../releases) and run it. No Python or dependencies required.

### For Developers

#### Prerequisites

- Python 3.12+
- Windows 10/11 (other OS support coming soon)
- CTags (optional, for code intelligence)

#### Setup

1. Clone the repository:
   \`\`\`bash
   git clone https://github.com/yourusername/taara-ide.git
   cd taara-ide
   \`\`\`

2. Install dependencies:
   \`\`\`bash
   pip install -r taara_ide/requirements.txt
   \`\`\`

3. Run the IDE:
   \`\`\`bash
   python run.py
   \`\`\`

## Building

### Development Build

For quick testing:
\`\`\`bash
python build_dev.py
\`\`\`

### Production Build

Create optimized executable:
\`\`\`bash
python build.py
\`\`\`

Output: `dist/TaaraIDE.exe`

### Create Installer

Build a single-file Windows installer:
\`\`\`bash
python create_installer.py
\`\`\`

See [INSTALLER.md](INSTALLER.md) for detailed instructions.

## Project Structure

\`\`\`
taara-ide/
├── taara_ide/              # Main application package
│   ├── config/             # Configuration and constants
│   ├── core/               # Core functionality (compiler, indexer)
│   ├── services/           # Services (build, debug, project)
│   ├── ui/                 # User interface components
│   │   ├── editor/         # Code editor and manager
│   │   ├── panels/         # Side panels (project, function list, etc.)
│   │   └── dialogs/        # Dialog windows
│   ├── utils/              # Utility functions
│   └── icons/              # Application icons
├── run.py                  # Run script for development
├── build.py                # Nuitka build script (production)
├── build_dev.py            # Quick development build
├── create_installer.py     # Installer creation script
└── installer.iss           # Inno Setup configuration
\`\`\`

## Usage

### Opening Projects

- **File → Open File** (Ctrl+O): Open a single file
- **File → Open Folder** (Ctrl+Shift+O): Open a folder for browsing
- **File → Open STM32 Project**: Open STM32 project structure

### Code Navigation

- **Ctrl+Click**: Go to definition
- **Function List**: View functions/classes in current file (right panel)
- **Breadcrumb**: See current file path and context (top bar)

### View Options

- **Word Wrap**: Toggle line wrapping
- **Show All Characters**: Show whitespace and special characters
- **Function List**: Toggle function list panel

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New File | Ctrl+N |
| Open File | Ctrl+O |
| Open Folder | Ctrl+Shift+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Close Tab | Ctrl+W |
| Go to Definition | Ctrl+Click |
| Find | Ctrl+F |
| Replace | Ctrl+H |

## Configuration

Settings are stored in:
- **Windows**: `%LOCALAPPDATA%/TaaraIDE/settings.ini`

All settings persist between sessions:
- Window size and position
- Panel visibility and sizes
- Open files and folders
- Active tab
- Editor preferences (word wrap, whitespace display)

## Development

### Adding New Features

The codebase uses a modular architecture:
- **Services** handle business logic (build, debug, project management)
- **UI Components** are in `taara_ide/ui/`
- **Actions** are defined in `ui/actions.py`
- **Menus** are configured in `ui/menu_manager.py`

### Code Style

- Follow PEP 8 conventions
- Use absolute imports: `from taara_ide.module import Class`
- Add docstrings to public methods

## Dependencies

Main dependencies:
- **PyQt6**: GUI framework
- **QScintilla**: Code editor component
- **CTags**: Code indexing (bundled with installer)

See [taara_ide/requirements.txt](taara_ide/requirements.txt) for full list.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and feature requests, please use the [GitHub Issues](../../issues) page.

## Roadmap

- [ ] STM32 project support
- [ ] Integrated compiler
- [ ] Hardware debugger integration
- [ ] Plugin system
- [ ] Git integration
- [ ] Multi-platform support (Linux, macOS)

## Credits

Developed by the Taara MCU team for embedded systems developers.
\`\`\`

```text file="LICENSE"
MIT License

Copyright (c) 2025 Taara MCU

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

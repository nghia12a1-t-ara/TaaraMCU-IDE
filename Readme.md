# Build Your Own IDE

This project focuses on creating a Text Editor and Debugger for Microcontrollers. This tool is based on the Python QsciScintilla Library.

## Project Structure

taara_debugger/
│
├── src/
│   ├── __init__.py
│   ├── main.py              # Main application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py      # Application settings and constants
│   │   └── themes.py        # Theme definitions
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py   # MainWindow class
│   │   ├── editor.py        # CodeEditor class
│   │   └── dialogs/
│   │       ├── __init__.py
│   │       └── find_dialog.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_handler.py   # File operations
│       └── session.py        # Session management
│
├── resources/
│   ├── icons/
│   │   ├── logoIcon.ico
│   │   └── close.png
│   └── themes/
│       └── khaki.json
│
├── backups/                  # Directory for unsaved file backups
│
├── Terminal.py               # Basic console implementation
├── QTerminalWidget.py        # Advanced terminal using QTermWidget
├── build_qtermwidget.py      # Script to build QTermWidget
├── QTermWidget_README.md     # Instructions for QTermWidget integration
│
└── README.md

## Features

- Syntax highlighting for multiple languages
- Code folding
- Line numbering
- Find and replace functionality
- Project explorer
- Function list
- Integrated terminal with command execution
- Advanced terminal with QTermWidget integration (full terminal emulation)

## Terminal Integration

The IDE now supports two types of terminals:

1. **Basic Console (Terminal.py)**: A simple console implementation that can execute commands and display output.
2. **QTermWidget Terminal (QTerminalWidget.py)**: A full terminal emulation using QTermWidget, providing a complete command prompt experience.

To use the QTermWidget terminal, you need to build the QTermWidget module first. See `QTermWidget_README.md` for instructions.
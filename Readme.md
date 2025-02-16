Build own IDE (focus on Text Editor and Debugger) for Microcontrollers. This tools based on the Python QsciScintilla Library

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
└── README.md
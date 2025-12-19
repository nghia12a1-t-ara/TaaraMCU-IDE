"""
Terminal Color Configuration - UI for customizing terminal log colors.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QColorDialog, QWidget,
    QScrollArea, QMessageBox
)
from PyQt6.QtCore import pyqtSignal as Signal, QSettings
from PyQt6.QtGui import QColor, QPalette
from typing import Dict


class ColorButton(QPushButton):
    """Button that displays and allows selection of a color."""
    
    color_changed = Signal(QColor)
    
    def __init__(self, initial_color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self._color = QColor(initial_color)
        self.setMinimumSize(80, 30)
        self.clicked.connect(self._choose_color)
        self._update_style()
    
    def _choose_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self._color, self, "Select Color")
        if color.isValid():
            self._color = color
            self._update_style()
            self.color_changed.emit(color)
    
    def _update_style(self):
        """Update button style to show current color."""
        # Calculate if color is dark for text color
        is_dark = (self._color.red() * 0.299 + 
                   self._color.green() * 0.587 + 
                   self._color.blue() * 0.114) < 128
        text_color = "#FFFFFF" if is_dark else "#000000"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                color: {text_color};
                border: 2px solid #4C4C4C;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: #007ACC;
            }}
        """)
        self.setText(self._color.name())
    
    def get_color(self) -> QColor:
        """Get current color."""
        return self._color
    
    def set_color(self, color: QColor):
        """Set color."""
        self._color = color
        self._update_style()


class TerminalColorConfig(QDialog):
    """
    Dialog for configuring terminal log colors.
    
    Signals:
        colors_changed: Emitted when colors are applied (color_dict)
    """
    
    colors_changed = Signal(dict)
    
    # Default color schemes
    DEFAULT_SCHEMES = {
        "Default Dark": {
            "background": "#1E1E1E",
            "text": "#D4D4D4",
            "prompt_path": "#569CD6",
            "prompt_symbol": "#DCDCAA",
            "command": "#98C379",
            "error": "#F44747",
            "warning": "#FFCC00",
            "success": "#4EC9B0",
            "info": "#D4D4D4",
            "debug": "#9CDCFE",
        },
        "Light Theme": {
            "background": "#FFFFFF",
            "text": "#000000",
            "prompt_path": "#0000FF",
            "prompt_symbol": "#FF8C00",
            "command": "#008000",
            "error": "#FF0000",
            "warning": "#FFA500",
            "success": "#00CED1",
            "info": "#404040",
            "debug": "#4169E1",
        },
        "Monokai": {
            "background": "#272822",
            "text": "#F8F8F2",
            "prompt_path": "#66D9EF",
            "prompt_symbol": "#F92672",
            "command": "#A6E22E",
            "error": "#F92672",
            "warning": "#E6DB74",
            "success": "#66D9EF",
            "info": "#F8F8F2",
            "debug": "#AE81FF",
        },
        "Solarized Dark": {
            "background": "#002B36",
            "text": "#839496",
            "prompt_path": "#268BD2",
            "prompt_symbol": "#B58900",
            "command": "#859900",
            "error": "#DC322F",
            "warning": "#CB4B16",
            "success": "#2AA198",
            "info": "#839496",
            "debug": "#6C71C4",
        },
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminal Color Configuration")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._color_buttons: Dict[str, ColorButton] = {}
        self._settings = QSettings('TaaraIDE', 'Terminal')
        
        self._setup_ui()
        self._load_colors()
    
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Customize Terminal Colors")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; padding: 8px;")
        layout.addWidget(header)
        
        # Scheme selector
        scheme_layout = QHBoxLayout()
        scheme_layout.addWidget(QLabel("Preset Schemes:"))
        
        for scheme_name in self.DEFAULT_SCHEMES.keys():
            btn = QPushButton(scheme_name)
            btn.clicked.connect(lambda checked, name=scheme_name: self._apply_scheme(name))
            scheme_layout.addWidget(btn)
        
        scheme_layout.addStretch()
        layout.addLayout(scheme_layout)
        
        # Scroll area for color options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)
        
        colors_widget = QWidget()
        colors_layout = QGridLayout(colors_widget)
        colors_layout.setSpacing(12)
        
        # Define color categories
        color_options = [
            ("background", "Background", "Main terminal background color"),
            ("text", "Text", "Default text color"),
            ("prompt_path", "Prompt Path", "Current directory path in prompt"),
            ("prompt_symbol", "Prompt Symbol", "Prompt symbol (>>>)"),
            ("command", "Command", "Executed commands"),
            ("error", "Error", "Error messages"),
            ("warning", "Warning", "Warning messages"),
            ("success", "Success", "Success messages"),
            ("info", "Info", "Information messages"),
            ("debug", "Debug", "Debug messages"),
        ]
        
        row = 0
        for key, label, description in color_options:
            # Label
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold; color: #FFFFFF;")
            colors_layout.addWidget(label_widget, row, 0)
            
            # Color button
            color_btn = ColorButton()
            self._color_buttons[key] = color_btn
            colors_layout.addWidget(color_btn, row, 1)
            
            # Description
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #AAAAAA; font-size: 10px;")
            colors_layout.addWidget(desc_label, row, 2)
            
            row += 1
        
        scroll.setWidget(colors_widget)
        layout.addWidget(scroll)
        
        # Preview
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        layout.addWidget(preview_label)
        
        self._preview = QLabel("""
D:\\Projects\\MyApp >>> git status
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  modified:   src/main.c

[INFO] Build completed successfully
[ERROR] Failed to connect to database
[WARNING] Deprecated API usage detected
[DEBUG] Processing 1000 records...
        """)
        self._preview.setStyleSheet("""
            QLabel {
                background-color: #1E1E1E;
                color: #D4D4D4;
                padding: 12px;
                border: 1px solid #4C4C4C;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        layout.addWidget(self._preview)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_colors)
        button_layout.addWidget(apply_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._ok_clicked)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        # Style dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
            }
            QLabel {
                color: #CCCCCC;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QScrollArea {
                border: 1px solid #4C4C4C;
                border-radius: 4px;
                background-color: #252526;
            }
        """)
        
        # Connect color changes to preview update
        for btn in self._color_buttons.values():
            btn.color_changed.connect(self._update_preview)
    
    def _apply_scheme(self, scheme_name: str):
        """Apply a preset color scheme."""
        if scheme_name not in self.DEFAULT_SCHEMES:
            return
        
        scheme = self.DEFAULT_SCHEMES[scheme_name]
        for key, color_hex in scheme.items():
            if key in self._color_buttons:
                self._color_buttons[key].set_color(QColor(color_hex))
        
        self._update_preview()
    
    def _reset_to_defaults(self):
        """Reset colors to default scheme."""
        self._apply_scheme("Default Dark")
    
    def _load_colors(self):
        """Load colors from settings."""
        # Try to load saved colors, otherwise use defaults
        scheme = self.DEFAULT_SCHEMES["Default Dark"]
        
        for key in self._color_buttons.keys():
            saved_color = self._settings.value(f"color_{key}", scheme.get(key, "#FFFFFF"))
            self._color_buttons[key].set_color(QColor(saved_color))
        
        self._update_preview()
    
    def _save_colors(self):
        """Save colors to settings."""
        for key, btn in self._color_buttons.items():
            self._settings.setValue(f"color_{key}", btn.get_color().name())
    
    def _get_color_dict(self) -> Dict[str, str]:
        """Get current colors as dictionary."""
        return {key: btn.get_color().name() for key, btn in self._color_buttons.items()}
    
    def _apply_colors(self):
        """Apply current colors."""
        colors = self._get_color_dict()
        self.colors_changed.emit(colors)
        self._save_colors()
    
    def _ok_clicked(self):
        """Handle OK button click."""
        self._apply_colors()
        self.accept()
    
    def _update_preview(self):
        """Update preview with current colors."""
        colors = self._get_color_dict()
        
        # Update preview background and text
        self._preview.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['background']};
                color: {colors['text']};
                padding: 12px;
                border: 1px solid #4C4C4C;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }}
        """)
        
        # Create preview HTML with colored text
        preview_html = f"""
<span style="color: {colors['prompt_path']};">D:\\Projects\\MyApp</span>
<span style="color: {colors['prompt_symbol']};">&gt;&gt;&gt;</span>
<span style="color: {colors['command']};">git status</span><br>
<span style="color: {colors['info']};">On branch main<br>
Your branch is up to date with 'origin/main'.<br><br>
Changes not staged for commit:<br>
  modified:   src/main.c</span><br><br>
<span style="color: {colors['info']};">[INFO] Build completed successfully</span><br>
<span style="color: {colors['error']};">[ERROR] Failed to connect to database</span><br>
<span style="color: {colors['warning']};">[WARNING] Deprecated API usage detected</span><br>
<span style="color: {colors['debug']};">[DEBUG] Processing 1000 records...</span>
        """
        
        self._preview.setText(preview_html)
    
    @staticmethod
    def get_colors_from_settings() -> Dict[str, str]:
        """Get saved colors from settings (static method)."""
        settings = QSettings('TaaraIDE', 'Terminal')
        default_scheme = TerminalColorConfig.DEFAULT_SCHEMES["Default Dark"]
        
        colors = {}
        for key in default_scheme.keys():
            colors[key] = settings.value(f"color_{key}", default_scheme[key])
        
        return colors

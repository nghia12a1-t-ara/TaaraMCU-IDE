"""
Taara IDE - Main Entry Point
"""
import sys
import os

os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false;qt.text.font.db=false"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Absolute imports
from taara_ide.ui.main_window import MainWindow

def main():
    """Main application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Taara IDE")
    app.setOrganizationName("Taara")
    app.setApplicationVersion("1.0.0")
    
    from PyQt6.QtGui import QFont
    default_font = QFont()
    default_font.setStyleHint(QFont.StyleHint.SansSerif)
    default_font.setFamily("Segoe UI")
    app.setFont(default_font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

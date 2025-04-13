"""
Taara IDE - Main Entry Point
"""
import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Absolute imports
from taara_ide.config import SettingsManager
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
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

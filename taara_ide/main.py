"""
Taara IDE - Main Entry Point
"""
import sys
import os

os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false;qt.text.font.db=false"

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QColor, QFont, QPainter
from PyQt6.QtCore import Qt


def _make_splash(app_version: str) -> QSplashScreen:
    """Create a simple programmatic splash screen (no image file needed)."""
    w, h = 480, 280
    pix = QPixmap(w, h)
    pix.fill(QColor("#1e1e2e"))

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Accent bar at top
    painter.fillRect(0, 0, w, 5, QColor("#007ACC"))

    # App name
    title_font = QFont("Segoe UI", 28, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.setPen(QColor("#e0e0e0"))
    painter.drawText(0, 60, w, 50, Qt.AlignmentFlag.AlignHCenter, "Taara IDE")

    # Subtitle
    sub_font = QFont("Segoe UI", 11)
    painter.setFont(sub_font)
    painter.setPen(QColor("#888"))
    painter.drawText(0, 115, w, 30, Qt.AlignmentFlag.AlignHCenter,
                     "Embedded Development Environment")

    # Version
    ver_font = QFont("Segoe UI", 9)
    painter.setFont(ver_font)
    painter.setPen(QColor("#555"))
    painter.drawText(0, h - 30, w, 20, Qt.AlignmentFlag.AlignHCenter,
                     f"v{app_version}")

    # Loading text (bottom-left)
    painter.setPen(QColor("#555"))
    painter.setFont(ver_font)
    painter.drawText(16, h - 30, w, 20, Qt.AlignmentFlag.AlignLeft, "Loading…")

    painter.end()

    splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setFont(QFont("Segoe UI", 9))
    return splash


def main():
    """Main application entry point."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Taara IDE")
    app.setOrganizationName("Taara")
    app.setApplicationVersion("1.0.0")

    default_font = QFont()
    default_font.setStyleHint(QFont.StyleHint.SansSerif)
    default_font.setFamily("Segoe UI")
    app.setFont(default_font)

    # Show splash immediately — user sees something while imports load
    splash = _make_splash("1.0.0")
    splash.show()
    app.processEvents()

    # Heavy import happens here, splash is already visible
    from taara_ide.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    splash.finish(window)   # closes splash once main window is ready

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

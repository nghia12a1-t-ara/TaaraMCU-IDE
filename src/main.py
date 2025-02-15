from PyQt6.QtWidgets import QApplication
import sys
from pathlib import Path
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # Ensure the application directories exist
    app_dir = Path(__file__).parent.parent
    (app_dir / "backups").mkdir(exist_ok=True)
    
    main() 
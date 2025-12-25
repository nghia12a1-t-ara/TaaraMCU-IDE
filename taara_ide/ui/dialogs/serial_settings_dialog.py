from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QPushButton, QLabel, QCheckBox, QSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtSerialPort import QSerialPortInfo


class SerialSettingsDialog(QDialog):
    """Dialog for configuring serial port settings."""
    
    settings_changed = pyqtSignal(dict)  # Emits settings dictionary
    
    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Port Settings")
        self.setMinimumWidth(400)
        self._current_settings = current_settings
        self._setup_ui()
        self._load_settings()
        parent._port_combo = self._port_combo  # Fix for terminal panel access issue
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Port Configuration Group
        port_group = QGroupBox("Port Configuration")
        port_layout = QFormLayout()
        
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(250)
        self._refresh_ports()
        port_layout.addRow("Port:", self._port_combo)
        
        refresh_btn = QPushButton("Refresh Ports")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addRow("", refresh_btn)
        
        self._baud_combo = QComboBox()
        self._baud_combo.addItems([
            "9600", "19200", "38400", "57600", 
            "115200", "230400", "460800", "921600"
        ])
        port_layout.addRow("Baud Rate:", self._baud_combo)
        
        self._data_bits_combo = QComboBox()
        self._data_bits_combo.addItems(["5", "6", "7", "8"])
        self._data_bits_combo.setCurrentText("8")
        port_layout.addRow("Data Bits:", self._data_bits_combo)
        
        self._parity_combo = QComboBox()
        self._parity_combo.addItems(["None", "Even", "Odd", "Space", "Mark"])
        port_layout.addRow("Parity:", self._parity_combo)
        
        self._stop_bits_combo = QComboBox()
        self._stop_bits_combo.addItems(["1", "1.5", "2"])
        port_layout.addRow("Stop Bits:", self._stop_bits_combo)
        
        port_group.setLayout(port_layout)
        layout.addWidget(port_group)
        
        # Options Group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self._auto_reconnect_check = QCheckBox("Auto-reconnect on disconnect")
        options_layout.addWidget(self._auto_reconnect_check)
        
        self._hex_view_check = QCheckBox("Display data in hexadecimal format")
        options_layout.addWidget(self._hex_view_check)
        
        self._timestamp_check = QCheckBox("Show timestamps")
        self._timestamp_check.setChecked(True)
        options_layout.addWidget(self._timestamp_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply_settings)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
                color: #CCCCCC;
            }
            QGroupBox {
                border: 1px solid #4C4C4C;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #CCCCCC;
            }
            QComboBox {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #4C4C4C;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QComboBox:hover {
                border-color: #007ACC;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2D2D;
                color: #CCCCCC;
                selection-background-color: #007ACC;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QCheckBox {
                color: #CCCCCC;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #4C4C4C;
                border-radius: 3px;
                background-color: #3C3C3C;
            }
            QCheckBox::indicator:checked {
                background-color: #007ACC;
                border-color: #007ACC;
            }
        """)
    
    def _refresh_ports(self):
        """Refresh available serial ports."""
        self._port_combo.clear()
        ports = QSerialPortInfo.availablePorts()
        
        if not ports:
            self._port_combo.addItem("No COM Port")
            self._port_combo.setEnabled(False)
        else:
            self._port_combo.setEnabled(True)
            for port in ports:
                display_text = f"{port.portName()} - {port.description()}"
                self._port_combo.addItem(display_text, port.portName())
    
    def _load_settings(self):
        """Load current settings into dialog."""
        if 'port' in self._current_settings:
            index = self._port_combo.findData(self._current_settings['port'])
            if index >= 0:
                self._port_combo.setCurrentIndex(index)
        
        if 'baud_rate' in self._current_settings:
            self._baud_combo.setCurrentText(str(self._current_settings['baud_rate']))
        else:
            self._baud_combo.setCurrentText("115200")
            
        self._auto_reconnect_check.setChecked(
            self._current_settings.get('auto_reconnect', False)
        )
        self._hex_view_check.setChecked(
            self._current_settings.get('hex_view', False)
        )
        self._timestamp_check.setChecked(
            self._current_settings.get('show_timestamps', True)
        )
    
    def _apply_settings(self):
        """Apply and emit settings."""
        settings = {
            'port': self._port_combo.currentData(),
            'baud_rate': int(self._baud_combo.currentText()),
            'data_bits': int(self._data_bits_combo.currentText()),
            'parity': self._parity_combo.currentText(),
            'stop_bits': float(self._stop_bits_combo.currentText()),
            'auto_reconnect': self._auto_reconnect_check.isChecked(),
            'hex_view': self._hex_view_check.isChecked(),
            'show_timestamps': self._timestamp_check.isChecked(),
        }
        self.settings_changed.emit(settings)
        self.accept()
    
    def get_settings(self) -> dict:
        """Get current settings from dialog."""
        return {
            'port': self._port_combo.currentData(),
            'baud_rate': int(self._baud_combo.currentText()),
            'data_bits': int(self._data_bits_combo.currentText()),
            'parity': self._parity_combo.currentText(),
            'stop_bits': float(self._stop_bits_combo.currentText()),
            'auto_reconnect': self._auto_reconnect_check.isChecked(),
            'hex_view': self._hex_view_check.isChecked(),
            'show_timestamps': self._timestamp_check.isChecked(),
        }

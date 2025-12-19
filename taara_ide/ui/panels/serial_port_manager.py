"""
Serial Port Manager - Handles COM port communication using QtSerialPort.
"""

from PyQt6.QtCore import QObject, QIODevice, pyqtSignal as Signal
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from typing import Optional, List, Dict


class SerialPortManager(QObject):
    """
    Manages serial port connections and communication.
    
    Signals:
        data_received: Emitted when data is received (bytes)
        error_occurred: Emitted when an error occurs (error_message: str)
        connection_changed: Emitted when connection status changes (is_connected: bool)
        port_list_updated: Emitted when available ports list changes
    """
    
    data_received = Signal(bytes)
    error_occurred = Signal(str)
    connection_changed = Signal(bool)
    port_list_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial_port: Optional[QSerialPort] = None
        self._is_connected = False
        
    def get_available_ports(self) -> List[Dict[str, str]]:
        """
        Get list of available serial ports.
        
        Returns:
            List of dicts with 'name', 'description', 'manufacturer' keys
        """
        ports = []
        for port_info in QSerialPortInfo.availablePorts():
            ports.append({
                'name': port_info.portName(),
                'description': port_info.description(),
                'manufacturer': port_info.manufacturer() or 'Unknown',
                'system_location': port_info.systemLocation(),
            })
        return ports
    
    def connect_port(self, 
                     port_name: str,
                     baud_rate: int = 115200,
                     data_bits: QSerialPort.DataBits = QSerialPort.DataBits.Data8,
                     parity: QSerialPort.Parity = QSerialPort.Parity.NoParity,
                     stop_bits: QSerialPort.StopBits = QSerialPort.StopBits.OneStop,
                     flow_control: QSerialPort.FlowControl = QSerialPort.FlowControl.NoFlowControl) -> bool:
        """
        Connect to a serial port with specified settings.
        
        Args:
            port_name: Name of the port (e.g., 'COM3', '/dev/ttyUSB0')
            baud_rate: Baud rate (default: 115200)
            data_bits: Data bits (default: 8)
            parity: Parity (default: None)
            stop_bits: Stop bits (default: 1)
            flow_control: Flow control (default: None)
            
        Returns:
            True if connection successful, False otherwise
        """
        # Disconnect if already connected
        if self._is_connected:
            self.disconnect_port()
        
        # Create serial port
        self._serial_port = QSerialPort()
        self._serial_port.setPortName(port_name)
        self._serial_port.setBaudRate(baud_rate)
        self._serial_port.setDataBits(data_bits)
        self._serial_port.setParity(parity)
        self._serial_port.setStopBits(stop_bits)
        self._serial_port.setFlowControl(flow_control)
        
        # Connect signals
        self._serial_port.readyRead.connect(self._on_ready_read)
        self._serial_port.errorOccurred.connect(self._on_error_occurred)
        
        # Open port
        if self._serial_port.open(QIODevice.OpenModeFlag.ReadWrite):
            self._is_connected = True
            self.connection_changed.emit(True)
            return True
        else:
            error = self._serial_port.errorString()
            self.error_occurred.emit(f"Failed to open port {port_name}: {error}")
            self._serial_port = None
            return False
    
    def disconnect_port(self):
        """Disconnect from the current serial port."""
        if self._serial_port and self._serial_port.isOpen():
            self._serial_port.close()
            self._serial_port.deleteLater()
            self._serial_port = None
            self._is_connected = False
            self.connection_changed.emit(False)
    
    def send_data(self, data: bytes) -> bool:
        """
        Send data through the serial port.
        
        Args:
            data: Bytes to send
            
        Returns:
            True if data sent successfully, False otherwise
        """
        if not self._is_connected or not self._serial_port:
            self.error_occurred.emit("Not connected to any port")
            return False
        
        try:
            bytes_written = self._serial_port.write(data)
            if bytes_written == -1:
                self.error_occurred.emit("Failed to write data")
                return False
            
            # Wait for data to be written
            if not self._serial_port.waitForBytesWritten(1000):
                self.error_occurred.emit("Timeout writing data")
                return False
            
            return True
        except Exception as e:
            self.error_occurred.emit(f"Error sending data: {str(e)}")
            return False
    
    def send_text(self, text: str, encoding: str = 'utf-8', line_ending: str = '\n') -> bool:
        """
        Send text through the serial port.
        
        Args:
            text: Text to send
            encoding: Text encoding (default: 'utf-8')
            line_ending: Line ending to append (default: '\n')
            
        Returns:
            True if text sent successfully, False otherwise
        """
        data = (text + line_ending).encode(encoding)
        return self.send_data(data)
    
    def is_connected(self) -> bool:
        """Check if currently connected to a port."""
        return self._is_connected
    
    def get_port_name(self) -> Optional[str]:
        """Get the name of the currently connected port."""
        if self._serial_port:
            return self._serial_port.portName()
        return None
    
    def get_settings(self) -> Optional[Dict]:
        """Get current port settings."""
        if not self._serial_port:
            return None
        
        return {
            'port_name': self._serial_port.portName(),
            'baud_rate': self._serial_port.baudRate(),
            'data_bits': self._serial_port.dataBits(),
            'parity': self._serial_port.parity(),
            'stop_bits': self._serial_port.stopBits(),
            'flow_control': self._serial_port.flowControl(),
        }
    
    # Private methods
    
    def _on_ready_read(self):
        """Handle incoming data."""
        if self._serial_port:
            data = self._serial_port.readAll()
            if data:
                self.data_received.emit(bytes(data))
    
    def _on_error_occurred(self, error: QSerialPort.SerialPortError):
        """Handle serial port errors."""
        if error == QSerialPort.SerialPortError.NoError:
            return
        
        if error == QSerialPort.SerialPortError.ResourceError:
            # Port was disconnected
            error_msg = "Port disconnected"
            self.disconnect_port()
        else:
            error_msg = self._serial_port.errorString() if self._serial_port else "Unknown error"
        
        self.error_occurred.emit(f"Serial port error: {error_msg}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.disconnect_port()

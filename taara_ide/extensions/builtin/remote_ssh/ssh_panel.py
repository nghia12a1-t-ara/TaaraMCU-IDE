"""
SshPanel — sidebar panel widget for the Remote SSH extension.

Layout:
  ┌─────────────────────────────────┐
  │  REMOTE SSH                     │
  │  ┌───────────────────────────┐  │
  │  │ user@host:22  [Connect]   │  │  ← connection bar
  │  └───────────────────────────┘  │
  │  [status: disconnected]         │
  │  ─────────────────────────────  │
  │  Remote Explorer (tree)         │  ← file tree (shown when connected)
  └─────────────────────────────────┘
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal as Signal, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QSizePolicy,
    QDialog, QFormLayout, QDialogButtonBox, QSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QProgressBar,
)

if TYPE_CHECKING:
    from taara_ide.extensions.builtin.remote_ssh.ssh_session import SshConnectWorker


# ─────────────────────────────────────────────────────────────────────────────
class ConnectDialog(QDialog):
    """Modal dialog to collect SSH connection details."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to SSH Host")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("192.168.1.100")
        layout.addRow("Host:", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        layout.addRow("Port:", self.port_spin)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("username")
        layout.addRow("User:", self.user_edit)

        self.key_check = QCheckBox("Use private key")
        self.key_check.toggled.connect(self._toggle_auth)
        layout.addRow("", self.key_check)

        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("password")
        layout.addRow("Password:", self.pass_edit)

        self.key_row = QWidget()
        key_layout = QHBoxLayout(self.key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("~/.ssh/id_rsa")
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(28)
        browse_btn.clicked.connect(self._browse_key)
        key_layout.addWidget(self.key_edit)
        key_layout.addWidget(browse_btn)
        self.key_row.setVisible(False)
        layout.addRow("Key file:", self.key_row)

        self.remote_dir_edit = QLineEdit()
        self.remote_dir_edit.setPlaceholderText("/home/user/project")
        layout.addRow("Remote folder:", self.remote_dir_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _toggle_auth(self, use_key: bool):
        self.pass_edit.setVisible(not use_key)
        self.key_row.setVisible(use_key)

    def _browse_key(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select private key",
            os.path.expanduser("~/.ssh"), "All files (*)"
        )
        if path:
            self.key_edit.setText(path)

    def get_params(self) -> dict:
        return {
            "host":       self.host_edit.text().strip(),
            "port":       self.port_spin.value(),
            "username":   self.user_edit.text().strip(),
            "password":   self.pass_edit.text() if not self.key_check.isChecked() else "",
            "key_path":   self.key_edit.text().strip() if self.key_check.isChecked() else "",
            "remote_dir": self.remote_dir_edit.text().strip() or "/",
        }


# ─────────────────────────────────────────────────────────────────────────────
class SshPanel(QWidget):
    """Sidebar panel contributed by the Remote SSH extension."""

    # Signals forwarded to the extension
    open_remote_file = Signal(str, str)   # remote_path, content
    run_remote_cmd   = Signal(str)        # command string

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session: Optional["SshConnectWorker"] = None
        self._remote_dir = "/"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # ── Title + connect button ────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel("REMOTE SSH")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        top.addWidget(title)
        top.addStretch()

        self.connect_btn = QPushButton("Connect…")
        self.connect_btn.setFixedWidth(84)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        top.addWidget(self.connect_btn)
        layout.addLayout(top)

        # ── Status bar ───────────────────────────────────────────────
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # ── File tree (hidden until connected) ───────────────────────
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setVisible(False)
        layout.addWidget(self.tree)

        # ── Disconnect button ────────────────────────────────────────
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setVisible(False)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        layout.addWidget(self.disconnect_btn)

    # ------------------------------------------------------------------ #
    # Connection flow
    # ------------------------------------------------------------------ #

    def _on_connect_clicked(self):
        dlg = ConnectDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        params = dlg.get_params()
        if not params["host"] or not params["username"]:
            QMessageBox.warning(self, "Remote SSH", "Host and username are required.")
            return

        self._remote_dir = params["remote_dir"]
        self._start_connection(params)

    def _start_connection(self, params: dict):
        from taara_ide.extensions.builtin.remote_ssh.ssh_session import (
            SshConnectWorker, _PARAMIKO_OK
        )
        if not _PARAMIKO_OK:
            QMessageBox.critical(
                self, "Remote SSH",
                "paramiko is not installed.\n\nRun:  pip install paramiko"
            )
            return

        self.status_label.setText(f"Connecting to {params['host']}…")
        self.progress.setVisible(True)
        self.progress.setValue(30)
        self.connect_btn.setEnabled(False)

        worker = SshConnectWorker(
            host=params["host"], port=params["port"],
            username=params["username"],
            password=params.get("password", ""),
            key_path=params.get("key_path", ""),
            parent=self,
        )
        worker.connected.connect(lambda: self._on_connected(worker))
        worker.failed.connect(self._on_connect_failed)
        self._session = worker
        worker.start()

    def _on_connected(self, worker: "SshConnectWorker"):
        self.progress.setValue(100)
        QTimer.singleShot(400, lambda: self.progress.setVisible(False))

        host = worker.host
        self.status_label.setText(f"Connected: {worker.username}@{host}")
        self.status_label.setStyleSheet("color: #5a5; font-size: 11px;")
        self.connect_btn.setVisible(False)
        self.disconnect_btn.setVisible(True)
        self.tree.setVisible(True)
        self._load_remote_dir(self._remote_dir, None)

    def _on_connect_failed(self, message: str):
        self.progress.setVisible(False)
        self.connect_btn.setEnabled(True)
        self.status_label.setText("Connection failed")
        self.status_label.setStyleSheet("color: #a55; font-size: 11px;")
        QMessageBox.warning(self, "SSH Connection Failed", message)

    def _on_disconnect(self):
        if self._session:
            self._session.close()
            self._session = None
        self.tree.clear()
        self.tree.setVisible(False)
        self.connect_btn.setVisible(True)
        self.disconnect_btn.setVisible(False)
        self.status_label.setText("Not connected")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")

    # ------------------------------------------------------------------ #
    # Remote file tree
    # ------------------------------------------------------------------ #

    def _load_remote_dir(self, path: str, parent_item: Optional[QTreeWidgetItem]):
        if not self._session:
            return
        entries = self._session.list_dir(path)
        target = parent_item or self.tree.invisibleRootItem()

        # Clear existing children (for refresh)
        while target.childCount():
            target.removeChild(target.child(0))

        for entry in entries:
            item = QTreeWidgetItem([entry["name"]])
            full_path = path.rstrip("/") + "/" + entry["name"]
            item.setData(0, Qt.ItemDataRole.UserRole, full_path)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, entry["is_dir"])
            if entry["is_dir"]:
                item.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                )
            target.addChild(item)

    def _on_item_expanded(self, item: QTreeWidgetItem):
        is_dir = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if is_dir and item.childCount() == 0:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            self._load_remote_dir(path, item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _col: int):
        is_dir = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if is_dir:
            return
        if not self._session:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        content = self._session.read_file(path)
        if content is not None:
            self.open_remote_file.emit(path, content)

    # ------------------------------------------------------------------ #
    # Public API used by the extension
    # ------------------------------------------------------------------ #

    def save_remote_file(self, remote_path: str, content: str) -> bool:
        if self._session:
            return self._session.write_file(remote_path, content)
        return False

    def exec_remote(self, command: str,
                    on_output, on_done) -> None:
        if self._session:
            self._session.exec_command(command, on_output, on_done)

    @property
    def is_connected(self) -> bool:
        return self._session is not None and self._session._client is not None

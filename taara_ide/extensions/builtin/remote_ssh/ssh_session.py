"""
SshSession — wraps paramiko SSH + SFTP in a background QThread.

Signals are used for all cross-thread communication so the UI
is never blocked by network I/O.

Requirements: paramiko  (pip install paramiko)
"""

from __future__ import annotations

import io
import logging
import os
import stat
from typing import Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal as Signal

log = logging.getLogger(__name__)

try:
    import paramiko
    _PARAMIKO_OK = True
except ImportError:
    _PARAMIKO_OK = False


class SshConnectWorker(QThread):
    """Opens the SSH connection in a background thread."""

    connected    = Signal()
    failed       = Signal(str)      # error message
    output       = Signal(str)      # stdout/stderr from commands

    def __init__(self, host: str, port: int, username: str,
                 password: str = "", key_path: str = "", parent=None):
        super().__init__(parent)
        self.host      = host
        self.port      = port
        self.username  = username
        self.password  = password
        self.key_path  = key_path

        self._client: Optional["paramiko.SSHClient"] = None
        self._sftp:   Optional["paramiko.SFTPClient"]  = None

    # ------------------------------------------------------------------ #
    def run(self):
        if not _PARAMIKO_OK:
            self.failed.emit(
                "paramiko is not installed.\n"
                "Run: pip install paramiko"
            )
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            connect_kwargs: dict = {
                "hostname": self.host,
                "port":     self.port,
                "username": self.username,
                "timeout":  10,
            }
            if self.key_path and os.path.isfile(self.key_path):
                connect_kwargs["key_filename"] = self.key_path
            elif self.password:
                connect_kwargs["password"] = self.password

            client.connect(**connect_kwargs)
            self._client = client
            self._sftp   = client.open_sftp()
            self.connected.emit()

        except Exception as exc:
            self.failed.emit(str(exc))
            try:
                client.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Convenience methods — call from main thread after connected()
    # ------------------------------------------------------------------ #

    def exec_command(self, command: str,
                     on_output: Callable[[str], None],
                     on_done: Callable[[int], None]) -> None:
        """Fire-and-forget: runs *command* in a daemon thread."""
        if not self._client:
            return

        def _run():
            try:
                _, stdout, stderr = self._client.exec_command(command, get_pty=True)
                for line in stdout:
                    on_output(line)
                for line in stderr:
                    on_output(line)
                rc = stdout.channel.recv_exit_status()
                on_done(rc)
            except Exception as exc:
                on_output(f"[SSH error] {exc}\n")
                on_done(-1)

        import threading
        threading.Thread(target=_run, daemon=True).start()

    # SFTP helpers -------------------------------------------------------

    def read_file(self, remote_path: str) -> Optional[str]:
        if not self._sftp:
            return None
        try:
            with self._sftp.open(remote_path, "r") as fh:
                return fh.read().decode("utf-8", errors="replace")
        except Exception as exc:
            log.warning("[SSH] read_file %s: %s", remote_path, exc)
            return None

    def write_file(self, remote_path: str, content: str) -> bool:
        if not self._sftp:
            return False
        try:
            with self._sftp.open(remote_path, "w") as fh:
                fh.write(content.encode("utf-8"))
            return True
        except Exception as exc:
            log.warning("[SSH] write_file %s: %s", remote_path, exc)
            return False

    def list_dir(self, remote_path: str) -> list[dict]:
        """Returns list of {name, size, is_dir, mtime} dicts."""
        if not self._sftp:
            return []
        try:
            entries = []
            for attr in self._sftp.listdir_attr(remote_path):
                entries.append({
                    "name":   attr.filename,
                    "size":   attr.st_size or 0,
                    "is_dir": stat.S_ISDIR(attr.st_mode or 0),
                    "mtime":  attr.st_mtime or 0,
                })
            return sorted(entries, key=lambda e: (not e["is_dir"], e["name"].lower()))
        except Exception as exc:
            log.warning("[SSH] list_dir %s: %s", remote_path, exc)
            return []

    def close(self) -> None:
        try:
            if self._sftp:
                self._sftp.close()
            if self._client:
                self._client.close()
        except Exception:
            pass
        self._sftp   = None
        self._client = None

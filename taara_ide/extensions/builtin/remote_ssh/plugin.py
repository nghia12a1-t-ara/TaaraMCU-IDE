"""
Remote SSH extension — plugin.py entry point.

Contributes:
  • A sidebar panel (SshPanel) with file explorer + connect dialog
  • Opens remote files as virtual tabs in the IDE editor
  • Saves modified remote files back via SFTP on Ctrl+S
"""

from __future__ import annotations

import logging
import os
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

from taara_ide.extensions.extension_base import (
    ExtensionBase, ExtensionInfo, ExtensionCategory
)

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow

log = logging.getLogger(__name__)

# Remote files opened in the editor are tracked as  remote_path → editor widget
_REMOTE_PREFIX = "[SSH] "


class Plugin(ExtensionBase):
    """Remote SSH extension."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panel: Optional["SshPanel"] = None    # imported lazily
        self._main_window: Optional["MainWindow"] = None
        # Map  remote_path → editor  for open remote files
        self._remote_editors: dict = {}

    # ------------------------------------------------------------------ #
    # ExtensionBase interface
    # ------------------------------------------------------------------ #

    @property
    def info(self) -> ExtensionInfo:
        manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
        try:
            return ExtensionInfo.from_manifest(manifest_path)
        except Exception:
            return ExtensionInfo(
                id="remote-ssh",
                name="Remote SSH",
                version="1.0.0",
                description="Open remote folders via SSH.",
                category=ExtensionCategory.REMOTE,
            )

    def activate(self, main_window: "MainWindow") -> bool:
        self._main_window = main_window

        # Import panel here so paramiko import error is caught gracefully
        try:
            from taara_ide.extensions.builtin.remote_ssh.ssh_panel import SshPanel
        except Exception as exc:
            log.error("[RemoteSSH] Failed to import SshPanel: %s", exc)
            return False

        self._panel = SshPanel()
        self._panel.open_remote_file.connect(self._on_open_remote_file)

        # Forward remote terminal output to IDE terminal if available
        if hasattr(main_window, '_terminal') and main_window._terminal:
            pass  # terminal integration hooked per-command in exec_remote

        # Connect IDE save signal so we can intercept remote-file saves
        if hasattr(main_window, '_editor_manager'):
            em = main_window._editor_manager
            em.file_saved.connect(self._on_file_saved)

        log.info("[RemoteSSH] Activated")
        return True

    def deactivate(self) -> None:
        if self._panel and self._panel.is_connected:
            self._panel._on_disconnect()

        if self._main_window and hasattr(self._main_window, '_editor_manager'):
            try:
                self._main_window._editor_manager.file_saved.disconnect(self._on_file_saved)
            except RuntimeError:
                pass

        self._remote_editors.clear()
        log.info("[RemoteSSH] Deactivated")

    def get_panel_widget(self) -> Optional[QWidget]:
        return self._panel

    # ------------------------------------------------------------------ #
    # Remote file handling
    # ------------------------------------------------------------------ #

    def _on_open_remote_file(self, remote_path: str, content: str) -> None:
        """Create an editor tab with the remote file content."""
        if not self._main_window:
            return
        em = self._main_window._editor_manager

        # Use a display name like "[SSH] /home/user/main.c"
        virtual_name = _REMOTE_PREFIX + remote_path

        # If already open, just switch to it
        for editor, info in em.editors.items():
            if info.get("file_path") == virtual_name:
                idx = em._tab_widget.indexOf(editor)
                em._tab_widget.setCurrentIndex(idx)
                return

        # Open a new untitled editor with the content
        editor = em.new_editor()
        if editor:
            editor.setText(content)
            editor.setModified(False)

            # Set virtual path so save knows it's remote
            editor.file_path = virtual_name
            if virtual_name in em.editors:
                em.editors[editor]["file_path"] = virtual_name

            # Update tab title
            idx = em._tab_widget.indexOf(editor)
            if idx >= 0:
                short = os.path.basename(remote_path)
                em._tab_widget.setTabText(idx, f"[SSH] {short}")

            self._remote_editors[virtual_name] = (editor, remote_path)

            # Detect language from extension
            ext = os.path.splitext(remote_path)[1].lower()
            if ext in ('.c', '.h', '.cpp', '.hpp'):
                editor.set_language("CPP")
            elif ext in ('.py',):
                editor.set_language("Python")

    def _on_file_saved(self, file_path: str) -> None:
        """Intercept saves of remote files and push them back via SFTP."""
        if not file_path.startswith(_REMOTE_PREFIX):
            return
        if not self._panel or not self._panel.is_connected:
            return

        entry = self._remote_editors.get(file_path)
        if not entry:
            return
        editor, remote_path = entry

        content = editor.text()
        ok = self._panel.save_remote_file(remote_path, content)
        if ok:
            log.info("[RemoteSSH] Saved remote file: %s", remote_path)
            if hasattr(self._main_window, '_status_manager'):
                self._main_window._status_manager.set_message(
                    f"Saved remote: {remote_path}", 3000
                )
        else:
            log.warning("[RemoteSSH] Failed to save remote file: %s", remote_path)

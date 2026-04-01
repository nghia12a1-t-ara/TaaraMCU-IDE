"""
ExtensionManager — installs, loads, enables and disables .tix extensions.

Directory layout (user data):
    <extensions_root>/
        <ext_id>/
            manifest.json
            plugin.py
            icon.png          (optional)
            ...

State (which extensions are enabled) is persisted via QSettings under
the key  "extensions/enabled"  as a JSON list of extension IDs.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import shutil
import sys
import zipfile
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal as Signal

from taara_ide.extensions.extension_base import ExtensionBase, ExtensionInfo

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow
    from taara_ide.config import SettingsManager

log = logging.getLogger(__name__)

# Folder inside user-writable area that holds unpacked extensions
_EXTENSIONS_SUBDIR = "extensions"


def _get_extensions_root() -> str:
    """Return (and create) the directory that holds all installed extensions."""
    from taara_ide.config.constants import get_cache_dir
    root = os.path.join(os.path.dirname(get_cache_dir()), _EXTENSIONS_SUBDIR)
    os.makedirs(root, exist_ok=True)
    return root


def _get_builtin_root() -> str:
    """Return the directory that holds built-in (bundled) extensions."""
    return os.path.join(os.path.dirname(__file__), "builtin")


class ExtensionManager(QObject):
    """
    Manages .tix extension lifecycle.

    Signals
    -------
    extension_installed(id)
    extension_uninstalled(id)
    extension_enabled(id)
    extension_disabled(id)
    install_progress(message, percent)   — 0‥100
    error(message)
    """

    extension_installed   = Signal(str)
    extension_uninstalled = Signal(str)
    extension_enabled     = Signal(str)
    extension_disabled    = Signal(str)
    install_progress      = Signal(str, int)
    error                 = Signal(str)
    # Emitted after activation when the extension provides a sidebar panel
    panel_widget_ready    = Signal(str, object)   # ext_id, QWidget

    def __init__(self, settings_manager: "SettingsManager", parent=None):
        super().__init__(parent)
        self._settings = settings_manager
        self._extensions_root = _get_extensions_root()
        self._builtin_root = _get_builtin_root()
        self._loaded: Dict[str, ExtensionBase] = {}   # id → instance
        self._infos:  Dict[str, ExtensionInfo]  = {}  # id → info (even if not activated)
        self._main_window: Optional["MainWindow"] = None

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def load_all(self, main_window: "MainWindow") -> None:
        """
        Call once at startup after MainWindow is ready.
        Discovers installed extensions and activates the enabled ones.
        """
        self._main_window = main_window
        enabled_ids = self._read_enabled_list()
        discovered = self._discover_installed()

        # Auto-enable built-in extensions on first run
        builtin_ids = [
            name for name in (os.listdir(self._builtin_root)
                              if os.path.isdir(self._builtin_root) else [])
            if os.path.isfile(os.path.join(self._builtin_root, name, "manifest.json"))
        ]
        changed = False
        for bid in builtin_ids:
            if bid not in enabled_ids:
                enabled_ids.append(bid)
                changed = True
        if changed:
            self._write_enabled_list(enabled_ids)

        for ext_id in discovered:
            info = self._read_info(ext_id)
            if info:
                self._infos[ext_id] = info
                if ext_id in enabled_ids:
                    self._activate(ext_id)

    # ------------------------------------------------------------------
    # Install / Uninstall
    # ------------------------------------------------------------------

    def install_from_file(self, tix_path: str) -> bool:
        """
        Unpack a .tix file and activate the extension.
        Returns True on success.
        """
        tix_path = os.path.abspath(tix_path)
        if not os.path.isfile(tix_path):
            self.error.emit(f"File not found: {tix_path}")
            return False

        if not zipfile.is_zipfile(tix_path):
            self.error.emit(f"Not a valid .tix file: {tix_path}")
            return False

        # Read manifest from the archive without extracting everything first
        self.install_progress.emit("Reading manifest…", 5)
        try:
            with zipfile.ZipFile(tix_path, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    self.error.emit(".tix archive is missing manifest.json")
                    return False
                manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
        except Exception as exc:
            self.error.emit(f"Failed to read .tix: {exc}")
            return False

        ext_id = manifest_data.get("id", "")
        if not ext_id:
            self.error.emit("manifest.json is missing required field 'id'")
            return False

        # Unpack to extensions root
        dest = os.path.join(self._extensions_root, ext_id)
        self.install_progress.emit(f"Installing {ext_id}…", 20)

        try:
            if os.path.exists(dest):
                shutil.rmtree(dest)
            with zipfile.ZipFile(tix_path, "r") as zf:
                zf.extractall(dest)
        except Exception as exc:
            self.error.emit(f"Extraction failed: {exc}")
            return False

        self.install_progress.emit("Loading extension…", 80)
        info = self._read_info(ext_id)
        if not info:
            self.error.emit(f"Could not read manifest after extraction: {dest}")
            return False

        self._infos[ext_id] = info
        self._enable(ext_id)

        self.install_progress.emit("Done", 100)
        self.extension_installed.emit(ext_id)
        log.info("[ExtensionManager] Installed: %s", ext_id)
        return True

    def uninstall(self, ext_id: str) -> bool:
        """Deactivate and remove an extension from disk."""
        if ext_id in self._loaded:
            self._deactivate(ext_id)

        dest = os.path.join(self._extensions_root, ext_id)
        try:
            if os.path.exists(dest):
                shutil.rmtree(dest)
        except Exception as exc:
            self.error.emit(f"Failed to remove {dest}: {exc}")
            return False

        self._infos.pop(ext_id, None)
        enabled = self._read_enabled_list()
        if ext_id in enabled:
            enabled.remove(ext_id)
            self._write_enabled_list(enabled)

        self.extension_uninstalled.emit(ext_id)
        log.info("[ExtensionManager] Uninstalled: %s", ext_id)
        return True

    # ------------------------------------------------------------------
    # Enable / Disable
    # ------------------------------------------------------------------

    def enable(self, ext_id: str) -> bool:
        if ext_id not in self._infos:
            return False
        self._enable(ext_id)
        return True

    def disable(self, ext_id: str) -> bool:
        if ext_id not in self._loaded:
            return False
        self._deactivate(ext_id)
        enabled = self._read_enabled_list()
        if ext_id in enabled:
            enabled.remove(ext_id)
            self._write_enabled_list(enabled)
        self.extension_disabled.emit(ext_id)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_installed(self) -> List[ExtensionInfo]:
        return list(self._infos.values())

    def get_loaded(self) -> Dict[str, ExtensionBase]:
        return dict(self._loaded)

    def get_extension(self, ext_id: str) -> Optional[ExtensionBase]:
        return self._loaded.get(ext_id)

    def is_enabled(self, ext_id: str) -> bool:
        return ext_id in self._loaded and self._loaded[ext_id].is_active

    # ------------------------------------------------------------------
    # IDE lifecycle forwarding
    # ------------------------------------------------------------------

    def notify_file_opened(self, file_path: str) -> None:
        for ext in self._loaded.values():
            try:
                ext.on_file_opened(file_path)
            except Exception as exc:
                log.warning("[ExtensionManager] %s.on_file_opened error: %s",
                            ext.info.id, exc)

    def notify_file_saved(self, file_path: str) -> None:
        for ext in self._loaded.values():
            try:
                ext.on_file_saved(file_path)
            except Exception as exc:
                log.warning("[ExtensionManager] %s.on_file_saved error: %s",
                            ext.info.id, exc)

    def notify_project_opened(self, project_path: str) -> None:
        for ext in self._loaded.values():
            try:
                ext.on_project_opened(project_path)
            except Exception as exc:
                log.warning("[ExtensionManager] %s.on_project_opened error: %s",
                            ext.info.id, exc)

    def notify_project_closed(self) -> None:
        for ext in self._loaded.values():
            try:
                ext.on_project_closed()
            except Exception as exc:
                log.warning("[ExtensionManager] %s.on_project_closed error: %s",
                            ext.info.id, exc)

    def shutdown(self) -> None:
        """Deactivate all extensions — call from MainWindow.closeEvent."""
        for ext_id in list(self._loaded.keys()):
            self._deactivate(ext_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover_installed(self) -> List[str]:
        ids = []
        # Built-in extensions (bundled with the IDE)
        try:
            for name in os.listdir(self._builtin_root):
                manifest = os.path.join(self._builtin_root, name, "manifest.json")
                if os.path.isfile(manifest):
                    ids.append(name)
        except Exception as exc:
            log.warning("[ExtensionManager] Builtin discovery error: %s", exc)
        # User-installed extensions
        try:
            for name in os.listdir(self._extensions_root):
                manifest = os.path.join(self._extensions_root, name, "manifest.json")
                if os.path.isfile(manifest) and name not in ids:
                    ids.append(name)
        except Exception as exc:
            log.warning("[ExtensionManager] Discovery error: %s", exc)
        return ids

    def _ext_dir(self, ext_id: str) -> str:
        """Return the directory for *ext_id*, preferring builtins."""
        builtin = os.path.join(self._builtin_root, ext_id)
        if os.path.isdir(builtin):
            return builtin
        return os.path.join(self._extensions_root, ext_id)

    def _read_info(self, ext_id: str) -> Optional[ExtensionInfo]:
        manifest_path = os.path.join(self._ext_dir(ext_id), "manifest.json")
        try:
            info = ExtensionInfo.from_manifest(manifest_path)
            info.install_path = self._ext_dir(ext_id)
            return info
        except Exception as exc:
            log.warning("[ExtensionManager] Cannot read manifest for %s: %s", ext_id, exc)
            return None

    def _load_plugin_class(self, ext_id: str) -> Optional[type]:
        plugin_path = os.path.join(self._ext_dir(ext_id), "plugin.py")
        if not os.path.isfile(plugin_path):
            log.warning("[ExtensionManager] plugin.py not found for %s", ext_id)
            return None
        try:
            module_name = f"_tix_{ext_id}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            # Make the extension's own directory importable
            ext_dir = os.path.dirname(plugin_path)
            if ext_dir not in sys.path:
                sys.path.insert(0, ext_dir)
            spec.loader.exec_module(module)
            if not hasattr(module, "Plugin"):
                log.warning("[ExtensionManager] plugin.py in %s has no Plugin class", ext_id)
                return None
            return module.Plugin
        except Exception as exc:
            log.error("[ExtensionManager] Failed to load plugin for %s: %s", ext_id, exc)
            return None

    def _enable(self, ext_id: str) -> None:
        if ext_id in self._loaded:
            return
        enabled = self._read_enabled_list()
        if ext_id not in enabled:
            enabled.append(ext_id)
            self._write_enabled_list(enabled)
        self._activate(ext_id)
        self.extension_enabled.emit(ext_id)

    def _activate(self, ext_id: str) -> None:
        if ext_id in self._loaded:
            return
        cls = self._load_plugin_class(ext_id)
        if cls is None:
            return
        try:
            instance: ExtensionBase = cls()
            if self._main_window:
                ok = instance.activate(self._main_window)
                if not ok:
                    log.warning("[ExtensionManager] activate() returned False for %s", ext_id)
                    return
            instance._set_active(True)
            self._loaded[ext_id] = instance
            log.info("[ExtensionManager] Activated: %s", ext_id)
            # Notify MainWindow if the extension provides a sidebar panel
            panel_widget = instance.get_panel_widget()
            if panel_widget is not None:
                self.panel_widget_ready.emit(ext_id, panel_widget)
        except Exception as exc:
            log.error("[ExtensionManager] Error activating %s: %s", ext_id, exc)

    def _deactivate(self, ext_id: str) -> None:
        instance = self._loaded.pop(ext_id, None)
        if instance:
            try:
                instance.deactivate()
                instance._set_active(False)
                log.info("[ExtensionManager] Deactivated: %s", ext_id)
            except Exception as exc:
                log.warning("[ExtensionManager] Error deactivating %s: %s", ext_id, exc)

    # Persistence of enabled list
    def _read_enabled_list(self) -> List[str]:
        raw = self._settings.get("extensions/enabled", "[]")
        try:
            return json.loads(raw)
        except Exception:
            return []

    def _write_enabled_list(self, ids: List[str]) -> None:
        self._settings.set("extensions/enabled", json.dumps(ids))

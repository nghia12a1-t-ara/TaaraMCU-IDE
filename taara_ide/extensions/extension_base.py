"""
ExtensionBase — abstract base class every .tix plugin must implement.

Compared to FrameworkBase (build / flash / MCU-specific),
ExtensionBase is IDE-feature-oriented: it can contribute panel widgets,
menu actions, toolbar buttons, and hook into IDE lifecycle events.
"""

from __future__ import annotations

import json
import os
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal as Signal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from taara_ide.ui.main_window import MainWindow


class ExtensionCategory(str, Enum):
    REMOTE     = "remote"       # Remote development (SSH, containers…)
    DEBUG      = "debug"        # Debug adapters
    LANGUAGE   = "language"     # Language support
    THEME      = "theme"        # Color themes
    TOOL       = "tool"         # CLI/toolchain wrappers
    OTHER      = "other"


@dataclass
class ExtensionInfo:
    """Metadata parsed from manifest.json."""
    id: str                                         # e.g. "remote-ssh"
    name: str                                       # e.g. "Remote SSH"
    version: str                                    # semver "1.0.0"
    description: str
    author: str = ""
    category: ExtensionCategory = ExtensionCategory.OTHER
    min_ide_version: str = "1.0.0"
    homepage: str = ""
    dependencies: List[str] = field(default_factory=list)  # list of ext IDs
    enabled: bool = True
    install_path: str = ""                          # set by ExtensionManager

    # ------------------------------------------------------------------ #
    @staticmethod
    def from_manifest(manifest_path: str) -> "ExtensionInfo":
        with open(manifest_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        return ExtensionInfo(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            category=ExtensionCategory(data.get("category", "other")),
            min_ide_version=data.get("minIdeVersion", "1.0.0"),
            homepage=data.get("homepage", ""),
            dependencies=data.get("dependencies", []),
        )

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category.value,
            "minIdeVersion": self.min_ide_version,
            "homepage": self.homepage,
            "dependencies": self.dependencies,
        }


# --------------------------------------------------------------------------- #

class ExtensionBase(QObject):
    """
    Abstract base class for all Taara IDE extensions.

    Lifecycle
    ---------
    1. ExtensionManager calls activate(main_window) when the IDE is ready.
    2. The extension can contribute widgets / actions at that point.
    3. deactivate() is called on uninstall or IDE shutdown.

    Signals
    -------
    status_message(str, int)   — show a message in the status bar (msg, ms)
    """

    status_message = Signal(str, int)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._main_window: Optional["MainWindow"] = None
        self._active = False

    # ------------------------------------------------------------------
    # Required
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def info(self) -> ExtensionInfo:
        """Return extension metadata."""

    @abstractmethod
    def activate(self, main_window: "MainWindow") -> bool:
        """
        Called once when the extension is enabled.
        Register actions, open connections, add panels here.
        Returns True on success.
        """

    @abstractmethod
    def deactivate(self) -> None:
        """
        Called when the extension is disabled or uninstalled.
        Clean up all resources / UI contributions.
        """

    # ------------------------------------------------------------------
    # Optional hooks — override what you need
    # ------------------------------------------------------------------

    def get_panel_widget(self) -> Optional[QWidget]:
        """Return a sidebar panel widget (added to activity bar stack)."""
        return None

    def get_actions(self) -> List[QAction]:
        """Return QAction objects to add to the IDE menus/toolbar."""
        return []

    def get_settings_widget(self) -> Optional[QWidget]:
        """Return a settings widget shown in the Extensions panel."""
        return None

    def on_file_opened(self, file_path: str) -> None:
        """Called whenever the user opens a file."""

    def on_file_saved(self, file_path: str) -> None:
        """Called whenever the user saves a file."""

    def on_project_opened(self, project_path: str) -> None:
        """Called when a project/folder is opened."""

    def on_project_closed(self) -> None:
        """Called when a project is closed."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._active

    def _set_active(self, active: bool) -> None:
        self._active = active

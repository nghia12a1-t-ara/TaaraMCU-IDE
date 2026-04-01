"""
Extensions Panel — install, enable/disable, and uninstall .tix extensions.

Layout:
  ┌─────────────────────────────────┐
  │  EXTENSIONS          [Install…] │
  │  ──────────────────────────────  │
  │  [  Search…                   ] │
  │  ──────────────────────────────  │
  │  ▸ INSTALLED (n)                │
  │    [icon] Name  v1.0  [●] [🗑]  │
  │    description…                  │
  │    …                            │
  └─────────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal as Signal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QSizePolicy, QFileDialog,
    QMessageBox,
)

if TYPE_CHECKING:
    from taara_ide.extensions import ExtensionManager, ExtensionInfo


# ─────────────────────────────────────────────────────────────────────────────
class _ExtensionCard(QFrame):
    """One row in the installed-extensions list."""

    toggle_requested   = Signal(str, bool)   # ext_id, enable?
    uninstall_requested = Signal(str)        # ext_id

    def __init__(self, info: "ExtensionInfo", enabled: bool, parent=None):
        super().__init__(parent)
        self._ext_id = info.id
        self._setup_ui(info, enabled)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            _ExtensionCard {
                background: #2a2a2a;
                border-radius: 4px;
                border: 1px solid #3a3a3a;
            }
        """)

    def _setup_ui(self, info: "ExtensionInfo", enabled: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # ── Top row: name + version + toggle + delete ──────────────────
        top = QHBoxLayout()

        name_label = QLabel(f"<b>{info.name}</b>")
        name_label.setStyleSheet("font-size: 12px;")
        top.addWidget(name_label)

        ver_label = QLabel(info.version)
        ver_label.setStyleSheet("color: #888; font-size: 10px;")
        top.addWidget(ver_label)

        top.addStretch()

        self._toggle_btn = QPushButton("●" if enabled else "○")
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.setToolTip("Disable extension" if enabled else "Enable extension")
        self._toggle_btn.setStyleSheet(
            "color: #5a5; font-size: 14px; border: none; background: transparent;"
            if enabled else
            "color: #888; font-size: 14px; border: none; background: transparent;"
        )
        self._toggle_btn.clicked.connect(self._on_toggle)
        top.addWidget(self._toggle_btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(24, 24)
        del_btn.setToolTip("Uninstall extension")
        del_btn.setStyleSheet("border: none; background: transparent; font-size: 13px;")
        del_btn.clicked.connect(lambda: self.uninstall_requested.emit(self._ext_id))
        top.addWidget(del_btn)

        layout.addLayout(top)

        # ── Description ──────────────────────────────────────────────────
        if info.description:
            desc = QLabel(info.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #aaa; font-size: 10px;")
            layout.addWidget(desc)

        # ── Category / author ────────────────────────────────────────────
        meta_parts = []
        if info.author:
            meta_parts.append(info.author)
        meta_parts.append(info.category.value)
        meta_label = QLabel("  ·  ".join(meta_parts))
        meta_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(meta_label)

    def _on_toggle(self):
        # Current state deduced from button text
        currently_enabled = self._toggle_btn.text() == "●"
        self.toggle_requested.emit(self._ext_id, not currently_enabled)

    def set_enabled_state(self, enabled: bool):
        self._toggle_btn.setText("●" if enabled else "○")
        self._toggle_btn.setToolTip("Disable extension" if enabled else "Enable extension")
        self._toggle_btn.setStyleSheet(
            "color: #5a5; font-size: 14px; border: none; background: transparent;"
            if enabled else
            "color: #888; font-size: 14px; border: none; background: transparent;"
        )


# ─────────────────────────────────────────────────────────────────────────────
class ExtensionsPanel(QWidget):
    """
    Sidebar panel for managing .tix extensions.

    Call set_extension_manager(em) after the ExtensionManager is ready.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._em: Optional["ExtensionManager"] = None
        self._cards: dict[str, _ExtensionCard] = {}   # ext_id → card widget
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_extension_manager(self, em: "ExtensionManager") -> None:
        """Wire up the panel to an ExtensionManager instance."""
        self._em = em
        em.extension_installed.connect(self._refresh)
        em.extension_uninstalled.connect(self._refresh)
        em.extension_enabled.connect(lambda eid: self._update_card_state(eid, True))
        em.extension_disabled.connect(lambda eid: self._update_card_state(eid, False))
        em.install_progress.connect(self._on_install_progress)
        em.error.connect(self._on_error)
        self._refresh()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── Header ───────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("EXTENSIONS")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        header.addWidget(title)
        header.addStretch()

        install_btn = QPushButton("Install…")
        install_btn.setFixedWidth(68)
        install_btn.setToolTip("Install a .tix extension file")
        install_btn.clicked.connect(self._on_install_clicked)
        header.addWidget(install_btn)
        root.addLayout(header)

        # ── Search ───────────────────────────────────────────────────────
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search installed extensions…")
        self._search_edit.textChanged.connect(self._filter_cards)
        root.addWidget(self._search_edit)

        # ── Progress label (hidden normally) ─────────────────────────────
        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #888; font-size: 10px;")
        self._progress_label.setVisible(False)
        root.addWidget(self._progress_label)

        # ── Scrollable card list ─────────────────────────────────────────
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._list_widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll, stretch=1)

        # ── Empty-state label ────────────────────────────────────────────
        self._empty_label = QLabel(
            "No extensions installed.\n\nClick 'Install…' to add a .tix file."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: #666; font-size: 11px;")
        root.addWidget(self._empty_label)

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_install_clicked(self):
        if not self._em:
            QMessageBox.warning(self, "Extensions", "Extension manager not ready.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Install Extension", "", "Taara Extension (*.tix);;All files (*)"
        )
        if path:
            self._progress_label.setText("Installing…")
            self._progress_label.setVisible(True)
            self._em.install_from_file(path)

    def _on_install_progress(self, message: str, percent: int):
        self._progress_label.setText(f"{message} ({percent}%)")
        if percent >= 100:
            self._progress_label.setVisible(False)

    def _on_error(self, message: str):
        self._progress_label.setVisible(False)
        QMessageBox.critical(self, "Extension Error", message)

    def _on_toggle(self, ext_id: str, enable: bool):
        if not self._em:
            return
        if enable:
            self._em.enable(ext_id)
        else:
            self._em.disable(ext_id)

    def _on_uninstall(self, ext_id: str):
        if not self._em:
            return
        reply = QMessageBox.question(
            self, "Uninstall Extension",
            f"Uninstall '{ext_id}'?\nThis will remove all its files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._em.uninstall(ext_id)

    # ------------------------------------------------------------------ #
    # Refresh / filter
    # ------------------------------------------------------------------ #

    def _refresh(self, _ext_id: str = ""):
        """Rebuild card list from extension manager state."""
        # Remove old cards (keep stretch at end)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        if not self._em:
            self._empty_label.setVisible(True)
            return

        infos = self._em.get_installed()
        if not infos:
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)
        for info in infos:
            enabled = self._em.is_enabled(info.id)
            card = _ExtensionCard(info, enabled)
            card.toggle_requested.connect(self._on_toggle)
            card.uninstall_requested.connect(self._on_uninstall)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
            self._cards[info.id] = card

        self._filter_cards(self._search_edit.text())

    def _filter_cards(self, text: str):
        q = text.lower().strip()
        for ext_id, card in self._cards.items():
            card.setVisible(not q or q in ext_id.lower())

    def _update_card_state(self, ext_id: str, enabled: bool):
        card = self._cards.get(ext_id)
        if card:
            card.set_enabled_state(enabled)

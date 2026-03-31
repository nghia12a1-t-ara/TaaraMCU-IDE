"""
LspClient - bridges a CodeEditor with LspService.

Responsibilities:
    - Sends didOpen / didChange / didClose to the server
    - Paints diagnostic squiggles (errors=red, warnings=yellow) via indicators
    - Provides hover_at(line, char) -> forwards to server
    - Provides goto_definition_at(line, char) -> forwards to server
"""

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import QTimer, QObject
from PyQt6.QtGui import QColor
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from taara_ide.ui.editor.code_editor import CodeEditor
    from taara_ide.services.lsp_service import LspService


# Scintilla indicator slots (must not conflict with code_editor.py: 0=highlight, 1=search)
_IND_ERROR   = 3
_IND_WARNING = 4


class LspClient(QObject):
    """
    One LspClient per CodeEditor instance.
    Call attach(lsp_service) once the server is running.
    """

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor
        self._lsp: Optional["LspService"] = None
        self._version = 0
        self._change_timer = QTimer(self)
        self._change_timer.setSingleShot(True)
        self._change_timer.timeout.connect(self._send_did_change)
        self._setup_indicators()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_indicators(self):
        e = self._editor
        e.indicatorDefine(QsciScintilla.IndicatorStyle.SquiggleIndicator, _IND_ERROR)
        e.setIndicatorForegroundColor(QColor("#FF3333"), _IND_ERROR)
        e.setIndicatorDrawUnder(True, _IND_ERROR)

        e.indicatorDefine(QsciScintilla.IndicatorStyle.SquiggleIndicator, _IND_WARNING)
        e.setIndicatorForegroundColor(QColor("#FFCC00"), _IND_WARNING)
        e.setIndicatorDrawUnder(True, _IND_WARNING)

    def attach(self, lsp: "LspService"):
        """Connect to a running LspService."""
        if self._lsp is lsp:
            return
        self._lsp = lsp
        lsp.diagnostics_ready.connect(self._on_diagnostics)
        # Connect editor text changes to debounced didChange
        self._editor.textChanged.connect(self._schedule_change)
        # Send initial open if file is already loaded
        if self._editor.file_path:
            self._send_did_open()

    def detach(self):
        if not self._lsp:
            return
        if self._editor.file_path:
            self._lsp.did_close(self._editor.file_path)
        self._lsp.diagnostics_ready.disconnect(self._on_diagnostics)
        try:
            self._editor.textChanged.disconnect(self._schedule_change)
        except RuntimeError:
            pass
        self._lsp = None

    # ------------------------------------------------------------------
    # Called by CodeEditor when a file is opened / closed
    # ------------------------------------------------------------------

    def notify_file_opened(self, file_path: str, text: str):
        self._version = 1
        if self._lsp and self._lsp.is_running():
            lang = "cpp" if file_path.endswith((".c", ".h", ".cpp", ".hpp", ".cc")) else "python"
            self._lsp.did_open(file_path, text, lang)

    def notify_file_closed(self, file_path: str):
        if self._lsp and self._lsp.is_running():
            self._lsp.did_close(file_path)

    # ------------------------------------------------------------------
    # Requests (called from outside, e.g. Ctrl+Hover, Ctrl+Click)
    # ------------------------------------------------------------------

    def request_hover(self, line: int, character: int) -> int:
        if self._lsp and self._lsp.is_running() and self._editor.file_path:
            return self._lsp.request_hover(self._editor.file_path, line, character)
        return 0

    def request_definition(self, line: int, character: int) -> int:
        if self._lsp and self._lsp.is_running() and self._editor.file_path:
            return self._lsp.request_definition(self._editor.file_path, line, character)
        return 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _schedule_change(self):
        self._change_timer.start(400)   # 400 ms debounce

    def _send_did_open(self):
        if not self._lsp or not self._editor.file_path:
            return
        fp = self._editor.file_path
        lang = "cpp" if fp.endswith((".c", ".h", ".cpp", ".hpp", ".cc")) else "python"
        self._lsp.did_open(fp, self._editor.text(), lang)

    def _send_did_change(self):
        if not self._lsp or not self._lsp.is_running():
            return
        if not self._editor.file_path:
            return
        self._version += 1
        self._lsp.did_change(self._editor.file_path, self._editor.text(), self._version)

    def _on_diagnostics(self, file_path: str, diagnostics: list):
        """Paint squiggles for this file (ignore diagnostics for other files)."""
        if not self._editor.file_path:
            return
        # Normalise both paths for comparison
        import os
        if os.path.normcase(os.path.normpath(file_path)) != \
                os.path.normcase(os.path.normpath(self._editor.file_path)):
            return

        e = self._editor
        # Clear previous markers
        for ind in (_IND_ERROR, _IND_WARNING):
            e.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, ind)
            e.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, e.length())

        for diag in diagnostics:
            severity = diag.get("severity", 1)   # 1=Error, 2=Warning, 3=Info, 4=Hint
            indicator = _IND_ERROR if severity == 1 else _IND_WARNING

            start = diag.get("range", {}).get("start", {})
            end   = diag.get("range", {}).get("end",   {})
            s_line = start.get("line", 0)
            s_char = start.get("character", 0)
            e_line = end.get("line", s_line)
            e_char = end.get("character", s_char + 1)

            start_pos = e.SendScintilla(QsciScintilla.SCI_FINDCOLUMN, s_line, s_char)
            end_pos   = e.SendScintilla(QsciScintilla.SCI_FINDCOLUMN, e_line, e_char)
            length = max(end_pos - start_pos, 1)

            e.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, indicator)
            e.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, start_pos, length)

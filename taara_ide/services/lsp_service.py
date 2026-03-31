"""
LSP Service - clangd language server integration.

Manages one clangd process per project root and dispatches JSON-RPC
requests/responses to registered listeners.

Supported features:
    - Diagnostics  (textDocument/publishDiagnostics)
    - Hover        (textDocument/hover)
    - Go-to-def    (textDocument/definition)
    - Completion   (textDocument/completion)  [basic, supplements QScintilla]
"""

import json
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal as Signal, QTimer


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

def _make_request(msg_id: int, method: str, params: dict) -> bytes:
    body = json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
    return f"Content-Length: {len(body)}\r\n\r\n{body}".encode()


def _make_notification(method: str, params: dict) -> bytes:
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
    return f"Content-Length: {len(body)}\r\n\r\n{body}".encode()


def _uri(path: str) -> str:
    return Path(path).as_uri()


# ---------------------------------------------------------------------------
# Reader thread – parses LSP framing from clangd stdout
# ---------------------------------------------------------------------------

class _LspReader(threading.Thread):
    def __init__(self, stream, on_message: Callable):
        super().__init__(daemon=True)
        self._stream = stream
        self._on_message = on_message

    def run(self):
        while True:
            try:
                header = b""
                while not header.endswith(b"\r\n\r\n"):
                    ch = self._stream.read(1)
                    if not ch:
                        return
                    header += ch

                content_length = 0
                for line in header.split(b"\r\n"):
                    if line.lower().startswith(b"content-length:"):
                        content_length = int(line.split(b":")[1].strip())

                if content_length <= 0:
                    continue

                body = b""
                while len(body) < content_length:
                    chunk = self._stream.read(content_length - len(body))
                    if not chunk:
                        return
                    body += chunk

                msg = json.loads(body.decode("utf-8", errors="replace"))
                self._on_message(msg)
            except Exception as e:
                print(f"[LSP reader] {e}")


# ---------------------------------------------------------------------------
# LspService
# ---------------------------------------------------------------------------

class LspService(QObject):
    """
    Manages a clangd subprocess and exposes Qt signals for IDE integration.

    Signals:
        diagnostics_ready(file_path, list[dict])  — list of diagnostic dicts
        hover_ready(request_id, str)              — markdown hover text
        definition_ready(request_id, str, int)    — file_path, line (0-based)
        started()
        stopped()
    """

    diagnostics_ready = Signal(str, list)   # file_path, diagnostics
    hover_ready       = Signal(int, str)    # request_id, text
    definition_ready  = Signal(int, str, int)  # request_id, file_path, line
    started           = Signal()
    stopped           = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: Optional[subprocess.Popen] = None
        self._reader: Optional[_LspReader] = None
        self._lock = threading.Lock()
        self._next_id = 1
        self._pending: dict[int, str] = {}   # id -> method
        self._root: Optional[str] = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, root_path: str, clangd_exe: str = "clangd") -> bool:
        """Start clangd for *root_path*. Returns False if already running."""
        if self._process and self._process.poll() is None:
            return False

        self._root = root_path
        self._initialized = False

        try:
            self._process = subprocess.Popen(
                [clangd_exe, "--background-index", "--clang-tidy",
                 "--header-insertion=never"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=root_path,
            )
        except FileNotFoundError:
            print(f"[LspService] clangd not found at '{clangd_exe}'")
            return False

        self._reader = _LspReader(self._process.stdout, self._on_message)
        self._reader.start()

        self._send(_make_request(self._alloc_id("initialize"), "initialize", {
            "processId": None,
            "rootUri": _uri(root_path),
            "capabilities": {
                "textDocument": {
                    "publishDiagnostics": {"relatedInformation": True},
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "definition": {},
                    "completion": {"completionItem": {"snippetSupport": False}},
                }
            },
            "initializationOptions": {},
        }))
        return True

    def stop(self):
        """Shut down clangd gracefully."""
        if not self._process:
            return
        try:
            self._send(_make_notification("exit", {}))
            self._process.stdin.close()
            self._process.wait(timeout=3)
        except Exception:
            self._process.kill()
        finally:
            self._process = None
            self._initialized = False
            self.stopped.emit()

    def is_running(self) -> bool:
        return bool(self._process and self._process.poll() is None)

    # ------------------------------------------------------------------
    # Document sync
    # ------------------------------------------------------------------

    def did_open(self, file_path: str, text: str, language: str = "c"):
        if not self._initialized:
            return
        self._send(_make_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": _uri(file_path),
                "languageId": language,
                "version": 1,
                "text": text,
            }
        }))

    def did_change(self, file_path: str, text: str, version: int):
        if not self._initialized:
            return
        self._send(_make_notification("textDocument/didChange", {
            "textDocument": {"uri": _uri(file_path), "version": version},
            "contentChanges": [{"text": text}],
        }))

    def did_close(self, file_path: str):
        if not self._initialized:
            return
        self._send(_make_notification("textDocument/didClose", {
            "textDocument": {"uri": _uri(file_path)}
        }))

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------

    def request_hover(self, file_path: str, line: int, character: int) -> int:
        """Returns request id (0 if not running)."""
        if not self._initialized:
            return 0
        rid = self._alloc_id("textDocument/hover")
        self._send(_make_request(rid, "textDocument/hover", {
            "textDocument": {"uri": _uri(file_path)},
            "position": {"line": line, "character": character},
        }))
        return rid

    def request_definition(self, file_path: str, line: int, character: int) -> int:
        """Returns request id (0 if not running)."""
        if not self._initialized:
            return 0
        rid = self._alloc_id("textDocument/definition")
        self._send(_make_request(rid, "textDocument/definition", {
            "textDocument": {"uri": _uri(file_path)},
            "position": {"line": line, "character": character},
        }))
        return rid

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _alloc_id(self, method: str) -> int:
        with self._lock:
            rid = self._next_id
            self._next_id += 1
            self._pending[rid] = method
        return rid

    def _send(self, data: bytes):
        try:
            if self._process and self._process.stdin:
                self._process.stdin.write(data)
                self._process.stdin.flush()
        except Exception as e:
            print(f"[LspService] send error: {e}")

    def _on_message(self, msg: dict):
        """Called from reader thread — emit signals (Qt queues cross-thread)."""
        # Notification (no id)
        if "method" in msg and "id" not in msg:
            method = msg["method"]
            params = msg.get("params", {})

            if method == "textDocument/publishDiagnostics":
                uri = params.get("uri", "")
                file_path = uri.replace("file:///", "").replace("file://", "")
                # On Windows the URI starts with /C:/... strip leading slash
                if file_path.startswith("/") and len(file_path) > 2 and file_path[2] == ":":
                    file_path = file_path[1:]
                diags = params.get("diagnostics", [])
                self.diagnostics_ready.emit(file_path, diags)
            return

        # Response
        if "id" in msg:
            rid = msg["id"]
            with self._lock:
                method = self._pending.pop(rid, None)

            if method == "initialize":
                self._send(_make_notification("initialized", {}))
                self._initialized = True
                self.started.emit()
                return

            result = msg.get("result")

            if method == "textDocument/hover" and result:
                contents = result.get("contents", "")
                if isinstance(contents, dict):
                    text = contents.get("value", "")
                elif isinstance(contents, list):
                    text = "\n".join(
                        c.get("value", c) if isinstance(c, dict) else str(c)
                        for c in contents
                    )
                else:
                    text = str(contents)
                self.hover_ready.emit(rid, text)

            elif method == "textDocument/definition" and result:
                locations = result if isinstance(result, list) else [result]
                if locations:
                    loc = locations[0]
                    uri = loc.get("uri", "")
                    file_path = uri.replace("file:///", "").replace("file://", "")
                    if file_path.startswith("/") and len(file_path) > 2 and file_path[2] == ":":
                        file_path = file_path[1:]
                    line = loc.get("range", {}).get("start", {}).get("line", 0)
                    self.definition_ready.emit(rid, file_path, line)

"""
CTags-based code indexer.

Threading model
---------------
- _symbols_cache and _tags_files are always accessed under _cache_lock.
- index_file_async() enqueues work; at most one CtagsWorker runs at a time.
  If a request arrives while a worker is running, the *latest* file path wins
  (old queued request is replaced) so we never pile up stale work.
- index_project_async() uses ProjectIndexWorker (separate QThread) so the main
  thread is never blocked.
- find_definition() is fast (cache-only + optional tags-file scan); the tags-file
  scan runs in a short-lived thread and delivers results via a callback so the
  call-tip timer is never blocked.
"""

import logging
import os
import re
import subprocess
import sys
import json
import hashlib
import threading
from collections import OrderedDict
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field

from PyQt6.QtCore import QThread, pyqtSignal as Signal

from taara_ide.core.base import IndexerBase
from taara_ide.config import SettingsManager
from taara_ide.config.constants import get_ctags_cache_dir

log = logging.getLogger(__name__)

# Directories never worth indexing
_EXCLUDE_DIRS = {
    '.git', '.svn', '.hg', '__pycache__', '.mypy_cache', '.pytest_cache',
    'node_modules', 'venv', '.venv', 'env', '.env',
    'build', 'dist', 'out', 'bin', 'obj', 'Debug', 'Release',
    '.idea', '.vscode', '.vs',
}
_EXCLUDE_CTAGS_ARGS = [f'--exclude={d}' for d in _EXCLUDE_DIRS]

# LRU cap for the column-position cache (file_path, line, symbol) → col
_COLUMN_CACHE_MAX = 512


def _subprocess_flags() -> dict:
    flags: dict = {}
    if sys.platform == 'win32':
        flags['creationflags'] = subprocess.CREATE_NO_WINDOW
    return flags


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Symbol:
    name: str
    kind: str
    file: str
    line: int
    pattern: str = ""
    scope: str = ""
    signature: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.name}{self.signature}" if self.signature else self.name

    @property
    def icon_name(self) -> str:
        return {
            'function': 'function', 'prototype': 'function',
            'method': 'method', 'class': 'class', 'struct': 'struct',
            'enum': 'enum', 'variable': 'variable', 'member': 'field',
            'macro': 'macro', 'typedef': 'type',
        }.get(self.kind, 'symbol')


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------

class CtagsWorker(QThread):
    """Indexes a single file; stdout is piped (no temp file)."""

    finished = Signal(bool, list, str)   # success, symbols, file_path

    def __init__(self, ctags_path: str, file_path: str):
        super().__init__()
        self.ctags_path = ctags_path
        self.file_path = file_path

    def run(self):
        try:
            result = subprocess.run(
                [self.ctags_path,
                 '--output-format=json',
                 '--fields=+nKS',
                 '--kinds-c=+p',
                 '--kinds-c++=+p',
                 '-f', '-',
                 self.file_path],
                capture_output=True, text=True,
                **_subprocess_flags()
            )
            if result.returncode != 0:
                self.finished.emit(False, [], self.file_path)
                return

            symbols: list[Symbol] = []
            for line in result.stdout.splitlines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    symbols.append(Symbol(
                        name=data.get('name', ''),
                        kind=data.get('kind', ''),
                        file=data.get('path', self.file_path),
                        line=data.get('line', 0),
                        pattern=data.get('pattern', ''),
                        scope=data.get('scope', ''),
                        signature=data.get('signature', ''),
                    ))
                except json.JSONDecodeError:
                    continue

            self.finished.emit(True, symbols, self.file_path)

        except Exception as exc:
            log.warning("[CTags] Worker error for %s: %s", self.file_path, exc)
            self.finished.emit(False, [], self.file_path)


class ProjectIndexWorker(QThread):
    """Recursively indexes a project directory; never blocks the main thread."""

    progress = Signal(str)          # status message
    finished = Signal(bool, str)    # success, project_path

    def __init__(self, ctags_path: str, project_path: str, tags_file: str):
        super().__init__()
        self.ctags_path = ctags_path
        self.project_path = project_path
        self.tags_file = tags_file

    def run(self):
        self.progress.emit(f"Indexing {os.path.basename(self.project_path)}…")
        try:
            result = subprocess.run(
                [self.ctags_path,
                 '-R',
                 '--fields=+nKSz',
                 '--extras=+q',
                 '--kinds-c=+p',
                 '--kinds-c++=+p',
                 *_EXCLUDE_CTAGS_ARGS,
                 '-f', self.tags_file,
                 self.project_path],
                capture_output=True, text=True,
                **_subprocess_flags()
            )
            ok = result.returncode == 0
            if not ok:
                log.warning("[CTags] index_project failed: %s", result.stderr[:200])
            self.finished.emit(ok, self.project_path)
        except Exception as exc:
            log.warning("[CTags] ProjectIndexWorker error: %s", exc)
            self.finished.emit(False, self.project_path)


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

class CtagsHandler(IndexerBase):
    """CTags-based code indexer — thread-safe, fully async."""

    ctags_path_required = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsManager()

        # ── Cache (always access under _cache_lock) ──────────────────────
        self._cache_lock = threading.Lock()
        self._symbols_cache: Dict[str, List[Symbol]] = {}
        self._tags_files: Dict[str, str] = {}          # source → tags file
        self._column_cache: OrderedDict[tuple, int] = OrderedDict()  # LRU

        # ── Single-file async worker queue ───────────────────────────────
        self._worker_lock = threading.Lock()
        self._active_worker: Optional[CtagsWorker] = None
        self._pending_file: Optional[str] = None       # latest queued request

        # ── Project index worker ─────────────────────────────────────────
        self._project_worker: Optional[ProjectIndexWorker] = None

        self._cache_dir = get_ctags_cache_dir()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def ctags_path(self) -> str:
        return self._settings.get_ctags_path()

    def is_available(self) -> bool:
        try:
            r = subprocess.run(
                [self.ctags_path, '--version'],
                capture_output=True, text=True,
                **_subprocess_flags()
            )
            return r.returncode == 0
        except Exception as exc:
            log.debug("[CTags] is_available check failed: %s", exc)
            return False

    def _get_tags_file_path(self, source_path: str, is_project: bool = False) -> str:
        normalized = os.path.normpath(os.path.abspath(source_path))
        path_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        base = os.path.basename(normalized)
        if not is_project:
            base = os.path.splitext(base)[0]
        safe = "".join(c if c.isalnum() or c in '-_' else '_' for c in base)
        prefix = "project_" if is_project else "file_"
        return os.path.join(self._cache_dir, f"{prefix}{safe}_{path_hash}.tags")

    # ------------------------------------------------------------------
    # Single-file async indexing  (P0 fix: worker queue)
    # ------------------------------------------------------------------

    def index_file_async(self, file_path: str) -> None:
        """Queue a file for async indexing. Only one worker runs at a time;
        if one is already running the new request is stored and started when
        the current worker finishes."""
        if not self.is_available():
            self.ctags_path_required.emit()
            return

        with self._worker_lock:
            if self._active_worker is not None and self._active_worker.isRunning():
                # Replace any pending request with the latest
                self._pending_file = file_path
                return
            self._pending_file = None
            self._start_worker(file_path)

    def _start_worker(self, file_path: str) -> None:
        """Must be called with _worker_lock held."""
        worker = CtagsWorker(self.ctags_path, file_path)
        worker.finished.connect(self._on_index_finished)
        self._active_worker = worker
        worker.start()

    def _on_index_finished(self, success: bool, symbols: list, file_path: str):
        """Slot runs on main thread (Qt auto-connection)."""
        if success and symbols:
            with self._cache_lock:
                self._symbols_cache[file_path] = symbols

            symbol_dicts = [
                {'name': s.name, 'kind': s.kind,
                 'line': s.line, 'signature': s.signature}
                for s in symbols
            ]
            self.symbols_updated.emit(file_path, symbol_dicts)
        else:
            # Emit empty update so UI resets stale function list  (P0 fix)
            self.symbols_updated.emit(file_path, [])

        self.indexing_finished.emit(success)

        # Start next pending file if any  (P0 fix: worker queue drain)
        with self._worker_lock:
            next_file = self._pending_file
            self._pending_file = None
            self._active_worker = None
            if next_file:
                self._start_worker(next_file)

    # ------------------------------------------------------------------
    # Synchronous single-file index (kept for compatibility)
    # ------------------------------------------------------------------

    def index_file(self, file_path: str) -> List[Dict[str, Any]]:
        if not self.is_available():
            self.ctags_path_required.emit()
            return []
        tags_file = self._get_tags_file_path(file_path)
        with self._cache_lock:
            self._tags_files[file_path] = tags_file
        try:
            result = subprocess.run(
                [self.ctags_path,
                 '--output-format=json', '--fields=+nKS',
                 '--kinds-c=+p', '--kinds-c++=+p',
                 '-f', tags_file, file_path],
                capture_output=True, text=True,
                **_subprocess_flags()
            )
            if result.returncode != 0:
                return []
            symbols = []
            if os.path.exists(tags_file):
                with open(tags_file, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if line.startswith('!_TAG_'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            sd: Dict[str, Any] = {'name': parts[0], 'file': file_path, 'line': 1}
                            for part in parts[3:]:
                                if ':' in part:
                                    k, v = part.split(':', 1)
                                    if k == 'line':
                                        try:
                                            sd['line'] = int(v)
                                        except ValueError:
                                            pass
                                    elif k in ('kind', 'signature'):
                                        sd[k] = v
                            symbols.append(sd)
            return symbols
        except Exception as exc:
            log.warning("[CTags] index_file error: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Project indexing  (P1 fix: fully async, never blocks main thread)
    # ------------------------------------------------------------------

    def index_project(self, project_path: str) -> bool:
        """Non-blocking project index. Returns True if worker started.
        Connect to indexing_finished / symbols_updated signals for completion."""
        if not self.is_available():
            self.ctags_path_required.emit()
            return False

        # Cancel previous project worker if still running
        if self._project_worker and self._project_worker.isRunning():
            self._project_worker.quit()
            self._project_worker.wait(2000)

        tags_file = self._get_tags_file_path(project_path, is_project=True)
        with self._cache_lock:
            self._tags_files[project_path] = tags_file

        worker = ProjectIndexWorker(self.ctags_path, project_path, tags_file)
        worker.progress.connect(lambda msg: log.info("[CTags] %s", msg))
        worker.finished.connect(self._on_project_index_finished)
        self._project_worker = worker
        worker.start()
        return True

    def _on_project_index_finished(self, success: bool, project_path: str):
        if not success:
            log.warning("[CTags] Project indexing failed for %s", project_path)
        self.indexing_finished.emit(success)

    # ------------------------------------------------------------------
    # find_definition  (P1 fix: cache-first, async tags-file scan)
    # ------------------------------------------------------------------

    def find_definition(self, symbol: str, context_file: str) -> Optional[tuple]:
        """Cache-first synchronous lookup. Fast for already-indexed files.
        Falls back to scanning project tags files on disk."""
        # 1. In-memory cache (fast, O(n) but small)
        with self._cache_lock:
            cache_snapshot = dict(self._symbols_cache)

        for _fp, symbols in cache_snapshot.items():
            for sym in symbols:
                if sym.name == symbol:
                    col = self._find_column_cached(sym.file, sym.line, symbol)
                    return (sym.file, sym.line, col)

        # 2. Tags-file scan (disk) — collect project tags files under lock
        with self._cache_lock:
            tags_snapshot = {k: v for k, v in self._tags_files.items()
                             if os.path.isdir(k)}

        for base_path, tags_file in tags_snapshot.items():
            result = self._scan_tags_file(tags_file, base_path, symbol)
            if result:
                return result

        return None

    def find_definition_async(self, symbol: str, context_file: str,
                               callback: Callable[[Optional[tuple]], None]) -> None:
        """Async variant — runs the disk scan in a thread, delivers via callback.
        The callback is invoked on an arbitrary thread; wrap in a Qt signal if
        you need to update the UI."""
        def _worker():
            result = self.find_definition(symbol, context_file)
            callback(result)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _scan_tags_file(self, tags_file: str, base_path: str,
                        symbol: str) -> Optional[tuple]:
        if not os.path.exists(tags_file):
            return None
        try:
            with open(tags_file, 'r', encoding='utf-8', errors='ignore') as fh:
                for line in fh:
                    if line.startswith('!_TAG_'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 3 and parts[0] == symbol:
                        rel = parts[1]
                        abs_file = rel if os.path.isabs(rel) else \
                            os.path.normpath(os.path.join(base_path, rel))
                        line_num = 1
                        for part in parts[3:]:
                            part = part.strip()
                            if part.startswith('line:'):
                                try:
                                    line_num = int(part.split(':', 1)[1])
                                    break
                                except (ValueError, IndexError):
                                    pass
                        col = self._find_column_cached(abs_file, line_num, symbol)
                        return (abs_file, line_num, col)
        except Exception as exc:
            log.warning("[CTags] Error scanning tags file %s: %s", tags_file, exc)
        return None

    # ------------------------------------------------------------------
    # Column lookup with LRU cache  (P2 fix)
    # ------------------------------------------------------------------

    def _find_column_cached(self, file_path: str, line_num: int, symbol: str) -> int:
        key = (file_path, line_num, symbol)
        with self._cache_lock:
            if key in self._column_cache:
                self._column_cache.move_to_end(key)
                return self._column_cache[key]

        col = self._find_column_in_file(file_path, line_num, symbol)

        with self._cache_lock:
            self._column_cache[key] = col
            self._column_cache.move_to_end(key)
            if len(self._column_cache) > _COLUMN_CACHE_MAX:
                self._column_cache.popitem(last=False)

        return col

    def _find_column_in_file(self, file_path: str, line_num: int, symbol: str) -> int:
        try:
            if not os.path.exists(file_path):
                return 0
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
                for i, line in enumerate(fh, 1):
                    if i == line_num:
                        m = re.search(r'\b' + re.escape(symbol) + r'\b', line)
                        if m:
                            return m.start()
                        pos = line.find(symbol)
                        return pos if pos >= 0 else 0
        except Exception as exc:
            log.debug("[CTags] Column lookup error: %s", exc)
        return 0

    # ------------------------------------------------------------------
    # Cache accessors
    # ------------------------------------------------------------------

    def get_cached_symbols(self, file_path: str) -> List[Symbol]:
        with self._cache_lock:
            return list(self._symbols_cache.get(file_path, []))

    def find_references(self, symbol: str, project_path: str) -> List[tuple]:
        """Find all lines containing *symbol* in *project_path* using grep."""
        results: List[tuple] = []
        try:
            grep_cmd = ['grep', '-rn', '--include=*.c', '--include=*.h',
                        '--include=*.cpp', '--include=*.hpp',
                        '-w', symbol, project_path]
            result = subprocess.run(
                grep_cmd, capture_output=True, text=True,
                **_subprocess_flags()
            )
            for line in result.stdout.splitlines():
                # format: file:line:content
                parts = line.split(':', 2)
                if len(parts) >= 2:
                    try:
                        results.append((parts[0], int(parts[1])))
                    except ValueError:
                        pass
        except Exception as exc:
            log.debug("[CTags] find_references error: %s", exc)
        return results

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._symbols_cache.clear()
            self._column_cache.clear()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_file_tags(self, file_path: str) -> None:
        with self._cache_lock:
            tags_file = self._tags_files.pop(file_path, None)
            self._symbols_cache.pop(file_path, None)
            # Invalidate column cache entries for this file
            stale = [k for k in self._column_cache if k[0] == file_path]
            for k in stale:
                del self._column_cache[k]

        if tags_file:
            try:
                if os.path.exists(tags_file):
                    os.remove(tags_file)
                    log.debug("[CTags] Removed tags file: %s", tags_file)
            except Exception as exc:
                log.warning("[CTags] Failed to remove %s: %s", tags_file, exc)

    def cleanup_project_tags(self, project_path: str) -> None:
        with self._cache_lock:
            tags_file = self._tags_files.pop(project_path, None)

        if tags_file:
            try:
                if os.path.exists(tags_file):
                    os.remove(tags_file)
                    log.debug("[CTags] Removed project tags file: %s", tags_file)
            except Exception as exc:
                log.warning("[CTags] Failed to remove %s: %s", tags_file, exc)

        self.clear_cache()

    def cleanup_all_tags(self) -> None:
        with self._cache_lock:
            files_to_remove = list(self._tags_files.values())
            self._tags_files.clear()
            self._symbols_cache.clear()
            self._column_cache.clear()

        for tags_file in files_to_remove:
            try:
                if os.path.exists(tags_file):
                    os.remove(tags_file)
            except Exception:
                pass

        try:
            if os.path.exists(self._cache_dir):
                for name in os.listdir(self._cache_dir):
                    fp = os.path.join(self._cache_dir, name)
                    try:
                        if os.path.isfile(fp):
                            os.remove(fp)
                    except Exception:
                        pass
                log.debug("[CTags] Cleaned cache dir: %s", self._cache_dir)
        except Exception as exc:
            log.warning("[CTags] Error cleaning cache dir: %s", exc)

"""
CTags-based code indexer
"""
import os
import subprocess
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal as Signal

from taara_ide.core.base import IndexerBase
from taara_ide.config import SettingsManager
from taara_ide.utils import Result


@dataclass
class Symbol:
    """Represents a code symbol (function, variable, etc.)"""
    name: str
    kind: str
    file: str
    line: int
    pattern: str = ""
    scope: str = ""
    signature: str = ""
    
    @property
    def display_name(self) -> str:
        """Get display name with signature if available"""
        if self.signature:
            return f"{self.name}{self.signature}"
        return self.name
    
    @property
    def icon_name(self) -> str:
        """Get icon name based on kind"""
        icons = {
            'function': 'function',
            'prototype': 'function',
            'method': 'method',
            'class': 'class',
            'struct': 'struct',
            'enum': 'enum',
            'variable': 'variable',
            'member': 'field',
            'macro': 'macro',
            'typedef': 'type',
        }
        return icons.get(self.kind, 'symbol')


class CtagsWorker(QThread):
    """Worker thread for ctags indexing"""
    
    finished = Signal(bool, list)  # success, symbols
    
    def __init__(self, ctags_path: str, file_path: str):
        super().__init__()
        self.ctags_path = ctags_path
        self.file_path = file_path
    
    def run(self):
        try:
            result = subprocess.run(
                [
                    self.ctags_path,
                    '--output-format=json',
                    '--fields=+nKS',
                    '--kinds-c=+p',
                    '--kinds-c++=+p',
                    '-f', '-',
                    self.file_path
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.finished.emit(False, [])
                return
            
            symbols = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    symbol = Symbol(
                        name=data.get('name', ''),
                        kind=data.get('kind', ''),
                        file=data.get('path', self.file_path),
                        line=data.get('line', 0),
                        pattern=data.get('pattern', ''),
                        scope=data.get('scope', ''),
                        signature=data.get('signature', '')
                    )
                    symbols.append(symbol)
                except json.JSONDecodeError:
                    continue
            
            self.finished.emit(True, symbols)
            
        except Exception as e:
            self.finished.emit(False, [])


class CtagsHandler(IndexerBase):
    """CTags-based code indexer"""
    
    # Signal for ctags path dialog request
    ctags_path_required = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsManager()
        self._worker: Optional[CtagsWorker] = None
        self._symbols_cache: Dict[str, List[Symbol]] = {}
    
    @property
    def ctags_path(self) -> str:
        return self._settings.get_ctags_path()
    
    def is_available(self) -> bool:
        """Check if ctags is available"""
        try:
            result = subprocess.run(
                [self.ctags_path, '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def index_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Synchronously index a single file.
        Returns list of symbol dictionaries.
        """
        if not self.is_available():
            self.ctags_path_required.emit()
            return []
        
        try:
            result = subprocess.run(
                [
                    self.ctags_path,
                    '--output-format=json',
                    '--fields=+nKS',
                    '--kinds-c=+p',
                    '--kinds-c++=+p',
                    '-f', '-',
                    file_path
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            symbols = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    symbols.append(data)
                except json.JSONDecodeError:
                    continue
            
            return symbols
            
        except Exception:
            return []
    
    def index_file_async(self, file_path: str) -> None:
        """Asynchronously index a file"""
        if not self.is_available():
            self.ctags_path_required.emit()
            return
        
        self._worker = CtagsWorker(self.ctags_path, file_path)
        self._worker.finished.connect(self._on_index_finished)
        self._worker.start()
    
    def _on_index_finished(self, success: bool, symbols: list):
        if success and symbols:
            # Cache symbols by file
            if symbols:
                file_path = symbols[0].file
                self._symbols_cache[file_path] = symbols
            
            # Convert to dict format for signal
            symbol_dicts = [
                {
                    'name': s.name,
                    'kind': s.kind,
                    'line': s.line,
                    'signature': s.signature
                }
                for s in symbols
            ]
            
            file_path = symbols[0].file if symbols else ""
            self.symbols_updated.emit(file_path, symbol_dicts)
        
        self.indexing_finished.emit(success)
    
    def index_project(self, project_path: str) -> bool:
        """Index entire project directory"""
        if not self.is_available():
            self.ctags_path_required.emit()
            return False
        
        tags_file = os.path.join(project_path, 'tags')
        
        try:
            result = subprocess.run(
                [
                    self.ctags_path,
                    '-R',
                    '--fields=+nKS',
                    '--kinds-c=+p',
                    '--kinds-c++=+p',
                    '-f', tags_file,
                    project_path
                ],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def find_definition(self, symbol: str, context_file: str) -> Optional[tuple]:
        """Find symbol definition
        
        Returns:
            Tuple of (file_path, line, column) or None if not found
        """
        # First check cache
        for file_path, symbols in self._symbols_cache.items():
            for sym in symbols:
                if sym.name == symbol:
                    return (sym.file, sym.line, 0)
        
        # Fallback to searching project tags file
        project_dir = os.path.dirname(context_file)
        tags_file = os.path.join(project_dir, 'tags')
        
        if os.path.exists(tags_file):
            try:
                with open(tags_file, 'r') as f:
                    for line in f:
                        if line.startswith(symbol + '\t'):
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                file = parts[1]
                                return (file, 1, 0)
            except Exception:
                pass
        
        return None
    
    def find_references(self, symbol: str, project_path: str) -> List[tuple]:
        """Find all references to symbol"""
        # TODO: Implement reference finding (requires grep or LSP)
        return []
    
    def get_cached_symbols(self, file_path: str) -> List[Symbol]:
        """Get cached symbols for file"""
        return self._symbols_cache.get(file_path, [])
    
    def clear_cache(self) -> None:
        """Clear symbol cache"""
        self._symbols_cache.clear()

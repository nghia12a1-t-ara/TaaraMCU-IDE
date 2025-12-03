"""
CTags-based code indexer
"""
import os
import subprocess
import json
import hashlib
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal as Signal

from taara_ide.core.base import IndexerBase
from taara_ide.config import SettingsManager
from taara_ide.config.constants import get_ctags_cache_dir
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
        self._tags_files: Dict[str, str] = {}  # file_path -> tags_file_path
        self._cache_dir = get_ctags_cache_dir()
    
    def _get_tags_filename(self, source_path: str, is_project: bool = False) -> str:
        """
        Generate a unique tags filename based on source path.
        Uses hash to avoid conflicts and keep names short.
        """
        # Normalize path for consistent hashing
        normalized = os.path.normpath(os.path.abspath(source_path))
        # Create hash of full path
        path_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        # Get base name for readability
        base_name = os.path.basename(normalized)
        # Remove extension for files
        if not is_project:
            base_name = os.path.splitext(base_name)[0]
        # Sanitize name (remove special chars)
        safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in base_name)
        
        prefix = "project_" if is_project else "file_"
        return f"{prefix}{safe_name}_{path_hash}.tags"
    
    def _get_tags_file_path(self, source_path: str, is_project: bool = False) -> str:
        """Get full path to tags file in cache directory"""
        filename = self._get_tags_filename(source_path, is_project)
        return os.path.join(self._cache_dir, filename)
    
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
        
        tags_file = self._get_tags_file_path(file_path, is_project=False)
        
        # Track tags file for cleanup
        self._tags_files[file_path] = tags_file
        
        try:
            result = subprocess.run(
                [
                    self.ctags_path,
                    '--output-format=json',
                    '--fields=+nKS',
                    '--kinds-c=+p',
                    '--kinds-c++=+p',
                    '-f', tags_file,
                    file_path
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            symbols = []
            if os.path.exists(tags_file):
                with open(tags_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.startswith('!_TAG_'):
                            continue
                        try:
                            # Parse ctags format: name\tfile\tpattern;\tfields
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                symbol_data = {
                                    'name': parts[0],
                                    'file': file_path,
                                    'line': 1
                                }
                                # Extract additional fields
                                for part in parts[3:]:
                                    if ':' in part:
                                        key, value = part.split(':', 1)
                                        if key == 'line':
                                            symbol_data['line'] = int(value)
                                        elif key == 'kind':
                                            symbol_data['kind'] = value
                                        elif key == 'signature':
                                            symbol_data['signature'] = value
                                symbols.append(symbol_data)
                        except Exception:
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
        
        tags_file = self._get_tags_file_path(project_path, is_project=True)
        
        # Track tags file for cleanup
        self._tags_files[project_path] = tags_file
        
        try:
            result = subprocess.run(
                [
                    self.ctags_path,
                    '-R',
                    '--fields=+nKSz',
                    '--extras=+q',
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
        """Find definition of symbol, searching cache first then tags files"""
        # Search in cache first
        for file_path, symbols in self._symbols_cache.items():
            for sym in symbols:
                if sym.name == symbol:
                    column = self._find_column_in_file(sym.file, sym.line, symbol)
                    return (sym.file, sym.line, column)
        
        # First try to find project tags file for context file's project
        context_dir = os.path.dirname(os.path.abspath(context_file))
        
        # Look for project root (has .taara_project or is in tracked projects)
        project_root = None
        current_dir = context_dir
        max_depth = 10
        
        for _ in range(max_depth):
            if os.path.exists(os.path.join(current_dir, '.taara_project')):
                project_root = current_dir
                break
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent
        
        # Search in all tracked tags files
        tags_files_to_search = []
        
        # Add project tags file if found
        if project_root and project_root in self._tags_files:
            tags_files_to_search.append((self._tags_files[project_root], project_root))
        
        # Also search all project tags files in cache
        for source_path, tags_file in self._tags_files.items():
            if os.path.isdir(source_path) and tags_file not in [t[0] for t in tags_files_to_search]:
                tags_files_to_search.append((tags_file, source_path))
        
        for tags_file, base_path in tags_files_to_search:
            if not os.path.exists(tags_file):
                continue
            
            try:
                with open(tags_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.startswith('!_TAG_'):
                            continue
                        
                        parts = line.split('\t')
                        if len(parts) >= 3 and parts[0] == symbol:
                            relative_file = parts[1]
                            
                            # Build absolute path
                            if os.path.isabs(relative_file):
                                abs_file = relative_file
                            else:
                                abs_file = os.path.normpath(os.path.join(base_path, relative_file))
                            
                            line_num = 1
                            
                            # Extract line number
                            for part in parts[3:]:
                                part = part.strip()
                                if part.startswith('line:'):
                                    try:
                                        line_num = int(part.split(':')[1])
                                        break
                                    except (ValueError, IndexError):
                                        pass
                            
                            column = self._find_column_in_file(abs_file, line_num, symbol)
                            return (abs_file, line_num, column)
            except Exception as e:
                print(f"[CTags] Error parsing tags file {tags_file}: {e}")
        
        return None
    
    def _find_column_in_file(self, file_path: str, line_num: int, symbol: str) -> int:
        """
        Find the column position of symbol in the specified line of file.
        Returns 0 if not found.
        """
        try:
            if not os.path.exists(file_path):
                return 0
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if i == line_num:
                        # Find symbol position in line
                        # Try to find whole word match
                        import re
                        pattern = r'\b' + re.escape(symbol) + r'\b'
                        match = re.search(pattern, line)
                        if match:
                            return match.start()
                        
                        # Fallback: simple find
                        pos = line.find(symbol)
                        if pos >= 0:
                            return pos
                        
                        break
        except Exception as e:
            print(f"[CTags] Error finding column: {e}")
        
        return 0
    
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
    
    def cleanup_file_tags(self, file_path: str) -> None:
        """Remove tags file for a specific file"""
        if file_path in self._tags_files:
            tags_file = self._tags_files[file_path]
            try:
                if os.path.exists(tags_file):
                    os.remove(tags_file)
                    print(f"[CTags] Cleaned up tags file: {tags_file}")
            except Exception as e:
                print(f"[CTags] Failed to remove tags file: {e}")
            del self._tags_files[file_path]
        
        if file_path in self._symbols_cache:
            del self._symbols_cache[file_path]
    
    def cleanup_project_tags(self, project_path: str) -> None:
        """Remove tags file for entire project"""
        if project_path in self._tags_files:
            tags_file = self._tags_files[project_path]
            try:
                if os.path.exists(tags_file):
                    os.remove(tags_file)
                    print(f"[CTags] Cleaned up project tags file: {tags_file}")
            except Exception as e:
                print(f"[CTags] Failed to remove project tags file: {e}")
            del self._tags_files[project_path]
        
        self.clear_cache()
    
    def cleanup_all_tags(self) -> None:
        """Clean up all tracked tags files and entire cache directory"""
        # Remove tracked files
        for file_path in list(self._tags_files.keys()):
            tags_file = self._tags_files[file_path]
            try:
                if os.path.exists(tags_file):
                    os.remove(tags_file)
            except Exception:
                pass
        
        self._tags_files.clear()
        self.clear_cache()
        
        try:
            if os.path.exists(self._cache_dir):
                for filename in os.listdir(self._cache_dir):
                    file_path = os.path.join(self._cache_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
                print(f"[CTags] Cleaned up cache directory: {self._cache_dir}")
        except Exception as e:
            print(f"[CTags] Error cleaning cache directory: {e}")

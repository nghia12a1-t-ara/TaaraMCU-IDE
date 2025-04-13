"""
File operation utilities
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional, Generator
from taara_ide.utils.resource import Result


class FileUtils:
    """Utility class for file operations"""
    
    # Common source file extensions
    SOURCE_EXTENSIONS = {'.c', '.cpp', '.h', '.hpp', '.s', '.S', '.asm'}
    HEADER_EXTENSIONS = {'.h', '.hpp'}
    
    @staticmethod
    def ensure_dir(path: str) -> Result:
        """Ensure directory exists, create if not"""
        try:
            os.makedirs(path, exist_ok=True)
            return Result.ok(path)
        except OSError as e:
            return Result.fail(f"Failed to create directory: {e}")
    
    @staticmethod
    def safe_remove(path: str) -> Result:
        """Safely remove file or directory"""
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            return Result.ok()
        except OSError as e:
            return Result.fail(f"Failed to remove: {e}")
    
    @staticmethod
    def copy_tree(src: str, dst: str, ignore_patterns: Optional[List[str]] = None) -> Result:
        """Copy directory tree with optional ignore patterns"""
        try:
            ignore = None
            if ignore_patterns:
                ignore = shutil.ignore_patterns(*ignore_patterns)
            shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)
            return Result.ok(dst)
        except OSError as e:
            return Result.fail(f"Failed to copy: {e}")
    
    @staticmethod
    def find_files(
        directory: str, 
        extensions: Optional[set] = None,
        recursive: bool = True
    ) -> Generator[str, None, None]:
        """
        Find files with specific extensions in directory.
        
        Args:
            directory: Root directory to search
            extensions: Set of extensions to match (e.g., {'.c', '.h'})
            recursive: Whether to search subdirectories
        """
        if extensions is None:
            extensions = FileUtils.SOURCE_EXTENSIONS
            
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if Path(file).suffix.lower() in extensions:
                        yield os.path.join(root, file)
        else:
            for file in os.listdir(directory):
                filepath = os.path.join(directory, file)
                if os.path.isfile(filepath) and Path(file).suffix.lower() in extensions:
                    yield filepath
    
    @staticmethod
    def read_file(path: str, encoding: str = 'utf-8') -> Result:
        """Read file contents safely"""
        try:
            with open(path, 'r', encoding=encoding) as f:
                return Result.ok(f.read())
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    return Result.ok(f.read())
            except Exception as e:
                return Result.fail(f"Failed to read file: {e}")
        except OSError as e:
            return Result.fail(f"Failed to read file: {e}")
    
    @staticmethod
    def write_file(path: str, content: str, encoding: str = 'utf-8') -> Result:
        """Write content to file safely"""
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            return Result.ok(path)
        except OSError as e:
            return Result.fail(f"Failed to write file: {e}")
    
    @staticmethod
    def get_relative_path(path: str, base: str) -> str:
        """Get path relative to base directory"""
        return os.path.relpath(path, base)

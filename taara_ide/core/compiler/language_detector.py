"""
Language detection utilities
"""
from pathlib import Path
from typing import Optional
from enum import Enum


class Language(Enum):
    """Supported programming languages"""
    C = "c"
    CPP = "cpp"
    ASSEMBLY = "asm"
    HEADER = "header"
    PYTHON = "python"  # Added Python language support
    UNKNOWN = "unknown"


class LanguageDetector:
    """Detect programming language from file extension"""
    
    EXTENSION_MAP = {
        # C
        '.c': Language.C,
        # C++
        '.cpp': Language.CPP,
        '.cxx': Language.CPP,
        '.cc': Language.CPP,
        '.c++': Language.CPP,
        # Headers
        '.h': Language.HEADER,
        '.hpp': Language.HEADER,
        '.hxx': Language.HEADER,
        # Assembly
        '.s': Language.ASSEMBLY,
        '.S': Language.ASSEMBLY,
        '.asm': Language.ASSEMBLY,
        # Python
        '.py': Language.PYTHON,
        '.pyw': Language.PYTHON,
    }
    
    @classmethod
    def detect(cls, file_path: str) -> Language:
        """
        Detect language from file path.
        
        Args:
            file_path: Path to source file
            
        Returns:
            Detected Language enum value
        """
        suffix = Path(file_path).suffix.lower()
        # Special case for .S (capital) which is preprocessed assembly
        if file_path.endswith('.S'):
            return Language.ASSEMBLY
        return cls.EXTENSION_MAP.get(suffix, Language.UNKNOWN)
    
    @classmethod
    def is_source_file(cls, file_path: str) -> bool:
        """Check if file is a compilable source file"""
        lang = cls.detect(file_path)
        return lang in (Language.C, Language.CPP, Language.ASSEMBLY)
    
    @classmethod
    def is_header_file(cls, file_path: str) -> bool:
        """Check if file is a header file"""
        return cls.detect(file_path) == Language.HEADER
    
    @classmethod
    def get_compiler_flag(cls, language: Language) -> Optional[str]:
        """Get compiler language flag for GCC"""
        flags = {
            Language.C: "-x c",
            Language.CPP: "-x c++",
            Language.ASSEMBLY: "-x assembler-with-cpp",
            Language.PYTHON: "-x python",  # Added Python compiler flag
        }
        return flags.get(language)

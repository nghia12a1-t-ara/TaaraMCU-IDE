"""
C Project Configuration Manager
Handles .cproject files for multi-file C/C++ project builds
"""
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class CProjectConfig:
    """C Project Build Configuration"""
    # Project information
    project_name: str = ""
    project_version: str = "1.0.0"
    
    # Source configuration
    source_files: List[str] = field(default_factory=list)  # Specific files or patterns like "src/*.c"
    source_dirs: List[str] = field(default_factory=lambda: ["src"])  # Directories to search
    exclude_files: List[str] = field(default_factory=list)  # Files to exclude
    
    # Include configuration
    include_dirs: List[str] = field(default_factory=lambda: ["inc", "include"])
    system_includes: List[str] = field(default_factory=list)  # System include paths
    
    # Compiler settings
    compiler: str = "gcc"  # gcc, g++, clang, clang++
    c_standard: str = "c11"  # c89, c99, c11, c17
    cpp_standard: str = "c++11"  # c++98, c++11, c++14, c++17, c++20
    
    # Optimization
    optimization_level: str = "O2"  # O0, O1, O2, O3, Os, Og
    debug_symbols: bool = True
    
    # Defines
    defines: List[str] = field(default_factory=list)  # ["DEBUG", "USE_HAL_DRIVER"]
    
    # Compiler flags
    compiler_flags: List[str] = field(default_factory=lambda: ["-Wall", "-Wextra"])
    cpp_flags: List[str] = field(default_factory=list)  # Additional C++ flags
    
    # Linker settings
    linker_flags: List[str] = field(default_factory=list)
    libraries: List[str] = field(default_factory=list)  # ["m", "pthread"]
    library_paths: List[str] = field(default_factory=list)
    
    # Output configuration
    output_name: str = ""  # Auto-generated from project_name if empty
    output_dir: str = "build"
    output_type: str = "executable"  # executable, static_lib, shared_lib
    
    # Build configuration
    build_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "Debug": {
            "optimization_level": "Og",
            "debug_symbols": True,
            "defines": ["DEBUG"]
        },
        "Release": {
            "optimization_level": "O2",
            "debug_symbols": False,
            "defines": ["NDEBUG"]
        }
    })
    active_config: str = "Debug"
    
    # Preprocessor
    preprocessor_defs: Dict[str, str] = field(default_factory=dict)  # {"VERSION": "1.0", "MAX_SIZE": "1024"}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CProjectConfig':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_active_config(self) -> Dict[str, Any]:
        """Get active build configuration"""
        return self.build_configs.get(self.active_config, {})
    
    def merge_with_active_config(self) -> 'CProjectConfig':
        """Create a merged config with active build config applied"""
        merged = CProjectConfig(**asdict(self))
        active = self.get_active_config()
        
        # Override with active config values
        if "optimization_level" in active:
            merged.optimization_level = active["optimization_level"]
        if "debug_symbols" in active:
            merged.debug_symbols = active["debug_symbols"]
        if "defines" in active:
            merged.defines = list(set(merged.defines + active["defines"]))
        
        return merged


class CProjectConfigManager:
    """Manager for .cproject configuration files"""
    
    CONFIG_FILENAME = ".cproject"
    
    @staticmethod
    def create_default(project_path: str, project_name: str) -> CProjectConfig:
        """Create default configuration"""
        return CProjectConfig(
            project_name=project_name,
            output_name=project_name.lower().replace(" ", "_")
        )
    
    @staticmethod
    def load(project_path: str) -> Optional[CProjectConfig]:
        """Load .cproject file from project directory"""
        config_path = os.path.join(project_path, CProjectConfigManager.CONFIG_FILENAME)
        
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return CProjectConfig.from_dict(data)
        except Exception as e:
            print(f"Error loading .cproject: {e}")
            return None
    
    @staticmethod
    def save(project_path: str, config: CProjectConfig) -> bool:
        """Save configuration to .cproject file"""
        config_path = os.path.join(project_path, CProjectConfigManager.CONFIG_FILENAME)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving .cproject: {e}")
            return False
    
    @staticmethod
    def collect_source_files(project_path: str, config: CProjectConfig) -> List[str]:
        """Collect all source files based on configuration"""
        import glob
        
        files = set()
        
        # Add explicitly specified files
        for file_pattern in config.source_files:
            if os.path.isabs(file_pattern):
                pattern = file_pattern
            else:
                pattern = os.path.join(project_path, file_pattern)
            
            # Support glob patterns
            matched = glob.glob(pattern, recursive=True)
            files.update(matched)
        
        # Add files from source directories
        for src_dir in config.source_dirs:
            if os.path.isabs(src_dir):
                dir_path = src_dir
            else:
                dir_path = os.path.join(project_path, src_dir)
            
            if os.path.isdir(dir_path):
                # Find C/C++ files
                for ext in ['*.c', '*.cpp', '*.cc', '*.cxx']:
                    pattern = os.path.join(dir_path, '**', ext)
                    matched = glob.glob(pattern, recursive=True)
                    files.update(matched)
        
        # Remove excluded files
        exclude_set = set()
        for exclude_pattern in config.exclude_files:
            if os.path.isabs(exclude_pattern):
                pattern = exclude_pattern
            else:
                pattern = os.path.join(project_path, exclude_pattern)
            
            matched = glob.glob(pattern, recursive=True)
            exclude_set.update(matched)
        
        files -= exclude_set
        
        return sorted(list(files))
    
    @staticmethod
    def resolve_include_paths(project_path: str, config: CProjectConfig) -> List[str]:
        """Resolve include paths to absolute paths"""
        paths = []
        
        for inc_dir in config.include_dirs:
            if os.path.isabs(inc_dir):
                paths.append(inc_dir)
            else:
                abs_path = os.path.join(project_path, inc_dir)
                if os.path.isdir(abs_path):
                    paths.append(abs_path)
        
        # Add system includes
        paths.extend(config.system_includes)
        
        return paths

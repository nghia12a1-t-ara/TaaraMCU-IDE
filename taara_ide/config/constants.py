"""
Application constants and default values
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AppConstants:
    """Application-wide constants"""
    APP_NAME: str = "Taara IDE"
    VERSION: str = "1.0.0"
    ORGANIZATION: str = "TaaraIDE"
    
    # File patterns
    PROJECT_FILE: str = ".taara_project"
    CONFIG_FILE: str = "project_config.json"
    
    # Default paths
    DEFAULT_WORKSPACE: str = "~/TaaraProjects"
    THEMES_DIR: str = "themes"
    ICONS_DIR: str = "icons"
    TEMPLATES_DIR: str = "templates"


@dataclass(frozen=True)
class BuildConstants:
    """Build system constants"""
    # Compiler defaults
    DEFAULT_GCC_PATH: str = "arm-none-eabi-gcc"
    DEFAULT_GDB_PATH: str = "arm-none-eabi-gdb"
    DEFAULT_OBJCOPY_PATH: str = "arm-none-eabi-objcopy"
    DEFAULT_SIZE_PATH: str = "arm-none-eabi-size"
    
    # Build directories
    BUILD_DIR: str = "build"
    OUTPUT_DIR: str = "output"
    
    # Common compiler flags
    COMMON_FLAGS: List[str] = (
        "-Wall",
        "-fdata-sections",
        "-ffunction-sections",
    )
    
    # Optimization levels
    OPTIMIZATION_LEVELS: Dict[str, str] = None
    
    def __post_init__(self):
        # Use object.__setattr__ for frozen dataclass
        object.__setattr__(self, 'OPTIMIZATION_LEVELS', {
            "Debug": "-Og",
            "Release": "-O2",
            "Size": "-Os",
            "Speed": "-O3",
        })


@dataclass(frozen=True)  
class DebugConstants:
    """Debugger constants"""
    # GDB defaults
    DEFAULT_GDB_PORT: int = 3333
    DEFAULT_OPENOCD_PORT: int = 4444
    
    # Breakpoint types
    BREAKPOINT_HW: str = "hardware"
    BREAKPOINT_SW: str = "software"
    
    # Debug interfaces
    INTERFACES: tuple = ("ST-Link", "J-Link", "CMSIS-DAP", "Black Magic Probe")

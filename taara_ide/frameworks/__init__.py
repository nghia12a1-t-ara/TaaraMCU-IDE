"""
Framework support for different MCU families.

This module provides a plugin architecture for supporting various
microcontroller frameworks like STM32, ESP32, NRF52, etc.
"""
from .base import FrameworkBase, FrameworkInfo, ProjectTemplate
from .plugin_manager import PluginManager

__all__ = [
    'FrameworkBase',
    'FrameworkInfo',
    'ProjectTemplate',
    'PluginManager',
]

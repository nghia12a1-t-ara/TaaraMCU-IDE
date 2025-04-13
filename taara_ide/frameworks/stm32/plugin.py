"""
STM32 Framework Plugin Entry Point
"""
from .stm32_handler import STM32Handler

# Plugin class that will be discovered by PluginManager
Plugin = STM32Handler

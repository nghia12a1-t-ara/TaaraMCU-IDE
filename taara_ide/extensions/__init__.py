"""
Taara IDE Extension System

Package format: .tix  (Taara IDE eXtension)
A .tix file is a ZIP archive with the following layout:

    manifest.json   — required: extension metadata
    plugin.py       — required: exports Plugin(ExtensionBase)
    icon.png        — optional: 48×48 icon shown in the panel
    README.md       — optional: help text
    <any other files the extension needs>

The extension is unpacked into:
    <user_data>/extensions/<extension_id>/

ExtensionManager handles install / uninstall / enable / disable.
"""

from taara_ide.extensions.extension_base import ExtensionBase, ExtensionInfo, ExtensionCategory
from taara_ide.extensions.extension_manager import ExtensionManager

__all__ = ["ExtensionBase", "ExtensionInfo", "ExtensionCategory", "ExtensionManager"]

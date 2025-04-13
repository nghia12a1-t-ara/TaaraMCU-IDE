import os
import sys
from dataclasses import dataclass
from typing import Optional

@dataclass
class Result:
    success: bool
    error_code: Optional[str] = None
    message: Optional[str] = None

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

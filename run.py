#!/usr/bin/env python3
"""
Taara IDE Runner Script
Run this file from the project root directory.

Usage:
    python run.py
    
Or make it executable:
    chmod +x run.py
    ./run.py
"""
import sys
import os

# Ensure the taara_ide package is in the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from taara_ide.main import main

if __name__ == "__main__":
    main()

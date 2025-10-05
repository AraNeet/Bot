"""
Application Manager Bot - Source Package

This package contains all the core modules for the Application Manager Bot system.

Modules:
- runner: System initialization and management logic
- startup: Application startup sequence functions
- parser: Configuration loading and parsing
- window_helper: Window management functions
- image_helper: Image processing and template matching functions
"""

from . import system_initializer

__all__ = [
    "system_initializer",
]


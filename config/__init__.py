"""Configuration package for application settings and logging."""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from config.logging_config import setup_logging

__all__ = ['setup_logging']
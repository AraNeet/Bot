"""Bot package for application management operations."""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from bot.application_bot import ApplicationManagerBot

__all__ = ['ApplicationManagerBot']
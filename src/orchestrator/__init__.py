"""Orchestrator package for managing bot sequences."""

import sys
from pathlib import Path

# Add parent directory to path for proper imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from orchestrator.application_orchestrator import ApplicationOrchestrator

__all__ = ['ApplicationOrchestrator']
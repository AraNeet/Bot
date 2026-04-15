#!/usr/bin/env python3
"""
Vision Service — Shared Singleton Instances

Provides a single shared TextScanner instance used by all handlers.
This avoids creating 15+ separate PaddleOCR instances (each ~500MB RAM).

Usage:
    from src.workflow_module.actions.helpers.vision_service import scanner
    
    success, text = scanner.extract_text(image)
"""

from src.workflow_module.actions.helpers.ocr_utils import TextScanner

# Single shared instance — initialized lazily on first use
scanner = TextScanner()

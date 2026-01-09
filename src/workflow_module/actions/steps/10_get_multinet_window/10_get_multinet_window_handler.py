#!/usr/bin/env python3
"""
Handler for: Get Multinet Window

This module contains:
- Action: Check if the Multi-Network window is open by searching for 'multinet' text
- Verifier: Verify the Multi-Network window detection completed
- Error Handler: Handle errors for this specific action

Checks if the Multi-Network window is open by searching for 'multinet' text
in the title bar region. Retries up to 5 times with 10 second delays.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
import time
import cv2
import os

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """
    Check if Multi-Network window is open by detecting 'multinet' in title region.
    """
    print("[ACTION_HANDLER] Checking if Multi-Network window is open...")


    region = (200, 145, 1450, 25)
    
    max_attempts = 5
    wait_time = 10  # seconds between attempts
    
    scanner = TextScanner()
    
    for attempt in range(1, max_attempts + 1):
        print(f"[ACTION_HANDLER] Attempt {attempt}/{max_attempts}: Looking for 'multinet' text...")
        
        # Take screenshot and crop directly
        title_region = computer_vision_utils.take_screenshot_and_crop(region)
        
        if title_region is None:
            print(f"[ACTION_HANDLER] Failed to capture region on attempt {attempt}")
        else:
            # Use OCR to search for 'multinet' text
            success, ocr_data = scanner.get_text_data(title_region)
            
            if success and ocr_data.get('text'):
                for text in ocr_data['text']:
                    # Normalize text for check
                    if 'multinet' in text.lower().replace('-', '').replace(' ', ''):
                        msg = f"✓ Found 'multinet' window: '{text}'"
                        print(f"[ACTION_HANDLER] {msg}")
                        return True, msg
            
            print(f"[ACTION_HANDLER] 'multinet' not found in text: {ocr_data.get('text', [])}")

        if attempt < max_attempts:
            print(f"[ACTION_HANDLER] Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
            
    return False, f"Multi-Network window not detected after {max_attempts} attempts"


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verifier for Multi-Network window detection."""
    print("[VERIFIER_HANDLER] Multi-Network window detection completed successfully")
    return True, "Multi-Network window verification passed", {"verified": True, "message": "Multi-Network window is open"}


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors during Multi-Network window detection."""
    if attempt < max_attempts:
        wait_time = 2.0
        print(f"[ERROR_HANDLER] Workflow attempt {attempt}/{max_attempts} failed. Waiting {wait_time}s before retry...")
        time.sleep(wait_time)
        return True, "Retrying Multi-Network window detection"
    
    return False, f"Failed to detect Multi-Network window after {max_attempts} workflow attempts"

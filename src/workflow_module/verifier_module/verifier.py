#!/usr/bin/env python3
"""
Verifier Module - Shared Verification Functions

This module contains all the LOW-LEVEL verification functions that are shared
across different verifier handlers. These functions provide the core verification
capabilities that action-specific verifiers can build upon.

Core Functions:
- Text verification (OCR-based)
- Template matching verification
- UI state change verification
- Screenshot and image processing
- Utility functions for verification

This module is used by verifier_handlers.py to implement specific verification logic.
"""

import time
import cv2
from typing import Dict, Any, Tuple, Optional, List
from ..helpers import ocr_utils
from ..helpers import computer_vision_utils


# ============================================================================
# TEXT VERIFICATION FUNCTIONS
# ============================================================================

def verify_text_entered(expected_text: str, 
                        region: Optional[Tuple[int, int, int, int]] = None,
                        case_sensitive: bool = False) -> Tuple[bool, str]:
    """
    Verify that specific text was entered on the screen.
    
    Args:
        expected_text: Text to search for
        region: Optional region to limit search (x, y, width, height)
        case_sensitive: Whether search should be case-sensitive
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Search for text
        if region:
            success, found = ocr_utils.find_text_in_region(
                screenshot, expected_text, region, case_sensitive
            )
        else:
            success, found = ocr_utils.find_text(
                screenshot, expected_text, case_sensitive
            )
        
        if not success:
            return False, "OCR text search failed"
        
        if found:
            return True, f"Text '{expected_text}' found on screen"
        else:
            return False, f"Text '{expected_text}' not found on screen"
            
    except Exception as e:
        return False, f"Error verifying text entry: {e}"

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        if not text1 or not text2:
            return 0.0
        
        # Remove spaces and special characters for comparison
        clean1 = ''.join(c.lower() for c in text1 if c.isalnum())
        clean2 = ''.join(c.lower() for c in text2 if c.isalnum())
        
        if not clean1 or not clean2:
            return 0.0
        
        # Simple character overlap calculation
        matches = sum(1 for c in clean1 if c in clean2)
        similarity = matches / max(len(clean1), len(clean2))
        return similarity
        
    except Exception as e:
        print(f"[VERIFIER ERROR] Error calculating text similarity: {e}")
        return 0.0
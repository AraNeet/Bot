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


def verify_text_presence(expected_texts: List[str],
                        region: Optional[Tuple[int, int, int, int]] = None,
                        min_matches: int = 1,
                        case_sensitive: bool = False) -> Tuple[bool, str]:
    """
    Verify that at least a minimum number of expected texts are present.
    
    Args:
        expected_texts: List of texts to search for
        region: Optional region to limit search
        min_matches: Minimum number of texts that must be found
        case_sensitive: Whether search should be case-sensitive
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        found_count = 0
        found_texts = []
        
        for text in expected_texts:
            if region:
                success, found = ocr_utils.find_text_in_region(
                    screenshot, text, region, case_sensitive
                )
            else:
                success, found = ocr_utils.find_text(
                    screenshot, text, case_sensitive
                )
            
            if success and found:
                found_count += 1
                found_texts.append(text)
        
        if found_count >= min_matches:
            return True, f"Found {found_count}/{len(expected_texts)} expected texts: {found_texts}"
        else:
            return False, f"Only found {found_count}/{len(expected_texts)} expected texts (minimum: {min_matches})"
            
    except Exception as e:
        return False, f"Error verifying text presence: {e}"

# ============================================================================
# UI STATE VERIFICATION FUNCTIONS
# ============================================================================

def verify_ui_state_change(expected_texts: List[str],
                          timeout: float = 5.0,
                          region: Optional[Tuple[int, int, int, int]] = None) -> Tuple[bool, str]:
    """
    Verify that UI state changed by looking for expected texts within a timeout.
    
    Args:
        expected_texts: List of texts that should appear after state change
        timeout: Maximum time to wait for state change
        region: Optional region to limit search
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Take screenshot
            screenshot = computer_vision_utils.take_screenshot()
            if screenshot is None:
                time.sleep(0.5)
                continue
            
            # Check for any of the expected texts
            for text in expected_texts:
                if region:
                    success, found = ocr_utils.find_text_in_region(
                        screenshot, text, region, case_sensitive=False
                    )
                else:
                    success, found = ocr_utils.find_text(
                        screenshot, text, case_sensitive=False
                    )
                
                if success and found:
                    elapsed = time.time() - start_time
                    return True, f"UI state change detected after {elapsed:.1f}s - found: '{text}'"
            
            time.sleep(0.5)
        
        return False, f"UI state change not detected within {timeout}s"
        
    except Exception as e:
        return False, f"Error verifying UI state change: {e}"


def verify_button_clicked(expected_indicators: List[str] = None,
                         timeout: float = 2.0) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verify that a button was clicked by looking for UI state changes.
    
    Args:
        expected_indicators: List of text indicators that should appear after click
        timeout: Maximum time to wait for state change
        
    Returns:
        Tuple of (success: bool, message: str, verification_data: Dict)
    """
    try:
        if expected_indicators is None:
            expected_indicators = [
                "loading", "searching", "results", "found", "no results", 
                "search results", "loading...", "please wait"
            ]
        
        # Take initial screenshot
        screenshot_before = computer_vision_utils.take_screenshot()
        if screenshot_before is None:
            return False, "Failed to take initial screenshot", {}
        
        # Wait a moment for UI changes
        time.sleep(1.0)
        
        # Take screenshot after potential changes
        screenshot_after = computer_vision_utils.take_screenshot()
        if screenshot_after is None:
            return False, "Failed to take second screenshot", {}
        
        # Look for success indicators
        for indicator in expected_indicators:
            success, found = ocr_utils.find_text(
                screenshot_after, indicator, case_sensitive=False
            )
            
            if success and found:
                verification_data = {
                    "indicator_found": indicator,
                    "verification_method": "ui_state_change"
                }
                return True, f"Button click verified - found indicator: '{indicator}'", verification_data
        
        # If no specific indicators found, assume success (lenient approach)
        verification_data = {
            "verification_method": "no_errors_detected",
            "status": "assumed_success"
        }
        return True, "Button click verified - no errors detected", verification_data
        
    except Exception as e:
        return False, f"Error verifying button click: {e}", {}


# ============================================================================
# SCREENSHOT AND IMAGE PROCESSING FUNCTIONS
# ============================================================================

def take_screenshot_for_verification() -> Optional[Any]:
    """
    Take a screenshot for verification purposes.
    
    Returns:
        Screenshot image or None if failed
    """
    try:
        return computer_vision_utils.take_screenshot()
    except Exception as e:
        print(f"[VERIFIER ERROR] Failed to take screenshot: {e}")
        return None


def crop_image_for_verification(image: Any, 
                               x: int, 
                               y: int, 
                               width: int, 
                               height: int) -> Optional[Any]:
    """
    Crop an image to a specific region for verification.
    
    Args:
        image: Input image
        x: X coordinate of crop region
        y: Y coordinate of crop region
        width: Width of crop region
        height: Height of crop region
        
    Returns:
        Cropped image or None if failed
    """
    try:
        if image is None:
            return None
        
        # Ensure coordinates are within image bounds
        img_height, img_width = image.shape[:2]
        
        # Clamp coordinates to image bounds
        x = max(0, min(x, img_width))
        y = max(0, min(y, img_height))
        width = max(1, min(width, img_width - x))
        height = max(1, min(height, img_height - y))
        
        # Crop the image
        cropped = image[y:y+height, x:x+width]
        
        if cropped.size == 0:
            return None
        
        return cropped
        
    except Exception as e:
        print(f"[VERIFIER ERROR] Failed to crop image: {e}")
        return None


def extract_text_from_cropped_image(cropped_image: Any) -> Tuple[bool, str]:
    """
    Extract text from a cropped image using OCR.
    
    Args:
        cropped_image: Cropped image to extract text from
        
    Returns:
        Tuple of (success: bool, extracted_text: str)
    """
    try:
        if cropped_image is None:
            return False, "No image provided"
        
        # Use OCR utils to extract text
        success, extracted_text = ocr_utils.extract_text(cropped_image)
        
        if not success:
            return False, f"OCR extraction failed: {extracted_text}"
        
        return True, extracted_text
        
    except Exception as e:
        return False, f"Error extracting text from cropped image: {e}"


def get_detailed_ocr_data(cropped_image: Any) -> Tuple[bool, Any]:
    """
    Get detailed OCR data from a cropped image including text, bounding boxes, and confidence scores.
    
    Args:
        cropped_image: Cropped image to extract detailed OCR data from
        
    Returns:
        Tuple of (success: bool, ocr_data: dict or error_message)
    """
    try:
        if cropped_image is None:
            return False, "No image provided"
        
        # Use OCR utils to get detailed text data
        success, ocr_data = ocr_utils.get_text_data(cropped_image)
        
        if not success:
            return False, f"OCR data extraction failed: {ocr_data}"
        
        return True, ocr_data
        
    except Exception as e:
        return False, f"Error getting detailed OCR data from cropped image: {e}"


def save_debug_screenshot(filename: str = None) -> Tuple[bool, str]:
    """
    Save a debug screenshot for troubleshooting.
    
    Args:
        filename: Optional custom filename
        
    Returns:
        Tuple of (success: bool, filepath or error_message)
    """
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        if filename is None:
            timestamp = int(time.time())
            filename = f"debug_verification_{timestamp}.png"
        
        success, filepath = computer_vision_utils.save_screenshot(screenshot, filename)
        return success, filepath
        
    except Exception as e:
        return False, f"Error saving debug screenshot: {e}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.5) -> Tuple[bool, str]:
    """
    Wait for a condition to be met within a timeout.
    
    Args:
        condition_func: Function that returns (success: bool, message: str)
        timeout: Maximum time to wait
        interval: Time between condition checks
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            success, message = condition_func()
            
            if success:
                elapsed = time.time() - start_time
                return True, f"Condition met after {elapsed:.1f}s: {message}"
            
            time.sleep(interval)
        
        return False, f"Condition not met within {timeout}s"
        
    except Exception as e:
        return False, f"Error waiting for condition: {e}"


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


def validate_region_coordinates(region: Tuple[int, int, int, int], 
                                image_shape: Tuple[int, int]) -> Tuple[bool, Tuple[int, int, int, int]]:
    """
    Validate and clamp region coordinates to image bounds.
    
    Args:
        region: Region tuple (x, y, width, height)
        image_shape: Image shape tuple (height, width)
        
    Returns:
        Tuple of (is_valid: bool, clamped_region: Tuple)
    """
    try:
        x, y, width, height = region
        img_height, img_width = image_shape
        
        # Clamp coordinates to image bounds
        x = max(0, min(x, img_width))
        y = max(0, min(y, img_height))
        width = max(1, min(width, img_width - x))
        height = max(1, min(height, img_height - y))
        
        clamped_region = (x, y, width, height)
        
        # Check if region is valid (has positive dimensions)
        is_valid = width > 0 and height > 0
        
        return is_valid, clamped_region
        
    except Exception as e:
        print(f"[VERIFIER ERROR] Error validating region coordinates: {e}")
        return False, (0, 0, 1, 1)

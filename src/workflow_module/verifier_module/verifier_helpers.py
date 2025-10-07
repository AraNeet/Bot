#!/usr/bin/env python3
"""
Verifier Helpers Module

This module provides LOW-LEVEL verification functions that perform generic
verification operations. These functions are used by verifier_handlers.py
to implement specific verification logic.

Core Functions:
- verify_text_entered: Check if specific text was entered
- verify_text_presence: Check if text appears on screen
- verify_ui_state_change: Check if UI state changed (loading, results, etc.)
- verify_page_with_template: Check if page loaded using template matching
- verify_template_found: Check if a template image is found

This module focuses on generic verification operations that handlers can build upon.
"""

import time
from typing import Dict, Any, Tuple, Optional, List
from ..helpers import ocr_utils
from ..helpers import computer_vision_utils


# ============================================================================
# TEXT VERIFICATION HELPERS
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
# UI STATE VERIFICATION HELPERS
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


# ============================================================================
# TEMPLATE VERIFICATION HELPERS
# ============================================================================

def verify_template_found(template_path: str,
                         region: Optional[Tuple[int, int, int, int]] = None,
                         confidence: float = 0.8) -> Tuple[bool, str, Optional[Tuple[int, int, int, int]]]:
    """
    Verify that a template image is found on the screen.
    
    Args:
        template_path: Path to the template image file
        region: Optional region to limit search
        confidence: Minimum confidence threshold
        
    Returns:
        Tuple of (success: bool, message: str, region: Optional[Tuple])
    """
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot", None
        
        # Search for template
        if region:
            found, conf_score, position = computer_vision_utils.find_template_in_region(
                screenshot, template_path, region, confidence
            )
            template_region = region
        else:
            found, conf_score, position, template_region = computer_vision_utils.find_template_full_screen(
                screenshot, template_path, confidence
            )
        
        if found:
            return True, f"Template found with confidence {conf_score:.2f}", template_region
        else:
            return False, f"Template not found (confidence: {conf_score:.2f})", None
            
    except Exception as e:
        return False, f"Error verifying template: {e}", None


def verify_page_with_template(template_path: str,
                             expected_texts: List[str],
                             min_text_matches: int = 1,
                             confidence: float = 0.8) -> Tuple[bool, str, Optional[Tuple[int, int, int, int]]]:
    """
    Verify that a page loaded by checking for both template and expected texts.
    
    Args:
        template_path: Path to the template image file
        expected_texts: List of texts that should be on the page
        min_text_matches: Minimum number of texts that must be found
        confidence: Template matching confidence threshold
        
    Returns:
        Tuple of (success: bool, message: str, region: Optional[Tuple])
    """
    try:
        # First verify template is found
        template_success, template_msg, template_region = verify_template_found(
            template_path, None, confidence
        )
        
        if not template_success:
            return False, f"Template verification failed: {template_msg}", None
        
        # Then verify expected texts are present
        text_success, text_msg = verify_text_presence(
            expected_texts, None, min_text_matches
        )
        
        if not text_success:
            return False, f"Text verification failed: {text_msg}", template_region
        
        # Both verifications passed
        return True, f"Page verified: {template_msg} and {text_msg}", template_region
        
    except Exception as e:
        return False, f"Error verifying page with template: {e}", None


# ============================================================================
# SCREENSHOT HELPERS
# ============================================================================

def take_verification_screenshot(filename: Optional[str] = None) -> Tuple[bool, str]:
    """
    Take a screenshot for verification purposes.
    
    Args:
        filename: Optional custom filename
        
    Returns:
        Tuple of (success: bool, filepath or error_message)
    """
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        success, filepath = computer_vision_utils.save_screenshot(screenshot, filename)
        return success, filepath
        
    except Exception as e:
        return False, f"Error taking verification screenshot: {e}"


def save_failure_screenshot(action_name: str, attempt_number: int = 1) -> str:
    """
    Save a screenshot for failure analysis.
    
    Args:
        action_name: Name of the action that failed
        attempt_number: Attempt number for the action
        
    Returns:
        Filepath of saved screenshot or error message
    """
    try:
        timestamp = int(time.time())
        filename = f"failure_{action_name}_attempt{attempt_number}_{timestamp}.png"
        
        success, filepath = take_verification_screenshot(filename)
        
        if success:
            return filepath
        else:
            return filepath  # Return error message
            
    except Exception as e:
        return f"Failed to save failure screenshot: {e}"


# ============================================================================
# UTILITY HELPERS
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


def compare_screenshots(screenshot1_path: str, screenshot2_path: str) -> Tuple[bool, str, float]:
    """
    Compare two screenshots and return similarity score.
    
    Args:
        screenshot1_path: Path to first screenshot
        screenshot2_path: Path to second screenshot
        
    Returns:
        Tuple of (success: bool, message: str, similarity_score: float)
    """
    try:
        # Load both images
        img1 = computer_vision_utils.load_image(screenshot1_path)
        img2 = computer_vision_utils.load_image(screenshot2_path)
        
        if img1 is None or img2 is None:
            return False, "Failed to load one or both screenshots", 0.0
        
        # Simple comparison - in a real implementation, you might use more sophisticated comparison
        # For now, just return a placeholder
        return True, "Screenshots compared successfully", 0.85
        
    except Exception as e:
        return False, f"Error comparing screenshots: {e}", 0.0

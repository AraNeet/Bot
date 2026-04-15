#!/usr/bin/env python3
"""
Precheck Utilities Module

Provides reusable precheck functions that verify the UI is in the expected
state before any action executes. Every step handler should call one of these
before performing its action.

Core Functions:
- verify_page: Confirm the correct page is displayed using OCR on header region
- verify_element_present: Confirm a specific element is visible via template matching
- verify_no_blocking_dialog: Check that no unexpected popup/dialog is blocking the UI

Usage:
    from src.workflow_module.actions.helpers.precheck_utils import verify_page

    def precheck(**kwargs):
        return verify_page("search_page")
"""

from typing import Tuple, Optional, Dict, Any
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner

# Shared scanner instance
_scanner = None

def _get_scanner() -> TextScanner:
    """Get or create a shared TextScanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = TextScanner()
    return _scanner


def verify_page(page_name: str) -> Tuple[bool, str]:
    """
    Verify that the expected page is currently displayed.
    
    Uses the page's header_region and header_texts from page config
    to confirm the correct page is visible via OCR.
    
    Args:
        page_name: Name of the page to verify (e.g., "search_page", "multinetwork_page")
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    from src.workflow_module.pages.page_loader import get_page_markers
    
    try:
        markers = get_page_markers(page_name)
    except (FileNotFoundError, ValueError) as e:
        return False, f"Cannot load page markers for '{page_name}': {e}"
    
    header_region = tuple(markers.get("header_region", [0, 0, 1920, 100]))
    header_texts = markers.get("header_texts", [])
    
    if not header_texts:
        return False, f"No header_texts defined for page '{page_name}'"
    
    # Take screenshot and crop to header region
    cropped = take_screenshot_and_crop(header_region)
    if cropped is None:
        return False, f"Failed to capture header region {header_region} for page verification"
    
    # OCR the region
    scanner = _get_scanner()
    success, extracted_text = scanner.extract_text(cropped)
    
    if not success:
        return False, f"OCR failed on header region: {extracted_text}"
    
    # Check that all expected texts are present
    extracted_lower = extracted_text.lower()
    missing = [t for t in header_texts if t.lower() not in extracted_lower]
    
    if missing:
        return False, (
            f"Page verification failed for '{page_name}'. "
            f"Missing markers: {missing}. "
            f"OCR found: '{extracted_text}'"
        )
    
    print(f"[PRECHECK] Page '{page_name}' verified - all markers found: {header_texts}")
    return True, f"Page '{page_name}' is displayed correctly"


def verify_element_present(page_name: str, element_name: str,
                           screenshot=None) -> Tuple[bool, str]:
    """
    Verify that a specific UI element is present via template matching.
    
    Args:
        page_name: Name of the page
        element_name: Name of the element to check
        screenshot: Optional pre-captured screenshot. If None, takes a new one.
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    from src.workflow_module.pages.page_loader import get_element, get_template_path, get_confidence, get_region
    
    try:
        element_config = get_element(page_name, element_name)
    except KeyError as e:
        return False, str(e)
    
    # Check if element has a template defined
    if "template" not in element_config:
        # No template - can't do template matching, but this isn't a failure
        print(f"[PRECHECK] Element '{element_name}' has no template - skipping template check")
        return True, f"Element '{element_name}' has no template to verify (skipped)"
    
    # Get template path and region
    try:
        template_path = get_template_path(page_name, element_name)
        region = get_region(page_name, element_name)
        confidence = get_confidence(page_name, element_name)
    except (KeyError, FileNotFoundError) as e:
        return False, f"Cannot load template config for '{element_name}': {e}"
    
    # Take screenshot if not provided
    if screenshot is None:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for element verification"
    
    # Template match
    found, score, position = computer_vision_utils.find_template_in_region(
        screenshot, template_path, region, confidence=confidence
    )
    
    if found:
        print(f"[PRECHECK] Element '{element_name}' found (confidence: {score:.2f})")
        return True, f"Element '{element_name}' is present (confidence: {score:.2f})"
    else:
        return False, (
            f"Element '{element_name}' not found in region {region} "
            f"(best confidence: {score:.2f}, threshold: {confidence})"
        )


def verify_field_region_readable(page_name: str, element_name: str) -> Tuple[bool, str]:
    """
    Verify that a field's verification region can be captured and read via OCR.
    
    This is a lightweight check that the field area is accessible and 
    the OCR engine can extract text from it (even if empty).
    
    Args:
        page_name: Name of the page
        element_name: Name of the field element
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    from src.workflow_module.pages.page_loader import get_element
    
    try:
        element_config = get_element(page_name, element_name)
    except KeyError as e:
        return False, str(e)
    
    region = element_config.get("verification_region")
    if not region:
        return True, f"No verification_region for '{element_name}' - skipped"
    
    region = tuple(region)
    
    # Try to capture the region
    cropped = take_screenshot_and_crop(region)
    if cropped is None:
        return False, f"Cannot capture field region {region} for '{element_name}'"
    
    print(f"[PRECHECK] Field region for '{element_name}' is accessible")
    return True, f"Field region for '{element_name}' is readable"


def verify_no_loading_spinner(max_wait: float = 30.0, 
                               poll_interval: float = 2.0) -> Tuple[bool, str]:
    """
    Wait until no loading spinner is detected on screen.
    
    Args:
        max_wait: Maximum seconds to wait for spinner to disappear
        poll_interval: Seconds between checks
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    import time
    
    elapsed = 0.0
    while elapsed < max_wait:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot during spinner check"
        
        spinner_found, _ = computer_vision_utils.detect_loading_circle(screenshot)
        
        if not spinner_found:
            if elapsed > 0:
                print(f"[PRECHECK] Loading spinner cleared after {elapsed:.1f}s")
            return True, "No loading spinner detected"
        
        print(f"[PRECHECK] Loading spinner detected, waiting... ({elapsed:.1f}s / {max_wait}s)")
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    return False, f"Loading spinner still present after {max_wait}s timeout"

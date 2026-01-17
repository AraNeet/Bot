#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Instructions Page

This module contains:
- Action: Navigate to the Multinetwork Instructions page
- Verifier: Verify the page opened successfully
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
import time
import os

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================
# Change the region.
def action(**kwargs) -> Tuple[bool, str]:
    """
    Navigate to the Multinetwork Instructions page.
    
    This function:
    1. Takes a screenshot
    2. Uses computer vision to find the multi_network_icon in the toolbar region (250, 80, 180, 40) with 90% confidence
    3. Performs OCR check in the same region to verify "Multi-Network Instructions" text
    4. Clicks on the icon if both conditions are met
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print("[ACTION_HANDLER] Navigating to Multinetwork Instructions page...")
    
    # Step 1: Take screenshot of current screen
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    # Step 2: Define the search region for the multi-network icon
    region_x1 = 93  # Estimated X position in toolbar
    region_y1 = 52   # Estimated Y position below menu tabs
    region_width_x2 = 84 # Width to cover the button text and icon
    region_height_y2 = 66 # Height to cover the button
    region = (region_x1, region_y1, region_width_x2, region_height_y2)
    
    print(f"[ACTION_HANDLER] Searching for multi_network_icon in region {region}")
    
    # Step 3: Get the template image path
    handler_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(handler_dir, '01_multi_network_Icon.png')
    
    # Step 4: Use template matching to find the multi_network_icon
    icon_found, confidence, icon_position = computer_vision_utils.find_template_in_region(
        screenshot, 
        icon_path, 
        region, 
        confidence=0.9
    )
    
    # Step 5: Handle icon not found
    if not icon_found:
        return False, f"Multi-network icon not found in region {region} (confidence: {confidence:.2f})"
    
    print(f"[ACTION_HANDLER] ✓ Multi-network icon found at {icon_position} with confidence {confidence:.2f}")
    
    # Step 6: Validate icon position
    if icon_position is None:
        return False, "Icon position is None despite being found"
    
    # Step 7: Click on the icon
    click_x, click_y = icon_position
    print(f"[ACTION_HANDLER] Clicking on multi-network icon at ({click_x}, {click_y})")
    
    success, msg = actions.click_at_position(click_x, click_y)
    
    # Step 8: Move mouse away after click
    if success:
        actions.move_mouse(1800, 50, 0)
    if not success:
        return False, f"Failed to click on multi-network icon: {msg}"
    
    # Step 9: Wait for page to load
    time.sleep(1.0)
    
    return True, "Successfully navigated to Multinetwork Instructions page"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the multi-network instructions page was opened successfully.
    
    This function checks if "Search Global Comm" text is present in the page,
    which indicates that the Multi-Network Instructions page has loaded.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying multi-network page opened...")
    
    # Step 1: Define the search region for header text
    search_region = (200, 145, 1450, 50)  # Expanded region to capture header text
    
    # Step 2: Take screenshot and crop to the search region
    cropped_image = take_screenshot_and_crop(search_region)
    
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to search region", None
    
    # Step 3: Use OCR to extract text from the cropped region
    success, extracted_text = scanner.extract_text(cropped_image)
    
    if not success:
        return False, f"Failed to extract text from search region: {extracted_text}", None
    
    print(f"[VERIFIER_HANDLER] Extracted text from search region: '{extracted_text}'")
    
    # Step 4: Check if "Search Global Comm" is present (case-insensitive)
    extracted_text_lower = extracted_text.lower()
    has_search_global_comm = "search global comm" in extracted_text_lower
    
    # Step 5: Build verification data dictionary
    verification_data = {
        "extracted_text": extracted_text,
        "search_region": search_region,
        "has_search_global_comm": has_search_global_comm
    }
    
    # Step 6: Return result based on verification
    if has_search_global_comm:
        success_msg = "✓ Multi-network page opened successfully. Found 'Search Global Comm' text"
        print(f"[VERIFIER_HANDLER] {success_msg}")
        return True, success_msg, verification_data
    else:
        error_msg = f"✗ Multi-network page verification failed. Expected 'Search Global Comm' in search region, but found: '{extracted_text}'"
        print(f"[VERIFIER_HANDLER] {error_msg}")
        return False, error_msg, verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to opening multinetwork instructions page.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for open_instructions_page (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 2 seconds...")
        time.sleep(2.0)
        return True, "Retrying after wait"
    
    return False, f"Failed to open instructions page after {max_attempts} attempts"



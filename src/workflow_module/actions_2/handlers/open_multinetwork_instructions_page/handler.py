#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Instructions Page

This module contains:
- Action: Navigate to the Multinetwork Instructions page
- Verifier: Verify the page opened successfully
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner
import time

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

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
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region for Multi-Network Instructions button in toolbar
        # Based on typical toolbar layout: (x, y, width, height) format
        region_x = 93  # Estimated X position in toolbar
        region_y = 52   # Estimated Y position below menu tabs
        region_width = 84 # Width to cover the button text and icon
        region_height = 66 # Height to cover the button
        region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for multi_network_icon in region {region}")
        
        # Step 1: Use computer vision to find the multi_network_icon
        icon_found, confidence, icon_position = computer_vision_utils.find_template_in_region(
            screenshot, 
            'src/workflow_module/actions_2/assets/multi_network_Icon.png', 
            region, 
            confidence=0.9
        )
        
        if not icon_found:
            return False, f"Multi-network icon not found in region {region} (confidence: {confidence:.2f})"
        
        print(f"[ACTION_HANDLER] ✓ Multi-network icon found at {icon_position} with confidence {confidence:.2f}")
        
        # Step 2: Use OCR to check for "Multi-Network Instructions" text in the same region
        print(f"[ACTION_HANDLER] Checking for 'Multi-Network Instructions' text in region {region}")

        # Step 3: Click on the icon position
        if icon_position is None:
            return False, "Icon position is None despite being found"
        
        click_x, click_y = icon_position
        print(f"[ACTION_HANDLER] Clicking on multi-network icon at ({click_x}, {click_y})")
        
        
        success, msg = actions.click_at_position(click_x, click_y)
        if success:
            actions.move_mouse(1800, 50, 0)
        if not success:
            return False, f"Failed to click on multi-network icon: {msg}"
        # Wait a moment for the page to load
        time.sleep(1.0)
        
        return True, "Successfully navigated to Multinetwork Instructions page"
        
    except Exception as e:
        error_msg = f"Error navigating to Multinetwork Instructions page: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the multi-network instructions page was opened successfully.
    
    This function checks if the search fields are visible at the expected region (206, 152, 1439, 79)
    or if the words "order" or "agency" are present in that region.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying multi-network page opened...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the search fields region
        field_region = (206, 152, 1439, 79)
        
        # Crop the screenshot to the search fields region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to search fields region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from search fields region: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from search fields region: '{extracted_text}'")
        
        # Check if the words "order" or "agency" are present in the extracted text
        extracted_text_lower = extracted_text.lower()
        has_order = "order" in extracted_text_lower
        has_agency = "agency" in extracted_text_lower
        
        verification_data = {
            "extracted_text": extracted_text,
            "field_region": field_region,
            "has_order": has_order,
            "has_agency": has_agency
        }
        
        if has_order or has_agency:
            success_msg = f"✓ Multi-network page opened successfully. Found search fields with {'order' if has_order else ''}{' and ' if has_order and has_agency else ''}{'agency' if has_agency else ''}"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Multi-network page verification failed. Expected 'order' or 'agency' in search fields region, but found: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying multi-network page opening: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

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
    print(f"[ERROR_HANDLER] Handling error for open_multinetwork_instructions_page (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    # Check if we should retry
    if attempt < max_attempts:
        # Wait a bit longer before retry
        print(f"[ERROR_HANDLER] Will retry after waiting 2 seconds...")
        time.sleep(2.0)
        return True, "Retrying after wait"
    
    # Max attempts reached
    return False, f"Failed to open multinetwork instructions page after {max_attempts} attempts"


#!/usr/bin/env python3
"""
Handler for: Type Agency Name

This module contains:
- Action: Type agency name in the search field
- Verifier: Verify the agency name was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
from src.workflow_module.actions.helpers.field_utils import type_text_in_field
import time
import os

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(agency_name: str, **kwargs) -> Tuple[bool, str]:
    """
    Type agency name in the search field.
    
    Args:
        agency_name: The agency name to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering agency name: '{agency_name}'")
    
    # Step 1: Call helper to type text in agency field
    return type_text_in_field(
        field_label="agency",
        text_to_type=agency_name,
        press_enter=True,
        typing_interval=0.02
    )


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(agency_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the agency name was entered correctly using OCR similarity check.
    
    Args:
        agency_name: The agency name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying agency name entered: '{agency_name}'")
    
    if not agency_name:
        return True, "No agency name to verify", None
    
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot for verification", None
    
    name_dialog_region = (65, 25, 1217, 383)
    print(f"[VERIFIER_HANDLER] Checking for Name search dialog in region {name_dialog_region}")
    
    # Get the directory where this handler file is located
    handler_dir = os.path.dirname(os.path.abspath(__file__))
    close_button_path = os.path.join(handler_dir, '03_close_name_pop_up.png')
    
    close_button_found, close_confidence, close_position = computer_vision_utils.find_template_in_region(
        screenshot,
        close_button_path,
        name_dialog_region,
        confidence=0.8
    )
    
    if close_button_found and close_position:
        print(f"[VERIFIER_HANDLER] ✓ Name search dialog found (confidence: {close_confidence:.2f}), closing it...")
        click_x, click_y = close_position
        close_success, close_msg = actions.click_at_position(click_x, click_y)
        if close_success:
            print(f"[VERIFIER_HANDLER] ✓ Successfully closed Name search dialog - returning False to trigger retry")
            time.sleep(0.5)
            return False, "Name search dialog appeared and was closed - retrying action", None
        else:
            print(f"[VERIFIER_HANDLER] Warning: Failed to click close button: {close_msg}")
            return False, f"Failed to click close button: {close_msg}", None
    
    print(f"[VERIFIER_HANDLER] No Name search dialog found (confidence: {close_confidence:.2f}), proceeding with verification")
    
    field_region = (668, 180, 130, 40)
    cropped_image = take_screenshot_and_crop(field_region)
    if cropped_image is None:
        return False, "Failed to crop image to agency field region", None
    
    # Check for underline - primary verification method
    has_underline = computer_vision_utils.detect_underline(cropped_image)
    
    # Perform OCR for logging/debugging purposes
    success, extracted_text = scanner.extract_text(cropped_image)
    extracted_agency = extract_string_from_text(extracted_text, agency_name) if success else None
    
    print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
    print(f"[VERIFIER_HANDLER] Extracted agency name: '{extracted_agency}'")
    print(f"[VERIFIER_HANDLER] Underline detected: {has_underline}")
    
    verification_data = {
        "expected_text": agency_name,
        "extracted_text": extracted_text,
        "extracted_agency_name": extracted_agency,
        "has_underline": has_underline,
        "field_region": field_region
    }
    
    if has_underline:
        success_msg = f"✓ Agency name verified (Underline detected)"
        print(f"[VERIFIER_HANDLER] {success_msg}")
        return True, success_msg, verification_data
    else:
        error_msg = f"✗ Agency name verification failed (No underline detected)"
        print(f"[VERIFIER_HANDLER] {error_msg}")
        return False, error_msg, verification_data


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to entering agency name.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for type_agency_name (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    agency_name = kwargs.get('agency_name', '')
    
    if "Could not determine exact position" in error_msg or "Failed to crop" in error_msg:
        print(f"[ERROR_HANDLER] OCR or field detection issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry after waiting 1 second...")
            time.sleep(1.0)
            return True, "Retrying after OCR/detection failure"
    
    if "Failed to type" in error_msg:
        print(f"[ERROR_HANDLER] Typing issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry with slower typing...")
            return True, "Retrying with adjusted typing speed"
    
    if "Name search dialog" in error_msg or "retrying action" in error_msg.lower():
        print(f"[ERROR_HANDLER] Name search dialog detected - will retry action")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to Name search dialog appearance"
    
    if "verification failed" in error_msg.lower():
        print(f"[ERROR_HANDLER] Verification failed")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to verification failure"
    
    if attempt >= max_attempts:
        return False, f"Failed to enter agency name '{agency_name}' after {max_attempts} attempts"
    
    time.sleep(0.5)
    return True, "Retrying action"



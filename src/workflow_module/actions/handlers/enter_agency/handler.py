#!/usr/bin/env python3
"""
Handler for: Enter Agency

This module contains:
- Action: Enter agency name in the search field
- Verifier: Verify the agency name was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
import time

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(agency_name: str, **kwargs) -> Tuple[bool, str]:
    """Enter agency name in the search field."""
    print(f"[ACTION_HANDLER] Entering agency name: '{agency_name}'")
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        region_x, region_y, region_width, region_height = 206, 152, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image"
        
        success, found, bbox = scanner.find_text_with_position(cropped_image, "agency", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not find 'agency' text"
        
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        field_x = region_x + cropped_text_x
        field_y = region_y + cropped_text_y + text_height + 15
        
        click_success, _ = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, "Failed to click on agency field"
        
        time.sleep(0.5)
        actions.clear_field()
        time.sleep(0.2)
        
        type_success, type_msg = actions.type_text(agency_name, interval=0.02)
        if not type_success:
            return False, f"Failed to type agency name: {type_msg}"
        
        time.sleep(0.2)
        
        # Press Enter to confirm input
        enter_success, enter_msg = actions.press_key('enter', presses=1)
        if not enter_success:
            print(f"[ACTION_HANDLER] Warning: Failed to press Enter: {enter_msg}")
        
        time.sleep(0.5)
        return True, f"Successfully entered agency name: '{agency_name}'"
        
    except Exception as e:
        return False, f"Error entering agency name: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(agency_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the agency name was entered correctly using OCR similarity check.
    
    First checks for the Name search dialog popup and closes it if found.
    
    Args:
        agency_name: Expected agency name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying agency name entered: '{agency_name}'")
    
    if not agency_name:
        return True, "No agency name to verify", None
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot", None
        
        # Check for Name search dialog popup in region (65, 25, 1217, 383)
        name_dialog_region = (65, 25, 1217, 383)
        print(f"[VERIFIER_HANDLER] Checking for Name search dialog in region {name_dialog_region}")
        
        close_button_found, close_confidence, close_position = computer_vision_utils.find_template_in_region(
            screenshot,
            'src/workflow_module/actions/handlers/enter_agency/close_name_pop_up.png',
            name_dialog_region,
            confidence=0.8
        )
        
        # If popup found, close it and return False immediately (don't do second check)
        if close_button_found and close_position:
            print(f"[VERIFIER_HANDLER] ✓ Name search dialog found (confidence: {close_confidence:.2f}), closing it...")
            click_x, click_y = close_position
            close_success, close_msg = actions.click_at_position(click_x, click_y)
            if close_success:
                print(f"[VERIFIER_HANDLER] ✓ Successfully closed Name search dialog - returning False to trigger retry")
                time.sleep(0.5)  # Wait for dialog to close
                # Return False immediately - don't proceed with verification check
                return False, "Name search dialog appeared and was closed - retrying action", None
            else:
                print(f"[VERIFIER_HANDLER] Warning: Failed to click close button: {close_msg}")
                return False, f"Failed to click close button: {close_msg}", None
        
        # Only proceed with verification if popup was NOT found
        print(f"[VERIFIER_HANDLER] No Name search dialog found (confidence: {close_confidence:.2f}), proceeding with verification")
        
        field_region = (668, 180, 130, 40)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        extracted_agency = extract_string_from_text(extracted_text, agency_name)
        if not extracted_agency:
            error_msg = f"The agency name '{agency_name}' was not correct or not written correctly"
            return False, error_msg, None
        
        similarity = calculate_text_similarity(agency_name, extracted_agency)
        
        if similarity >= 0.80:
            return True, f"✓ Agency verified with {similarity:.2%} similarity", {"similarity": similarity}
        else:
            error_msg = f"The agency name '{agency_name}' was not correct or not written correctly"
            print(f"[VERIFIER_HANDLER] {error_msg} (Expected: '{agency_name}', Extracted: '{extracted_agency}', Similarity: {similarity:.2%})")
            return False, error_msg, {"similarity": similarity}
        
    except Exception as e:
        return False, f"Error verifying agency: {e}", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering agency."""
    print(f"[ERROR_HANDLER] Handling error for enter_agency (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    # Check if Name search dialog appeared and was closed
    if "Name search dialog" in error_msg or "retrying action" in error_msg.lower():
        print(f"[ERROR_HANDLER] Name search dialog detected - will retry action")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to Name search dialog appearance"
    
    # Default retry logic
    if attempt < max_attempts:
        time.sleep(0.5)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"

# All helper functions have been moved to helpers/verification_utils.py


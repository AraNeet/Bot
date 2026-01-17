#!/usr/bin/env python3
"""
Handler for: Type Advertiser Name

This module contains:
- Action: Type advertiser name in the search field
- Verifier: Verify the advertiser name was entered correctly
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

def action(advertiser_name: str, **kwargs) -> Tuple[bool, str]:
    """
    Type advertiser name in the search field.
    """
    print(f"[ACTION_HANDLER] Entering advertiser name: '{advertiser_name}'")
    
    # Step 1: Call helper to type text in advertiser field
    return type_text_in_field(
        field_label="advertiser",
        text_to_type=advertiser_name,
        press_enter=True,
        typing_interval=0.02
    )

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(advertiser_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the advertiser name was entered correctly using OCR similarity check."""
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    # Step 1: Handle empty advertiser name
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    # Step 2: Take screenshot for verification
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot for verification", None
    
    # Step 3: Define region to check for Name search dialog popup
    name_dialog_region = (0, 0, 500, 383)
    print(f"[VERIFIER_HANDLER] Checking for Name search dialog in region {name_dialog_region}")
    
    # Step 4: Get the close button template path
    handler_dir = os.path.dirname(os.path.abspath(__file__))
    close_button_path = os.path.join(handler_dir, '02_close_name_pop_up.png')
    
    # Step 5: Search for the Name search dialog close button
    close_button_found, close_confidence, close_position = computer_vision_utils.find_template_in_region(
        screenshot,
        close_button_path,
        name_dialog_region,
        confidence=0.8
    )
    
    # Step 6: If dialog found, close it and trigger retry
    if close_button_found and close_position:
        print(f"[VERIFIER_HANDLER] ✓ Name search dialog found (confidence: {close_confidence:.2f}), closing it...")
        # Step 6a: Get template dimensions to adjust click position
        template_img = computer_vision_utils.load_image(close_button_path)
        if template_img is not None:
             h, w = template_img.shape[:2]
             click_x, click_y = close_position
             click_x += w // 2  # Offset to right side for X-close button
        else:
             click_x, click_y = close_position

        # Step 6b: Click to close the dialog
        close_success, close_msg = actions.click_at_position(click_x, click_y)
        if close_success:
            print(f"[VERIFIER_HANDLER] ✓ Successfully closed Name search dialog - returning False to trigger retry")
            time.sleep(0.5)
            return False, "Name search dialog appeared and was closed - retrying action", None
        else:
            print(f"[VERIFIER_HANDLER] Warning: Failed to click close button: {close_msg}")
            return False, f"Failed to click close button: {close_msg}", None
    
    print(f"[VERIFIER_HANDLER] No Name search dialog found (confidence: {close_confidence:.2f}), proceeding with verification")
    
    # Step 7: Define field region and crop screenshot
    field_region = (370, 175, 160, 48)
    cropped_image = take_screenshot_and_crop(field_region)
    
    if cropped_image is None:
        return False, "Failed to crop image to advertiser field region", None
    
    # Step 8: Check for underline (primary verification method)
    has_underline = computer_vision_utils.detect_underline(cropped_image)
    
    # Step 9: Perform OCR for logging/debugging purposes
    success, extracted_text = scanner.extract_text(cropped_image)
    extracted_advertiser_name = extract_string_from_text(extracted_text, advertiser_name) if success else None
    
    print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
    print(f"[VERIFIER_HANDLER] Extracted advertiser name: '{extracted_advertiser_name}'")
    print(f"[VERIFIER_HANDLER] Underline detected: {has_underline}")
    
    # Step 10: Build verification data dictionary
    verification_data = {
        "expected_text": advertiser_name,
        "extracted_text": extracted_text,
        "extracted_advertiser_name": extracted_advertiser_name,
        "has_underline": has_underline,
        "field_region": field_region
    }
    
    # Step 11: Return result based on underline detection
    if has_underline:
        success_msg = f"✓ Advertiser name verified (Underline detected)"
        print(f"[VERIFIER_HANDLER] {success_msg}")
        return True, success_msg, verification_data
    else:
        error_msg = f"✗ Advertiser name verification failed (No underline detected)"
        print(f"[VERIFIER_HANDLER] {error_msg}")
        return False, error_msg, verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering advertiser name."""
    # Step 1: Log error details
    print(f"[ERROR_HANDLER] Handling error for type_advertiser_name (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    # Step 2: Extract advertiser name from kwargs
    advertiser_name = kwargs.get('advertiser_name', '')
    
    # Step 3: Handle OCR/field detection issues
    if "Could not determine exact position" in error_msg or "Failed to crop" in error_msg:
        print(f"[ERROR_HANDLER] OCR or field detection issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry after waiting 1 second...")
            time.sleep(1.0)
            return True, "Retrying after OCR/detection failure"
    
    # Step 4: Handle typing issues
    if "Failed to type" in error_msg:
        print(f"[ERROR_HANDLER] Typing issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry with slower typing...")
            return True, "Retrying with adjusted typing speed"
    
    # Step 5: Handle Name search dialog appearance
    if "Name search dialog" in error_msg or "retrying action" in error_msg.lower():
        print(f"[ERROR_HANDLER] Name search dialog detected - will retry action")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to Name search dialog appearance"
    
    # Step 6: Handle verification failures
    if "verification failed" in error_msg.lower():
        print(f"[ERROR_HANDLER] Verification failed")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to verification failure"
    
    # Step 7: Check if max attempts reached
    if attempt >= max_attempts:
        return False, f"Failed to enter advertiser name '{advertiser_name}' after {max_attempts} attempts"
    
    # Step 8: Default retry behavior
    time.sleep(0.5)
    return True, "Retrying action"



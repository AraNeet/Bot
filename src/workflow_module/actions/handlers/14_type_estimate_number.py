#!/usr/bin/env python3
"""
Handler for: Type Estimate Number

This module contains:
- Action: Type estimate number in the search field
- Verifier: Verify the estimate number was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_number_from_text
import time

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(estimate_number: str, **kwargs) -> Tuple[bool, str]:
    """
    Type estimate number in the search field.
    
    Args:
        estimate_number: The estimate number to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering estimate number: '{estimate_number}'")
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        region_x, region_y, region_width, region_height = 206, 152, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        success, found, bbox = scanner.find_text_with_position(cropped_image, "estimate", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'estimate' text in cropped image"
        
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x
        text_y = region_y + cropped_text_y
        field_x = text_x
        field_y = text_y + text_height + 15
        
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, f"Failed to click on estimate field: {click_msg}"
        
        time.sleep(0.5)
        clear_success, clear_msg = actions.clear_field()
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
        
        time.sleep(0.2)
        type_success, type_msg = actions.type_text(estimate_number, interval=0.02)
        if not type_success:
            return False, f"Failed to type estimate number: {type_msg}"
        
        time.sleep(0.5)
        print(f"[ACTION_HANDLER] ✓ Successfully entered estimate number: '{estimate_number}'")
        return True, f"Successfully entered estimate number: '{estimate_number}'"
        
    except Exception as e:
        error_msg = f"Error entering estimate number: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(estimate_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the estimate number was entered correctly using OCR similarity check.
    
    Args:
        estimate_number: The estimate number to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying estimate number entered: '{estimate_number}'")
    
    if not estimate_number:
        return True, "No estimate number to verify", None
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        field_region = (286, 175, 80, 48)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image to estimate field region", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text from estimate field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
        
        extracted_estimate_number = extract_number_from_text(extracted_text, estimate_number)
        if not extracted_estimate_number:
            error_msg = f"Could not extract estimate number from: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": estimate_number,
                "extracted_text": extracted_text,
                "extracted_estimate_number": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted estimate number: '{extracted_estimate_number}'")
        
        similarity = calculate_text_similarity(estimate_number, extracted_estimate_number)
        
        verification_data = {
            "expected_text": estimate_number,
            "extracted_text": extracted_text,
            "extracted_estimate_number": extracted_estimate_number,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Estimate number verified with {similarity:.2%} similarity (extracted: '{extracted_estimate_number}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Estimate number verification failed. Similarity: {similarity:.2%}"
            print(f"[VERIFIER_HANDLER] {error_msg} (Expected: '{estimate_number}', Extracted: '{extracted_estimate_number}')")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying estimate number entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to entering estimate number.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for type_estimate_number (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    estimate_number = kwargs.get('estimate_number', '')
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 0.5 seconds...")
        time.sleep(0.5)
        return True, "Retrying action"
    
    return False, f"Failed to enter estimate number '{estimate_number}' after {max_attempts} attempts"



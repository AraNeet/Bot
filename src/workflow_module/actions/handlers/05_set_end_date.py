#!/usr/bin/env python3
"""
Handler for: Set End Date

This module contains:
- Action: Set the end date in the search field
- Verifier: Verify the end date was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_date_from_text
import time

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(end_date: str, **kwargs) -> Tuple[bool, str]:
    """
    Set the end date in the search field.
    
    Args:
        end_date: The end date to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering end date: '{end_date}'")
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        region_x, region_y, region_width, region_height = 206, 152, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        success, found, bbox = scanner.find_text_with_position(cropped_image, "end", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'end' text in cropped image"
        
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        field_x = region_x + cropped_text_x
        field_y = region_y + cropped_text_y + text_height + 15
        
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, f"Failed to click on end date field: {click_msg}"
        
        time.sleep(0.5)
        clear_success, clear_msg = actions.clear_field()
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
        
        time.sleep(0.2)
        type_success, type_msg = actions.type_text(end_date, interval=0.02)
        if not type_success:
            return False, f"Failed to type end date: {type_msg}"
        
        time.sleep(0.5)
        print(f"[ACTION_HANDLER] ✓ Successfully entered end date: '{end_date}'")
        return True, f"Successfully entered end date: '{end_date}'"
        
    except Exception as e:
        error_msg = f"Error entering end date: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(end_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the end date was entered correctly using OCR similarity check.
    
    Args:
        end_date: The end date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying end date entered: '{end_date}'")
    
    if not end_date:
        return True, "No end date to verify", None
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        field_region = (1105, 175, 114, 50)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image to end date field region", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text from end date field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
        
        extracted_date = extract_date_from_text(extracted_text, end_date)
        if not extracted_date:
            error_msg = f"Could not extract date from: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": end_date,
                "extracted_text": extracted_text,
                "extracted_date": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted end date: '{extracted_date}'")
        
        similarity = calculate_text_similarity(end_date, extracted_date)
        
        verification_data = {
            "expected_text": end_date,
            "extracted_text": extracted_text,
            "extracted_date": extracted_date,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ End date verified with {similarity:.2%} similarity (extracted: '{extracted_date}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ End date verification failed. Similarity: {similarity:.2%}"
            print(f"[VERIFIER_HANDLER] {error_msg} (Expected: '{end_date}', Extracted: '{extracted_date}')")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying end date entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to entering end date.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for set_end_date (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    end_date = kwargs.get('end_date', '')
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 0.5 seconds...")
        time.sleep(0.5)
        return True, "Retrying action"
    
    return False, f"Failed to enter end date '{end_date}' after {max_attempts} attempts"



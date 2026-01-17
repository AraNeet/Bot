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
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
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
    """
    print(f"[ACTION_HANDLER] Entering estimate number: '{estimate_number}'")
    
    # Step 1: Take screenshot and crop
    region_x, region_y, region_width, region_height = 206, 152, 1439, 79
    cropped_image = take_screenshot_and_crop((region_x, region_y, region_width, region_height))
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to search region"
    
    # Step 2: Find 'estimate' text via OCR
    success, found, bbox = scanner.find_text_with_position(cropped_image, "estimate", case_sensitive=False)
    if not success or not found or bbox is None:
        return False, "Could not determine exact position of 'estimate' text in cropped image"
    
    # Step 3: Calculate field position
    cropped_text_x, cropped_text_y, text_width, text_height = bbox
    text_x = region_x + cropped_text_x
    text_y = region_y + cropped_text_y
    field_x = text_x
    field_y = text_y + text_height + 15
    
    # Step 4: Click field
    click_success, click_msg = actions.click_at_position(field_x, field_y)
    if not click_success:
        return False, f"Failed to click on estimate field: {click_msg}"
    
    time.sleep(0.5)
    
    # Step 5: Clear field
    clear_success, clear_msg = actions.clear_field()
    if not clear_success:
        print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
    
    time.sleep(0.2)
    
    # Step 6: Type estimate number
    type_success, type_msg = actions.type_text(estimate_number, interval=0.02)
    if not type_success:
        return False, f"Failed to type estimate number: {type_msg}"
    
    time.sleep(0.5)
    print(f"[ACTION_HANDLER] ✓ Successfully entered estimate number: '{estimate_number}'")
    return True, f"Successfully entered estimate number: '{estimate_number}'"


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(estimate_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the estimate number was entered correctly using OCR similarity check."""
    print(f"[VERIFIER_HANDLER] Verifying estimate number entered: '{estimate_number}'")
    
    # Step 1: Handle empty estimate number
    if not estimate_number:
        return True, "No estimate number to verify", None
    
    # Step 2: Define field region and crop screenshot
    field_region = (286, 175, 80, 48)
    cropped_image = take_screenshot_and_crop(field_region)
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to estimate field region", None
    
    # Step 3: Extract text using OCR
    success, extracted_text = scanner.extract_text(cropped_image)
    if not success:
        return False, f"Failed to extract text from estimate field: {extracted_text}", None
    
    print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
    
    # Step 4: Extract estimate number from OCR text
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
    
    # Step 5: Calculate similarity between expected and extracted
    similarity = calculate_text_similarity(estimate_number, extracted_estimate_number)
    
    # Step 6: Build verification data dictionary
    verification_data = {
        "expected_text": estimate_number,
        "extracted_text": extracted_text,
        "extracted_estimate_number": extracted_estimate_number,
        "similarity_score": similarity,
        "field_region": field_region,
        "threshold": 0.80
    }
    
    # Step 7: Return result based on similarity threshold
    if similarity >= 0.80:
        success_msg = f"✓ Estimate number verified with {similarity:.2%} similarity (extracted: '{extracted_estimate_number}')"
        print(f"[VERIFIER_HANDLER] {success_msg}")
        return True, success_msg, verification_data
    else:
        error_msg = f"✗ Estimate number verification failed. Similarity: {similarity:.2%}"
        print(f"[VERIFIER_HANDLER] {error_msg} (Expected: '{estimate_number}', Extracted: '{extracted_estimate_number}')")
        return False, error_msg, verification_data


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering estimate number."""
    print(f"[ERROR_HANDLER] Handling error for type_estimate_number (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    estimate_number = kwargs.get('estimate_number', '')
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 0.5 seconds...")
        time.sleep(0.5)
        return True, "Retrying action"
    
    return False, f"Failed to enter estimate number '{estimate_number}' after {max_attempts} attempts"

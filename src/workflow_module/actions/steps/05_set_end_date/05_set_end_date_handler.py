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
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_date_from_text
from src.workflow_module.actions.helpers.field_utils import type_text_in_field
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
    
    # Step 1: Call helper to type text in end date field
    return type_text_in_field(
        field_label="end",
        text_to_type=end_date,
        press_enter=False,
        typing_interval=0.02
    )


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
    
    field_region = (1105, 175, 114, 50)
    cropped_image = take_screenshot_and_crop(field_region)
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



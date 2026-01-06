#!/usr/bin/env python3
"""
Handler for: Click Search Button

This module contains:
- Action: Click the search button to submit the search form
- Verifier: Verify the search button was clicked and results loaded
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
from src.workflow_module.actions.helpers.table_utils import get_results_count
import time
import cv2

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """Click the search button to submit the search form."""
    print("[ACTION_HANDLER] Clicking search button...")
    
    # Step 1: Take screenshot
    region_x, region_y, region_width, region_height = 206, 170, 1439, 79
    cropped_image = take_screenshot_and_crop((region_x, region_y, region_width, region_height))
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to search region"
    
    # Save debug image
    debug_filename = f"search_button_search_region_{int(time.time())}.png"
    cv2.imwrite(debug_filename, cropped_image)
    
    # Step 2: Find search button via OCR
    success, found, bbox = scanner.find_text_with_position(cropped_image, "search", case_sensitive=False)
    if not success or not found or bbox is None:
        return False, "Could not determine exact position of 'search' text"
    
    # Step 3: Click on the search button
    cropped_text_x, cropped_text_y, text_width, text_height = bbox
    text_x = region_x + cropped_text_x
    text_y = region_y + cropped_text_y
    
    button_x = text_x + (text_width // 2)
    button_y = text_y + (text_height // 2)
    
    click_success, click_msg = actions.click_at_position(button_x, button_y)
    if not click_success:
        return False, f"Failed to click on search button: {click_msg}"

    time.sleep(0.5)
    
    return True, "Successfully clicked search button"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the search button was clicked successfully and results are present."""
    print("[VERIFIER_HANDLER] Verifying search button clicked and checking results...")
    
    # Wait 2 seconds before verification
    time.sleep(2.0)
    
    field_region = (205, 225, 50, 30)
    cropped_image = take_screenshot_and_crop(field_region)
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to order field region", None
    
    success, extracted_text = scanner.extract_text(cropped_image)
    if not success:
        return False, f"Failed to extract text from order field: {extracted_text}", None
    
    extracted_results = extract_string_from_text(extracted_text, "Results")
    if not extracted_results:
        return False, f"Expected 'Results', could not extract from: '{extracted_text}'", None
    
    similarity = calculate_text_similarity("Results", extracted_results)
    
    # Check results count
    results_count = get_results_count()
    if results_count is None:
        return False, "Failed to extract results count from the page", None
    
    verification_data = {
        "expected_text": "Results",
        "extracted_text": extracted_text,
        "similarity_score": similarity,
        "results_count": results_count
    }
    
    # Check if results count is greater than 0
    if results_count == 0:
        return False, f"✗ Search returned 0 results. No data found matching the search criteria.", verification_data
    
    if similarity >= 0.80:
        return True, f"✓ Search results verified with {similarity:.2%} similarity. Found {results_count} result(s).", verification_data
    else:
        return False, f"✗ Search button verification failed. Similarity: {similarity:.2%}", verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to clicking search button.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for click_search_button (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 1 second...")
        time.sleep(1.0)
        return True, "Retrying action"
    
    return False, f"Failed to click search button after {max_attempts} attempts"

# All helper functions have been moved to helpers/verification_utils.py




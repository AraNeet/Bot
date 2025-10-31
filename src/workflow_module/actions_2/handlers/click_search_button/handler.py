#!/usr/bin/env python3
"""
Handler for: Click Search Button

This module contains:
- Action: Click the search button to submit the search form
- Verifier: Verify the search button was clicked and results loaded
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner
from src.workflow_module.actions_2.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
import time
import cv2

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """Click the search button to submit the search form."""
    print("[ACTION_HANDLER] Clicking search button...")
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        region_x, region_y, region_width, region_height = 206, 170, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        # Save debug image
        debug_filename = f"search_button_search_region_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        
        success, found, bbox = scanner.find_text_with_position(cropped_image, "search", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'search' text"
        
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x
        text_y = region_y + cropped_text_y
        
        button_x = text_x + (text_width // 2)
        button_y = text_y + (text_height // 2)
        
        click_success, click_msg = actions.click_at_position(button_x, button_y)
        if not click_success:
            return False, f"Failed to click on search button: {click_msg}"
        
        actions.move_mouse(1400, 288, 0)
        time.sleep(0.5)
        
        return True, "Successfully clicked search button"
        
    except Exception as e:
        return False, f"Error clicking search button: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the search button was clicked successfully."""
    print("[VERIFIER_HANDLER] Verifying search button clicked...")
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        field_region = (205, 225, 50, 30)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        extracted_results = extract_string_from_text(extracted_text, "Results")
        if not extracted_results:
            return False, f"Expected 'Results', could not extract from: '{extracted_text}'", None
        
        similarity = calculate_text_similarity("Results", extracted_results)
        
        verification_data = {
            "expected_text": "Results",
            "extracted_text": extracted_text,
            "similarity_score": similarity
        }
        
        if similarity >= 0.80:
            return True, f"✓ Search results verified with {similarity:.2%} similarity", verification_data
        else:
            return False, f"✗ Search button verification failed. Similarity: {similarity:.2%}", verification_data
        
    except Exception as e:
        return False, f"Error verifying search button click: {e}", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to clicking search button."""
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"

# All helper functions have been moved to helpers/verification_utils.py


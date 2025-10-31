#!/usr/bin/env python3
"""
Handler for: Enter Deal Number

This module contains:
- Action: Enter deal number in the search field
- Verifier: Verify the deal number was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner
from src.workflow_module.actions_2.helpers.verification_utils import calculate_text_similarity, extract_number_from_text
import time

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(deal_number: str, **kwargs) -> Tuple[bool, str]:
    """Enter deal number in the search field."""
    print(f"[ACTION_HANDLER] Entering deal number: '{deal_number}'")
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        region_x, region_y, region_width, region_height = 206, 152, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        success, found, bbox = scanner.find_text_with_position(cropped_image, "deal", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'deal' text"
        
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x
        text_y = region_y + cropped_text_y
        field_x = text_x
        field_y = text_y + text_height + 15
        
        click_success, _ = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, "Failed to click on deal field"
        
        time.sleep(0.5)
        actions.clear_field()
        time.sleep(0.2)
        
        type_success, type_msg = actions.type_text(deal_number, interval=0.02)
        if not type_success:
            return False, f"Failed to type deal number: {type_msg}"
        
        time.sleep(0.5)
        return True, f"Successfully entered deal number: '{deal_number}'"
        
    except Exception as e:
        return False, f"Error entering deal number: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(deal_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the deal number was entered correctly."""
    if not deal_number:
        return True, "No deal number to verify", None
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        field_region = (286, 175, 80, 48)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image to deal field region", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        extracted_deal_number = extract_number_from_text(extracted_text, deal_number)
        if not extracted_deal_number:
            return False, f"Could not extract deal number from: '{extracted_text}'", None
        
        similarity = calculate_text_similarity(deal_number, extracted_deal_number)
        
        verification_data = {
            "expected_text": deal_number,
            "extracted_text": extracted_text,
            "similarity_score": similarity
        }
        
        if similarity >= 0.80:
            return True, f"✓ Deal number verified with {similarity:.2%} similarity", verification_data
        else:
            return False, f"✗ Deal number verification failed. Similarity: {similarity:.2%}", verification_data
        
    except Exception as e:
        return False, f"Error verifying deal number: {e}", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering deal number."""
    if attempt < max_attempts:
        time.sleep(0.5)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"

# All helper functions have been moved to helpers/verification_utils.py


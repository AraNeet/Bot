#!/usr/bin/env python3
"""
Handler for: Enter Agency

This module contains:
- Action: Enter agency name in the search field
- Verifier: Verify the agency name was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner
from src.workflow_module.actions_2.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
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
        
        time.sleep(0.5)
        return True, f"Successfully entered agency name: '{agency_name}'"
        
    except Exception as e:
        return False, f"Error entering agency name: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(agency_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the agency name was entered correctly."""
    if not agency_name:
        return True, "No agency name to verify", None
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot", None
        
        field_region = (668, 180, 130, 40)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        
        extracted_agency = extract_string_from_text(extracted_text, agency_name)
        if not extracted_agency:
            return False, f"Could not extract agency from: '{extracted_text}'", None
        
        similarity = calculate_text_similarity(agency_name, extracted_agency)
        
        if similarity >= 0.80:
            return True, f"✓ Agency verified with {similarity:.2%} similarity", {"similarity": similarity}
        else:
            return False, f"✗ Agency verification failed. Similarity: {similarity:.2%}", {"similarity": similarity}
        
    except Exception as e:
        return False, f"Error verifying agency: {e}", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering agency."""
    if attempt < max_attempts:
        time.sleep(0.5)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"

# All helper functions have been moved to helpers/verification_utils.py


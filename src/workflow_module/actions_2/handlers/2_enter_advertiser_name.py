#!/usr/bin/env python3
"""
Handler for: Enter Advertiser Name

This module contains:
- Action: Enter advertiser name in the search field
- Verifier: Verify the advertiser name was entered correctly
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

def action(advertiser_name: str, **kwargs) -> Tuple[bool, str]:
    """
    Enter advertiser name in the search field.
    
    This function:
    1. Takes a screenshot
    2. Uses OCR to find the word "advertiser" within region (206, 152, 1439, 79)
    3. Clicks 15 pixels below the "advertiser" text
    4. Enters the advertiser name in the field
    
    Args:
        advertiser_name: Name of advertiser to enter
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    print(f"[ACTION_HANDLER] Entering advertiser name: '{advertiser_name}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Define the region to search for "advertiser" word
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'advertiser' word in region {search_region}")
        
        # Crop the image to the search region for better OCR accuracy
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        
        print(f"[ACTION_HANDLER] Cropped image to region {search_region} for OCR search")
        
        success, found, bbox = scanner.find_text_with_position(
            cropped_image,
            "advertiser",
            case_sensitive=False
        )
        
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'advertiser' text in cropped image"
        
        # Convert cropped image coordinates back to full screenshot coordinates
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x
        text_y = region_y + cropped_text_y
        
        print(f"[ACTION_HANDLER] ✓ 'advertiser' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        
        # Calculate the input field position 15 pixels below the "advertiser" text
        field_spacing = 15
        field_x = text_x
        field_y = text_y + text_height + field_spacing
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'advertiser' text")
        
        # Click on the input field
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, f"Failed to click on advertiser field: {click_msg}"
        
        time.sleep(0.5)
        
        # Clear any existing text
        clear_success, clear_msg = actions.clear_field()
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
        
        time.sleep(0.2)
        
        # Type the advertiser name
        type_success, type_msg = actions.type_text(advertiser_name, interval=0.02)
        if not type_success:
            return False, f"Failed to type advertiser name: {type_msg}"
        
        time.sleep(0.5)
        
        print(f"[ACTION_HANDLER] ✓ Successfully entered advertiser name: '{advertiser_name}'")
        return True, f"Successfully entered advertiser name: '{advertiser_name}'"
        
    except Exception as e:
        error_msg = f"Error entering advertiser name: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(advertiser_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the advertiser name was entered correctly using OCR similarity check.
    
    Args:
        advertiser_name: Expected advertiser name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Define the advertiser field region
        field_region = (370, 175, 160, 48)
        
        # Crop the screenshot to the advertiser field region
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to advertiser field region", None
        
        # Use OCR to extract text from the cropped field region
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from advertiser field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
        
        # Extract advertiser name from the OCR text using similarity matching
        extracted_advertiser_name = extract_string_from_text(extracted_text, advertiser_name)
        
        if not extracted_advertiser_name:
            error_msg = f"✗ Advertiser name verification failed. Expected: '{advertiser_name}', Could not extract from OCR text: '{extracted_text}'"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            verification_data = {
                "expected_text": advertiser_name,
                "extracted_text": extracted_text,
                "extracted_advertiser_name": None,
                "field_region": field_region,
                "threshold": 0.80
            }
            return False, error_msg, verification_data
        
        print(f"[VERIFIER_HANDLER] Extracted advertiser name: '{extracted_advertiser_name}'")
        
        # Perform similarity check (80% threshold)
        similarity = calculate_text_similarity(advertiser_name, extracted_advertiser_name)
        
        verification_data = {
            "expected_text": advertiser_name,
            "extracted_text": extracted_text,
            "extracted_advertiser_name": extracted_advertiser_name,
            "similarity_score": similarity,
            "field_region": field_region,
            "threshold": 0.80
        }
        
        if similarity >= 0.80:
            success_msg = f"✓ Advertiser name verified with {similarity:.2%} similarity (extracted: '{extracted_advertiser_name}')"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Advertiser name verification failed. Expected: '{advertiser_name}', Extracted: '{extracted_advertiser_name}', Similarity: {similarity:.2%} (threshold: 80%)"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying advertiser name entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to entering advertiser name.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context (includes advertiser_name)
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for enter_advertiser_name (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    advertiser_name = kwargs.get('advertiser_name', '')
    
    # Check if error is related to OCR or field detection
    if "Could not determine exact position" in error_msg or "Failed to crop" in error_msg:
        print(f"[ERROR_HANDLER] OCR or field detection issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry after waiting 1 second...")
            time.sleep(1.0)
            return True, "Retrying after OCR/detection failure"
    
    # Check if error is related to typing
    if "Failed to type" in error_msg:
        print(f"[ERROR_HANDLER] Typing issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry with slower typing...")
            return True, "Retrying with adjusted typing speed"
    
    # Check if verification failed
    if "verification failed" in error_msg.lower():
        print(f"[ERROR_HANDLER] Verification failed")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to verification failure"
    
    # Max attempts reached or unknown error
    if attempt >= max_attempts:
        return False, f"Failed to enter advertiser name '{advertiser_name}' after {max_attempts} attempts"
    
    # Default retry
    time.sleep(0.5)
    return True, "Retrying action"

# All helper functions have been moved to helpers/verification_utils.py


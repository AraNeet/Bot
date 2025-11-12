#!/usr/bin/env python3
"""
Handler for: Type Advertiser Name

This module contains:
- Action: Type advertiser name in the search field
- Verifier: Verify the advertiser name was entered correctly
- Error Handler: Handle errors for this specific action
"""
#Unify this with the other type_text actions.
from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
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
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[ACTION_HANDLER] Searching for 'advertiser' word in region {search_region}")
        
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
        
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x
        text_y = region_y + cropped_text_y
        
        print(f"[ACTION_HANDLER] ✓ 'advertiser' text found at ({text_x}, {text_y}) with size {text_width}x{text_height}")
        
        field_spacing = 15
        field_x = text_x
        field_y = text_y + text_height + field_spacing
        
        print(f"[ACTION_HANDLER] Calculated field position: ({field_x}, {field_y}) - 15px below 'advertiser' text")
        
        click_success, click_msg = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, f"Failed to click on advertiser field: {click_msg}"
        
        time.sleep(0.5)
        clear_success, clear_msg = actions.clear_field()
        if not clear_success:
            print(f"[ACTION_HANDLER] Warning: Failed to clear field: {clear_msg}")
        
        time.sleep(0.2)
        
        type_success, type_msg = actions.type_text(advertiser_name, interval=0.02)
        if not type_success:
            return False, f"Failed to type advertiser name: {type_msg}"
        
        time.sleep(0.2)
        
        enter_success, enter_msg = actions.press_key('enter', presses=1)
        if not enter_success:
            print(f"[ACTION_HANDLER] Warning: Failed to press Enter: {enter_msg}")
        
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
    """Verify that the advertiser name was entered correctly using OCR similarity check."""
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        name_dialog_region = (65, 25, 1217, 383)
        print(f"[VERIFIER_HANDLER] Checking for Name search dialog in region {name_dialog_region}")
        
        # Get the directory where this handler file is located
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        close_button_path = os.path.join(handler_dir, 'close_name_pop_up.png')
        
        close_button_found, close_confidence, close_position = computer_vision_utils.find_template_in_region(
            screenshot,
            close_button_path,
            name_dialog_region,
            confidence=0.8
        )
        
        if close_button_found and close_position:
            print(f"[VERIFIER_HANDLER] ✓ Name search dialog found (confidence: {close_confidence:.2f}), closing it...")
            click_x, click_y = close_position
            close_success, close_msg = actions.click_at_position(click_x, click_y)
            if close_success:
                print(f"[VERIFIER_HANDLER] ✓ Successfully closed Name search dialog - returning False to trigger retry")
                time.sleep(0.5)
                return False, "Name search dialog appeared and was closed - retrying action", None
            else:
                print(f"[VERIFIER_HANDLER] Warning: Failed to click close button: {close_msg}")
                return False, f"Failed to click close button: {close_msg}", None
        
        print(f"[VERIFIER_HANDLER] No Name search dialog found (confidence: {close_confidence:.2f}), proceeding with verification")
        
        field_region = (370, 175, 160, 48)
        cropped_image = computer_vision_utils.crop_image(
            screenshot, 
            field_region[0], 
            field_region[1], 
            field_region[2], 
            field_region[3]
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to advertiser field region", None
        
        success, extracted_text = scanner.extract_text(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from advertiser field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
        
        extracted_advertiser_name = extract_string_from_text(extracted_text, advertiser_name)
        
        if not extracted_advertiser_name:
            error_msg = f"The advertiser name '{advertiser_name}' was not correct or not written correctly"
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
            error_msg = f"The advertiser name '{advertiser_name}' was not correct or not written correctly"
            print(f"[VERIFIER_HANDLER] {error_msg} (Expected: '{advertiser_name}', Extracted: '{extracted_advertiser_name}', Similarity: {similarity:.2%})")
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying advertiser name entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering advertiser name."""
    print(f"[ERROR_HANDLER] Handling error for type_advertiser_name (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    advertiser_name = kwargs.get('advertiser_name', '')
    
    if "Could not determine exact position" in error_msg or "Failed to crop" in error_msg:
        print(f"[ERROR_HANDLER] OCR or field detection issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry after waiting 1 second...")
            time.sleep(1.0)
            return True, "Retrying after OCR/detection failure"
    
    if "Failed to type" in error_msg:
        print(f"[ERROR_HANDLER] Typing issue detected")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry with slower typing...")
            return True, "Retrying with adjusted typing speed"
    
    if "Name search dialog" in error_msg or "retrying action" in error_msg.lower():
        print(f"[ERROR_HANDLER] Name search dialog detected - will retry action")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to Name search dialog appearance"
    
    if "verification failed" in error_msg.lower():
        print(f"[ERROR_HANDLER] Verification failed")
        if attempt < max_attempts:
            print(f"[ERROR_HANDLER] Will retry entire action...")
            time.sleep(0.5)
            return True, "Retrying due to verification failure"
    
    if attempt >= max_attempts:
        return False, f"Failed to enter advertiser name '{advertiser_name}' after {max_attempts} attempts"
    
    time.sleep(0.5)
    return True, "Retrying action"



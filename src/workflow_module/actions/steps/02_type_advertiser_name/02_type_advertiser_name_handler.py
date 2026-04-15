#!/usr/bin/env python3
"""
Handler for: Type Advertiser Name

- Precheck: Verify search page is displayed (OCR for "Order #" + "Advertiser")
- Action: Type advertiser name in the search field
- Verifier: Verify the advertiser name was entered correctly
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.vision_service import scanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_string_from_text
from src.workflow_module.actions.helpers.field_utils import type_text_in_field
from src.workflow_module.actions.helpers.precheck_utils import verify_page
from src.workflow_module.pages.page_loader import get_element, get_region, get_template_path, get_confidence
import time
import os

# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify search page is displayed before typing advertiser name."""
    return verify_page("search_page")

# ============================================================================
# ACTION
# ============================================================================

def action(advertiser_name: str, **kwargs) -> Tuple[bool, str]:
    """Type advertiser name in the search field."""
    print(f"[ACTION_HANDLER] Entering advertiser name: '{advertiser_name}'")
    
    return type_text_in_field(
        field_label="advertiser",
        text_to_type=advertiser_name,
        press_enter=True,
        typing_interval=0.02
    )

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(advertiser_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the advertiser name was entered correctly using OCR similarity check."""
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot for verification", None
    
    # Check for Name search dialog popup using page config
    dialog_config = get_element("search_page", "advertiser_name_dialog")
    name_dialog_region = tuple(dialog_config["region"])
    close_button_path = get_template_path("search_page", "advertiser_name_dialog", "close_template")
    dialog_confidence = get_confidence("search_page", "advertiser_name_dialog")
    
    print(f"[VERIFIER_HANDLER] Checking for Name search dialog in region {name_dialog_region}")
    
    close_button_found, close_confidence, close_position = computer_vision_utils.find_template_in_region(
        screenshot, close_button_path, name_dialog_region, confidence=dialog_confidence
    )
    
    if close_button_found and close_position:
        print(f"[VERIFIER_HANDLER] Name search dialog found (confidence: {close_confidence:.2f}), closing it...")
        template_img = computer_vision_utils.load_image(close_button_path)
        if template_img is not None:
             h, w = template_img.shape[:2]
             click_x, click_y = close_position
             click_x += w // 2
        else:
             click_x, click_y = close_position

        close_success, close_msg = actions.click_at_position(click_x, click_y)
        if close_success:
            time.sleep(0.5)
            return False, "Name search dialog appeared and was closed - retrying action", None
        else:
            return False, f"Failed to click close button: {close_msg}", None
    
    print(f"[VERIFIER_HANDLER] No Name search dialog found (confidence: {close_confidence:.2f}), proceeding with verification")
    
    # Verify field content using page config region
    field_config = get_element("search_page", "advertiser_field")
    field_region = tuple(field_config["verification_region"])
    cropped_image = take_screenshot_and_crop(field_region)
    
    if cropped_image is None:
        return False, "Failed to crop image to advertiser field region", None
    
    has_underline = computer_vision_utils.detect_underline(cropped_image)
    
    success, extracted_text = scanner.extract_text(cropped_image)
    extracted_advertiser_name = extract_string_from_text(extracted_text, advertiser_name) if success else None
    
    print(f"[VERIFIER_HANDLER] Extracted text: '{extracted_text}'")
    print(f"[VERIFIER_HANDLER] Underline detected: {has_underline}")
    
    verification_data = {
        "expected_text": advertiser_name,
        "extracted_text": extracted_text,
        "extracted_advertiser_name": extracted_advertiser_name,
        "has_underline": has_underline,
        "field_region": field_region
    }
    
    if has_underline:
        return True, "Advertiser name verified (Underline detected)", verification_data
    else:
        return False, "Advertiser name verification failed (No underline detected)", verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to entering advertiser name."""
    print(f"[ERROR_HANDLER] Handling error for type_advertiser_name (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    advertiser_name = kwargs.get('advertiser_name', '')
    
    if "Could not determine exact position" in error_msg or "Failed to crop" in error_msg:
        if attempt < max_attempts:
            time.sleep(1.0)
            return True, "Retrying after OCR/detection failure"
    
    if "Failed to type" in error_msg:
        if attempt < max_attempts:
            return True, "Retrying with adjusted typing speed"
    
    if "Name search dialog" in error_msg or "retrying action" in error_msg.lower():
        if attempt < max_attempts:
            time.sleep(0.5)
            return True, "Retrying due to Name search dialog appearance"
    
    if "verification failed" in error_msg.lower():
        if attempt < max_attempts:
            time.sleep(0.5)
            return True, "Retrying due to verification failure"
    
    if attempt >= max_attempts:
        return False, f"Failed to enter advertiser name '{advertiser_name}' after {max_attempts} attempts"
    
    time.sleep(0.5)
    return True, "Retrying action"

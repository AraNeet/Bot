#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Instructions Page

- Precheck: Verify application is visible (take screenshot succeeds)
- Action: Navigate to the Multinetwork Instructions page via toolbar icon
- Verifier: Verify the page opened (OCR for "Order #" and "Advertiser")
- Error Handler: Retry with wait
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.vision_service import scanner
from src.workflow_module.pages.page_loader import get_element, get_region, get_template_path, get_confidence, get_page_markers
import time
import os

# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify application is visible and we can take a screenshot."""
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Cannot take screenshot — application may not be visible"
    return True, "Application is visible"

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """Navigate to the Multinetwork Instructions page."""
    print("[ACTION_HANDLER] Navigating to Multinetwork Instructions page...")
    
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    # Get region and template from page config
    region = get_region("search_page", "multi_network_icon")
    icon_path = get_template_path("search_page", "multi_network_icon")
    confidence = get_confidence("search_page", "multi_network_icon")
    
    print(f"[ACTION_HANDLER] Searching for multi_network_icon in region {region}")
    
    icon_found, conf_score, icon_position = computer_vision_utils.find_template_in_region(
        screenshot, icon_path, region, confidence=confidence
    )
    
    if not icon_found:
        return False, f"Multi-network icon not found in region {region} (confidence: {conf_score:.2f})"
    
    print(f"[ACTION_HANDLER] Multi-network icon found at {icon_position} with confidence {conf_score:.2f}")
    
    if icon_position is None:
        return False, "Icon position is None despite being found"
    
    click_x, click_y = icon_position
    print(f"[ACTION_HANDLER] Clicking on multi-network icon at ({click_x}, {click_y})")
    
    success, msg = actions.click_at_position(click_x, click_y)
    
    if success:
        mouse_park = get_element("search_page", "mouse_park")["position"]
        actions.move_mouse(mouse_park[0], mouse_park[1], 0)
    if not success:
        return False, f"Failed to click on multi-network icon: {msg}"
    
    time.sleep(1.0)
    return True, "Successfully navigated to Multinetwork Instructions page"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the multi-network instructions page was opened successfully."""
    print("[VERIFIER_HANDLER] Verifying multi-network page opened...")
    
    markers = get_page_markers("search_page")
    search_region = tuple(markers["header_region"])
    header_texts = markers["header_texts"]
    
    cropped_image = take_screenshot_and_crop(search_region)
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to search region", None
    
    success, extracted_text = scanner.extract_text(cropped_image)
    if not success:
        return False, f"Failed to extract text from search region: {extracted_text}", None
    
    print(f"[VERIFIER_HANDLER] Extracted text from search region: '{extracted_text}'")
    
    extracted_text_lower = extracted_text.lower()
    has_order_num = "order #" in extracted_text_lower
    has_advertiser = "advertiser" in extracted_text_lower
    
    verification_data = {
        "extracted_text": extracted_text,
        "search_region": search_region,
        "has_order_num": has_order_num,
        "has_advertiser": has_advertiser
    }
    
    if has_order_num and has_advertiser:
        return True, "Multi-network page opened successfully", verification_data
    else:
        return False, f"Page verification failed. Found: '{extracted_text}'", verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to opening multinetwork instructions page."""
    print(f"[ERROR_HANDLER] Handling error for open_instructions_page (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 2 seconds...")
        time.sleep(2.0)
        return True, "Retrying after wait"
    
    return False, f"Failed to open instructions page after {max_attempts} attempts"

#!/usr/bin/env python3
"""
Handler for: Save Action

This module contains:
- Action: Save and close the multinetwork (save icon in 0,0,200,100; X icon in 1580,140,70,30 via template matching)
- Verifier: Verify save and close completed
- Error Handler: Handle errors for this action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.vision_service import scanner
from src.workflow_module.actions.helpers.precheck_utils import verify_page
from src.workflow_module.pages.page_loader import get_element, get_region, get_template_path, get_confidence
import time
import os

# Load regions from page config
SAVE_ICON_REGION = get_region("multinetwork_page", "save_icon")
CLOSE_X_REGION = get_region("multinetwork_page", "close_x_button")
MULTINET_TITLE_REGION = get_region("multinetwork_page", "title_bar")

# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify multinet window is open before saving."""
    return verify_page("multinetwork_page")

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """
    Save and close the multinetwork: click save icon in (0,0,200,100), then click X in (1580,140,70,30).
    """
    print("[ACTION_HANDLER] Save action: save and close multinetwork")

    # Step 1: Take screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"

    # Step 2: Find save icon via template matching
    save_icon_path = get_template_path("multinetwork_page", "save_icon")
    save_confidence_threshold = get_confidence("multinetwork_page", "save_icon")

    save_found, save_confidence, save_position = computer_vision_utils.find_template_in_region(
        screenshot, save_icon_path, SAVE_ICON_REGION, confidence=save_confidence_threshold
    )
    if not save_found or save_position is None:
        return False, f"Save icon not found in region {SAVE_ICON_REGION} (confidence: {save_confidence:.2f})"

    # Step 3: Click save icon
    click_x, click_y = save_position
    success, msg = actions.click_at_position(click_x, click_y)
    if not success:
        return False, f"Failed to click save icon: {msg}"
    print(f"[ACTION_HANDLER] ✓ Clicked save icon at ({click_x}, {click_y})")
    time.sleep(0.5)

    # Step 4: Find X (close) icon via template matching
    x_icon_path = get_template_path("multinetwork_page", "close_x_button")
    x_confidence_threshold = get_confidence("multinetwork_page", "close_x_button")
    x_found, x_confidence, x_position = computer_vision_utils.find_template_in_region(
        computer_vision_utils.take_screenshot(), x_icon_path, CLOSE_X_REGION, confidence=x_confidence_threshold
    )
    if not x_found or x_position is None:
        return False, f"Close X icon not found in region {CLOSE_X_REGION} (confidence: {x_confidence:.2f})"

    # Step 5: Click close X once
    center_x, center_y = x_position
    success, msg = actions.click_at_position(center_x, center_y, clicks=1)
    if not success:
        return False, f"Failed to click close X: {msg}"
    print(f"[ACTION_HANDLER] ✓ Clicked close X at ({center_x}, {center_y})")
    time.sleep(0.3)

    print("[ACTION_HANDLER] ✓ Save and close multinetwork completed")
    return True, "Save and close multinetwork completed"


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify save and close by checking the same area as step 10: multinet tab should not be open."""
    print("[VERIFIER_HANDLER] Verifying save action: checking if multinet tab is closed (same region as step 10)")

    title_region = take_screenshot_and_crop(MULTINET_TITLE_REGION)
    if title_region is None:
        return False, "Failed to capture title region for verification", None

    success, ocr_data = scanner.get_text_data(title_region)
    if not success:
        return False, "Failed to get OCR data from title region", None

    texts = ocr_data.get("text", [])
    for text in texts:
        if "multinet" in text.lower().replace("-", "").replace(" ", ""):
            return False, "Multinet tab still open in title region; save/close may not have completed", None

    print("[VERIFIER_HANDLER] ✓ Save action verified (multinet tab not open in title region)")
    return True, "Save action verified (multinet tab closed)", None


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors for save action."""
    print(f"[ERROR_HANDLER] Handling error for save_action (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")

    if attempt < max_attempts:
        print("[ERROR_HANDLER] Will retry after waiting 0.5 seconds...")
        time.sleep(0.5)
        return True, "Retrying action"

    return False, f"Save action failed after {max_attempts} attempts"

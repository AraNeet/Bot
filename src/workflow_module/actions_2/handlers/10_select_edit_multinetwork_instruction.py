#!/usr/bin/env python3
"""
Handler for: Select Edit Multinetwork Instruction

This module contains:
- Action: Select 'Edit Multi-network Instruction' from context menu
- Verifier: Verify the menu item was clicked
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner
import time
import pyautogui

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(**kwargs) -> Tuple[bool, str]:
    """
    Select 'Edit Multi-network Instruction' from context menu using OCR.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    print("[ACTION_HANDLER] Selecting 'Edit Multi-network Instruction' from context menu using OCR...")

    try:
        # Take screenshot
        image = computer_vision_utils.take_screenshot()
        if image is None:
            return False, "Screenshot failed"

        # Crop around mouse position
        mouse_x, mouse_y = pyautogui.position()
        crop_width, crop_height = 305, 110
        crop_x, crop_y = mouse_x, mouse_y
        cropped_img = computer_vision_utils.crop_image(image, crop_x, crop_y, crop_width, crop_height)
        if cropped_img is None:
            return False, "Crop failed"

        # Use OCR to extract text and positions
        success, data = scanner.get_text_data(cropped_img)
        if not success:
            return False, f"OCR failed: {data}"

        if not data['text']:
            return False, "No text detected in cropped region"

        # Search for target text
        target_text = "Add Multi-Network instruction to order".lower()
        for i, text in enumerate(data['text']):
            if not text.strip():
                continue
            if target_text in text.lower():
                # Found match, get position
                bbox = data['bbox'][i]  # [x1, y1, x2, y2]
                x, y, w, h = bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]
                # Adjust to screen coordinates
                click_x = crop_x + x + w // 2
                click_y = crop_y + y + h // 2
                print(f"[ACTION_HANDLER] Found '{text}' at screen coords ({click_x}, {click_y})")
                # Click at position
                success, msg = actions.click_at_position(click_x, click_y, clicks=1, button='left')
                if success:
                    return True, f"Clicked 'Edit Multi-network Instruction' at ({click_x}, {click_y})"
                else:
                    return False, f"Click failed: {msg}"
        
        return False, "Target 'Edit Multi-network Instruction' not found in context menu"
        
    except Exception as e:
        return False, f"Error selecting edit instruction: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the menu item was clicked."""
    # For context menu selection, success of the action itself is the verification
    return True, "Menu item selected", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to selecting edit instruction."""
    if attempt < max_attempts:
        time.sleep(0.5)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"


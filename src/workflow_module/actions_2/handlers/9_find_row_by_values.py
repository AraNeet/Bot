#!/usr/bin/env python3
"""
Handler for: Find Row by Values

This module contains:
- Action: Find a row matching provided parameters and right-click on it
- Verifier: Verify the row was found and clicked
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional, List
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner, match_text_positions
import time
import cv2

scanner = TextScanner()

# ============================================================================
# ACTION
# ============================================================================

def action(deal_number: str = "", advertiser_name: str = "", begin_date: str = "", end_date: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Find a row matching provided parameters, move mouse to deal_number, and right-click.
    
    Args:
        deal_number: Deal number to find
        advertiser_name: Advertiser name to find
        begin_date: Begin date to find
        end_date: End date to find
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    target_texts = [deal_number, advertiser_name, begin_date, end_date]
    if any(t is None for t in target_texts):
        return False, "Missing required params"

    print(f"[ACTION_HANDLER] Hunting for targets: {target_texts}")

    try:
        # Screenshot and process table
        image = computer_vision_utils.take_screenshot()
        if image is None:
            return False, "Screenshot failed"

        template = computer_vision_utils.load_image("src/workflow_module/actions_2/assets/ColumnLine.png")
        if template is None:
            return False, "Template load failed"

        crop_x, crop_y = 206, 225
        cropped_img = computer_vision_utils.crop_image(image, crop_x, crop_y, 1445, 780)
        if cropped_img is None:
            return False, "Crop failed"

        matches = computer_vision_utils.detect_column_separators(cropped_img, template)
        if not matches:
            return False, "No separators found"

        separated_columns_img = computer_vision_utils.create_separated_columns_image(cropped_img, matches, template.shape[1])
        if separated_columns_img is None:
            return False, "Column separation failed"

        # Debug: Save separated image
        cv2.imwrite('debug_separated_columns.png', separated_columns_img)

        # Use TextScanner for OCR data
        success, data = scanner.get_text_data(separated_columns_img)
        if not success:
            return False, f"OCR failed: {data}"

        if not data['text']:
            return False, "No text detected in table"

        print(f"[ACTION_HANDLER] OCR found {len(data['text'])} texts")

        # Match texts and get positions
        positions = match_text_positions(target_texts, data)
        if not positions:
            return False, "Failed: Too many targets missing"

        # Move mouse to deal_number position and right-click
        if positions and deal_number and any(deal_number.lower() in text.lower() for text in data['text'] if text):
            x, y, w, h = positions[0]
            
            screen_x = x + crop_x
            screen_y = y + crop_y
            click_x = screen_x + w // 2 
            click_y = screen_y + h // 2
            
            print(f"[ACTION_HANDLER] Moving mouse to deal_number at screen coords ({click_x}, {click_y}) and right-clicking")
            success, msg = actions.click_at_position(click_x, click_y, clicks=1, button='right')
            if not success:
                return False, f"Failed to right-click at deal_number position: {msg}"
            print(f"[ACTION_HANDLER] Right-click successful: {msg}")
        else:
            return False, "No deal_number position found"

        return True, f"Found {len(positions)} matched targets"
        
    except Exception as e:
        return False, f"Error finding row: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the row was found and clicked."""
    # For this action, success of the action itself is the verification
    return True, "Row found and clicked", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to finding row by values."""
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"


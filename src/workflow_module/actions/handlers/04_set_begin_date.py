#!/usr/bin/env python3
"""
Handler for: Set Begin Date
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_date_from_text
import time

scanner = TextScanner()


def action(begin_date: str, **kwargs) -> Tuple[bool, str]:
    print(f"[ACTION_HANDLER] Entering begin date: '{begin_date}'")
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        region_x, region_y, region_width, region_height = 206, 152, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image"
        success, found, bbox = scanner.find_text_with_position(cropped_image, "begin", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not find 'begin' text"
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        field_x = region_x + cropped_text_x
        field_y = region_y + cropped_text_y + text_height + 15
        click_success, _ = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, "Failed to click on begin date field"
        time.sleep(0.5)
        actions.clear_field()
        time.sleep(0.2)
        type_success, type_msg = actions.type_text(begin_date, interval=0.02)
        if not type_success:
            return False, f"Failed to type begin date: {type_msg}"
        time.sleep(0.5)
        return True, f"Successfully entered begin date: '{begin_date}'"
    except Exception as e:
        return False, f"Error entering begin date: {e}"


def verifier(begin_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    if not begin_date:
        return True, "No begin date to verify", None
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot", None
        field_region = (992, 175, 114, 50)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image", None
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        extracted_date = extract_date_from_text(extracted_text, begin_date)
        if not extracted_date:
            return False, f"Could not extract date from: '{extracted_text}'", None
        similarity = calculate_text_similarity(begin_date, extracted_date)
        if similarity >= 0.80:
            return True, f"✓ Begin date verified with {similarity:.2%} similarity", {"similarity": similarity}
        else:
            return False, f"✗ Begin date verification failed. Similarity: {similarity:.2%}", {"similarity": similarity}
    except Exception as e:
        return False, f"Error verifying begin date: {e}", None


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    if attempt < max_attempts:
        time.sleep(0.5)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"



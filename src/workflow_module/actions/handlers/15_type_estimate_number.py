#!/usr/bin/env python3
"""
Handler for: Type Estimate Number
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.verification_utils import calculate_text_similarity, extract_number_from_text
import time

scanner = TextScanner()


def action(estimate_number: str, **kwargs) -> Tuple[bool, str]:
    print(f"[ACTION_HANDLER] Entering estimate number: '{estimate_number}'")
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        region_x, region_y, region_width, region_height = 206, 152, 1439, 79
        cropped_image = computer_vision_utils.crop_image(screenshot, region_x, region_y, region_width, region_height)
        if cropped_image is None:
            return False, "Failed to crop image to search region"
        success, found, bbox = scanner.find_text_with_position(cropped_image, "estimate", case_sensitive=False)
        if not success or not found or bbox is None:
            return False, "Could not determine exact position of 'estimate' text"
        cropped_text_x, cropped_text_y, text_width, text_height = bbox
        text_x = region_x + cropped_text_x
        text_y = region_y + cropped_text_y
        field_x = text_x
        field_y = text_y + text_height + 15
        click_success, _ = actions.click_at_position(field_x, field_y)
        if not click_success:
            return False, "Failed to click on estimate field"
        time.sleep(0.5)
        actions.clear_field()
        time.sleep(0.2)
        type_success, type_msg = actions.type_text(estimate_number, interval=0.02)
        if not type_success:
            return False, f"Failed to type estimate number: {type_msg}"
        time.sleep(0.5)
        return True, f"Successfully entered estimate number: '{estimate_number}'"
    except Exception as e:
        return False, f"Error entering estimate number: {e}"


def verifier(estimate_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    if not estimate_number:
        return True, "No estimate number to verify", None
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        field_region = (286, 175, 80, 48)
        cropped_image = computer_vision_utils.crop_image(screenshot, *field_region)
        if cropped_image is None:
            return False, "Failed to crop image to estimate field region", None
        success, extracted_text = scanner.extract_text(cropped_image)
        if not success:
            return False, f"Failed to extract text: {extracted_text}", None
        extracted_estimate_number = extract_number_from_text(extracted_text, estimate_number)
        if not extracted_estimate_number:
            return False, f"Could not extract estimate number from: '{extracted_text}'", None
        similarity = calculate_text_similarity(estimate_number, extracted_estimate_number)
        verification_data = {
            "expected_text": estimate_number,
            "extracted_text": extracted_text,
            "similarity_score": similarity
        }
        if similarity >= 0.80:
            return True, f"✓ Estimate number verified with {similarity:.2%} similarity", verification_data
        else:
            return False, f"✗ Estimate number verification failed. Similarity: {similarity:.2%}", verification_data
    except Exception as e:
        return False, f"Error verifying estimate number: {e}", None


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    if attempt < max_attempts:
        time.sleep(0.5)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"



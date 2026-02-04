#!/usr/bin/env python3
"""
Field Utilities Module

This module provides utilities for typing text into form fields by locating
field labels and calculating field positions with offsets.
"""

from typing import Tuple, Optional, Union, List
import re
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.debug_utils import Debugger
import time

scanner = TextScanner()

# Default search region for finding field labels
DEFAULT_SEARCH_REGION = (206, 152, 1439, 79)
DEFAULT_FIELD_SPACING = 15  # Pixels below the label text


def type_text_in_field(
    field_label: Union[str, List[str]],
    text_to_type: str,
    press_enter: bool = False,
    search_region: Optional[Tuple[int, int, int, int]] = None,
    field_spacing: int = DEFAULT_FIELD_SPACING,
    typing_interval: float = 0.02,
    debugger: Optional[Debugger] = None
) -> Tuple[bool, str]:
    """
    Type text into a form field by locating the field label and calculating the field position.
    
    This function:
    1. Takes a screenshot
    2. Searches for the field label text in the search region
    3. Calculates the field position (label position + offset)
    4. Clicks on the field
    5. Clears the field
    6. Types the text
    7. Optionally presses Enter
    
    Args:
        field_label: The label text to search for (e.g., "advertiser", "agency", "begin", "end")
                     Can be a string or a list of strings to try.
        text_to_type: The text to type into the field
        press_enter: Whether to press Enter after typing (default: False)
        search_region: Region to search for the label (x, y, width, height). 
                      Defaults to DEFAULT_SEARCH_REGION
        field_spacing: Pixels below the label text to click (default: 15)
        typing_interval: Delay between keystrokes in seconds (default: 0.02)
        debugger: Optional Debugger instance for saving images
        
    Returns:
        Tuple of (success: bool, message: str)
        
    Example:
        success, msg = type_text_in_field("advertiser", "Acme Corp", press_enter=True)
        success, msg = type_text_in_field("begin", "09/16/2025", press_enter=False)
    """
    # Handle list of labels
    if isinstance(field_label, str):
        labels_to_try = [field_label]
    else:
        labels_to_try = field_label
        
    print(f"[FIELD_UTILS] Entering '{text_to_type}' into '{labels_to_try[0]}' field")
    
    # ============================================================================
    # STEP 1: Setup search region
    # ============================================================================
    if search_region is None:
        search_region = DEFAULT_SEARCH_REGION
    
    region_x, region_y, region_width, region_height = search_region
    
    # ============================================================================
    # STEP 2: Take screenshot and crop to search region
    # ============================================================================
    cropped_image = take_screenshot_and_crop(search_region)
    if cropped_image is None:
        return False, "Failed to take screenshot and crop to search region"
    
    if debugger:
        debugger.save_image(cropped_image, f"search_region_{labels_to_try[0]}.png")
    
    print(f"[FIELD_UTILS] Searching for labels {labels_to_try} in region {search_region}")
    
    # ============================================================================
    # STEP 3: Find the field label text using OCR
    # ============================================================================
    success = False
    found = False
    bbox = None
    
    # Try each label in the list
    for label in labels_to_try:
        success, found, bbox = scanner.find_text_with_position(
            cropped_image,
            label,
            case_sensitive=False
        )
        if success and found and bbox:
            print(f"[FIELD_UTILS] ✓ Found label '{label}'")
            field_label = label # Set the actual found label for later use
            break
            
    if not success or not found or bbox is None:
        # Debugging: Print what WAS found
        success_ocr, data = scanner.get_text_data(cropped_image)
        if success_ocr and data.get('text'):
            print(f"[FIELD_UTILS] ✗ Label not found. OCR detected text: {data['text']}")
        return False, f"Could not determine exact position of any of {labels_to_try} text in cropped image"
    
    # ============================================================================
    # STEP 4: Calculate field position (label position + offset)
    # ============================================================================
    cropped_text_x, cropped_text_y, text_width, text_height = bbox
    field_x = region_x + cropped_text_x
    field_y = region_y + cropped_text_y + text_height + field_spacing
    
    print(f"[FIELD_UTILS] ✓ '{field_label}' text found at ({field_x}, {field_y - field_spacing - text_height})")
    print(f"[FIELD_UTILS] Calculated field position: ({field_x}, {field_y}) - {field_spacing}px below '{field_label}' text")
    
    # ============================================================================
    # STEP 5: Click on the field
    # ============================================================================
    click_success, click_msg = actions.click_at_position(field_x, field_y)
    if not click_success:
        return False, f"Failed to click on {field_label} field: {click_msg}"
    
    time.sleep(0.5)
    
    # ============================================================================
    # STEP 6: Clear the field
    # ============================================================================
    clear_success, clear_msg = actions.clear_field()
    if not clear_success:
        print(f"[FIELD_UTILS] Warning: Failed to clear field: {clear_msg}")
    
    time.sleep(0.2)
    
    # ============================================================================
    # STEP 7: Type the text
    # ============================================================================
    type_success, type_msg = actions.type_text(text_to_type, interval=typing_interval)
    if not type_success:
        return False, f"Failed to type {field_label} text: {type_msg}"
    
    # ============================================================================
    # STEP 8: Optionally press Enter
    # ============================================================================
    if press_enter:
        time.sleep(0.2)
        enter_success, enter_msg = actions.press_key('enter', presses=1)
        if not enter_success:
            print(f"[FIELD_UTILS] Warning: Failed to press Enter: {enter_msg}")
    
    time.sleep(0.5)
    
    success_msg = f"Successfully entered '{text_to_type}' into {field_label} field"
    print(f"[FIELD_UTILS] ✓ {success_msg}")
    return True, success_msg

# ============================================================================
# RESULTS COUNT EXTRACTION
# ============================================================================

def get_results_count() -> Optional[int]:
    """
    Extract the number of results from the results count region.
    
    Returns:
        Number of results as integer, or None if failed to extract
    """
    try:
        # Take screenshot and crop results region (x, y, width, height)
        results_region = take_screenshot_and_crop((206, 225, 225, 25))
        if results_region is None:
            print("[GET_RESULTS] Failed to take screenshot and crop results region")
            return None
        
        # OCR the region
        success, data = scanner.get_text_data(results_region)
        if not success or not data['text']:
            print("[GET_RESULTS] OCR failed or no text found")
            return None
        
        # Extract number from text
        # Expected format could be like "30 results" or "Results: 30" etc.
        all_text = ' '.join(data['text'])
        print(f"[GET_RESULTS] OCR text from results region: '{all_text}'")
        
        # Extract all numbers from the text
        numbers = re.findall(r'\d+', all_text)
        
        if numbers:
            # Take the first number found
            result_count = int(numbers[0])
            print(f"[GET_RESULTS] Extracted result count: {result_count}")
            return result_count
        else:
            print("[GET_RESULTS] No numbers found in results region")
            return None
            
    except Exception as e:
        print(f"[GET_RESULTS] Error extracting results count: {e}")
        return None


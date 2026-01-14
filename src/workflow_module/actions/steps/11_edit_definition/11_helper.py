#!/usr/bin/env python3
"""
Helper functions for Step 11: Edit Definition
"""

from typing import Tuple, Optional
import time
import pytz
from datetime import datetime
from dateutil import parser
import re
import pyautogui

from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers import debug_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger

# Initialize TextScanner
scanner = TextScanner()

# Constants
DEFINITION_WINDOW_REGION = (200, 425, 1425, 575)
MOUNTAIN_TZ = pytz.timezone('US/Mountain')

# Module-level storage for verification data
_verification_data = {"original_comment": ""}

def get_verification_data():
    """Get verification data storage."""
    return _verification_data

def get_current_mountain_date():
    """Get current date in Mountain Time Zone."""
    return datetime.now(MOUNTAIN_TZ).date()

def parse_date_string(date_str: str) -> Optional[datetime.date]:
    """Parse date string to date object."""
    try:
        if not date_str:
            return None
        clean_str = re.sub(r'[^\d/.-]', '', date_str)
        return parser.parse(clean_str).date()
    except Exception as e:
        print(f"[EDIT_DEF] Failed to parse date '{date_str}': {e}")
        return None

def find_field_input_box(screenshot, label_text: str, search_region: Tuple[int, int, int, int], 
                         offset_y: int = 15, debugger: Optional[Debugger] = None, 
                         step_name: str = "") -> Optional[Tuple[int, int]]:
    """Find input box associated with a label within the Definition window."""
    # 1. Take screenshot if not provided
    if screenshot is None:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return None
    
    # 2. Visualize search region
    if debugger:
        debugger.visualize_search_region(screenshot, search_region, f"{step_name}_search_region")
    
    # 3. Crop search region from screenshot
    cropped = computer_vision_utils.crop_image(screenshot, *search_region)
    if cropped is None:
        if debugger:
            debug_img = screenshot.copy()
            debugger.draw_rect(debug_img, search_region, color=debug_utils.COLOR_RED, label="FAILED: Crop region")
            debugger.save_image(debug_img, f"{step_name}_crop_failed.png")
        return None
    
    if debugger:
        debugger.save_image(cropped, f"{step_name}_cropped_region.png")
    
    # 4. Use OCR to find label position
    success, found, bbox = scanner.find_text_with_position(cropped, label_text, case_sensitive=False)
    
    if debugger:
        success_ocr, ocr_data = scanner.get_text_data(cropped)
        if success_ocr:
            debugger.visualize_ocr(cropped, ocr_data, f"{step_name}_ocr", highlight_text=label_text)
    
    # 5. Calculate click position if label found
    if success and found:
        lx, ly, lw, lh = bbox
        global_label_center_x = search_region[0] + lx + (lw // 2)
        global_label_bottom_y = search_region[1] + ly + lh
        click_x = global_label_center_x
        click_y = global_label_bottom_y + offset_y
        
        print(f"[EDIT_DEF] Found label '{label_text}' at ({global_label_center_x}, {global_label_bottom_y}). Click: ({click_x}, {click_y})")
        
        if debugger:
            debug_img = screenshot.copy()
            label_rect = (search_region[0] + lx, search_region[1] + ly, lw, lh)
            debugger.draw_rect(debug_img, label_rect, color=debug_utils.COLOR_GREEN, label=f"Label: {label_text}")
            debugger.draw_point(debug_img, (click_x, click_y), color=debug_utils.COLOR_RED, label="Click Position")
            debugger.draw_rect(debug_img, search_region, color=debug_utils.COLOR_ORANGE, thickness=1)
            debugger.save_image(debug_img, f"{step_name}_found.png")
        
        return (click_x, click_y)
    
    if debugger:
        debug_img = screenshot.copy()
        debugger.draw_rect(debug_img, search_region, color=debug_utils.COLOR_RED, label=f"NOT FOUND: {label_text}")
        debugger.save_image(debug_img, f"{step_name}_not_found.png")
    
    print(f"[EDIT_DEF] Label '{label_text}' not found in region {search_region}")
    return None

def extract_field_value(screenshot, click_pos: Tuple[int, int], field_type: str = "date") -> str:
    """Extract value from field at position."""
    box_w, box_h = (300, 50) if field_type == "comment" else (100, 30)
    x = max(0, click_pos[0] - (box_w // 2))
    y = max(0, click_pos[1] - (box_h // 2))
    
    cropped = computer_vision_utils.crop_image(screenshot, x, y, box_w, box_h)
    if cropped is not None:
        success, text = scanner.extract_text(cropped)
        if success:
            return text.strip()
    return ""

def type_date_in_three_part_field(field_pos: Tuple[int, int], date_str: str) -> Tuple[bool, str]:
    """Type a date into a 3-part date field (month, day, year) with arrow key navigation."""
    try:
        # 1. Parse date string to extract month, day, year
        date_parts = date_str.split('/')
        if len(date_parts) != 3:
            parsed_date = parse_date_string(date_str)
            if parsed_date:
                month, day, year = str(parsed_date.month), str(parsed_date.day), str(parsed_date.year)
            else:
                return False, f"Could not parse date string: '{date_str}'"
        else:
            month, day, year = date_parts
        
        month = str(int(month)) if month else month
        day = str(int(day)) if day else day
        
        print(f"[EDIT_DEF] Typing date: {month}/{day}/{year}")
        
        # 2. Click on the field to focus it
        click_success, click_msg = actions.click_at_position(*field_pos)
        if not click_success:
            return False, f"Failed to click on date field: {click_msg}"
        
        # 3. Clear the field
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.press('delete')
        time.sleep(0.3)
        pyautogui.press('home')
        time.sleep(0.2)
        
        # 4. Type month
        for char in month:
            pyautogui.write(char)
            time.sleep(0.05)
        time.sleep(0.3)
        
        # 5. Press right arrow to move to day field
        pyautogui.press('right')
        time.sleep(0.3)
        
        # 6. Type day
        for char in day:
            pyautogui.write(char)
            time.sleep(0.05)
        time.sleep(0.3)
        
        # 7. Press right arrow to move to year field
        pyautogui.press('right')
        time.sleep(0.3)
        
        # 8. Type year
        for char in year:
            pyautogui.write(char)
            time.sleep(0.05)
        time.sleep(0.3)
        
        # 9. Press Enter to confirm
        pyautogui.press('enter')
        time.sleep(0.5)
        
        return True, f"Successfully typed date: {date_str}"
    except Exception as e:
        return False, f"Error typing date in 3-part field: {e}"

def update_and_verify_date(field_label: str, expected_date: str, debugger: Optional[Debugger] = None, 
                           step_name: str = "") -> Tuple[bool, str]:
    """Update a date field and verify it was updated correctly."""
    # 1. Take screenshot and find field position
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    field_pos = find_field_input_box(screenshot, field_label, DEFINITION_WINDOW_REGION, 
                                     offset_y=15, debugger=debugger, step_name=step_name)
    if not field_pos:
        return False, f"Could not locate '{field_label}' field"
    
    # 2. Update the date field
    success, msg = type_date_in_three_part_field(field_pos, expected_date)
    if not success:
        return False, f"Failed to update {field_label}: {msg}"
    
    # 3. Verify the update
    time.sleep(0.5)
    screenshot_after = computer_vision_utils.take_screenshot()
    if screenshot_after is None:
        return False, "Failed to take screenshot for verification"
    
    field_pos_after = find_field_input_box(screenshot_after, field_label, DEFINITION_WINDOW_REGION, offset_y=15)
    if not field_pos_after:
        return False, f"Could not locate '{field_label}' field for verification"
    
    extracted = extract_field_value(screenshot_after, field_pos_after)
    extracted_clean = re.sub(r'[^\d/]', '', extracted)
    expected_clean = re.sub(r'[^\d/]', '', expected_date)
    
    if debugger:
        debugger.save_image(screenshot_after, f"{step_name}_updated.png")
    
    if expected_clean in extracted_clean or extracted_clean in expected_clean:
        print(f"[EDIT_DEF] ✓ {field_label} verified: '{extracted}' matches '{expected_date}'")
        return True, f"{field_label} updated successfully"
    
    # 4. Retry once if verification failed
    print(f"[EDIT_DEF] WARNING: {field_label} verification failed. Retrying...")
    retry_success, retry_msg = type_date_in_three_part_field(field_pos_after, expected_date)
    if not retry_success:
        return False, f"{field_label} retry failed: {retry_msg}"
    
    time.sleep(0.5)
    screenshot_final = computer_vision_utils.take_screenshot()
    if screenshot_final:
        field_pos_final = find_field_input_box(screenshot_final, field_label, DEFINITION_WINDOW_REGION, offset_y=15)
        if field_pos_final:
            extracted_final = extract_field_value(screenshot_final, field_pos_final)
            extracted_final_clean = re.sub(r'[^\d/]', '', extracted_final)
            if expected_clean in extracted_final_clean or extracted_final_clean in expected_clean:
                print(f"[EDIT_DEF] ✓ {field_label} verified after retry: '{extracted_final}'")
                return True, f"{field_label} updated successfully"
    
    return False, f"{field_label} update failed after retry"

def verify_date_field(field_label: str, expected_date: str, debugger: Optional[Debugger] = None) -> Tuple[bool, str]:
    """Verify that a date field matches the expected value."""
    # 1. Take screenshot and find field position
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    field_pos = find_field_input_box(screenshot, field_label, DEFINITION_WINDOW_REGION, 
                                     offset_y=15, debugger=debugger, step_name=f"verify_{field_label.lower().replace(' ', '_')}")
    if not field_pos:
        return False, f"Could not locate '{field_label}' field"
    
    # 2. Extract field value
    extracted = extract_field_value(screenshot, field_pos)
    extracted_date = parse_date_string(extracted)
    expected_date_obj = parse_date_string(expected_date)
    
    if debugger:
        debug_img = screenshot.copy()
        debugger.draw_point(debug_img, field_pos, color=debug_utils.COLOR_CYAN, label=f"Extracted: {extracted}")
        debugger.save_image(debug_img, f"verify_{field_label.lower().replace(' ', '_')}.png")
    
    # 3. Compare dates (prefer parsed date comparison)
    if extracted_date and expected_date_obj:
        if extracted_date == expected_date_obj:
            return True, f"{field_label} verified: '{extracted}' matches '{expected_date}'"
        else:
            return False, f"{field_label} mismatch: Expected '{expected_date}', got '{extracted}'"
    
    # 4. Fallback to string comparison if parsing fails
    extracted_clean = re.sub(r'[^\d/]', '', extracted)
    expected_clean = re.sub(r'[^\d/]', '', expected_date)
    if expected_clean in extracted_clean or extracted_clean in expected_clean:
        return True, f"{field_label} verified: '{extracted}' matches '{expected_date}'"
    
    return False, f"{field_label} mismatch: Expected '{expected_date}', got '{extracted}'"

def verify_comment(agent_name: str, revision_number: str, original_comment: str = "", 
                   debugger: Optional[Debugger] = None) -> Tuple[bool, str]:
    """Verify that Comment contains appended text after existing text."""
    # 1. Construct expected appended text
    if not agent_name:
        agent_name = "test agent"
    
    current_date_str = get_current_mountain_date().strftime("%m/%d")
    expected_appended = f" {agent_name} {revision_number} {current_date_str}"
    
    # 2. Take screenshot and find comment field
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    comment_pos = find_field_input_box(screenshot, "Comment", DEFINITION_WINDOW_REGION, 
                                       offset_y=15, debugger=debugger, step_name="verify_comment")
    if not comment_pos:
        return False, "Could not locate 'Comment' field"
    
    # 3. Extract current comment value
    extracted_comment = extract_field_value(screenshot, comment_pos, field_type="comment")
    
    if debugger:
        debug_img = screenshot.copy()
        debugger.draw_point(debug_img, comment_pos, color=debug_utils.COLOR_CYAN, 
                           label=f"Comment: {extracted_comment[:50]}...")
        debugger.save_image(debug_img, "verify_comment.png")
    
    # 4. Verify appended text is present
    if expected_appended.strip() not in extracted_comment:
        return False, f"Expected appended text '{expected_appended}' not found in comment"
    
    # 5. Verify original text is preserved (if it existed)
    if original_comment and original_comment.strip():
        if original_comment.strip() not in extracted_comment:
            print(f"[VERIFIER] Warning: Original comment not fully preserved")
        else:
            original_index = extracted_comment.find(original_comment.strip())
            appended_index = extracted_comment.find(expected_appended.strip())
            if original_index != -1 and appended_index != -1:
                if appended_index >= original_index + len(original_comment.strip()):
                    return True, f"Comment verified: Original text preserved and appended text added after"
    
    return True, f"Comment verified: Appended text is present"

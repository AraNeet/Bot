#!/usr/bin/env python3
"""
Helper functions for Step 13: Edit Assignment Percentage

identify_assignment_area(): Finds the Assignment section region (from "Assignment" header to end of work area).
find_aliases_in_assignment_area(): Finds alias letters (A, B, C...) within the identified assignment area.
ensure_assignment_aliases_in_view(): Scrolls until Total or 10+ aliases are in view; calls identify + find_aliases.
select_all_in_alias_input_fields(): For each alias, clicks the input field next to it and selects all content (Ctrl+A).
right_click_delete_field(): Right-clicks on field, finds "Delete" in work area crop, clicks it.
input_value_in_field(): After field is deleted, clicks the field and types the value (for the corresponding alias).
"""

from typing import Tuple, Optional, Dict, List
import re
import time
import pyautogui

from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
from src.workflow_module.actions.helpers.debug_utils import Debugger

scanner = TextScanner()

# ============================================================================
# CONSTANTS
# ============================================================================

# Work area - subwindow containing Definition, Media Details, and Assignment sections
WORK_AREA = (200, 425, 1450, 570)  # x, y, width, height

# Scroll area - region that accepts scroll (e.g. scrollbar)
SCROLL_AREA = (1625, 460, 20, 540)  # x, y, width, height
SCROLL_AMOUNT = 25

# Alias column width (left side of assignment area)
ALIAS_COLUMN_WIDTH = 60

# Offset from alias X to the percentage input field (pixels to the right)
INPUT_FIELD_OFFSET = 60

# OCR corrections for common misreads
OCR_FIXES = {'1': 'I', '|': 'I', '0': 'O', '@': 'Q', '9': 'Q'}


def find_total_in_work_area(screenshot) -> bool:
    """Return True if 'Total' text is visible in the work area."""
    cropped = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
    if cropped is None:
        return False
    success, found, _ = scanner.find_text_with_position(cropped, "Total", case_sensitive=False)
    return bool(success and found)


def get_total_percentage(screenshot) -> Optional[int]:
    """Find 'Total' in work area and read the percentage value to the right. Returns int or None."""
    cropped = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
    if cropped is None:
        return None
    success, found, bbox = scanner.find_text_with_position(cropped, "Total", case_sensitive=False)
    if not (success and found):
        return None
    tx, ty, tw, th = bbox
    val_x = WORK_AREA[0] + tx + tw
    val_y = WORK_AREA[1] + max(0, ty - 5)
    val_crop = computer_vision_utils.crop_image(screenshot, val_x, val_y, 100, th + 10)
    if val_crop is None:
        return None
    ok, data = scanner.get_text_data(val_crop)
    if not ok:
        return None
    text = " ".join(data.get("text", []))
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else None


def verify_all_fields_have_numbers(screenshot, aliases: List[Dict]) -> Tuple[bool, List[str]]:
    """
    For each alias, OCR the input field region and check it contains at least one digit.
    Returns (all_ok, list of alias letters that have no number in the field).
    """
    invalid = []
    for a in aliases:
        field_x = a["alias_x"] + INPUT_FIELD_OFFSET
        field_y = a["row_y"]
        # Crop small region around the input field
        crop_x = max(0, field_x - 15)
        crop_y = max(0, field_y - 12)
        field_crop = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, 70, 28)
        if field_crop is None:
            invalid.append(a["alias"])
            continue
        ok, data = scanner.get_text_data(field_crop)
        if not ok:
            invalid.append(a["alias"])
            continue
        text = " ".join(data.get("text", []))
        if not re.search(r"\d", text):
            invalid.append(a["alias"])
    return (len(invalid) == 0, invalid)


# ============================================================================
# IDENTIFY ASSIGNMENT AREA
# ============================================================================

def identify_assignment_area(screenshot, debugger: Optional[Debugger] = None) -> Tuple[bool, Optional[Dict]]:
    """
    Identify the Assignment area: from the "Assignment" header to the end of the work area.
    
    Returns:
        (found, region) where region is {x, y, width, height} in screen coordinates.
        The region starts at the Assignment header and extends to the bottom of WORK_AREA.
    """
    # Step 1: Crop to work area and search for "Assignment" text.
    cropped = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
    if cropped is None:
        return False, None
    
    success, found, bbox = scanner.find_text_with_position(cropped, "Assignment", case_sensitive=False)
    if not (success and found):
        return False, None
    
    # Step 2: Compute assignment area region.
    # Assignment area starts at the Assignment header and goes to the bottom of the work area.
    work_x, work_y, work_w, work_h = WORK_AREA
    # bbox is (x, y, width, height) relative to cropped work area
    header_top_rel = bbox[1]
    
    # Assignment area: from Assignment header to bottom of work area
    area_x = work_x
    area_y = work_y + header_top_rel
    area_w = work_w
    area_h = work_h - header_top_rel
    
    if area_h <= 0:
        return False, None
    
    region = {
        'x': area_x,
        'y': area_y,
        'width': area_w,
        'height': area_h,
    }
    
    if debugger:
        # Save cropped assignment area for debug
        area_crop = computer_vision_utils.crop_image(screenshot, area_x, area_y, area_w, area_h)
        if area_crop is not None:
            debugger.save_image(area_crop, "assignment_area.png")
    
    print(f"[ASSIGNMENT] Identified assignment area: x={area_x}, y={area_y}, w={area_w}, h={area_h}")
    return True, region


# ============================================================================
# FIND ALIASES IN ASSIGNMENT AREA
# ============================================================================

def find_aliases_in_assignment_area(screenshot, region: Dict, debugger: Optional[Debugger] = None) -> List[Dict]:
    """
    Find alias letters (A, B, C...) within the identified assignment area.
    
    Args:
        screenshot: Full screenshot.
        region: Assignment area from identify_assignment_area: {x, y, width, height}.
        debugger: Optional debugger for saving images.
    
    Returns:
        List of dicts: [{'alias': 'A', 'alias_x': int, 'row_y': int}, ...] sorted by Y position.
    """
    area_x = region['x']
    area_y = region['y']
    area_w = region['width']
    area_h = region['height']
    
    # Crop to assignment area, then to alias column (left side)
    area_crop = computer_vision_utils.crop_image(screenshot, area_x, area_y, area_w, area_h)
    if area_crop is None:
        return []
    
    alias_column = area_crop[:, 0:min(ALIAS_COLUMN_WIDTH, area_w)]
    if debugger:
        debugger.save_image(alias_column, "alias_column_scan_assignment.png")
    
    success, data = scanner.get_text_data(alias_column)
    if not success:
        return []
    
    # Collect single characters with positions (relative to full screenshot)
    raw_results = []
    for i, text in enumerate(data['text']):
        text_clean = text.strip().upper()
        if len(text_clean) == 1:
            bbox = data['bbox'][i]
            # Convert to screen coordinates (area_crop is at area_x, area_y)
            alias_x = area_x + (bbox[0] + bbox[2]) // 2
            row_y = area_y + (bbox[1] + bbox[3]) // 2
            raw_results.append({
                'raw_text': text_clean,
                'alias_x': alias_x,
                'row_y': row_y,
            })
    raw_results.sort(key=lambda r: r['row_y'])
    
    # Apply OCR corrections and deduplicate (keep letter aliases only)
    aliases = []
    seen = set()
    for r in raw_results:
        text = r['raw_text']
        alias = text if text.isalpha() else OCR_FIXES.get(text)
        if alias and alias.isalpha() and alias not in seen:
            seen.add(alias)
            aliases.append({
                'alias': alias,
                'alias_x': r['alias_x'],
                'row_y': r['row_y'],
            })
    aliases.sort(key=lambda a: a['row_y'])
    
    print(f"[ASSIGNMENT] Aliases found in area: {[a['alias'] for a in aliases]}")
    return aliases


# ============================================================================
# ENSURE ALIASES IN VIEW
# ============================================================================

def ensure_assignment_aliases_in_view(debugger: Optional[Debugger] = None) -> Tuple[bool, Optional[Dict], List[Dict]]:
    """
    Scroll until the assignment area has either Total visible or at least 10 aliases in view.
    Calls identify_assignment_area and find_aliases_in_assignment_area each iteration.
    
    Returns:
        (success, region, aliases). On failure: (False, None, []).
    """
    max_scrolls = 20
    print("[ASSIGNMENT] Ensuring assignment area has Total or 10+ aliases in view...")
    
    for scroll_num in range(max_scrolls):
        # Step 1: Take screenshot.
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            pyautogui.moveTo(SCROLL_AREA[0] + SCROLL_AREA[2] // 2, SCROLL_AREA[1] + SCROLL_AREA[3] // 2, duration=0.1)
            pyautogui.scroll(-SCROLL_AMOUNT)
            time.sleep(0.2)
            continue
        if debugger and scroll_num == 0:
            work_crop = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
            if work_crop is not None:
                debugger.save_image(work_crop, "ensure_step_initial.png")
        
        # Step 2: Identify assignment area.
        found_area, region = identify_assignment_area(screenshot, debugger if scroll_num == 0 else None)
        if not found_area:
            print(f"[ASSIGNMENT] Assignment area not found, scrolling down ({scroll_num + 1}/{max_scrolls})")
            pyautogui.moveTo(SCROLL_AREA[0] + SCROLL_AREA[2] // 2, SCROLL_AREA[1] + SCROLL_AREA[3] // 2, duration=0.1)
            pyautogui.scroll(-SCROLL_AMOUNT)
            time.sleep(0.2)
            continue
        
        # Step 3: Find aliases in the assignment area.
        aliases = find_aliases_in_assignment_area(screenshot, region, debugger if scroll_num == 0 else None)
        
        # Step 4: Check if we have Total or at least 10 aliases.
        total_visible = find_total_in_work_area(screenshot)
        if total_visible:
            print(f"[ASSIGNMENT] Total in view - scrolling 2 more times then stopping")
            for _ in range(2):
                pyautogui.moveTo(SCROLL_AREA[0] + SCROLL_AREA[2] // 2, SCROLL_AREA[1] + SCROLL_AREA[3] // 2, duration=0.1)
                pyautogui.scroll(-SCROLL_AMOUNT)
                time.sleep(0.2)
            screenshot = computer_vision_utils.take_screenshot()
            if screenshot is not None:
                found_area, region = identify_assignment_area(screenshot, debugger)
                if found_area:
                    aliases = find_aliases_in_assignment_area(screenshot, region, debugger)
            return True, region, aliases
        if len(aliases) >= 10:
            print(f"[ASSIGNMENT] 10+ aliases in view ({len(aliases)}) - stopping")
            return True, region, aliases
        
        # Step 5: Not enough yet - scroll down.
        print(f"[ASSIGNMENT] Only {len(aliases)} aliases, no Total - scrolling down ({scroll_num + 1}/{max_scrolls})")
        pyautogui.moveTo(SCROLL_AREA[0] + SCROLL_AREA[2] // 2, SCROLL_AREA[1] + SCROLL_AREA[3] // 2, duration=0.1)
        pyautogui.scroll(-SCROLL_AMOUNT)
        time.sleep(0.2)
    
    print(f"[ASSIGNMENT] Failed to get Total or 10+ aliases after {max_scrolls} scrolls")
    return False, None, []


# ============================================================================
# SELECT ALL IN INPUT FIELDS
# ============================================================================

def select_all_in_alias_input_fields(aliases: List[Dict], debugger: Optional[Debugger] = None) -> None:
    """
    For each alias, click the input field next to it (percentage field) and select all content (Ctrl+A).
    
    Args:
        aliases: List from find_aliases_in_assignment_area: [{'alias', 'alias_x', 'row_y'}, ...].
        debugger: Optional (unused, for future debug images).
    """
    for a in aliases:
        field_x = a['alias_x'] + INPUT_FIELD_OFFSET
        field_y = a['row_y']
        pyautogui.click(field_x, field_y, duration=0.15)
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.15)


def right_click_delete_field(alias: Dict, debugger: Optional[Debugger] = None) -> bool:
    """
    Right-click on the input field next to the alias (after content is selected), open context menu,
    find "Delete" in the work area crop, and click it.
    
    Args:
        alias: Dict with 'alias_x', 'row_y' from find_aliases_in_assignment_area.
        debugger: Optional for saving debug images.
    
    Returns:
        True if Delete was found and clicked, False otherwise.
    """
    field_x = alias['alias_x'] + INPUT_FIELD_OFFSET
    field_y = alias['row_y']
    pyautogui.click(field_x, field_y, button='right', duration=0.15)
    time.sleep(0.5)
    
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        pyautogui.press('escape')
        return False
    
    work_crop = computer_vision_utils.crop_image(screenshot, *WORK_AREA)
    if work_crop is None:
        pyautogui.press('escape')
        return False
    
    if debugger:
        debugger.save_image(work_crop, f"right_click_menu_{alias.get('alias', '?')}.png")
    
    success, found, bbox = scanner.find_text_with_position(work_crop, "Delete", case_sensitive=False)
    if not (success and found):
        pyautogui.press('escape')
        return False
    
    # Convert bbox to global screen coordinates (work_crop is at WORK_AREA offset)
    delete_x = WORK_AREA[0] + bbox[0] + bbox[2] // 2
    delete_y = WORK_AREA[1] + bbox[1] + bbox[3] // 2
    pyautogui.click(delete_x, delete_y)
    time.sleep(0.3)
    return True


def input_value_in_field(alias: Dict, value: str, debugger: Optional[Debugger] = None) -> None:
    """
    After the field is deleted, click the input field and type the value.
    Called in alias order so values correspond to the order of aliases passed in.
    
    Args:
        alias: Dict with 'alias_x', 'row_y' from find_aliases_in_assignment_area.
        value: String to type (e.g. percentage "50"). If empty, nothing is typed.
        debugger: Optional (unused, for future debug images).
    """
    if not value:
        return
    field_x = alias['alias_x'] + INPUT_FIELD_OFFSET
    field_y = alias['row_y']
    pyautogui.click(field_x, field_y, duration=0.15)
    time.sleep(0.2)
    pyautogui.typewrite(value, interval=0.05)
    time.sleep(0.2)

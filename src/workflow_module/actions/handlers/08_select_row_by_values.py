#!/usr/bin/env python3
"""
Handler for: Select Row by Values
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
import time
import pyautogui


# Constants
TABLE_CROP_X = 206
TABLE_CROP_Y = 225
TABLE_CROP_WIDTH = 1450
TABLE_CROP_HEIGHT = 780
SCROLLBAR_CHECK_REGION = (205, 225, 1450, 780)
TARGET_REGION_Y = 225
TARGET_REGION_HEIGHT = 250
SCROLLBAR_CONFIDENCE = 0.95


def scroll_to_table_top(table_center_x: int, table_center_y: int) -> None:
    """
    Scroll the table to the top position by looking for 'Network Code' or 'Estimate' text.
    Stops scrolling when either of these texts is found (indicating we're at the top).
    
    Args:
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
    """
    print(f"[ACTION_HANDLER] Scrolling up to beginning (looking for 'Network Code' or 'Estimate')...")
    
    scanner = TextScanner()
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.2)
    
    max_scroll_attempts = 200
    at_top = False
    
    for scroll_num in range(1, max_scroll_attempts + 1):
        pyautogui.scroll(50)  # Positive value scrolls up
        time.sleep(0.05)
        
        check_screenshot = computer_vision_utils.take_screenshot()
        if check_screenshot is not None:
            # Crop the table header region to search for text
            header_region = check_screenshot[TABLE_CROP_Y:TABLE_CROP_Y+100, TABLE_CROP_X:TABLE_CROP_X+TABLE_CROP_WIDTH]
            
            # Extract text from the header region
            success, extracted_text = scanner.extract_text(header_region)
            
            if success:
                # Check if we found either "Network Code" or "Estimate"
                found_network_code = "network code" in extracted_text.lower()
                found_estimate = "estimate" in extracted_text.lower()
                
                if found_network_code or found_estimate:
                    found_text = []
                    if found_network_code:
                        found_text.append("'Network Code'")
                    if found_estimate:
                        found_text.append("'Estimate'")
                    print(f"[ACTION_HANDLER] ✓ Found {' and '.join(found_text)} - reached top position after {scroll_num} scroll(s)")
                    at_top = True
                    break
                elif scroll_num % 10 == 0:
                    print(f"[ACTION_HANDLER] Not at top yet (no 'Network Code' or 'Estimate' found), scrolled {scroll_num} times, continuing...")
            elif scroll_num % 10 == 0:
                print(f"[ACTION_HANDLER] Warning: OCR extraction failed at scroll {scroll_num}, continuing...")
        else:
            print(f"[ACTION_HANDLER] Warning: Failed to take screenshot at scroll {scroll_num}")
    
    if at_top:
        print(f"[ACTION_HANDLER] ✓ Successfully scrolled to top of table")
    else:
        print(f"[ACTION_HANDLER] Warning: Reached max scroll attempts ({max_scroll_attempts}), assuming at top")


def position_row_in_target_region(click_x: int, click_y: int, 
                                   table_center_x: int, table_center_y: int,
                                   crop_x: int, crop_y: int, crop_width: int, crop_height: int,
                                   template, target_texts, estimate_number: str) -> Tuple[bool, str]:
    """
    After clicking a row, scroll down to position it within the target region if needed.
    Uses blue color detection to find the highlighted row position.
    
    Args:
        click_x: X position of the clicked row
        click_y: Current Y position of the clicked row
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
        crop_x, crop_y, crop_width, crop_height: Table crop region for searching
        template: Template for column detection
        target_texts: Target texts to search for
        estimate_number: Estimate number for searching
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    target_region_bottom = TARGET_REGION_Y + TARGET_REGION_HEIGHT
    
    # Wait for the row to be highlighted in blue after clicking
    time.sleep(0.3)
    
    # Detect blue highlighted row
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        print(f"[ACTION_HANDLER] Warning: Failed to take screenshot for blue detection")
        return False, "Failed to take screenshot"
    
    found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(screenshot)
    if not found_blue or row_info is None:
        print(f"[ACTION_HANDLER] Warning: Could not detect blue highlighted row after clicking")
        return False, "Could not detect blue highlighted row"
    
    blue_row_y = row_info['y']
    blue_row_height = row_info['height']
    blue_row_center_y = blue_row_y + (blue_row_height // 2)
    blue_row_top = blue_row_y
    blue_row_bottom = blue_row_y + blue_row_height
    
    print(f"[ACTION_HANDLER] Blue highlighted row detected at y={blue_row_y}, center_y={blue_row_center_y}, height={blue_row_height}")
    print(f"[ACTION_HANDLER] Blue row bounds: top={blue_row_top}, bottom={blue_row_bottom}")
    print(f"[ACTION_HANDLER] Target region bounds: top={TARGET_REGION_Y}, bottom={target_region_bottom}")
    
    # Check if the entire row (or at least most of it) is already within the target region
    # Consider the row "in region" if its top is below target top and its center is above target bottom
    row_in_region = (blue_row_top >= TARGET_REGION_Y) and (blue_row_center_y <= target_region_bottom)
    
    if row_in_region:
        print(f"[ACTION_HANDLER] ✓ Row already in target region (top={blue_row_top}, center={blue_row_center_y})")
        print(f"[ACTION_HANDLER] ✓ No scrolling needed - row is already positioned correctly")
        return True, "Row already in target region"
    
    print(f"[ACTION_HANDLER] ✗ Row NOT in target region (top={blue_row_top} vs target_top={TARGET_REGION_Y}, center={blue_row_center_y} vs target_bottom={target_region_bottom})")
    print(f"[ACTION_HANDLER] Scrolling down to position row in target region {TARGET_REGION_Y}-{target_region_bottom}...")
    
    # Load end scrollbar template to detect when we can't scroll anymore
    end_scrollbar_template = computer_vision_utils.load_image("src/workflow_module/actions/assets/EndScrollbar.png")
    if end_scrollbar_template is None:
        print(f"[ACTION_HANDLER] Warning: EndScrollbar template not found")
    
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.2)
    
    max_position_scrolls = 100
    scroll_amount = -20  # Scroll down slowly (negative value)
    
    for scroll_num in range(1, max_position_scrolls + 1):
        pyautogui.scroll(scroll_amount)
        time.sleep(0.05)
        
        check_screenshot = computer_vision_utils.take_screenshot()
        if check_screenshot is None:
            if scroll_num % 10 == 0:
                print(f"[ACTION_HANDLER] Warning: Screenshot failed at scroll {scroll_num}")
            continue
        
        # Check if scrollbar is at the end (can't scroll anymore)
        if end_scrollbar_template is not None:
            end_found, _, _ = computer_vision_utils.match_template_in_region(
                check_screenshot, end_scrollbar_template, SCROLLBAR_CHECK_REGION, confidence=SCROLLBAR_CONFIDENCE
            )
            
            if end_found:
                print(f"[ACTION_HANDLER] ✓ Scrollbar at end position, can't scroll further. Continuing with current position.")
                return True, "Scrollbar at end, continuing with current row position"
        
        # Detect blue row position
        check_found, check_row_info = computer_vision_utils.find_blue_highlighted_row(check_screenshot)
        
        if check_found and check_row_info:
            new_blue_y = check_row_info['y']
            new_blue_height = check_row_info['height']
            new_blue_center_y = new_blue_y + (new_blue_height // 2)
            
            # Check if row is now in target region
            if TARGET_REGION_Y <= new_blue_center_y <= target_region_bottom:
                print(f"[ACTION_HANDLER] ✓ Row positioned in target region after {scroll_num} scroll(s) (y={new_blue_center_y})")
                return True, f"Row positioned in target region at y={new_blue_center_y}"
            elif scroll_num % 10 == 0:
                print(f"[ACTION_HANDLER] Positioning scroll {scroll_num}: blue row at y={new_blue_center_y}, continuing...")
        elif scroll_num % 10 == 0:
            print(f"[ACTION_HANDLER] Warning: Blue row not detected at scroll {scroll_num}, continuing...")
    
    print(f"[ACTION_HANDLER] Warning: Reached max positioning scrolls ({max_position_scrolls}), continuing anyway")
    return True, "Reached max positioning scrolls, continuing with current position"


def click_and_position_row(match_info: Dict, table_center_x: int, table_center_y: int,
                           crop_x: int, crop_y: int, crop_width: int, crop_height: int,
                           template, target_texts, estimate_number: str) -> Tuple[bool, str]:
    """
    Click on a matched row and position it in the target region.
    
    Args:
        match_info: Dictionary containing match information (click_x, click_y, button, matched_count)
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
        crop_x, crop_y, crop_width, crop_height: Table crop region for searching
        template: Template for column detection
        target_texts: Target texts to search for
        estimate_number: Estimate number for searching
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    click_x = match_info['click_x']
    click_y = match_info['click_y']
    button = match_info['button']
    matched_count = match_info['matched_count']
    
    print(f"[ACTION_HANDLER] Clicking at ({click_x}, {click_y}) with button={button}")
    success, action_msg = actions.click_at_position(click_x, click_y, clicks=1, button=button)
    if not success:
        return False, f"Failed to click at position: {action_msg}"
    
    # Position row in target region
    time.sleep(0.3)
    position_success, position_msg = position_row_in_target_region(
        click_x, click_y, table_center_x, table_center_y,
        crop_x, crop_y, crop_width, crop_height,
        template, target_texts, estimate_number
    )
    
    if not position_success:
        print(f"[ACTION_HANDLER] Warning: {position_msg}")
    
    return True, f"Row found and clicked! Matched {matched_count}/{len(target_texts)} targets"


def action(estimate_number: str = "", advertiser_name: str = "", begin_date: str = "", end_date: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Main action handler to select a row by matching values.
    
    Args:
        estimate_number: Estimate number to search for
        advertiser_name: Advertiser name to search for
        begin_date: Begin date to search for
        end_date: End date to search for
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    target_texts = [estimate_number, advertiser_name, begin_date, end_date]
    if any(t is None for t in target_texts):
        return False, "Missing required params"

    print(f"[ACTION_HANDLER] Hunting for targets: {target_texts}")
    
    try:
        # Calculate table center coordinates
        table_center_x = TABLE_CROP_X + TABLE_CROP_WIDTH // 2
        table_center_y = TABLE_CROP_Y + TABLE_CROP_HEIGHT // 2
        
        # Check if we're at the top by looking for header text
        print(f"[ACTION_HANDLER] Checking if table is at top position...")
        scanner = TextScanner()
        screenshot = computer_vision_utils.take_screenshot()
        
        if screenshot is None:
            print(f"[ACTION_HANDLER] Warning: Failed to take screenshot, will scroll to top to be safe")
            scroll_to_table_top(table_center_x, table_center_y)
        else:
            # Check header region for "Network Code" or "Estimate"
            header_region = screenshot[TABLE_CROP_Y:TABLE_CROP_Y+100, TABLE_CROP_X:TABLE_CROP_X+TABLE_CROP_WIDTH]
            success, extracted_text = scanner.extract_text(header_region)
            
            if success:
                found_network_code = "network code" in extracted_text.lower()
                found_estimate = "estimate" in extracted_text.lower()
                
                if found_network_code or found_estimate:
                    found_text = []
                    if found_network_code:
                        found_text.append("'Network Code'")
                    if found_estimate:
                        found_text.append("'Estimate'")
                    print(f"[ACTION_HANDLER] ✓ Found {' and '.join(found_text)} - table is at top position, ready to search")
                else:
                    print(f"[ACTION_HANDLER] ✗ Header text not found - table is not at top")
                    scroll_to_table_top(table_center_x, table_center_y)
            else:
                print(f"[ACTION_HANDLER] Warning: OCR extraction failed, will scroll to top to be safe")
                scroll_to_table_top(table_center_x, table_center_y)

        # Load column template
        template = computer_vision_utils.load_image("src/workflow_module/actions/assets/ColumnLine.png")
        if template is None:
            return False, "Template load failed"

        # Check results count to determine if scrolling is needed
        print(f"[ACTION_HANDLER] Checking results count...")
        results_count = table_utils.get_results_count()
        should_scroll = True
        
        if results_count is not None:
            print(f"[ACTION_HANDLER] Found {results_count} results in table")
            if results_count <= 30:
                print(f"[ACTION_HANDLER] Results count ({results_count}) <= 30, will NOT scroll")
                should_scroll = False
            else:
                print(f"[ACTION_HANDLER] Results count ({results_count}) > 30, will scroll through table")
        else:
            print(f"[ACTION_HANDLER] Could not determine results count, will proceed with scrolling")

        # Search initial view
        print(f"\n[ACTION_HANDLER] ========== Searching initial view (scroll 0) ==========")
        found, msg, match_info = table_utils.search_current_view(
            target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT, 
            template, select_row=False
        )
        
        if found and match_info:
            print(f"[ACTION_HANDLER] ✓ Match found in initial view! Matched {match_info['matched_count']}/{len(target_texts)} targets")
            print(f"[ACTION_HANDLER] Using first match immediately")
            return click_and_position_row(
                match_info, table_center_x, table_center_y,
                TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
                template, target_texts, estimate_number
            )
        else:
            print(f"[ACTION_HANDLER] Target not in initial view: {msg}")

        if not should_scroll:
            return False, "Target not found in initial view (results <= 30, no scrolling performed)"

        # Search with scrolling
        print(f"[ACTION_HANDLER] Starting search with scrolling (max 50 scroll attempts)")
        pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
        time.sleep(0.3)

        max_scroll_attempts = 50
        scroll_amount = -35
        scrolls_per_page = 11

        for scroll_attempt in range(1, max_scroll_attempts + 1):
            print(f"\n[ACTION_HANDLER] ========== Scroll attempt {scroll_attempt}/{max_scroll_attempts} ==========")
            
            for _ in range(scrolls_per_page):
                pyautogui.scroll(scroll_amount)
                time.sleep(0.05)
            time.sleep(0.3)
            
            found, msg, match_info = table_utils.search_current_view(
                target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
                template, select_row=True
            )
            
            if found and match_info:
                print(f"[ACTION_HANDLER] ✓ Match found at scroll {scroll_attempt}! Matched {match_info['matched_count']}/{len(target_texts)} targets")
                print(f"[ACTION_HANDLER] Using first match immediately")
                return click_and_position_row(
                    match_info, table_center_x, table_center_y,
                    TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
                    template, target_texts, estimate_number
                )
            else:
                print(f"[ACTION_HANDLER] Target not found at scroll {scroll_attempt}: {msg}")

        return False, f"Target not found after scrolling through {max_scroll_attempts} pages"
        
    except Exception as e:
        return False, f"Error finding row: {e}"


def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verifier function for action."""
    return True, "Row found and clicked", None


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Error handler for retrying the action."""
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"


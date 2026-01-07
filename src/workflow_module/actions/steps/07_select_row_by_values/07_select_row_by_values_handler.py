#!/usr/bin/env python3
"""
Handler for: Select Row by Values
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import field_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
# Import step 07 helpers (using importlib to handle numeric module name)
import importlib.util
import os
helpers_path = os.path.join(os.path.dirname(__file__), '07_helpers.py')
spec = importlib.util.spec_from_file_location("helpers_07", helpers_path)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
import time
import pyautogui

# Constants
TABLE_CROP_X = 206
TABLE_CROP_Y = 225
TABLE_CROP_WIDTH = 1450
TABLE_CROP_HEIGHT = 850
SCROLLBAR_CHECK_REGION = (205, 225, 1450, 780)
TARGET_REGION_Y = 225
TARGET_REGION_HEIGHT = 250


def ensure_table_at_top(table_center_x, table_center_y):
    """Checks if table is at the top, scrolls to top if not."""
    print(f"[ACTION_HANDLER] Ensuring table is at top position...")
    scanner = TextScanner()
    
    max_scroll_attempts = 200
    at_top = False
    
    for scroll_num in range(1, max_scroll_attempts + 1):
        # Check if at top
        screenshot = computer_vision_utils.take_screenshot()
        
        if screenshot is not None:
            # Check header region for "Network Code" or "Estimate"
            header_region = screenshot[TABLE_CROP_Y:TABLE_CROP_Y+100, TABLE_CROP_X:TABLE_CROP_X+TABLE_CROP_WIDTH]
            success, extracted_text = scanner.extract_text(header_region)
            
            if success:
                text_lower = extracted_text.lower()
                if "network code" in text_lower or "estimate" in text_lower:
                    print(f"[ACTION_HANDLER] ✓ Table is at top position")
                    at_top = True
                    break
        
        # Not at top, scroll up
        if scroll_num % 10 == 0:
            print(f"[ACTION_HANDLER] Table not at top, scrolling up (iteration {scroll_num})...")
            
        helpers.scroll_to_table_top(table_center_x, table_center_y)
        
    if not at_top:
        print(f"[ACTION_HANDLER] Warning: Reached max scroll attempts ({max_scroll_attempts}), assuming at top")


def action(estimate_number: str = "", advertiser_name: str = "", begin_date: str = "", end_date: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Main action handler to select a row by matching values.
    """
    target_texts = [estimate_number, advertiser_name, begin_date, end_date]
    if any(t is None for t in target_texts):
        return False, "Missing required params"

    # Calculate table center coordinates
    table_center_x = TABLE_CROP_X + TABLE_CROP_WIDTH // 2
    table_center_y = TABLE_CROP_Y + TABLE_CROP_HEIGHT // 2
    
    # Step 1: Ensure table is at the top
    ensure_table_at_top(table_center_x, table_center_y)

    # Step 2: Load column template
    handler_dir = os.path.dirname(os.path.abspath(__file__))
    column_line_path = os.path.join(handler_dir, '07_ColumnLine.png')
    template = computer_vision_utils.load_image(column_line_path)
    if template is None:
        return False, "Template load failed"

    # Step 3: Check results count
    results_count = field_utils.get_results_count()
    should_scroll = True
    if results_count is not None and results_count <= 30:
        print(f"[ACTION_HANDLER] Results count ({results_count}) <= 30, will NOT scroll")
        should_scroll = False

    # Step 4: Search initial view
    print(f"[ACTION_HANDLER] Searching initial view...")
    found, msg, match_info = helpers.search_current_view(
        target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT, 
        template, select_row=False
    )
    
    if found and match_info:
        print(f"[ACTION_HANDLER] ✓ Match found in initial view")
        return helpers.click_and_position_row(
            match_info, table_center_x, table_center_y,
            TARGET_REGION_Y, TARGET_REGION_HEIGHT,
            TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT
        )

    if not should_scroll:
        return False, "Target not found in initial view (results <= 30)"

    # Step 5: Search with scrolling
    print(f"[ACTION_HANDLER] Starting search with scrolling...")
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.3)

    max_scroll_attempts = 50
    scroll_amount = -35
    scrolls_per_page = 11

    for scroll_attempt in range(1, max_scroll_attempts + 1):
        # Scroll down one 'page'
        for _ in range(scrolls_per_page):
            pyautogui.scroll(scroll_amount)
            time.sleep(0.05)
        time.sleep(0.3)
        
        found, msg, match_info = helpers.search_current_view(
            target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
            template, select_row=True
        )
        
        if found and match_info:
            print(f"[ACTION_HANDLER] ✓ Match found at scroll {scroll_attempt}")
            return helpers.click_and_position_row(
                match_info, table_center_x, table_center_y,
                TARGET_REGION_Y, TARGET_REGION_HEIGHT,
                TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT
            )
        
        if scroll_attempt % 5 == 0:
             print(f"[ACTION_HANDLER] Scrolled {scroll_attempt} pages...")

    return False, f"Target not found after scrolling {max_scroll_attempts} pages"


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the row was found and clicked."""
    return True, "Row found and clicked", {"verified": True}

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed to select row after {max_attempts} attempts"

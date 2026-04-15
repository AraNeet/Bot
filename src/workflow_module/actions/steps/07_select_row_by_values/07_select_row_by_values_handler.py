#!/usr/bin/env python3
"""
Handler for: Select Row by Values

- Precheck: Verify search page is displayed with results loaded
- Action: Search through table rows to find matching estimate number (unchanged logic)
- Verifier: Pass-through (row click verified by next step)
- Error Handler: Retry with wait
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import field_utils
from src.workflow_module.actions.helpers.vision_service import scanner
from src.workflow_module.actions.helpers.precheck_utils import verify_page
from src.workflow_module.pages.page_loader import get_element
# Import step 07 helpers (using importlib to handle numeric module name)
import importlib.util
import os
helpers_path = os.path.join(os.path.dirname(__file__), '07_helpers.py')
spec = importlib.util.spec_from_file_location("helpers_07", helpers_path)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
import time
import pyautogui

# Load table config from page config
_table_config = get_element("search_page", "results_table")
TABLE_CROP_X = _table_config["crop_x"]
TABLE_CROP_Y = _table_config["crop_y"]
TABLE_CROP_WIDTH = _table_config["crop_width"]
TABLE_CROP_HEIGHT = _table_config["crop_height"]
SCROLLBAR_CHECK_REGION = tuple(_table_config["scrollbar_check_region"])
TARGET_REGION_Y = _table_config["target_region_y"]
TARGET_REGION_HEIGHT = _table_config["target_region_height"]

# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify search page is displayed and results are loaded."""
    page_ok, page_msg = verify_page("search_page")
    if not page_ok:
        return False, page_msg
    
    # Also verify results count is > 0
    results_count = field_utils.get_results_count()
    if results_count is not None and results_count > 0:
        return True, f"Search page visible with {results_count} results"
    elif results_count == 0:
        return False, "Search results show 0 results — nothing to search in"
    else:
        # Can't read results count, but page is visible — proceed anyway
        return True, "Search page visible (results count unreadable)"

# ============================================================================
# ACTION (logic unchanged, only constant sources changed)
# ============================================================================

def ensure_table_at_top(table_center_x, table_center_y):
    """Checks if table is at the top, scrolls to top if not."""
    print(f"[ACTION_HANDLER] Ensuring table is at top position...")
    local_scanner = scanner  # Use shared singleton
    
    max_scroll_attempts = 200
    at_top = False
    
    for scroll_num in range(1, max_scroll_attempts + 1):
        screenshot = computer_vision_utils.take_screenshot()
        
        if screenshot is not None:
            header_region = screenshot[TABLE_CROP_Y:TABLE_CROP_Y+100, TABLE_CROP_X:TABLE_CROP_X+TABLE_CROP_WIDTH]
            success, extracted_text = local_scanner.extract_text(header_region)
            
            if success:
                text_lower = extracted_text.lower()
                if "network code" in text_lower or "estimate" in text_lower:
                    print(f"[ACTION_HANDLER] Table is at top position")
                    at_top = True
                    break
        
        if scroll_num % 10 == 0:
            print(f"[ACTION_HANDLER] Table not at top, scrolling up (iteration {scroll_num})...")
            
        helpers.scroll_to_table_top(table_center_x, table_center_y)
    
    if not at_top:
        print(f"[ACTION_HANDLER] Warning: Reached max scroll attempts ({max_scroll_attempts}), assuming at top")


def action(estimate_number: str = "", advertiser_name: str = "", begin_date: str = "", end_date: str = "", **kwargs) -> Tuple[bool, str]:
    """Main action handler to select a row by matching values."""
    target_texts = [estimate_number, advertiser_name, begin_date, end_date]
    if any(t is None for t in target_texts):
        return False, "Missing required params"

    table_center_x = TABLE_CROP_X + TABLE_CROP_WIDTH // 2
    table_center_y = TABLE_CROP_Y + TABLE_CROP_HEIGHT // 2
    
    ensure_table_at_top(table_center_x, table_center_y)

    handler_dir = os.path.dirname(os.path.abspath(__file__))
    column_line_path = os.path.join(handler_dir, '07_ColumnLine.png')
    template = computer_vision_utils.load_image(column_line_path)
    if template is None:
        return False, "Template load failed"

    results_count = field_utils.get_results_count()
    should_scroll = True
    if results_count is not None and results_count <= 30:
        print(f"[ACTION_HANDLER] Results count ({results_count}) <= 30, will NOT scroll")
        should_scroll = False

    print(f"[ACTION_HANDLER] Searching initial view...")
    found, msg, match_info = helpers.search_current_view(
        target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT, 
        template, select_row=False
    )
    
    if found and match_info:
        print(f"[ACTION_HANDLER] Match found in initial view")
        return helpers.click_and_position_row(
            match_info, table_center_x, table_center_y,
            TARGET_REGION_Y, TARGET_REGION_HEIGHT,
            TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT
        )

    if not should_scroll:
        return False, "Target not found in initial view (results <= 30)"

    print(f"[ACTION_HANDLER] Starting search with scrolling...")
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.3)

    max_scroll_attempts = 50
    scroll_amount = -35
    scrolls_per_page = 11

    for scroll_attempt in range(1, max_scroll_attempts + 1):
        for _ in range(scrolls_per_page):
            pyautogui.scroll(scroll_amount)
            time.sleep(0.05)
        time.sleep(0.3)
        
        found, msg, match_info = helpers.search_current_view(
            target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
            template, select_row=True
        )
        
        if found and match_info:
            print(f"[ACTION_HANDLER] Match found at scroll {scroll_attempt}")
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

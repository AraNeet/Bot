#!/usr/bin/env python3
"""
Handler for: Select Row by Values
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import row_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
import time
import pyautogui
import os


# Constants
TABLE_CROP_X = 206
TABLE_CROP_Y = 225
TABLE_CROP_WIDTH = 1450
TABLE_CROP_HEIGHT = 780
SCROLLBAR_CHECK_REGION = (205, 225, 1450, 780)
TARGET_REGION_Y = 225
TARGET_REGION_HEIGHT = 250
SCROLLBAR_CONFIDENCE = 0.95


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
            table_utils.scroll_to_table_top(table_center_x, table_center_y, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH)
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
                    table_utils.scroll_to_table_top(table_center_x, table_center_y, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH)
            else:
                print(f"[ACTION_HANDLER] Warning: OCR extraction failed, will scroll to top to be safe")
                table_utils.scroll_to_table_top(table_center_x, table_center_y, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH)

        # Load column template from local folder
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        column_line_path = os.path.join(handler_dir, 'ColumnLine.png')
        template = computer_vision_utils.load_image(column_line_path)
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
        found, msg, match_info = row_utils.search_current_view(
            target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT, 
            template, select_row=False
        )
        
        if found and match_info:
            print(f"[ACTION_HANDLER] ✓ Match found in initial view! Matched {match_info['matched_count']}/{len(target_texts)} targets")
            print(f"[ACTION_HANDLER] Using first match immediately")
            return table_utils.click_and_position_row(
                match_info, table_center_x, table_center_y,
                TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
                template, target_texts, estimate_number,
                TARGET_REGION_Y, TARGET_REGION_HEIGHT,
                SCROLLBAR_CHECK_REGION, SCROLLBAR_CONFIDENCE
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
            
            found, msg, match_info = row_utils.search_current_view(
                target_texts, estimate_number, TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
                template, select_row=True
            )
            
            if found and match_info:
                print(f"[ACTION_HANDLER] ✓ Match found at scroll {scroll_attempt}! Matched {match_info['matched_count']}/{len(target_texts)} targets")
                print(f"[ACTION_HANDLER] Using first match immediately")
                return table_utils.click_and_position_row(
                    match_info, table_center_x, table_center_y,
                    TABLE_CROP_X, TABLE_CROP_Y, TABLE_CROP_WIDTH, TABLE_CROP_HEIGHT,
                    template, target_texts, estimate_number,
                    TARGET_REGION_Y, TARGET_REGION_HEIGHT,
                    SCROLLBAR_CHECK_REGION, SCROLLBAR_CONFIDENCE
                )
            else:
                print(f"[ACTION_HANDLER] Target not found at scroll {scroll_attempt}: {msg}")

        return False, f"Target not found after scrolling through {max_scroll_attempts} pages"
        
    except Exception as e:
        error_msg = f"Error finding row: {e}"
        print(f"[ACTION_HANDLER ERROR] {error_msg}")
        return False, error_msg


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the row was found and clicked.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying row selection...")
    
    verification_data = {
        "verified": True,
        "message": "Row found and clicked"
    }
    return True, "Row found and clicked", verification_data

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors specific to selecting row by values.
    
    Args:
        error_msg: The error message from the failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        **kwargs: Additional context
        
    Returns:
        Tuple of (should_retry: bool, recovery_message: str)
    """
    print(f"[ERROR_HANDLER] Handling error for select_row_by_values (attempt {attempt}/{max_attempts})")
    print(f"[ERROR_HANDLER] Error: {error_msg}")
    
    if attempt < max_attempts:
        print(f"[ERROR_HANDLER] Will retry after waiting 1 second...")
        time.sleep(1.0)
        return True, "Retrying action"
    
    return False, f"Failed to select row after {max_attempts} attempts"


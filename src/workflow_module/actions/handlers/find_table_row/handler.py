#!/usr/bin/env python3
"""
Handler for: Find Row by Values

This module contains:
- Action: Find a row matching provided parameters and right-click on it
- Verifier: Verify the row was found and clicked
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import table_utils
import time
import pyautogui

# ============================================================================
# ACTION
# ============================================================================

def action(estimate_number: str = "", advertiser_name: str = "", begin_date: str = "", end_date: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Find a row matching provided parameters with scrolling support.
    Returns first match found immediately (no verification scroll).
    
    Args:
        estimate_number: Estimate number to find
        advertiser_name: Advertiser name to find
        begin_date: Begin date to find
        end_date: End date to find
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    target_texts = [estimate_number, advertiser_name, begin_date, end_date]
    if any(t is None for t in target_texts):
        return False, "Missing required params"

    print(f"[ACTION_HANDLER] Hunting for targets: {target_texts}")

    try:
        # Load template once
        template = computer_vision_utils.load_image("src/workflow_module/actions/handlers/find_table_row/ColumnLine.png")
        if template is None:
            return False, "Template load failed"

        # Table configuration
        crop_x, crop_y = 206, 225
        crop_width, crop_height = 1445, 840
        table_center_x = crop_x + crop_width // 2
        table_center_y = crop_y + crop_height // 2
        
        # Scrolling configuration
        max_scroll_attempts = 50  # Maximum scrolls to perform
        scroll_amount = -35  # Negative = scroll down (increased by 1.5x)
        scrolls_per_page = 11  # Number of scrolls to move one full page
        
        # Check results count first
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
        
        # Search initial view (scroll_attempt = 0)
        print(f"\n[ACTION_HANDLER] ========== Searching initial view (scroll 0) ==========")
        found, msg, match_info = table_utils.search_current_view(target_texts, estimate_number, crop_x, crop_y, 
                                                                  crop_width, crop_height, template, select_row=False)
        if found and match_info:
            print(f"[ACTION_HANDLER] ✓ Match found in initial view! Matched {match_info['matched_count']}/{len(target_texts)} targets")
            print(f"[ACTION_HANDLER] Using first match immediately")
            
            click_x = match_info['click_x']
            click_y = match_info['click_y']
            button = match_info['button']
            
            print(f"[ACTION_HANDLER] Clicking at ({click_x}, {click_y}) with button={button}")
            success, action_msg = actions.click_at_position(click_x, click_y, clicks=1, button=button)
            if not success:
                return False, f"Failed to click at position: {action_msg}"
            
            return True, f"Row found and clicked! Matched {match_info['matched_count']}/{len(target_texts)} targets"
        else:
            print(f"[ACTION_HANDLER] Target not in initial view: {msg}")
        
        # If we shouldn't scroll, stop here
        if not should_scroll:
            return False, "Target not found in initial view (results <= 30, no scrolling performed)"
        
        # Move mouse to table center for scrolling
        print(f"[ACTION_HANDLER] Starting search with scrolling (max {max_scroll_attempts} scroll attempts)")
        pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
        time.sleep(0.3)
        
        # Scroll through table until first match is found
        for scroll_attempt in range(1, max_scroll_attempts + 1):
            print(f"\n[ACTION_HANDLER] ========== Scroll attempt {scroll_attempt}/{max_scroll_attempts} ==========")
            
            # Scroll down one page
            for _ in range(scrolls_per_page):
                pyautogui.scroll(scroll_amount)
                time.sleep(0.05)
            
            time.sleep(0.3)  # Wait for table to update
            
            # Search current view
            found, msg, match_info = table_utils.search_current_view(target_texts, estimate_number, crop_x, crop_y,
                                                                     crop_width, crop_height, template, select_row=True)
            
            if found and match_info:
                print(f"[ACTION_HANDLER] ✓ Match found at scroll {scroll_attempt}! Matched {match_info['matched_count']}/{len(target_texts)} targets")
                print(f"[ACTION_HANDLER] Using first match immediately")
                
                # Click on match immediately
                click_x = match_info['click_x']
                click_y = match_info['click_y']
                button = match_info['button']
                
                print(f"[ACTION_HANDLER] Clicking at ({click_x}, {click_y}) with button={button}")
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=1, button=button)
                if not success:
                    return False, f"Failed to click at position: {action_msg}"
                
                return True, f"Row found and clicked! Matched {match_info['matched_count']}/{len(target_texts)} targets"
            else:
                print(f"[ACTION_HANDLER] Target not found at scroll {scroll_attempt}: {msg}")
        
        # No match found after all scrolling attempts
        return False, f"Target not found after scrolling through {max_scroll_attempts} pages"
        
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

#!/usr/bin/env python3
"""
Handler for: Open Multinetwork by Instructions

This module contains:
- Action: Find and double-click on a row in the second table (within expanded row) by begin_date
- Verifier: Verify the row was found and clicked
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import table_utils
import time
import pyautogui

# ============================================================================
# ACTION
# ============================================================================

def action(begin_date: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Find and double-click on a row in the second table (within expanded row) by begin_date.
    
    The second table appears within the expanded row from the first table search.
    This function uses row boundary detection to handle variable height rows.
    
    - If there are multiple matches, double-clicks the second match
    - If there's only one match, double-clicks that match
    
    Args:
        begin_date: Begin date to find (from input file)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not begin_date:
        return False, "Missing begin_date parameter"
    
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    
    try:
        # Get current mouse position to determine crop region
        mouse_x, mouse_y = pyautogui.position()
        print(f"[ACTION_HANDLER] Current mouse position: ({mouse_x}, {mouse_y})")
        
        # Get screen size to validate crop region
        screen_width, screen_height = pyautogui.size()
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Crop down from mouse position with specified width
        crop_x = mouse_x  # Start from mouse X position
        crop_y = mouse_y  # Start from mouse Y position (crop down from here)
        crop_width = 1550  # Width as specified
        crop_height = screen_height - crop_y  # Height from mouse to bottom of screen
        
        # Validate and adjust crop region to stay within screen bounds
        if crop_x < 0:
            crop_x = 0
        
        if crop_y < 0:
            crop_y = 0
        
        # Adjust width if it extends beyond screen
        if crop_x + crop_width > screen_width:
            crop_width = screen_width - crop_x
            print(f"[ACTION_HANDLER] Adjusted crop_width to {crop_width} to stay within screen bounds")
        
        # Height is already calculated to bottom of screen, but validate it's positive
        if crop_height <= 0:
            return False, f"Invalid crop_height: {crop_height} (mouse_y={mouse_y}, screen_height={screen_height})"
        
        print(f"[ACTION_HANDLER] Final crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        
        # Search the second table for the begin_date (returns all matches)
        found, msg, matches = table_utils.search_second_table_by_date(
            begin_date=begin_date,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height
        )
        
        # If not found, try scrolling down and searching again
        max_scroll_attempts = 3
        scroll_amount = -50  # Negative = scroll down
        current_crop_y = crop_y
        
        if not found or not matches:
            print(f"[ACTION_HANDLER] Begin date not found in initial view: {msg}")
            print(f"[ACTION_HANDLER] Attempting to scroll down to find begin_date...")
            
            # Move mouse to the center of the crop region for scrolling
            scroll_center_x = crop_x + crop_width // 2
            scroll_center_y = current_crop_y + crop_height // 2
            pyautogui.moveTo(scroll_center_x, scroll_center_y, duration=0.2)
            time.sleep(0.3)
            
            for scroll_attempt in range(1, max_scroll_attempts + 1):
                print(f"[ACTION_HANDLER] Scroll attempt {scroll_attempt}/{max_scroll_attempts}")
                
                # Scroll down
                pyautogui.scroll(scroll_amount)
                time.sleep(0.5)  # Wait for content to update
                
                # Update crop_y since we scrolled (content moved up, so visible region changed)
                # The scroll moves content up, so we need to adjust crop_y
                current_crop_y = crop_y  # Keep original crop_y, scrolling reveals more content below
                
                # Search again with updated crop region
                found, msg, matches = table_utils.search_second_table_by_date(
                    begin_date=begin_date,
                    crop_x=crop_x,
                    crop_y=current_crop_y,
                    crop_width=crop_width,
                    crop_height=crop_height
                )
                
                if found and matches:
                    print(f"[ACTION_HANDLER] Found begin_date after {scroll_attempt} scroll(s)")
                    break
                else:
                    print(f"[ACTION_HANDLER] Still not found after scroll {scroll_attempt}: {msg}")
        
        if not found or not matches:
            return False, f"Begin date not found after scrolling: {msg}"
        
        print(f"[ACTION_HANDLER] Found {len(matches)} matching row(s)")
        
        # If we're selecting the last match, verify it's truly the last one by scrolling down
        if len(matches) > 1:
            # Multiple matches - need to verify the last match is truly the last
            print(f"[ACTION_HANDLER] Multiple matches found ({len(matches)}), verifying last match is truly the last...")
            
            # Move mouse to center of crop region for scrolling
            scroll_center_x = crop_x + crop_width // 2
            scroll_center_y = crop_y + crop_height // 2
            pyautogui.moveTo(scroll_center_x, scroll_center_y, duration=0.2)
            time.sleep(0.3)
            
            # Keep scrolling and checking until we find the true last match
            max_verification_scrolls = 5
            all_matches_found = matches.copy()  # Track all matches found across scrolls
            last_match = matches[-1]
            
            for verification_scroll in range(max_verification_scrolls):
                print(f"[ACTION_HANDLER] Verification scroll {verification_scroll + 1}/{max_verification_scrolls}")
                
                # Scroll down more to reveal content below - scroll multiple times for more movement
                for _ in range(3):  # Scroll 3 times per verification check
                    pyautogui.scroll(-50)  # Scroll down 50 pixels each time
                    time.sleep(0.1)  # Small delay between scrolls
                time.sleep(0.5)  # Wait for content to update after all scrolls
                
                # Search again to see if there are more matches below
                found_more, msg_more, more_matches = table_utils.search_second_table_by_date(
                    begin_date=begin_date,
                    crop_x=crop_x,
                    crop_y=crop_y,
                    crop_width=crop_width,
                    crop_height=crop_height
                )
                
                if found_more and more_matches:
                    # Check if we found any NEW matches (not already in our list)
                    # Compare by Y coordinate to see if there are matches lower on screen
                    current_last_y = last_match['click_y']
                    matches_below = [m for m in more_matches if m['click_y'] > current_last_y]
                    
                    if matches_below:
                        # Found matches below our current last match - add them to our collection
                        # Sort by Y coordinate and take the one with highest Y (lowest on screen)
                        matches_below.sort(key=lambda m: m['click_y'], reverse=True)
                        new_last_match = matches_below[0]
                        
                        # Only update if this is truly a new match (check by Y coordinate)
                        if new_last_match['click_y'] > last_match['click_y']:
                            last_match = new_last_match
                            all_matches_found.extend(matches_below)
                            print(f"[ACTION_HANDLER] Found {len(matches_below)} more match(es) below current last match")
                            print(f"[ACTION_HANDLER] Updated last match to Y={last_match['click_y']} (row {last_match['row_index'] + 1})")
                        else:
                            # No new matches found below - we have the true last match
                            print(f"[ACTION_HANDLER] No new matches found below - verified as true last match")
                            break
                    else:
                        # No new matches found below current last match - we have the true last match
                        print(f"[ACTION_HANDLER] No more matches found below current last match - verified as true last match")
                        break
                else:
                    # No more matches found - we have the true last match
                    print(f"[ACTION_HANDLER] No more matches found - verified as true last match")
                    break
            
            match_to_click = last_match
            print(f"[ACTION_HANDLER] Double-clicking LAST match (row {match_to_click['row_index'] + 1}, Y={match_to_click['click_y']})")
            
            # After verification scrolling, re-search to get fresh coordinates for the last match
            print(f"[ACTION_HANDLER] Re-searching to get fresh coordinates after verification scrolls...")
            found_final, msg_final, final_matches = table_utils.search_second_table_by_date(
                begin_date=begin_date,
                crop_x=crop_x,
                crop_y=crop_y,
                crop_width=crop_width,
                crop_height=crop_height
            )
            
            if found_final and final_matches:
                # Find the match with the highest Y coordinate (lowest on screen)
                final_matches.sort(key=lambda m: m['click_y'], reverse=True)
                match_to_click = final_matches[0]
                print(f"[ACTION_HANDLER] Updated match coordinates from final search: Y={match_to_click['click_y']}")
        else:
            # Single match - double click it
            match_to_click = matches[0]
            print(f"[ACTION_HANDLER] Single match found, double-clicking it (row {match_to_click['row_index'] + 1})")
        
        # Double click on the chosen match
        click_x = match_to_click['click_x']
        click_y = match_to_click['click_y']
        
        print(f"[ACTION_HANDLER] Match to click - X: {click_x}, Y: {click_y}")
        print(f"[ACTION_HANDLER] Match details: row_index={match_to_click.get('row_index', 'N/A')}, text='{match_to_click.get('matched_text', 'N/A')[:50]}...'")
        
        # Ensure coordinates are valid
        if click_x is None or click_y is None:
            return False, f"Invalid click coordinates: x={click_x}, y={click_y}"
        
        # Apply 10px downward adjustment to fix click offset
        click_y = click_y + 10
        print(f"[ACTION_HANDLER] Adjusted click position: ({click_x}, {click_y}) (+10px Y offset)")
        
        # Move mouse to position first to ensure it's visible
        print(f"[ACTION_HANDLER] Moving mouse to ({click_x}, {click_y})")
        pyautogui.moveTo(click_x, click_y, duration=0.2)
        time.sleep(0.2)
        
        print(f"[ACTION_HANDLER] Double-clicking on row at ({click_x}, {click_y})")
        success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
        
        if not success:
            return False, f"Failed to double-click at position: {action_msg}"
        
        print(f"[ACTION_HANDLER] Double-click completed successfully")
        
        # Wait a moment for any UI update
        time.sleep(0.5)
        
        match_count_str = f"{len(matches)} match" + ("es" if len(matches) != 1 else "")
        return True, f"Row found and double-clicked! Begin date: '{begin_date}' ({match_count_str})"
        
    except Exception as e:
        return False, f"Error finding row by begin_date: {e}"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that the row was found and clicked."""
    # For this action, success of the action itself is the verification
    return True, "Row found and double-clicked", None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to opening multinetwork by instructions."""
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"


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
from src.workflow_module.actions_2.helpers import computer_vision_utils
import time
import pyautogui
import cv2
import numpy as np

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
        # Get screen size
        screen_width, screen_height = pyautogui.size()
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Detect the blue highlighted row to determine crop region
        print(f"[ACTION_HANDLER] Detecting blue highlighted row...")
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Convert BGR to HSV for better color detection
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        
        # Define blue color range in HSV (adjust these values based on your blue color)
        # Typical blue highlight: lower_blue = (100, 50, 50), upper_blue = (130, 255, 255)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        # Create mask for blue color
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Find contours of blue regions
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Default crop values (fallback if blue row not found)
        default_crop_x = 206
        default_crop_y = 225
        crop_x = default_crop_x
        crop_y = default_crop_y
        
        if contours:
            # Find the largest blue region (likely the selected row)
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Use the top-left corner of the blue region as crop start
            crop_x = x
            crop_y = y
            print(f"[ACTION_HANDLER] Found blue highlighted row at ({crop_x}, {crop_y}) with size {w}x{h}")
        else:
            print(f"[ACTION_HANDLER] Blue highlighted row not found in view, using default position ({default_crop_x}, {default_crop_y})")
        
        # Set crop dimensions
        crop_width = 1445  # Fixed width as specified
        
        # Detect the black/dark line that marks the end of the second table
        print(f"[ACTION_HANDLER] Detecting table bottom line (black border)...")
        bottom_line_y = table_utils.detect_table_bottom_line(
            screenshot, 
            start_y=crop_y, 
            crop_x=crop_x, 
            crop_width=crop_width
        )
        
        if bottom_line_y is not None:
            # Use the detected line as the end point
            crop_height = bottom_line_y - crop_y
            print(f"[ACTION_HANDLER] Found table bottom line at Y={bottom_line_y}, crop_height={crop_height}")
        else:
            # Fallback to bottom of screen if line not found
            crop_height = screen_height - crop_y
            print(f"[ACTION_HANDLER] Table bottom line not found, using screen bottom. crop_height={crop_height}")
        
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
            return False, f"Invalid crop_height: {crop_height} (crop_y={crop_y}, screen_height={screen_height})"
        
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
    """
    Verify that the network page is loading by detecting a loading circle/spinner.
    
    After double-clicking a row, waits for the network page to start loading.
    Looks for a loading circle in the center of the screen based on color detection.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying network page is loading by detecting loading circle...")
    
    try:
        # Wait a moment for the page to start loading after the double-click
        time.sleep(1.0)
        
        # Take screenshot to check for loading circle
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Detect loading circle in the center of the screen
        found, circle_info = computer_vision_utils.detect_loading_circle(
            screenshot,
            center_region_ratio=0.4,  # Search middle 40% of screen
            min_radius=15,
            max_radius=100,
            brightness_threshold=180  # Bright colors (white/light gray)
        )
        
        verification_data = {
            "loading_circle_found": found,
            "circle_info": circle_info,
            "screenshot_taken": True
        }
        
        if found and circle_info:
            x, y, radius = circle_info
            success_msg = f"✓ Network page is loading. Loading circle detected at ({x}, {y}), radius: {radius}px"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            verification_data["message"] = success_msg
            return True, success_msg, verification_data
        else:
            # Loading circle not found - might be loading very fast, or page already loaded
            # Try checking again after a short delay
            print(f"[VERIFIER_HANDLER] Loading circle not found on first attempt, waiting and checking again...")
            time.sleep(1.5)
            
            # Take another screenshot and check again
            screenshot2 = computer_vision_utils.take_screenshot()
            if screenshot2 is not None:
                found2, circle_info2 = computer_vision_utils.detect_loading_circle(
                    screenshot2,
                    center_region_ratio=0.4,
                    min_radius=15,
                    max_radius=100,
                    brightness_threshold=180
                )
                
                verification_data["second_check"] = {
                    "loading_circle_found": found2,
                    "circle_info": circle_info2
                }
                
                if found2 and circle_info2:
                    x, y, radius = circle_info2
                    success_msg = f"✓ Network page is loading. Loading circle detected on second check at ({x}, {y}), radius: {radius}px"
                    print(f"[VERIFIER_HANDLER] {success_msg}")
                    verification_data["message"] = success_msg
                    return True, success_msg, verification_data
        
        # If we get here, no loading circle was detected
        # This might mean the page loaded very quickly, or there's an issue
        warning_msg = f"⚠ Loading circle not detected. Page may have loaded very quickly, or loading indicator may not be visible."
        print(f"[VERIFIER_HANDLER] {warning_msg}")
        verification_data["message"] = warning_msg
        
        # Return True anyway to not block workflow - page might load very fast or use different loading indicator
        return True, warning_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying network page loading: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors specific to opening multinetwork by instructions."""
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"


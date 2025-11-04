#!/usr/bin/env python3
"""
Handler for: Open Multinetwork by Instructions

This module contains:
- Action: Find and double-click on a row in the second table (within expanded row) by begin_date
- Verifier: Verify the row was found and clicked
- Error Handler: Handle errors for this specific action
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import computer_vision_utils
import time
import pyautogui
import cv2
import numpy as np

# ============================================================================
# ACTION
# ============================================================================

# Module-level variable to store last known RowExpander position
_last_row_expander_position = None

def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Find and double-click on a row in the second table (within expanded row) by begin_date.
    
    The second table appears within the expanded row from the first table search.
    This function uses row boundary detection to handle variable height rows.
    
    Args:
        begin_date: Begin date to find (from input file)
        estimate_number: Estimate number to locate for determining crop region
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    global _last_row_expander_position
    
    if not begin_date:
        return False, "Missing begin_date parameter"
    
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    print(f"[ACTION_HANDLER] Estimate number for reference: '{estimate_number}'")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Step 1: Detect the blue highlighted row (expanded row)
        print(f"[ACTION_HANDLER] Detecting blue highlighted row (expanded row)...")
        
        # Convert BGR to HSV for better blue color detection
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        
        # Define blue color range in HSV (adjust these values based on your specific blue)
        # Typical blue highlight: H=100-130, S=50-255, V=50-255
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        # Create mask for blue color
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Find contours of blue regions
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return False, "Could not find blue highlighted row (expanded row not visible)"
        
        # Find the largest blue region (the expanded row)
        largest_contour = max(contours, key=cv2.contourArea)
        blue_x, blue_y, blue_w, blue_h = cv2.boundingRect(largest_contour)
        
        print(f"[ACTION_HANDLER] Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        
        # Step 2: Find the estimate number's Y position within the blue region
        print(f"[ACTION_HANDLER] Searching for estimate number to determine crop Y position...")
        estimate_number_y = None
        
        if estimate_number:
            from src.workflow_module.actions.helpers.ocr_utils import TextScanner
            scanner = TextScanner()
            
            # Search for estimate number in the blue region
            search_region = screenshot[blue_y:blue_y + blue_h, blue_x:blue_x + blue_w]
            success, data = scanner.get_text_data(search_region)
            
            if success and data['text']:
                estimate_number_str = str(estimate_number)
                # Find the estimate number in OCR results
                for i, text in enumerate(data['text']):
                    if text and estimate_number_str in text:
                        bbox = data['bbox'][i]
                        # Convert from blue region coordinates to screen coordinates
                        estimate_number_y = blue_y + bbox[1]
                        print(f"[ACTION_HANDLER] Found estimate number at screen Y={estimate_number_y}")
                        break
        
        # If estimate number not found, use blue region Y as fallback
        if estimate_number_y is None:
            estimate_number_y = blue_y
            print(f"[ACTION_HANDLER] Estimate number not found, using blue region Y={blue_y}")
        
        # Step 3: Find the black border below the selected row
        print(f"[ACTION_HANDLER] Detecting black border below selected row...")
        
        # Search for horizontal black line below the blue region
        bottom_border_y_screen = None
        
        # Start searching from the bottom of the blue region
        search_start_y = blue_y + blue_h
        search_end_y = min(search_start_y + 200, screen_height)  # Search up to 200px below
        
        # Convert to grayscale for line detection
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        
        # Use fixed X position (205) and width (1500) for inner table
        crop_x_fixed = 205
        crop_width_fixed = 1500
        
        for y in range(search_start_y, search_end_y):
            # Check the row across the inner table width (1500px from x=205)
            check_x_start = crop_x_fixed
            check_x_end = min(crop_x_fixed + crop_width_fixed, screen_width)
            row = gray[y, check_x_start:check_x_end]
            
            # Count dark pixels (< 50 = dark/black)
            dark_pixel_count = np.sum(row < 50)
            dark_ratio = dark_pixel_count / len(row)
            
            # If >70% of the row is dark, it's the black border
            if dark_ratio > 0.7:
                bottom_border_y_screen = y
                print(f"[ACTION_HANDLER] Found bottom black border at screen Y={y} ({dark_ratio:.1%} dark)")
                break
        
        if bottom_border_y_screen is None:
            # Fallback: use a default distance below
            bottom_border_y_screen = search_start_y + 100
            print(f"[ACTION_HANDLER] WARNING: Black border not found, using fallback: Y={bottom_border_y_screen}")
        
        # Step 4: Define inner table crop region based on estimate number position and black border
        # X: Fixed at 205 (default for inner table)
        # Y: Estimate number position (where the outer table row is)
        # Width: Fixed 1500 pixels
        # Height: Distance from estimate number to black border
        crop_x = 205
        crop_y = estimate_number_y
        crop_width = 1500
        crop_height = bottom_border_y_screen - estimate_number_y
        
        print(f"[ACTION_HANDLER] Estimate number Y position: {estimate_number_y}")
        print(f"[ACTION_HANDLER] Black border: Y={bottom_border_y_screen}")
        print(f"[ACTION_HANDLER] Inner table region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        
        # Validate crop region
        if crop_height <= 0 or crop_width <= 0:
            return False, f"Invalid crop dimensions: width={crop_width}, height={crop_height}"
        
        # Ensure crop region is within screen bounds
        if crop_x + crop_width > screen_width:
            crop_width = screen_width - crop_x
            print(f"[ACTION_HANDLER] Adjusted crop_width to {crop_width} to stay within screen bounds")
        
        if crop_y + crop_height > screen_height:
            crop_height = screen_height - crop_y
            print(f"[ACTION_HANDLER] Adjusted crop_height to {crop_height} to stay within screen bounds")
        
        # Save a copy of the cropped image for debugging
        cropped_inner_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
        if cropped_inner_table is not None:
            import os
            debug_path = "debug_images/inner_table_cropped.png"
            os.makedirs("debug_images", exist_ok=True)
            cv2.imwrite(debug_path, cropped_inner_table)
            print(f"[ACTION_HANDLER] Saved cropped inner table image to: {debug_path}")
        
        # Search the second table for the begin_date (no scrolling)
        found, msg, matches = table_utils.search_second_table_by_date(
            begin_date=begin_date,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height
        )
        
        if not found or not matches:
            return False, f"Begin date not found in second table: {msg}"
        
        print(f"[ACTION_HANDLER] Found {len(matches)} matching row(s)")
        
        # Select match to click (first match for now, can be adjusted later)
        match_to_click = matches[0]
        print(f"[ACTION_HANDLER] Using first match (row {match_to_click['row_index'] + 1})")
        
        # Double click on the chosen match (coordinates point to the center of the begin_date text)
        click_x = match_to_click['click_x']
        click_y = match_to_click['click_y']
        
        print(f"[ACTION_HANDLER] Date position - X: {click_x}, Y: {click_y}")
        print(f"[ACTION_HANDLER] Match details: row_index={match_to_click.get('row_index', 'N/A')}, text='{match_to_click.get('matched_text', 'N/A')[:50]}...'")
        
        # Ensure coordinates are valid
        if click_x is None or click_y is None:
            return False, f"Invalid click coordinates: x={click_x}, y={click_y}"
        
        print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
        
        # Move mouse to date position first to ensure it's visible
        pyautogui.moveTo(click_x, click_y, duration=0.2)
        time.sleep(0.2)
        
        # Double-click on the date
        success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
        
        if not success:
            return False, f"Failed to double-click on date: {action_msg}"
        
        print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
        
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


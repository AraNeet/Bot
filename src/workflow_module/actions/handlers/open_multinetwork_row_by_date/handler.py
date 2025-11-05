#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Row by Date

Find and double-click on a row in the second table (within expanded row) by begin_date.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import ocr_utils
import time
import pyautogui
import cv2
import numpy as np


def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    if not begin_date:
        return False, "Missing begin_date parameter"
    
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    print(f"[ACTION_HANDLER] Estimate number for reference: '{estimate_number}'")
    
    try:
        time.sleep(2)
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Step 1: Find blue highlighted row using computer vision utils
        print(f"[ACTION_HANDLER] Detecting blue highlighted row (expanded row)...")
        found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(screenshot, exclude_bottom_pixels=100)
        
        if not found_blue or row_info is None:
            return False, "Could not find blue highlighted row (expanded row not visible)"
        
        blue_x = row_info['x']
        blue_y = row_info['y']
        blue_w = row_info['width']
        blue_h = row_info['height']
        
        print(f"[ACTION_HANDLER] Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        
        # Step 2: Find estimate number Y position using OCR utils
        print(f"[ACTION_HANDLER] Searching for estimate number to determine crop Y position...")
        estimate_number_y = None
        
        if estimate_number:
            search_region = screenshot[blue_y:blue_y + blue_h, blue_x:blue_x + blue_w]
            found_text, y_pos = ocr_utils.find_topmost_text_position(
                estimate_number, 
                search_region, 
                blue_x, 
                blue_y
            )
            
            if found_text and y_pos is not None:
                estimate_number_y = y_pos
                print(f"[ACTION_HANDLER] Found estimate number at screen Y={estimate_number_y}")
        
        if estimate_number_y is None:
            estimate_number_y = blue_y
            print(f"[ACTION_HANDLER] Estimate number not found, using blue region Y={blue_y}")
        
        # Step 3: Detect bottom border using template matching
        print(f"[ACTION_HANDLER] Detecting black border below selected row using template matching...")
        bottom_border_y_screen = None
        search_start_y = blue_y + blue_h
        search_end_y = min(search_start_y + 200, screen_height)
        crop_x_fixed = 205
        crop_width_fixed = 1500
        
        # Define search region for template matching
        search_region_x = crop_x_fixed
        search_region_y = search_start_y
        search_region_width = min(crop_width_fixed, screen_width - crop_x_fixed)
        search_region_height = search_end_y - search_start_y
        
        # Load and match BorderLine template
        border_line_template_path = "src/workflow_module/actions/handlers/open_multinetwork_row_by_date/BorderLine.png"
        found, confidence, position = computer_vision_utils.find_template_in_region(
            screenshot,
            border_line_template_path,
            (search_region_x, search_region_y, search_region_width, search_region_height),
            confidence=0.7
        )
        
        if found and position is not None:
            # Position is (center_x, center_y) in global coordinates
            _, bottom_border_y_screen = position
            print(f"[ACTION_HANDLER] Found bottom black border at screen Y={bottom_border_y_screen} (confidence: {confidence:.2f})")
        else:
            fallback_y = search_start_y + 100
            bottom_exclusion_y = max(0, screen_height - 100)
            bottom_border_y_screen = min(fallback_y, bottom_exclusion_y - 2)
            print(f"[ACTION_HANDLER] WARNING: Black border not found via template matching, using fallback: Y={bottom_border_y_screen}")
        
        # Step 4: Calculate crop region for inner table
        crop_x = 205
        crop_y = estimate_number_y
        crop_width = 1500
        crop_height = bottom_border_y_screen - estimate_number_y
        print(f"[ACTION_HANDLER] === Crop Region Calculation ===")
        print(f"[ACTION_HANDLER] Screen dimensions: {screen_width}x{screen_height}")
        print(f"[ACTION_HANDLER] Blue row position: Y={blue_y}, H={blue_h}")
        print(f"[ACTION_HANDLER] Estimate number Y position: {estimate_number_y}")
        print(f"[ACTION_HANDLER] Black border detected at: Y={bottom_border_y_screen}")
        print(f"[ACTION_HANDLER] Initial crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        print(f"[ACTION_HANDLER] Max bottom Y (screen - 100): {max(0, screen_height - 100)}")
        if crop_height <= 0 or crop_width <= 0:
            return False, f"Invalid crop dimensions: width={crop_width}, height={crop_height}"
        if crop_x + crop_width > screen_width:
            crop_width = screen_width - crop_x
            print(f"[ACTION_HANDLER] Adjusted crop_width to {crop_width} to stay within screen bounds")
        if crop_y + crop_height > screen_height:
            crop_height = screen_height - crop_y
            print(f"[ACTION_HANDLER] Adjusted crop_height to {crop_height} to stay within screen bounds")
        max_bottom_y = max(0, screen_height - 100)
        if crop_y + crop_height > max_bottom_y:
            crop_height = max(0, max_bottom_y - crop_y)
            print(f"[ACTION_HANDLER] Adjusted crop_height to {crop_height} to avoid taskbar region")
        
        # Final validation after all adjustments
        print(f"[ACTION_HANDLER] === After Adjustments ===")
        print(f"[ACTION_HANDLER] Final crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        
        if crop_height <= 0 or crop_width <= 0:
            error_msg = f"Invalid crop dimensions after adjustments: width={crop_width}, height={crop_height}. "
            error_msg += f"Estimate Y: {estimate_number_y}, Bottom border Y: {bottom_border_y_screen}. "
            error_msg += "The inner table region is too small or collapsed. The expanded row may not have enough content."
            print(f"[ACTION_HANDLER] ERROR: {error_msg}")
            return False, error_msg
        
        if crop_y < 0 or crop_x < 0:
            return False, f"Invalid crop position: x={crop_x}, y={crop_y}. Position cannot be negative."
        
        # Check minimum height requirement (at least 20 pixels for a meaningful table)
        if crop_height < 20:
            warning_msg = f"Warning: Crop height is very small ({crop_height}px). Inner table may not be fully visible."
            print(f"[ACTION_HANDLER] {warning_msg}")
        
        cropped_inner_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
        
        if cropped_inner_table is None:
            error_msg = f"Failed to crop inner table region. Region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}"
            print(f"[ACTION_HANDLER] ERROR: {error_msg}")
            return False, error_msg
        
        # Save debug image
        try:
            import os
            debug_path = "debug_images/inner_table_cropped.png"
            os.makedirs("debug_images", exist_ok=True)
            cv2.imwrite(debug_path, cropped_inner_table)
            abs_path = os.path.abspath(debug_path)
            print(f"[ACTION_HANDLER] Saved cropped inner table image to: {abs_path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save debug image: {e}")
        
        # Step 5: Search for date in inner table and click
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
        match_to_click = matches[0]
        print(f"[ACTION_HANDLER] Using first match (row {match_to_click['row_index'] + 1})")
        click_x = match_to_click['click_x']
        click_y = match_to_click['click_y']
        print(f"[ACTION_HANDLER] Date position - X: {click_x}, Y: {click_y}")
        print(f"[ACTION_HANDLER] Match details: row_index={match_to_click.get('row_index', 'N/A')}, text='{match_to_click.get('matched_text', 'N/A')[:50]}...'")
        if click_x is None or click_y is None:
            return False, f"Invalid click coordinates: x={click_x}, y={click_y}"
        print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
        pyautogui.moveTo(click_x, click_y, duration=0.2)
        time.sleep(0.2)
        success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
        if not success:
            return False, f"Failed to double-click on date: {action_msg}"
        print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
        time.sleep(0.5)
        match_count_str = f"{len(matches)} match" + ("es" if len(matches) != 1 else "")
        return True, f"Row found and double-clicked! Begin date: '{begin_date}' ({match_count_str})"
    except Exception as e:
        return False, f"Error finding row by begin_date: {e}"


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"



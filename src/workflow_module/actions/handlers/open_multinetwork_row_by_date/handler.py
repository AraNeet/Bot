#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Row by Date

Find and double-click on a row in the second table (within expanded row) by begin_date.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import computer_vision_utils
import time
import pyautogui
import cv2
import numpy as np


def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    global _last_row_expander_position
    if not begin_date:
        return False, "Missing begin_date parameter"
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    print(f"[ACTION_HANDLER] Estimate number for reference: '{estimate_number}'")
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        print(f"[ACTION_HANDLER] Detecting blue highlighted row (expanded row)...")
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return False, "Could not find blue highlighted row (expanded row not visible)"
        bottom_exclusion_y = max(0, screen_height - 100)
        candidate_contours = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if y >= bottom_exclusion_y:
                continue
            if h < 18 or h > 40:
                continue
            if w < 300:
                continue
            candidate_contours.append((cnt, x, y, w, h))
        if candidate_contours:
            candidate_contours.sort(key=lambda item: (item[3], cv2.contourArea(item[0])), reverse=True)
            chosen_cnt, blue_x, blue_y, blue_w, blue_h = candidate_contours[0]
        else:
            largest_contour = max(contours, key=cv2.contourArea)
            blue_x, blue_y, blue_w, blue_h = cv2.boundingRect(largest_contour)
            if blue_y >= bottom_exclusion_y:
                blue_y = max(0, bottom_exclusion_y - max(blue_h, 40))
        print(f"[ACTION_HANDLER] Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        print(f"[ACTION_HANDLER] Searching for estimate number to determine crop Y position...")
        estimate_number_y = None
        if estimate_number:
            from src.workflow_module.actions.helpers.ocr_utils import TextScanner
            scanner = TextScanner()
            search_region = screenshot[blue_y:blue_y + blue_h, blue_x:blue_x + blue_w]
            success, data = scanner.get_text_data(search_region)
            if success and data['text']:
                estimate_number_str = str(estimate_number)
                # Choose the first estimate number in visual reading order: top-most, then left-most
                best_local_bbox = None  # (x1, y1, x2, y2)
                for i, text in enumerate(data['text']):
                    if text and estimate_number_str in text:
                        x1, y1, x2, y2 = map(int, data['bbox'][i])
                        if best_local_bbox is None or y1 < best_local_bbox[1] or (y1 == best_local_bbox[1] and x1 < best_local_bbox[0]):
                            best_local_bbox = (x1, y1, x2, y2)
                if best_local_bbox is not None:
                    estimate_number_y = blue_y + best_local_bbox[1]
                    print(f"[ACTION_HANDLER] Found top-most estimate number at screen Y={estimate_number_y} (local bbox={best_local_bbox})")
        if estimate_number_y is None:
            estimate_number_y = blue_y
            print(f"[ACTION_HANDLER] Estimate number not found, using blue region Y={blue_y}")
        print(f"[ACTION_HANDLER] Detecting black border below selected row...")
        bottom_border_y_screen = None
        search_start_y = blue_y + blue_h
        search_end_y = min(search_start_y + 200, screen_height)
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        crop_x_fixed = 205
        crop_width_fixed = 1500
        for y in range(search_start_y, search_end_y):
            check_x_start = crop_x_fixed
            check_x_end = min(crop_x_fixed + crop_width_fixed, screen_width)
            row = gray[y, check_x_start:check_x_end]
            dark_pixel_count = np.sum(row < 50)
            dark_ratio = dark_pixel_count / len(row)
            if dark_ratio > 0.7:
                bottom_border_y_screen = y
                print(f"[ACTION_HANDLER] Found bottom black border at screen Y={y} ({dark_ratio:.1%} dark)")
                break
        if bottom_border_y_screen is None:
            fallback_y = search_start_y + 100
            bottom_exclusion_y = max(0, screen_height - 100)
            bottom_border_y_screen = min(fallback_y, bottom_exclusion_y - 2)
            print(f"[ACTION_HANDLER] WARNING: Black border not found, using fallback: Y={bottom_border_y_screen}")
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



#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Row by Date

Find and double-click on a row in the second table (within expanded row) by begin_date.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import date_utils
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import ocr_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger, COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_YELLOW
import time
import pyautogui
import cv2
import numpy as np
import os


def check_target_region(
    screenshot: np.ndarray,
    scroll_num: int,
    scroll_crop_x: int,
    scroll_crop_y: int,
    scroll_crop_width: int,
    scroll_crop_height: int,
    target_region_offset_y: int,
    target_region_height: int,
    scroll_template: np.ndarray,
    begin_date: str,
    debug: Debugger
) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Check if begin_date exists in the target region.
    
    Args:
        screenshot: Screenshot to search in
        scroll_num: Current scroll attempt number (for debug naming)
        scroll_crop_x: X position of scroll crop region
        scroll_crop_y: Y position of scroll crop region
        scroll_crop_width: Width of scroll crop region
        scroll_crop_height: Height of scroll crop region
        target_region_offset_y: Y offset for target region within scroll crop
        target_region_height: Height of target region
        scroll_template: Template image for column separator detection
        begin_date: Date string to search for
        debug: Debugger instance for saving debug images
        
    Returns:
        Tuple of (found: bool, click_x: Optional[int], click_y: Optional[int])
    """
    target_crop_y = scroll_crop_y + target_region_offset_y
    target_crop_height = target_region_height
    
    # Crop to target region
    target_region_img = computer_vision_utils.crop_image(
        screenshot, scroll_crop_x, target_crop_y, scroll_crop_width, target_crop_height
    )
    
    if target_region_img is None:
        print(f"[ACTION_HANDLER] Warning: Failed to crop target region")
        return False, None, None
    
    print(f"[ACTION_HANDLER] Checking full region: x={scroll_crop_x}, y={target_crop_y}, w={scroll_crop_width}, h={target_crop_height}")
    
    # Click on a row to select it
    select_row_x = scroll_crop_x + 100
    select_row_y = target_crop_y + 50
    print(f"[ACTION_HANDLER] Clicking row at ({select_row_x}, {select_row_y}) to select it")
    actions.click_at_position(select_row_x, select_row_y, clicks=1, button='left')
    time.sleep(0.3)
    
    # Take fresh screenshot after clicking
    fresh_screenshot = computer_vision_utils.take_screenshot()
    if fresh_screenshot is None:
        print(f"[ACTION_HANDLER] Warning: Failed to take screenshot after clicking")
        return False, None, None
    
    # Crop target region from fresh screenshot
    target_region_img = computer_vision_utils.crop_image(
        fresh_screenshot, scroll_crop_x, target_crop_y, scroll_crop_width, target_crop_height
    )
    
    if target_region_img is None:
        print(f"[ACTION_HANDLER] Warning: Failed to crop target region from fresh screenshot")
        return False, None, None
    
    # Detect column separators
    print(f"[ACTION_HANDLER] Separating columns with RowColumnLineSecondTable.png...")
    separator_matches = table_utils.detect_column_separators(target_region_img, scroll_template, match_threshold=0.85)
    
    if not separator_matches:
        print(f"[ACTION_HANDLER] No separators found in full region")
        return False, None, None
    
    # Extract column 5
    column_5_img = table_utils.get_column_5_image(
        target_region_img, 
        separator_matches, 
        scroll_template.shape[1],
        debug=False
    )
    
    if column_5_img is None:
        print(f"[ACTION_HANDLER] Failed to extract column 5 from full region")
        return False, None, None
    
    # Perform OCR on column 5
    scanner = ocr_utils.TextScanner()
    ocr_success, ocr_data = scanner.get_text_data(column_5_img)
    
    if not ocr_success or not ocr_data or not ocr_data.get('text'):
        print(f"[ACTION_HANDLER] OCR failed in full region")
        return False, None, None
    
    print(f"[ACTION_HANDLER] OCR found {len(ocr_data['text'])} text elements in full region")
    
    # Debug: Visualize OCR results
    debug.visualize_ocr(column_5_img, ocr_data, f"scroll_{scroll_num:02d}_ocr")
    
    # Check if begin_date is in OCR results (skip header row)
    begin_date_str = str(begin_date)
    begin_date_normalized = date_utils.normalize_date(begin_date_str)
    header_height_estimate = 40
    
    for i, text in enumerate(ocr_data['text']):
        if text:
            bbox = ocr_data['bbox'][i]
            x1, y1, x2, y2 = map(int, bbox)
            center_y = (y1 + y2) // 2
            
            # Skip header row
            if center_y < header_height_estimate:
                continue
            
            text_normalized = date_utils.normalize_date(text)
            if begin_date_normalized in text_normalized or begin_date_str in text:
                print(f"[ACTION_HANDLER] ✓ Found matching date: '{text}' (index {i}, Y={center_y})")
                
                # Convert from column 5 image coordinates to screen coordinates
                click_y_local = (y1 + y2) // 2
                
                # Calculate column boundaries to find column 5's left edge
                column_split_positions = []
                for position, score in separator_matches:
                    x_position = position[0]
                    split_center = x_position + (scroll_template.shape[1] // 2)
                    column_split_positions.append(split_center)
                
                unique_split_positions = sorted(set(column_split_positions))
                image_width = target_region_img.shape[1]
                all_column_boundaries = [0] + unique_split_positions + [image_width]
                
                # Column 5 is at index 4 (0-based)
                if len(all_column_boundaries) >= 6:
                    column_5_left = all_column_boundaries[4]
                    click_x_local = column_5_left + ((x1 + x2) // 2)
                else:
                    column_5_width = column_5_img.shape[1]
                    click_x_local = ((x1 + x2) // 2)
                
                # Convert to screen coordinates
                click_x = click_x_local + scroll_crop_x
                click_y = click_y_local + target_crop_y
                
                print(f"[ACTION_HANDLER] Click coordinates: screen=({click_x}, {click_y})")
                
                # Debug: Highlight matched text
                matched_img = column_5_img.copy()
                debug.visualize_ocr(matched_img, ocr_data, f"scroll_{scroll_num:02d}_matched", highlight_text=text)
                debug.draw_point(matched_img, ((x1 + x2) // 2, (y1 + y2) // 2), color=COLOR_RED, radius=5)
                debug.save_image(matched_img, f"scroll_{scroll_num:02d}_match_highlighted.png")
                
                return True, click_x, click_y
    
    print(f"[ACTION_HANDLER] No match found in full region")
    return False, None, None


def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Find and double-click on a row in the second table by begin_date.
    
    Args:
        begin_date: The date to search for in the table
        estimate_number: Estimate number for reference (optional)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not begin_date:
        return False, "Missing begin_date parameter"
    
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    print(f"[ACTION_HANDLER] Estimate number for reference: '{estimate_number}'")
    
    # Initialize debugger
    debug = Debugger("action_08_steps")
    
    try:
        # ============================================================================
        # STEP 1: Initialize and capture screenshot
        # ============================================================================
        time.sleep(4)
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        debug.save_image(screenshot, "01_initial_screenshot.png")
        
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # ============================================================================
        # STEP 2: Find blue highlighted row (expanded row)
        # ============================================================================
        print(f"[ACTION_HANDLER] Detecting blue highlighted row (expanded row)...")
        found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(screenshot, exclude_bottom_pixels=100)
        
        blue_x = None
        blue_y = None
        blue_w = None
        blue_h = None
        
        if found_blue and row_info is not None:
            blue_x = row_info['x']
            blue_y = row_info['y']
            blue_w = row_info['width']
            blue_h = row_info['height']
            print(f"[ACTION_HANDLER] Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        else:
            print(f"[ACTION_HANDLER] WARNING: Blue highlighted row not found, will use Y=230 for crop start")
        
        # Debug: Visualize blue row detection
        annotated_screenshot = screenshot.copy()
        if found_blue and blue_x is not None:
            debug.draw_rect(annotated_screenshot, (blue_x, blue_y, blue_w, blue_h), 
                          color=COLOR_GREEN, thickness=3, label="Blue Highlighted Row")
        else:
            cv2.putText(annotated_screenshot, "Blue Row Not Found - Using Y=230", (10, 230), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_RED, 2)
            cv2.line(annotated_screenshot, (0, 230), (screen_width, 230), COLOR_RED, 2)
        debug.save_image(annotated_screenshot, "02_blue_highlighted_row_detected.png")
        
        # ============================================================================
        # STEP 3: Find estimate number or "Estimate #" column header Y position using OCR
        # ============================================================================
        print(f"[ACTION_HANDLER] Searching for estimate number or 'Estimate #' column header to determine crop Y position...")
        estimate_number_y = None
        
        # Define search region for the header/estimate number
        if found_blue and blue_x is not None and blue_y is not None:
            header_search_y = blue_y
            header_search_h = min(blue_h + 80, 150)
            header_search_x = 205
            header_search_w = 1500
            header_search_h = min(header_search_h, screen_height - header_search_y - 100)
            search_region = screenshot[header_search_y:header_search_y + header_search_h, 
                                      header_search_x:header_search_x + header_search_w]
            print(f"[ACTION_HANDLER] Searching in expanded row region: Y={header_search_y}, H={header_search_h}")
        else:
            default_search_y = 230
            default_search_h = 50
            default_search_x = 205
            default_search_w = 1500
            search_region = screenshot[default_search_y:default_search_y + default_search_h, 
                                      default_search_x:default_search_x + default_search_w]
            header_search_y = default_search_y
            header_search_x = default_search_x
            print(f"[ACTION_HANDLER] Blue row not found, searching at default Y={header_search_y}")
        
        # Debug: Save search region
        debug.save_image(search_region, "03_estimate_search_region.png")
        
        # Perform OCR on search region
        scanner = ocr_utils.TextScanner()
        ocr_success, ocr_data = scanner.get_text_data(search_region)
        
        if ocr_success and ocr_data and ocr_data.get('text'):
            print(f"[ACTION_HANDLER] OCR detected {len(ocr_data['text'])} text elements")
            debug.visualize_ocr(search_region, ocr_data, "03_estimate_search")
            
            # First, try to find the actual estimate number value if provided
            if estimate_number:
                print(f"[ACTION_HANDLER] Searching for estimate number value: '{estimate_number}'")
                estimate_value_y = None
                
                for i, text in enumerate(ocr_data['text']):
                    if text:
                        # Check if the text contains the estimate number (case-insensitive, partial match)
                        text_clean = text.strip().upper()
                        estimate_clean = estimate_number.strip().upper()
                        
                        # Check for exact match or if estimate number is contained in text
                        if estimate_clean == text_clean or estimate_clean in text_clean or text_clean in estimate_clean:
                            bbox = ocr_data['bbox'][i]
                            x1, y1, x2, y2 = map(int, bbox)
                            estimate_value_y = y1 + header_search_y
                            print(f"[ACTION_HANDLER] ✓ Found estimate number value: '{text}' at screen Y={estimate_value_y}")
                            estimate_number_y = estimate_value_y
                            break
                
                if estimate_number_y is not None:
                    print(f"[ACTION_HANDLER] ✓ Using estimate number value Y position: {estimate_number_y}")
                else:
                    print(f"[ACTION_HANDLER] ✗ Estimate number value '{estimate_number}' not found in search region")
            
            # If estimate number value not found, search for "Estimate #" or "Estimate" header text
            if estimate_number_y is None:
                print(f"[ACTION_HANDLER] Searching for 'Estimate #' header text...")
                estimate_header_texts = ["Estimate #", "Estimate", "estimate", "ESTIMATE"]
                estimate_header_y = None
                
                for i, text in enumerate(ocr_data['text']):
                    if text:
                        text_lower = text.lower()
                        if any(header_text.lower() in text_lower for header_text in estimate_header_texts):
                            bbox = ocr_data['bbox'][i]
                            x1, y1, x2, y2 = map(int, bbox)
                            estimate_header_y = y1 + header_search_y
                            print(f"[ACTION_HANDLER] ✓ Found 'Estimate #' header text: '{text}' at screen Y={estimate_header_y}")
                            break
                
                if estimate_header_y is not None:
                    estimate_number_y = estimate_header_y
                    print(f"[ACTION_HANDLER] ✓ Using 'Estimate #' header Y position: {estimate_number_y}")
                else:
                    print(f"[ACTION_HANDLER] ✗ 'Estimate #' header not found in search region")
        
        if estimate_number_y is None:
            estimate_number_y = 230
            print(f"[ACTION_HANDLER] WARNING: Neither estimate number nor 'Estimate #' header found, using default Y=230")
        
        # Debug: Visualize estimate number Y position
        annotated_screenshot = screenshot.copy()
        cv2.line(annotated_screenshot, (0, estimate_number_y), (screen_width, estimate_number_y), COLOR_BLUE, 2)
        cv2.putText(annotated_screenshot, f"Estimate Number Y: {estimate_number_y}", (10, estimate_number_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_BLUE, 2)
        debug.save_image(annotated_screenshot, "04_estimate_number_y_position.png")
        
        # ============================================================================
        # STEP 4: Detect bottom border using template matching
        # ============================================================================
        print(f"[ACTION_HANDLER] Detecting black border below selected row using template matching...")
        
        # Determine search start Y
        if found_blue and blue_y is not None and blue_h is not None:
            search_start_y = blue_y + blue_h
            print(f"[ACTION_HANDLER] Starting border search below blue row at Y={search_start_y}")
        else:
            search_start_y = 230
            print(f"[ACTION_HANDLER] Blue row not found, starting border search at Y={search_start_y}")
        
        search_end_y = min(search_start_y + 1000, screen_height - 100)
        crop_x_fixed = 205
        crop_width_fixed = 1500
        
        search_region_x = crop_x_fixed
        search_region_y = search_start_y
        search_region_width = min(crop_width_fixed, screen_width - crop_x_fixed)
        search_region_height = search_end_y - search_start_y
        
        print(f"[ACTION_HANDLER] Searching for border template in region: x={search_region_x}, y={search_region_y}, w={search_region_width}, h={search_region_height}")
        
        # Debug: Visualize search region
        debug.visualize_search_region(screenshot, (search_region_x, search_region_y, search_region_width, search_region_height), "04a_border")
        
        # Load and match BorderLine template
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        border_line_template_path = os.path.join(handler_dir, 'BorderLine.png')
        print(f"[ACTION_HANDLER] Loading border template from: {border_line_template_path}")
        
        found, confidence, position = computer_vision_utils.find_template_in_region(
            screenshot,
            border_line_template_path,
            (search_region_x, search_region_y, search_region_width, search_region_height),
            confidence=0.7
        )
        
        if found and position is not None:
            _, bottom_border_y_screen = position
            print(f"[ACTION_HANDLER] ✓ Found bottom black border at screen Y={bottom_border_y_screen} (confidence: {confidence:.2f})")
        else:
            max_bottom_y = max(0, screen_height - 100)
            bottom_border_y_screen = max_bottom_y
            print(f"[ACTION_HANDLER] WARNING: Black border template not found (confidence: {confidence:.2f if confidence else 'N/A'})")
            print(f"[ACTION_HANDLER] Using full table height: Y={bottom_border_y_screen}")
        
        # Debug: Visualize template match
        border_template = computer_vision_utils.load_image(border_line_template_path)
        template_size = border_template.shape[:2][::-1] if border_template is not None else (100, 10)
        debug.visualize_template_match(screenshot, found, position, template_size, "04_bottom_border", confidence or 0.0)
        
        # ============================================================================
        # STEP 5: Calculate crop region for inner table
        # ============================================================================
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
        
        # Validate and adjust crop dimensions
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
        
        print(f"[ACTION_HANDLER] Final crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        
        if crop_height <= 0 or crop_width <= 0:
            error_msg = f"Invalid crop dimensions after adjustments: width={crop_width}, height={crop_height}. "
            error_msg += f"Estimate Y: {estimate_number_y}, Bottom border Y: {bottom_border_y_screen}. "
            error_msg += "The inner table region is too small or collapsed."
            return False, error_msg
        
        if crop_y < 0 or crop_x < 0:
            return False, f"Invalid crop position: x={crop_x}, y={crop_y}. Position cannot be negative."
        
        if crop_height < 20:
            print(f"[ACTION_HANDLER] Warning: Crop height is very small ({crop_height}px). Inner table may not be fully visible.")
        
        # Debug: Visualize crop region
        annotated_screenshot = screenshot.copy()
        debug.draw_rect(annotated_screenshot, (crop_x, crop_y, crop_width, crop_height), 
                       color=COLOR_YELLOW, thickness=3, 
                       label=f"Crop: {crop_width}x{crop_height}")
        cv2.line(annotated_screenshot, (crop_x, crop_y), (crop_x + crop_width, crop_y), COLOR_YELLOW, 2)
        cv2.line(annotated_screenshot, (crop_x, crop_y + crop_height), (crop_x + crop_width, crop_y + crop_height), COLOR_YELLOW, 2)
        debug.save_image(annotated_screenshot, "05_crop_region_marked.png")
        
        # Crop inner table
        cropped_inner_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
        
        if cropped_inner_table is None:
            error_msg = f"Failed to crop inner table region. Region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}"
            return False, error_msg
        
        debug.save_image(cropped_inner_table, "06_cropped_inner_table.png")
        
        # ============================================================================
        # STEP 6: Search for date in inner table (first attempt with ColumnLineSecondTable.png)
        # ============================================================================
        print(f"[ACTION_HANDLER] === First check with ColumnLineSecondTable.png ===")
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        column_line_path = os.path.join(handler_dir, 'ColumnLineSecondTable.png')
        
        found, msg, matches = table_utils.search_second_table_by_date(
            begin_date=begin_date,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height,
            template_path=column_line_path
        )
        
        if found and matches:
            print(f"[ACTION_HANDLER] ✓ Found {len(matches)} matching row(s) in first check")
            match_to_click = matches[0]
            click_x = match_to_click['click_x']
            click_y = match_to_click['click_y']
            print(f"[ACTION_HANDLER] Using first match (row {match_to_click['row_index'] + 1})")
            print(f"[ACTION_HANDLER] Date position - X: {click_x}, Y: {click_y}")
            
            if click_x is None or click_y is None:
                return False, f"Invalid click coordinates: x={click_x}, y={click_y}"
            
            # Debug: Visualize match before clicking
            annotated_screenshot = screenshot.copy()
            debug.draw_point(annotated_screenshot, (click_x, click_y), color=COLOR_GREEN, radius=10, 
                           label=f"Match: {begin_date}")
            debug.save_image(annotated_screenshot, "07_date_match_found_before_click.png")
            
            # Double-click on the date
            print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
            pyautogui.moveTo(click_x, click_y, duration=0.2)
            time.sleep(0.2)
            success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
            if not success:
                return False, f"Failed to double-click on date: {action_msg}"
            
            # Debug: Save screenshot after clicking
            time.sleep(0.3)
            post_click_screenshot = computer_vision_utils.take_screenshot()
            if post_click_screenshot is not None:
                debug.save_image(post_click_screenshot, "08_after_double_click.png")
            
            print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
            time.sleep(0.5)
            match_count_str = f"{len(matches)} match" + ("es" if len(matches) != 1 else "")
            return True, f"Row found and double-clicked! Begin date: '{begin_date}' ({match_count_str})"
        
        # ============================================================================
        # STEP 7: Scroll search with RowColumnLineSecondTable.png
        # ============================================================================
        print(f"[ACTION_HANDLER] ✗ No match in first check: {msg}")
        print(f"[ACTION_HANDLER] === Starting scroll search with RowColumnLineSecondTable.png ===")
        
        # Load scrolling column separator template
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        row_column_line_path = os.path.join(handler_dir, 'RowColumnLineSecondTable.png')
        scroll_template = computer_vision_utils.load_image(row_column_line_path)
        if scroll_template is None:
            return False, f"Failed to load RowColumnLineSecondTable template from {row_column_line_path}"
        
        # Define scroll crop region
        scroll_crop_x = 205
        scroll_crop_y = 230
        scroll_crop_width = 1450
        scroll_crop_height = 780
        
        target_region_offset_y = 0
        target_region_height = 780
        
        # Calculate center position for scrolling
        table_center_x = scroll_crop_x + scroll_crop_width // 2
        table_center_y = scroll_crop_y + scroll_crop_height // 2
        
        max_scroll_attempts = 20
        scroll_amount = -150  # Negative scrolls down
        
        # ============================================================================
        # STEP 8: Check full region before scrolling
        # ============================================================================
        print(f"\n[ACTION_HANDLER] ========== Checking full region before scrolling ==========")
        initial_screenshot = computer_vision_utils.take_screenshot()
        if initial_screenshot is not None:
            debug.save_image(initial_screenshot, "09_before_region_check.png")
            
            found_in_region, click_x, click_y = check_target_region(
                initial_screenshot, 0, scroll_crop_x, scroll_crop_y, scroll_crop_width, 
                scroll_crop_height, target_region_offset_y, target_region_height, 
                scroll_template, begin_date, debug
            )
            if found_in_region:
                # Debug: Visualize match in full region
                annotated_screenshot = initial_screenshot.copy()
                debug.draw_point(annotated_screenshot, (click_x, click_y), color=COLOR_GREEN, radius=10,
                               label=f"Match: {begin_date}")
                debug.save_image(annotated_screenshot, "10_match_found_in_full_region.png")
                
                # Double-click on the date
                print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.2)
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
                if not success:
                    return False, f"Failed to double-click on date: {action_msg}"
                
                # Debug: Save screenshot after clicking
                time.sleep(0.3)
                post_click_screenshot = computer_vision_utils.take_screenshot()
                if post_click_screenshot is not None:
                    debug.save_image(post_click_screenshot, "11_after_full_region_click.png")
                
                print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
                time.sleep(0.5)
                return True, f"Row found in full region and double-clicked! Begin date: '{begin_date}'"
        
        # ============================================================================
        # STEP 9: Scroll to find the date
        # ============================================================================
        print(f"[ACTION_HANDLER] Begin date not in full region, starting scroll to move rows up...")
        
        for scroll_attempt in range(1, max_scroll_attempts + 1):
            print(f"\n[ACTION_HANDLER] ========== Scroll attempt {scroll_attempt}/{max_scroll_attempts} ==========")
            
            # Move to table center and scroll
            pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
            time.sleep(0.2)
            pyautogui.scroll(scroll_amount)
            time.sleep(0.3)
            
            # Take screenshot after scrolling
            scroll_screenshot = computer_vision_utils.take_screenshot()
            if scroll_screenshot is None:
                print(f"[ACTION_HANDLER] Warning: Failed to take screenshot at scroll {scroll_attempt}")
                continue
            
            # Debug: Save screenshot for each scroll attempt
            debug.save_image(scroll_screenshot, f"12_scroll_attempt_{scroll_attempt:02d}.png")
            
            # Check target region
            found_in_region, click_x, click_y = check_target_region(
                scroll_screenshot, scroll_attempt, scroll_crop_x, scroll_crop_y, 
                scroll_crop_width, scroll_crop_height, target_region_offset_y, 
                target_region_height, scroll_template, begin_date, debug
            )
            
            if found_in_region:
                # Debug: Visualize match found during scroll
                annotated_screenshot = scroll_screenshot.copy()
                debug.draw_point(annotated_screenshot, (click_x, click_y), color=COLOR_GREEN, radius=10,
                               label=f"Match After Scroll {scroll_attempt}: {begin_date}")
                debug.save_image(annotated_screenshot, f"13_match_found_after_scroll_{scroll_attempt:02d}.png")
                
                # Double-click on the date
                print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.2)
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
                
                if not success:
                    return False, f"Failed to double-click on date: {action_msg}"
                
                # Debug: Save screenshot after clicking
                time.sleep(0.3)
                post_click_screenshot = computer_vision_utils.take_screenshot()
                if post_click_screenshot is not None:
                    debug.save_image(post_click_screenshot, f"14_after_scroll_{scroll_attempt:02d}_click.png")
                
                print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
                time.sleep(0.5)
                return True, f"Row found and double-clicked after {scroll_attempt} scroll(s)! Begin date: '{begin_date}'"
            
            print(f"[ACTION_HANDLER] No match at scroll {scroll_attempt}, continuing...")
        
        return False, f"Begin date not found after {max_scroll_attempts} scroll attempts"
        
    except Exception as e:
        return False, f"Error finding row by begin_date: {e}"


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors and retry logic."""
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"

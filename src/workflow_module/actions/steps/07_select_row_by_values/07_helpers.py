#!/usr/bin/env python3
"""
Helper functions for Step 07: Select Row by Values

This module contains utility functions for:
- Table scrolling
- Row positioning
- Column detection and separation
- Row searching
"""

import time
import pyautogui
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional, List

# Import dependencies
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers.ocr_utils import TextScanner, match_text_positions

scanner = TextScanner()


def scroll_to_table_top(table_center_x: int, table_center_y: int) -> None:
    """
    Scroll the table up by one step.
    
    Args:
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
    """
    print(f"[07_HELPERS] Scrolling up...")
    
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    pyautogui.scroll(50)  # Positive value scrolls up
    time.sleep(0.05)

def is_row_expanded(screenshot: np.ndarray, row_info: Dict[str, int], min_expanded_height: int = 80) -> bool:
    """
    Check if a detected row is expanded (has nested content visible).
    
    An expanded row will have:
    - Height > min_expanded_height (nested table adds height)
    - Or visible nested content below the row header
    
    Args:
        screenshot: Current screenshot
        row_info: Row info dict with 'x', 'y', 'width', 'height'
        min_expanded_height: Minimum height to consider expanded (default: 80px)
        
    Returns:
        True if row appears expanded, False otherwise
    """
    # Validate row_info has required keys
    required_keys = ['x', 'y', 'width', 'height']
    if not all(key in row_info for key in required_keys):
        return False
    
    height = row_info.get('height', 0)
    
    # Check 1: Height threshold - expanded rows are taller
    if height >= min_expanded_height:
        print(f"[07_HELPERS] Row height {height}px >= {min_expanded_height}px threshold - appears expanded")
        return True
    
    # Check 2: Look for nested content below the row
    x = row_info.get('x', 0)
    y = row_info.get('y', 0)
    width = row_info.get('width', 0)
    
    # Check region below the row header for nested content
    screen_height, screen_width = screenshot.shape[:2]
    check_y_start = min(y + height, screen_height - 10)
    check_y_end = min(y + height + 100, screen_height)
    check_x_start = max(0, x)
    check_x_end = min(x + width, screen_width)
    
    if check_y_end > check_y_start and check_x_end > check_x_start:
        nested_region = screenshot[check_y_start:check_y_end, check_x_start:check_x_end]
        
        if nested_region is not None and nested_region.size > 0:
            gray = cv2.cvtColor(nested_region, cv2.COLOR_BGR2GRAY)
            std_dev = np.std(gray)
            if std_dev > 15:
                print(f"[07_HELPERS] Found nested content below row (std_dev: {std_dev:.1f}) - appears expanded")
                return True
    
    print(f"[07_HELPERS] Row height {height}px < {min_expanded_height}px and no nested content - appears collapsed")
    return False


def position_row_in_target_region(table_center_x: int, table_center_y: int,
                                   target_region_y: int, target_region_height: int,
                                   crop_x: int, crop_y: int, crop_width: int, crop_height: int) -> Tuple[bool, str, bool]:
    """
    After clicking a row, scroll down to position it within the target region if needed.
    Uses blue color detection to find the highlighted row position.
    
    Returns:
        Tuple of (success: bool, message: str, is_expanded: bool)
    """
    # Step 1: Calculate target region bounds
    target_region_bottom = target_region_y + target_region_height
    
    # Step 2: Wait for row highlight after clicking
    time.sleep(0.3)
    
    # Step 3: Take cropped screenshot for blue row detection
    cropped_screenshot = take_screenshot_and_crop((crop_x, crop_y, crop_width, crop_height))
    if cropped_screenshot is None:
        print(f"[07_HELPERS] Warning: Failed to take and crop screenshot for blue detection")
        return False, "Failed to take and crop screenshot", False
    
    # Step 4: Adjust target region coordinates to cropped image space
    target_region_y_cropped = target_region_y - crop_y
    target_region_bottom_cropped = target_region_bottom - crop_y
    
    # Step 5: Detect blue highlighted row
    found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(cropped_screenshot)
    if not found_blue or row_info is None:
        print(f"[07_HELPERS] Warning: Could not detect blue highlighted row after clicking")
        return False, "Could not detect blue highlighted row", False
    
    # Step 6: Check if row is expanded
    row_is_expanded = is_row_expanded(cropped_screenshot, row_info)
    
    # Step 7: Extract row position information
    blue_row_y = row_info['y']
    blue_row_height = row_info['height']
    blue_row_center_y = blue_row_y + (blue_row_height // 2)
    blue_row_top = blue_row_y
    blue_row_bottom = blue_row_y + blue_row_height
    
    # Step 8: Convert to screen coordinates for logging
    blue_row_y_screen = blue_row_y + crop_y
    blue_row_center_y_screen = blue_row_center_y + crop_y
    
    print(f"[07_HELPERS] Blue highlighted row detected at y={blue_row_y_screen} (cropped y={blue_row_y}), center_y={blue_row_center_y_screen}, height={blue_row_height}")
    print(f"[07_HELPERS] Blue row bounds: top={blue_row_top + crop_y}, bottom={blue_row_bottom + crop_y}")
    print(f"[07_HELPERS] Target region bounds: top={target_region_y}, bottom={target_region_bottom}")
    print(f"[07_HELPERS] Row is {'EXPANDED' if row_is_expanded else 'COLLAPSED'}")
    
    # Step 9: Check if row is already in target region
    if row_is_expanded:
        # Expanded row: Ensure row HEADER (top) is in target region
        header_margin = 50  # Allow 50px margin for expanded content below header
        row_header_in_region = (blue_row_top >= target_region_y_cropped) and (blue_row_top <= target_region_bottom_cropped - header_margin)
        
        if row_header_in_region:
            print(f"[07_HELPERS] ✓ Expanded row HEADER already in target region (top={blue_row_top + crop_y})")
            return True, "Expanded row header already in target region", True
    else:
        # Collapsed row: Use center position
        row_in_region = (blue_row_top >= target_region_y_cropped) and (blue_row_center_y <= target_region_bottom_cropped)
        
        if row_in_region:
            print(f"[07_HELPERS] ✓ Row already in target region (top={blue_row_top + crop_y}, center={blue_row_center_y_screen})")
            return True, "Row already in target region", False
    
    # Step 10: Row not in target region, prepare to scroll
    if row_is_expanded:
        print(f"[07_HELPERS] ✗ Expanded row HEADER NOT in target region (top={blue_row_top + crop_y} vs target_top={target_region_y})")
        print(f"[07_HELPERS] Scrolling to position expanded row HEADER in target region {target_region_y}-{target_region_bottom}...")
    else:
        print(f"[07_HELPERS] ✗ Row NOT in target region (top={blue_row_top + crop_y} vs target_top={target_region_y}, center={blue_row_center_y_screen} vs target_bottom={target_region_bottom})")
        print(f"[07_HELPERS] Scrolling down to position row in target region {target_region_y}-{target_region_bottom}...")
    
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.2)
    
    max_position_scrolls = 100
    scroll_amount = -20  # Scroll down slowly (negative value)
    last_blue_top = blue_row_top
    last_blue_center_y = blue_row_center_y
    
    # Step 11: Scroll loop to position row
    for scroll_num in range(1, max_position_scrolls + 1):
        # Step 11a: Scroll down
        pyautogui.scroll(scroll_amount)
        time.sleep(0.05)
        
        # Step 11b: Take new screenshot
        check_cropped_screenshot = take_screenshot_and_crop((crop_x, crop_y, crop_width, crop_height))
        if check_cropped_screenshot is None:
            if scroll_num % 10 == 0:
                print(f"[07_HELPERS] Warning: Screenshot failed at scroll {scroll_num}")
            continue
        
        # Step 11c: Detect blue row position
        check_found, check_row_info = computer_vision_utils.find_blue_highlighted_row(check_cropped_screenshot)
        
        if check_found and check_row_info:
            new_blue_y = check_row_info['y']
            new_blue_height = check_row_info['height']
            new_blue_center_y = new_blue_y + (new_blue_height // 2)
            new_blue_top = new_blue_y
            
            # Step 11c1: Re-check if row is expanded
            check_row_is_expanded = is_row_expanded(check_cropped_screenshot, check_row_info)
            if check_row_is_expanded != row_is_expanded:
                print(f"[07_HELPERS] Row expansion state changed: {row_is_expanded} -> {check_row_is_expanded}")
                row_is_expanded = check_row_is_expanded
            
            # Step 11d: Check if row is now in target region
            if row_is_expanded:
                header_margin = 50
                if target_region_y_cropped <= new_blue_top <= (target_region_bottom_cropped - header_margin):
                    new_blue_top_screen = new_blue_top + crop_y
                    print(f"[07_HELPERS] ✓ Expanded row HEADER positioned in target region after {scroll_num} scroll(s) (top={new_blue_top_screen})")
                    return True, f"Expanded row header positioned in target region at y={new_blue_top_screen}", True
            else:
                if target_region_y_cropped <= new_blue_center_y <= target_region_bottom_cropped:
                    new_blue_center_y_screen = new_blue_center_y + crop_y
                    print(f"[07_HELPERS] ✓ Row positioned in target region after {scroll_num} scroll(s) (y={new_blue_center_y_screen})")
                    return True, f"Row positioned in target region at y={new_blue_center_y_screen}", False
            
            # Step 11e: Check if row stopped moving
            position_unchanged = abs(new_blue_top - last_blue_top) < 5 if row_is_expanded else abs(new_blue_center_y - last_blue_center_y) < 5
            if position_unchanged:
                if row_is_expanded:
                    new_blue_top_screen = new_blue_top + crop_y
                    print(f"[07_HELPERS] Expanded row header position unchanged at y={new_blue_top_screen}. Assuming end of table.")
                else:
                    new_blue_center_y_screen = new_blue_center_y + crop_y
                    print(f"[07_HELPERS] Row position unchanged at y={new_blue_center_y_screen}. Assuming end of table.")
                return True, "End of scroll reached, continuing with current row position", row_is_expanded
            
            last_blue_top = new_blue_top
            last_blue_center_y = new_blue_center_y
            
            if scroll_num % 10 == 0:
                print(f"[07_HELPERS] Positioning scroll {scroll_num}, continuing...")
        elif scroll_num % 10 == 0:
            print(f"[07_HELPERS] Warning: Blue row not detected at scroll {scroll_num}, continuing...")
    
    print(f"[07_HELPERS] Warning: Reached max positioning scrolls ({max_position_scrolls}), continuing anyway")
    return True, "Reached max positioning scrolls, continuing with current position", row_is_expanded

def click_and_position_row(match_info: Dict, table_center_x: int, table_center_y: int,
                           target_region_y: int, target_region_height: int,
                           crop_x: int, crop_y: int, crop_width: int, crop_height: int) -> Tuple[bool, str]:
    """
    Click on a matched row and position it in the target region.
    Ensures the row is expanded for subsequent steps.
    """
    # Step 1: Extract click information
    click_x = match_info['click_x']
    click_y = match_info['click_y']
    button = match_info['button']
    matched_count = match_info['matched_count']
    
    # Step 2: Click on the matched row
    print(f"[07_HELPERS] Clicking at ({click_x}, {click_y}) with button={button}")
    success, action_msg = actions.click_at_position(click_x, click_y, clicks=1, button=button)
    if not success:
        return False, f"Failed to click at position: {action_msg}"
    
    # Step 3: Wait for row to potentially expand
    time.sleep(0.5)
    
    # Step 4: Position row in target region and check expansion status
    position_success, position_msg, is_expanded = position_row_in_target_region(
        table_center_x, table_center_y,
        target_region_y, target_region_height,
        crop_x, crop_y, crop_width, crop_height
    )
    
    if not position_success:
        print(f"[07_HELPERS] Warning: {position_msg}")
        return True, "Row clicked but positioning failed"

    # Step 5: Enforce Expansion
    if not is_expanded:
        print("[07_HELPERS] Row is collapsed but Step 8 requires it to be expanded.")
        print("[07_HELPERS] Attempting to expand row by clicking again...")
        
        # Retry click - maybe double click this time to ensure action? 
        # Or just single click again if it didn't register? 
        # Let's try single click again at the same spot (assuming it's the expander or text)
        print(f"[07_HELPERS] Retrying click at ({click_x}, {click_y})...")
        actions.click_at_position(click_x, click_y, clicks=1, button='left')
        time.sleep(1.0) # Wait longer for animation
        
        # Check expansion again (without scrolling this time, just check state)
        # We assume it's still roughly in position
        print("[07_HELPERS] Checking expansion state after retry...")
        cropped_screenshot = take_screenshot_and_crop((crop_x, crop_y, crop_width, crop_height))
        if cropped_screenshot is not None:
             found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(cropped_screenshot)
             if found_blue and row_info:
                 is_expanded = is_row_expanded(cropped_screenshot, row_info)
                 print(f"[07_HELPERS] Row expansion after retry: {is_expanded}")

    # Final check
    if not is_expanded:
        print("[07_HELPERS] WARNING: Row still appears collapsed. Step 8 might fail.")
    else:
        print("[07_HELPERS] Row is successfully expanded.")
    
    return True, f"Row found, clicked, and positioned! Matched {matched_count} targets"

# ============================================================================
# COLUMN DETECTION
# ============================================================================

def detect_column_separators(source_img, template_img, match_threshold=0.9, mask_size_factor=0.9, debug=False):
    """
    Detects column separator positions by template matching.
    
    Process:
    1. Creates match heatmap using TM_CCOEFF_NORMED
    2. Finds all peaks above threshold iteratively
    3. Masks nearby maxima to get unique matches only
    
    Args:
        source_img: Source image to search
        template_img: Template image of column separator
        match_threshold: Minimum confidence threshold (default: 0.9)
        mask_size_factor: Factor for masking nearby matches (default: 0.9)
        debug: Enable debug output (default: False)
    
    Returns:
        List of ((x, y), confidence) tuples
    """
    # Step 1: Get template dimensions
    template_height, template_width = template_img.shape[:2]
    
    # Step 2: Create match heatmap using template matching
    match_heatmap = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    column_separator_positions = []
    
    # Step 3: Iteratively find all matches above threshold
    while True:
        # Step 3a: Find best remaining match
        min_val, max_confidence, min_loc, best_match_position = cv2.minMaxLoc(match_heatmap)
        
        # Step 3b: Stop if below threshold
        if max_confidence < match_threshold:
            break
        
        # Step 3c: Record this separator position
        column_separator_positions.append((best_match_position, max_confidence))
        
        # Step 3d: Calculate mask dimensions
        mask_height = int(template_height * mask_size_factor)
        mask_width = int(template_width * mask_size_factor)
        
        # Step 3e: Calculate mask bounds
        y_start = max(0, best_match_position[1] - mask_height // 2)
        y_end = min(match_heatmap.shape[0], best_match_position[1] + mask_height // 2)
        x_start = max(0, best_match_position[0] - mask_width // 2)
        x_end = min(match_heatmap.shape[1], best_match_position[0] + mask_width // 2)
        
        # Step 3f: Mask nearby area to prevent duplicate detections
        match_heatmap[y_start:y_end, x_start:x_end] = 0
    
    # Step 4: Debug output
    if debug:
        if column_separator_positions:
            print(f"[DETECT_SEPARATORS] Found {len(column_separator_positions)} separators (threshold: {match_threshold}):")
            for i, (position, confidence) in enumerate(column_separator_positions, 1):
                print(f"[DETECT_SEPARATORS] Separator {i}: x={position[0]}, y={position[1]}, confidence={confidence:.3f}")
        else:
            print(f"[DETECT_SEPARATORS] No separators found above threshold {match_threshold}")
    
    return column_separator_positions

def create_separated_columns_image(source_img, column_separator_positions, template_width, 
                                   padding_width=10, debug=False):
    """
    Creates separated columns image without filtering.
    
    Processing steps:
    1. Calculate column boundaries from separator positions
    2. Crop all columns
    3. Add white padding between columns
    4. Combine into single image
    
    Args:
        source_img: Source image to process
        column_separator_positions: List of ((x, y), confidence) tuples
        template_width: Width of separator template
        padding_width: Width of padding between columns (default: 10)
        debug: Enable debug output (default: False)
    
    Returns:
        Combined image with separated columns, or None if processing fails
    """
    # Step 1: Validate input
    if not column_separator_positions:
        print("[CREATE_COLUMNS] No column separators found")
        return None
    
    print(f"[CREATE_COLUMNS] Processing {len(column_separator_positions)} separators")
    
    # Step 2: Calculate split positions from separator positions
    column_split_positions = []
    for position, score in column_separator_positions:
        x_position = position[0]
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    # Step 3: Build column boundaries (including image edges)
    unique_split_positions = sorted(set(column_split_positions))
    image_width = source_img.shape[1]
    all_column_boundaries = [0] + unique_split_positions + [image_width]
    
    if debug:
        print(f"[CREATE_COLUMNS] Column boundaries: {all_column_boundaries}")
    
    # Step 4: Crop all columns
    print(f"[CREATE_COLUMNS] Cropping {len(all_column_boundaries)-1} columns")
    
    all_columns = []
    for column_index in range(len(all_column_boundaries) - 1):
        left_edge = all_column_boundaries[column_index]
        right_edge = all_column_boundaries[column_index + 1]
        single_column = source_img[:, left_edge:right_edge]
        all_columns.append(single_column)
        
        if debug:
            column_width = right_edge - left_edge
            print(f"[CREATE_COLUMNS] Column {column_index+1}: x={left_edge} to x={right_edge} (width={column_width}px)")
    
    # Step 5: Validate columns were extracted
    if not all_columns:
        print("[CREATE_COLUMNS] No columns extracted")
        return None
    
    total_columns = len(all_columns)
    print(f"[CREATE_COLUMNS] Using all {total_columns} columns (no filtering)")
    
    # Step 6: Create white padding between columns
    image_height = source_img.shape[0]
    white_padding = np.full((image_height, padding_width, 3), 255, dtype=np.uint8)
    
    # Step 7: Combine columns with padding
    final_parts = [all_columns[0]]
    for next_column in all_columns[1:]:
        final_parts.append(white_padding)
        final_parts.append(next_column)
    
    separated_columns_image = np.hstack(final_parts)
    
    # Step 8: Log result and save debug image if enabled
    final_width = separated_columns_image.shape[1]
    print(f"[CREATE_COLUMNS] Created separated columns image: {final_width}px wide, {len(all_columns)} columns")
    
    if debug:
        cv2.imwrite('separated_columns.png', separated_columns_image)
        print("[CREATE_COLUMNS] Saved debug image: 'separated_columns.png'")
    
    return separated_columns_image

def search_current_view(target_texts: List[str], estimate_number: str, crop_x: int, crop_y: int, 
                       crop_width: int, crop_height: int, template, select_row: bool = True) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Search for target row in the current visible table view.
    
    Args:
        target_texts: List of texts to search for [estimate_number, advertiser_name, begin_date, end_date]
        estimate_number: Estimate number to find
        crop_x, crop_y: Crop coordinates
        crop_width, crop_height: Crop dimensions
        template: Column separator template
        select_row: Whether to click to select a row before processing (default: True)
                   Set to False for initial view when first row may already be visible
        
    Returns:
        Tuple of (found: bool, message: str, match_info: Optional[Dict])
        match_info contains: {
            'click_x': int, 'click_y': int, 'button': str,
            'matched_count': int, 'matched_texts': List[str],
            'all_texts': List[str]
        }
    """
    try:
        # Select a row within the separator region (only if needed)
        if select_row:
            select_row_x = crop_x + crop_width // 2
            select_row_y = crop_y + 100
            
            print(f"[SEARCH_VIEW] Clicking row at ({select_row_x}, {select_row_y}) to select for separator detection")
            success, msg = actions.click_at_position(select_row_x, select_row_y, clicks=1, button='left')
            if success:
                time.sleep(0.3)  # Wait for row selection
        else:
            print(f"[SEARCH_VIEW] Skipping row selection (select_row=False)")
        
        # Take screenshot and crop after row selection
        cropped_img = take_screenshot_and_crop((crop_x, crop_y, crop_width, crop_height))
        if cropped_img is None:
            return False, "Screenshot and crop failed", None
        
        matches = detect_column_separators(cropped_img, template)
        if not matches:
            return False, "No separators found", None
        
        separated_columns_img = create_separated_columns_image(cropped_img, matches, template.shape[1])
        if separated_columns_img is None:
            return False, "Column separation failed", None
        
        # OCR
        success, data = scanner.get_text_data(separated_columns_img)
        if not success or not data['text']:
            return False, "OCR failed or no text", None
        
        print(f"[SEARCH_VIEW] OCR found {len(data['text'])} texts")
        
        # Match texts
        positions = match_text_positions(target_texts, data)
        if not positions:
            return False, "Targets not found in view", None
        
        # Check if estimate_number exists (convert to string to handle integers)
        estimate_number_str = str(estimate_number)
        if not (positions and estimate_number and any(estimate_number_str.lower() in text.lower() for text in data['text'] if text)):
            return False, "Estimate number not found in view", None
        
        # Count how many target texts were matched
        matched_texts = []
        for target in target_texts:
            if target:
                target_str = str(target)  # Convert to string to handle integers
                if any(target_str.lower() in text.lower() for text in data['text'] if text):
                    matched_texts.append(target_str)
        
        matched_count = len(matched_texts)
        print(f"[SEARCH_VIEW] Matched {matched_count}/{len(target_texts)} target texts: {matched_texts}")
        
        # Found the row - find the estimate_number position specifically
        # We need to find which position corresponds to the estimate_number
        estimate_number_position = None
        for i, target in enumerate(target_texts):
            if target:
                target_str = str(target)  # Convert to string to handle integers
                if target_str.lower() == estimate_number_str.lower():
                    # Find the position that matches this target by checking OCR data
                    for j, text in enumerate(data['text']):
                        if text and estimate_number_str.lower() in text.lower():
                            bbox = data['bbox'][j]
                            estimate_number_position = (bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
                            print(f"[SEARCH_VIEW] Found estimate_number '{estimate_number}' at position {estimate_number_position}")
                            break
                    if estimate_number_position:
                        break
        
        # If we couldn't find estimate_number specifically, use first position
        if not estimate_number_position and positions:
            estimate_number_position = positions[0]
            print(f"[SEARCH_VIEW] Using first matched position as estimate_number: {estimate_number_position}")
        
        if not estimate_number_position:
            return False, "Could not determine estimate_number position", None
        
        x, y, w, h = estimate_number_position
        screen_x = x + crop_x
        screen_y = y + crop_y
        
        # Load RowExpander template
        row_expander_template = computer_vision_utils.load_image("src/workflow_module/actions/assets/07_RowExpander.png")
        if row_expander_template is None:
            return False, "Failed to load RowExpander template", None
        
        # Take full screenshot for RowExpander search (needed for screen coordinate matching)
        image = computer_vision_utils.take_screenshot()
        if image is None:
            return False, "Failed to take full screenshot for RowExpander search", None
        
        # Define search region - look for RowExpander in the same row as estimate_number
        # Search horizontally across the table at the same Y level as the estimate_number
        search_region_x = crop_x
        search_region_y = max(0, screen_y - h // 2)
        search_region_width = min(image.shape[1] - crop_x, crop_width)
        search_region_height = h * 2
        search_region = (search_region_x, search_region_y, search_region_width, search_region_height)
        
        print(f"[SEARCH_VIEW] Searching for RowExpander in region: x={search_region_x}, y={search_region_y}, w={search_region_width}, h={search_region_height}")
        
        # Search for RowExpander
        found, confidence, expander_position = computer_vision_utils.match_template_in_region(
            image, row_expander_template, search_region, confidence=0.7
        )
        
        match_info = {
            'matched_count': matched_count,
            'matched_texts': matched_texts,
            'all_texts': data['text']
        }
        
        if found and expander_position:
            exp_x, exp_y = expander_position
            # Verify RowExpander is in the same row (similar Y coordinate)
            if abs(exp_y - screen_y) <= h * 1.5:  # Allow some tolerance
                click_x, click_y = expander_position
                print(f"[SEARCH_VIEW] Found RowExpander at ({click_x}, {click_y}) with confidence {confidence:.2f} (same row as estimate_number)")
                match_info['click_x'] = click_x
                match_info['click_y'] = click_y
                match_info['button'] = 'left'
                return True, f"Row found with RowExpander at ({click_x}, {click_y})", match_info
            else:
                print(f"[SEARCH_VIEW] RowExpander found but Y mismatch (expander: {exp_y}, estimate_number: {screen_y}), using estimate_number position")
        
        # Fallback to estimate_number position - click slightly to the left of the estimate number text
        click_x = screen_x - 50  # Click to the left of the estimate number
        click_y = screen_y + h // 2  # Center vertically on the estimate number row
        print(f"[SEARCH_VIEW] RowExpander not found or wrong row, using estimate_number row position ({click_x}, {click_y})")
        match_info['click_x'] = click_x
        match_info['click_y'] = click_y
        match_info['button'] = 'left' # Changed from 'right' to 'left' to ensure correct selection
        return True, f"Row found at estimate_number row position ({click_x}, {click_y})", match_info
        
    except Exception as e:
        return False, f"Error searching view: {e}", None

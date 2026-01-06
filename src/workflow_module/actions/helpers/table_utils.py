#!/usr/bin/env python3
"""
Table Utilities Module

This module provides utilities for working with tables:
- Results count extraction
- Second table searching (within expanded rows)
- Table scrolling and row positioning
- Re-exports functions from other specialized modules for backward compatibility

The table utilities are organized into separate modules:
- date_utils: Date normalization
- column_detection: Column separator detection and processing
- row_utils: Row boundary detection and row searching
"""

import re
import time
import pyautogui
from typing import Tuple, Dict, Any, Optional, List
import cv2
import numpy as np

# Import dependencies
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import take_screenshot_and_crop
from src.workflow_module.actions.helpers import date_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner, match_text_positions

scanner = TextScanner()


# ============================================================================
# RESULTS COUNT EXTRACTION
# ============================================================================

def get_results_count() -> Optional[int]:
    """
    Extract the number of results from the results count region.
    
    Returns:
        Number of results as integer, or None if failed to extract
    """
    try:
        # Take screenshot and crop results region (x, y, width, height)
        results_region = take_screenshot_and_crop((206, 225, 225, 25))
        if results_region is None:
            print("[GET_RESULTS] Failed to take screenshot and crop results region")
            return None
        
        # OCR the region
        success, data = scanner.get_text_data(results_region)
        if not success or not data['text']:
            print("[GET_RESULTS] OCR failed or no text found")
            return None
        
        # Extract number from text
        # Expected format could be like "30 results" or "Results: 30" etc.
        all_text = ' '.join(data['text'])
        print(f"[GET_RESULTS] OCR text from results region: '{all_text}'")
        
        # Extract all numbers from the text
        numbers = re.findall(r'\d+', all_text)
        
        if numbers:
            # Take the first number found
            result_count = int(numbers[0])
            print(f"[GET_RESULTS] Extracted result count: {result_count}")
            return result_count
        else:
            print("[GET_RESULTS] No numbers found in results region")
            return None
            
    except Exception as e:
        print(f"[GET_RESULTS] Error extracting results count: {e}")
        return None

# ============================================================================
# SECOND TABLE SEARCHING (WITHIN EXPANDED ROW)
# ============================================================================

# def search_second_table_by_date(begin_date: str, crop_x: int, crop_y: int, 
#                                 crop_width: int, crop_height: int,
#                                 template_path: Optional[str] = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
#     """
#     Search for rows in the second table (within expanded row) by begin_date.
#     Uses column separator template to detect columns, then row boundary detection to handle variable height rows.
#     Returns all matches.
    
#     Args:
#         begin_date: Begin date to match (e.g., "01/01/2024" or "2024-01-01")
#         crop_x, crop_y: Crop coordinates for the second table region
#         crop_width, crop_height: Crop dimensions
#         template_path: Optional path to column separator template. 
#                       If None, uses default from assets folder.
        
#     Returns:
#         Tuple of (found: bool, message: str, matches: List[Dict])
#         Each match contains: {
#             'click_x': int, 'click_y': int,
#             'row_top': int, 'row_bottom': int,
#             'matched_text': str, 'row_index': int
#         }
#     """
#     try:
#         # Convert begin_date to string to handle integers
#         begin_date_str = str(begin_date)
#         print(f"[SEARCH_SECOND_TABLE] Searching for begin_date: '{begin_date_str}'")
        
#         # Load column separator template for second table
#         if template_path is None:
#             template_path = "src/workflow_module/actions/assets/08_ColumnLineSecondTable.png"
#         template = computer_vision_utils.load_image(template_path)
#         if template is None:
#             return False, f"Failed to load ColumnLineSecondTable template from {template_path}", []
        
#         time.sleep(2)
#         # Take screenshot and crop to second table region
#         cropped_img = take_screenshot_and_crop((crop_x, crop_y, crop_width, crop_height))
#         if cropped_img is None:
#             return False, "Failed to take screenshot and crop to second table region", []
        
#         # Store original cropped image dimensions for coordinate conversion
#         original_cropped_height, original_cropped_width = cropped_img.shape[:2]
        
#         # Detect column separators using template
#         print(f"[SEARCH_SECOND_TABLE] Detecting column separators...")
#         matches = detect_column_separators(cropped_img, template)
#         if not matches:
#             print(f"[SEARCH_SECOND_TABLE] No column separators found, proceeding with direct OCR")
#             using_separated_columns = False
#         else:
#             print(f"[SEARCH_SECOND_TABLE] Found {len(matches)} column separators")
            
#             # Create separated columns image
#             separated_columns_img = create_separated_columns_image(cropped_img, matches, template.shape[1])
#             if separated_columns_img is not None:
#                 print(f"[SEARCH_SECOND_TABLE] Using separated columns image for OCR")
#                 cropped_img = separated_columns_img
#                 using_separated_columns = True
#             else:
#                 print(f"[SEARCH_SECOND_TABLE] Column separation failed, using original cropped image")
#                 using_separated_columns = False
        
#         # Get the actual dimensions of the image used for OCR
#         ocr_img_height, ocr_img_width = cropped_img.shape[:2]
#         print(f"[SEARCH_SECOND_TABLE] OCR image dimensions: {ocr_img_width}x{ocr_img_height} (original cropped: {original_cropped_width}x{original_cropped_height})")
        
#         # Perform OCR on the processed image
#         success, data = scanner.get_text_data(cropped_img)
#         if not success or not data['text']:
#             return False, "OCR failed or no text", []
        
#         print(f"[SEARCH_SECOND_TABLE] OCR found {len(data['text'])} text elements")
        
#         # Determine row boundaries
#         row_boundaries, row_count = determine_row_boundaries(
#             data['bbox'], 
#             data['text'],
#             min_row_height=15,
#             line_tolerance=5,
#             row_gap_tolerance=20
#         )
        
#         print(f"[SEARCH_SECOND_TABLE] Detected {row_count} rows")
        
#         if row_count == 0:
#             return False, "No rows detected", []
        
#         # Normalize begin_date for matching by removing leading zeros
#         # Example: 09/16/2025 → 9/16/2025
#         begin_date_normalized = date_utils.normalize_date(begin_date_str)
#         print(f"[SEARCH_SECOND_TABLE] Searching for begin_date: '{begin_date_str}' → normalized: '{begin_date_normalized}'")
        
#         # Also create a version without separators for flexible matching
#         date_normalized = begin_date_normalized.replace('/', '').replace('-', '').replace(' ', '')
        
#         # Extract digits from begin_date to help identify date values
#         date_digits = re.sub(r'[^\d]', '', begin_date_normalized)
#         print(f"[SEARCH_SECOND_TABLE] Date digits: '{date_digits}'")
        
#         # Words to exclude (like "begin", "date", "end")
#         exclude_words = ['begin', 'date', 'end', 'start', 'from', 'to']
        
#         # Search for begin_date in each row (skip first row which is the header)
#         all_matches = []
#         for row_idx, (row_top, row_bottom) in enumerate(row_boundaries):
#             # Skip the first row (header row) - only search data rows
#             if row_idx == 0:
#                 print(f"[SEARCH_SECOND_TABLE] Skipping row {row_idx + 1} (header row)")
#                 continue
#             # Find all texts in this row
#             row_texts = []
#             row_boxes = []
#             for i, bbox in enumerate(data['bbox']):
#                 x1, y1, x2, y2 = map(int, bbox)
#                 center_y = (y1 + y2) / 2
                
#                 # Check if this box is within the row boundaries
#                 if row_top <= center_y <= row_bottom:
#                     row_texts.append(data['text'][i])
#                     row_boxes.append(bbox)
            
#             # Check if any text in this row matches the begin_date
#             row_text_combined = ' '.join(row_texts)
#             # Normalize row text for comparison (remove leading zeros too)
#             row_text_normalized_with_sep = date_utils.normalize_date(row_text_combined)
#             row_text_normalized = row_text_normalized_with_sep.replace('/', '').replace('-', '').replace(' ', '')
            
#             # Check if the normalized date is in the normalized row text
#             # Also check with separators for more flexible matching
#             if date_normalized in row_text_normalized or begin_date_normalized in row_text_normalized_with_sep:
#                 print(f"[SEARCH_SECOND_TABLE] Found matching row {row_idx + 1}/{row_count}")
#                 print(f"[SEARCH_SECOND_TABLE] Row text: '{row_text_combined}'")
#                 print(f"[SEARCH_SECOND_TABLE] Looking for begin_date: '{begin_date_str}' (normalized: '{date_normalized}')")
                
#                 # Find the actual bbox that contains the begin_date VALUE (not the word "begin" or "date")
#                 # Prioritize text that contains digits and matches the date
#                 begin_date_bbox = None
#                 best_match_score = 0
                
#                 # First, try to find exact match or closest match that contains digits
#                 for i, text in enumerate(data['text']):
#                     bbox = data['bbox'][i]
#                     x1, y1, x2, y2 = map(int, bbox)
#                     center_y = (y1 + y2) / 2
                    
#                     # Check if this box is in the matching row
#                     if row_top <= center_y <= row_bottom:
#                         # Normalize OCR text (remove leading zeros too)
#                         text_normalized_with_sep = date_utils.normalize_date(text)
#                         text_normalized = text_normalized_with_sep.replace('/', '').replace('-', '').replace(' ', '')
#                         text_lower = text.lower()
                        
#                         # Skip if this is a label word like "begin", "date", etc.
#                         if any(exclude_word in text_lower for exclude_word in exclude_words):
#                             continue
                        
#                         # Check if text contains digits (dates have numbers)
#                         text_digits = re.sub(r'[^\d]', '', text)
#                         if not text_digits:
#                             continue  # Skip text without digits
                        
#                         # Check for exact match (with or without separators)
#                         if date_normalized == text_normalized or begin_date_normalized == text_normalized_with_sep:
#                             begin_date_bbox = (x1, y1, x2, y2)
#                             print(f"[SEARCH_SECOND_TABLE] Found exact begin_date match: '{text}' at bbox ({x1}, {y1}, {x2}, {y2})")
#                             break
#                         elif date_normalized in text_normalized or begin_date_normalized in text_normalized_with_sep:
#                             # Partial match - check how many digits match
#                             matching_digits = sum(1 for d in date_digits if d in text_digits)
#                             if matching_digits > best_match_score:
#                                 best_match_score = matching_digits
#                                 begin_date_bbox = (x1, y1, x2, y2)
#                                 print(f"[SEARCH_SECOND_TABLE] Found partial begin_date match: '{text}' (matched digits: {matching_digits}/{len(date_digits)})")
                
#                 # If no single box match, try to find the box that contains the most matching digits
#                 if begin_date_bbox is None:
#                     print(f"[SEARCH_SECOND_TABLE] No single box match, searching for best date match...")
#                     for i, text in enumerate(data['text']):
#                         bbox = data['bbox'][i]
#                         x1, y1, x2, y2 = map(int, bbox)
#                         center_y = (y1 + y2) / 2
                        
#                         if row_top <= center_y <= row_bottom:
#                             text_lower = text.lower()
                            
#                             # Skip label words
#                             if any(exclude_word in text_lower for exclude_word in exclude_words):
#                                 continue
                            
#                             # Check if text contains digits
#                             text_digits = re.sub(r'[^\d]', '', text)
#                             if not text_digits:
#                                 continue
                            
#                             # Count matching digits
#                             matching_digits = sum(1 for d in date_digits if d in text_digits)
#                             if matching_digits > best_match_score:
#                                 best_match_score = matching_digits
#                                 begin_date_bbox = (x1, y1, x2, y2)
#                                 print(f"[SEARCH_SECOND_TABLE] Best date match so far: '{text}' (matched digits: {matching_digits}/{len(date_digits)})")
                
#                 if begin_date_bbox is None:
#                     # Fallback: use center of row
#                     print(f"[SEARCH_SECOND_TABLE] WARNING: Could not find begin_date bbox, using row center")
#                     click_x_ocr = ocr_img_width // 2
#                     click_y_ocr = row_top + (row_bottom - row_top) // 2
#                 else:
#                     # Use the exact center of the begin_date bbox (no modification)
#                     x1, y1, x2, y2 = begin_date_bbox
#                     click_x_ocr = (x1 + x2) // 2  # Center X of the date bbox
#                     click_y_ocr = (y1 + y2) // 2  # Center Y of the date bbox
#                     print(f"[SEARCH_SECOND_TABLE] Using begin_date bbox center: bbox=({x1}, {y1}, {x2}, {y2}), center=({click_x_ocr}, {click_y_ocr})")
                
#                 # Convert OCR image coordinates to original cropped image coordinates
#                 # OCR bbox coordinates are relative to the OCR image (cropped_img or separated_columns_img)
#                 # We need to convert them to coordinates relative to the original cropped image
                
#                 # Y coordinates: Height doesn't change between cropped_img and separated_columns_img
#                 # So Y coordinates are always relative to the original cropped image
#                 click_y_cropped = int(click_y_ocr)
                
#                 # X coordinates: Need conversion if using separated columns (width changes)
#                 if using_separated_columns:
#                     # Separated columns image has different width due to padding
#                     # Map X coordinate from separated_columns_img back to original cropped_img
#                     # Using proportional scaling based on width ratio
#                     scale_factor = original_cropped_width / ocr_img_width
#                     click_x_cropped = int(click_x_ocr * scale_factor)
#                     print(f"[SEARCH_SECOND_TABLE] X coordinate conversion (separated columns): OCR={click_x_ocr}, scale={scale_factor:.4f}, cropped={click_x_cropped}")
#                 else:
#                     # No conversion needed - OCR image is the same as cropped image
#                     click_x_cropped = int(click_x_ocr)
#                     print(f"[SEARCH_SECOND_TABLE] X coordinate (no conversion needed): {click_x_cropped}")
                
#                 print(f"[SEARCH_SECOND_TABLE] Coordinates after OCR→Cropped conversion: ({click_x_cropped}, {click_y_cropped})")
                
#                 # Convert cropped coordinates to screen coordinates
#                 # Add the crop offset to get absolute screen coordinates
#                 click_x = click_x_cropped + crop_x
#                 click_y = click_y_cropped + crop_y
                
#                 print(f"[SEARCH_SECOND_TABLE] Final screen coordinates: ({click_x}, {click_y})")
#                 print(f"[SEARCH_SECOND_TABLE] Conversion path: OCR({click_x_ocr}, {click_y_ocr}) → Cropped({click_x_cropped}, {click_y_cropped}) → Screen({click_x}, {click_y})")
#                 print(f"[SEARCH_SECOND_TABLE] Crop offsets applied: crop_x={crop_x}, crop_y={crop_y}")
                
#                 match_info = {
#                     'click_x': click_x,
#                     'click_y': click_y,
#                     'row_top': row_top + crop_y,
#                     'row_bottom': row_bottom + crop_y,
#                     'matched_text': row_text_combined,
#                     'row_index': row_idx
#                 }
                
#                 all_matches.append(match_info)
        
#         if all_matches:
#             print(f"[SEARCH_SECOND_TABLE] Found {len(all_matches)} matching rows")
#             return True, f"Found {len(all_matches)} matching rows", all_matches
#         else:
#             return False, f"Begin date '{begin_date_str}' not found in any row", []
        
#     except Exception as e:
#         return False, f"Error searching second table: {e}", []


# ============================================================================
# TABLE SCROLLING AND ROW POSITIONING
# ============================================================================

def scroll_to_table_top(table_center_x: int, table_center_y: int, 
                        table_crop_x: int, table_crop_y: int, table_crop_width: int) -> None:
    """
    Scroll the table up by one step.
    
    Args:
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
        table_crop_x: X coordinate of table crop region (unused)
        table_crop_y: Y coordinate of table crop region (unused)
        table_crop_width: Width of table crop region (unused)
    """
    print(f"[TABLE_UTILS] Scrolling up...")
    
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    pyautogui.scroll(50)  # Positive value scrolls up
    time.sleep(0.05)

def position_row_in_target_region(click_x: int, click_y: int, 
                                   table_center_x: int, table_center_y: int,
                                   crop_x: int, crop_y: int, crop_width: int, crop_height: int,
                                   template, target_texts, estimate_number: str,
                                   target_region_y: int, target_region_height: int) -> Tuple[bool, str]:
    """
    After clicking a row, scroll down to position it within the target region if needed.
    Uses blue color detection to find the highlighted row position.
    
    Args:
        click_x: X position of the clicked row
        click_y: Current Y position of the clicked row
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
        crop_x, crop_y: Table crop region for searching
        crop_width, crop_height: Table crop dimensions
        template: Template for column detection
        target_texts: Target texts to search for
        estimate_number: Estimate number for searching
        target_region_y: Y coordinate of target region top
        target_region_height: Height of target region
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    target_region_bottom = target_region_y + target_region_height
    
    # Wait for the row to be highlighted in blue after clicking
    time.sleep(0.3)
    
    # Detect blue highlighted row
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        print(f"[TABLE_UTILS] Warning: Failed to take screenshot for blue detection")
        return False, "Failed to take screenshot"
    
    found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(screenshot)
    if not found_blue or row_info is None:
        print(f"[TABLE_UTILS] Warning: Could not detect blue highlighted row after clicking")
        return False, "Could not detect blue highlighted row"
    
    blue_row_y = row_info['y']
    blue_row_height = row_info['height']
    blue_row_center_y = blue_row_y + (blue_row_height // 2)
    blue_row_top = blue_row_y
    blue_row_bottom = blue_row_y + blue_row_height
    
    print(f"[TABLE_UTILS] Blue highlighted row detected at y={blue_row_y}, center_y={blue_row_center_y}, height={blue_row_height}")
    print(f"[TABLE_UTILS] Blue row bounds: top={blue_row_top}, bottom={blue_row_bottom}")
    print(f"[TABLE_UTILS] Target region bounds: top={target_region_y}, bottom={target_region_bottom}")
    
    # Check if the entire row (or at least most of it) is already within the target region
    # Consider the row "in region" if its top is below target top and its center is above target bottom
    row_in_region = (blue_row_top >= target_region_y) and (blue_row_center_y <= target_region_bottom)
    
    if row_in_region:
        print(f"[TABLE_UTILS] ✓ Row already in target region (top={blue_row_top}, center={blue_row_center_y})")
        print(f"[TABLE_UTILS] ✓ No scrolling needed - row is already positioned correctly")
        return True, "Row already in target region"
    
    print(f"[TABLE_UTILS] ✗ Row NOT in target region (top={blue_row_top} vs target_top={target_region_y}, center={blue_row_center_y} vs target_bottom={target_region_bottom})")
    print(f"[TABLE_UTILS] Scrolling down to position row in target region {target_region_y}-{target_region_bottom}...")
    
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.2)
    
    max_position_scrolls = 100
    scroll_amount = -20  # Scroll down slowly (negative value)
    
    last_blue_center_y = blue_row_center_y
    
    for scroll_num in range(1, max_position_scrolls + 1):
        pyautogui.scroll(scroll_amount)
        time.sleep(0.05)
        
        check_screenshot = computer_vision_utils.take_screenshot()
        if check_screenshot is None:
            if scroll_num % 10 == 0:
                print(f"[TABLE_UTILS] Warning: Screenshot failed at scroll {scroll_num}")
            continue
        
        # Detect blue row position
        check_found, check_row_info = computer_vision_utils.find_blue_highlighted_row(check_screenshot)
        
        if check_found and check_row_info:
            new_blue_y = check_row_info['y']
            new_blue_height = check_row_info['height']
            new_blue_center_y = new_blue_y + (new_blue_height // 2)
            
            # Check if row is now in target region
            if target_region_y <= new_blue_center_y <= target_region_bottom:
                print(f"[TABLE_UTILS] ✓ Row positioned in target region after {scroll_num} scroll(s) (y={new_blue_center_y})")
                return True, f"Row positioned in target region at y={new_blue_center_y}"
            
            # Check if we stopped moving (end of scroll)
            if abs(new_blue_center_y - last_blue_center_y) < 5:
                print(f"[TABLE_UTILS] Row position unchanged at y={new_blue_center_y}. Assuming end of table.")
                return True, "End of scroll reached, continuing with current row position"
            
            last_blue_center_y = new_blue_center_y
            
            if scroll_num % 10 == 0:
                print(f"[TABLE_UTILS] Positioning scroll {scroll_num}: blue row at y={new_blue_center_y}, continuing...")
        elif scroll_num % 10 == 0:
            print(f"[TABLE_UTILS] Warning: Blue row not detected at scroll {scroll_num}, continuing...")
    
    print(f"[TABLE_UTILS] Warning: Reached max positioning scrolls ({max_position_scrolls}), continuing anyway")
    return True, "Reached max positioning scrolls, continuing with current position"

def click_and_position_row(match_info: Dict, table_center_x: int, table_center_y: int,
                           crop_x: int, crop_y: int, crop_width: int, crop_height: int,
                           template, target_texts, estimate_number: str,
                           target_region_y: int, target_region_height: int) -> Tuple[bool, str]:
    """
    Click on a matched row and position it in the target region.
    
    Args:
        match_info: Dictionary containing match information (click_x, click_y, button, matched_count)
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
        crop_x, crop_y: Table crop region for searching
        crop_width, crop_height: Table crop dimensions
        template: Template for column detection
        target_texts: Target texts to search for
        estimate_number: Estimate number for searching
        target_region_y: Y coordinate of target region top
        target_region_height: Height of target region
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    click_x = match_info['click_x']
    click_y = match_info['click_y']
    button = match_info['button']
    matched_count = match_info['matched_count']
    
    print(f"[TABLE_UTILS] Clicking at ({click_x}, {click_y}) with button={button}")
    success, action_msg = actions.click_at_position(click_x, click_y, clicks=1, button=button)
    if not success:
        return False, f"Failed to click at position: {action_msg}"
    
    # Position row in target region
    time.sleep(0.3)
    position_success, position_msg = position_row_in_target_region(
        click_x, click_y, table_center_x, table_center_y,
        crop_x, crop_y, crop_width, crop_height,
        template, target_texts, estimate_number,
        target_region_y, target_region_height
    )
    
    if not position_success:
        print(f"[TABLE_UTILS] Warning: {position_msg}")
    
    return True, f"Row found and clicked! Matched {matched_count}/{len(target_texts)} targets"

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
    template_height, template_width = template_img.shape[:2]
    
    # Create match heatmap
    match_heatmap = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    column_separator_positions = []
    
    while True:
        # Find best remaining match
        min_val, max_confidence, min_loc, best_match_position = cv2.minMaxLoc(match_heatmap)
        
        # Stop if below threshold
        if max_confidence < match_threshold:
            break
        
        # Record this separator
        column_separator_positions.append((best_match_position, max_confidence))
        
        # Mask nearby area to prevent duplicate detections
        mask_height = int(template_height * mask_size_factor)
        mask_width = int(template_width * mask_size_factor)
        
        y_start = max(0, best_match_position[1] - mask_height // 2)
        y_end = min(match_heatmap.shape[0], best_match_position[1] + mask_height // 2)
        x_start = max(0, best_match_position[0] - mask_width // 2)
        x_end = min(match_heatmap.shape[1], best_match_position[0] + mask_width // 2)
        
        match_heatmap[y_start:y_end, x_start:x_end] = 0
    
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
    if not column_separator_positions:
        print("[CREATE_COLUMNS] No column separators found")
        return None
    
    # Calculate column boundaries
    print(f"[CREATE_COLUMNS] Processing {len(column_separator_positions)} separators")
    
    column_split_positions = []
    for position, score in column_separator_positions:
        x_position = position[0]
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    unique_split_positions = sorted(set(column_split_positions))
    image_width = source_img.shape[1]
    all_column_boundaries = [0] + unique_split_positions + [image_width]
    
    if debug:
        print(f"[CREATE_COLUMNS] Column boundaries: {all_column_boundaries}")
    
    # Crop all columns
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
    
    if not all_columns:
        print("[CREATE_COLUMNS] No columns extracted")
        return None
    
    # Keep all columns (no filtering)
    total_columns = len(all_columns)
    print(f"[CREATE_COLUMNS] Using all {total_columns} columns (no filtering)")
    
    # Create white padding
    image_height = source_img.shape[0]
    white_padding = np.full((image_height, padding_width, 3), 255, dtype=np.uint8)
    
    # Combine columns with padding
    final_parts = [all_columns[0]]
    for next_column in all_columns[1:]:
        final_parts.append(white_padding)
        final_parts.append(next_column)
    
    separated_columns_image = np.hstack(final_parts)
    
    final_width = separated_columns_image.shape[1]
    print(f"[CREATE_COLUMNS] Created separated columns image: {final_width}px wide, {len(all_columns)} columns")
    
    if debug:
        cv2.imwrite('separated_columns.png', separated_columns_image)
        print("[CREATE_COLUMNS] Saved debug image: 'separated_columns.png'")
    
    return separated_columns_image

def get_column_by_index(source_img, column_separator_positions, template_width, column_index: int, debug=False):
    """
    Extracts a specific column from the source image using column separators.
    
    Processing steps:
    1. Calculate column boundaries from separator positions
    2. Extract the specified column (0-based index)
    3. Return the single column image
    
    Args:
        source_img: Source image to process
        column_separator_positions: List of ((x, y), confidence) tuples
        template_width: Width of separator template
        column_index: Column index to extract (0-based, e.g., 0 = first column, 4 = column 5)
        debug: Enable debug output (default: False)
    
    Returns:
        Image containing only the specified column, or None if processing fails or column doesn't exist
    """
    if not column_separator_positions:
        print(f"[GET_COLUMN] No column separators found")
        return None
    
    # Calculate column boundaries
    print(f"[GET_COLUMN] Processing {len(column_separator_positions)} separators")
    
    column_split_positions = []
    for position, score in column_separator_positions:
        x_position = position[0]
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    unique_split_positions = sorted(set(column_split_positions))
    image_width = source_img.shape[1]
    all_column_boundaries = [0] + unique_split_positions + [image_width]
    
    if debug:
        print(f"[GET_COLUMN] Column boundaries: {all_column_boundaries}")
    
    # Calculate total number of columns
    total_columns = len(all_column_boundaries) - 1
    print(f"[GET_COLUMN] Found {total_columns} columns")
    
    # Check if requested column exists
    if column_index < 0 or column_index >= total_columns:
        print(f"[GET_COLUMN] Column {column_index + 1} does not exist. Only {total_columns} columns found")
        return None
    
    # Extract the specified column
    left_edge = all_column_boundaries[column_index]
    right_edge = all_column_boundaries[column_index + 1]
    column_image = source_img[:, left_edge:right_edge]
    
    if debug:
        column_width = right_edge - left_edge
        print(f"[GET_COLUMN] Column {column_index + 1}: x={left_edge} to x={right_edge} (width={column_width}px)")
        cv2.imwrite(f'column_{column_index + 1}_extracted.png', column_image)
        print(f"[GET_COLUMN] Saved debug image: 'column_{column_index + 1}_extracted.png'")
    
    print(f"[GET_COLUMN] Successfully extracted column {column_index + 1}")
    return column_image

def get_column_5_image(source_img, column_separator_positions, template_width, debug=False):
    """
    Extracts only column 5 from the source image using column separators.
    (Legacy function - uses get_column_by_index internally)
    """
    return get_column_by_index(source_img, column_separator_positions, template_width, column_index=4, debug=debug)

def find_begin_date_column_index(target_region_img, separator_matches, template_width, ocr_data=None):
    """
    Finds which column index contains the "Begin" or "Begin Date" header.
    
    Args:
        target_region_img: The target region image
        separator_matches: List of separator positions
        template_width: Width of separator template
        ocr_data: Optional OCR data dict with 'text' and 'bbox' keys. If None, will perform OCR.
    
    Returns:
        Column index (0-based) if found, or None if not found
    """
    from src.workflow_module.actions.helpers import ocr_utils
    
    # Calculate column boundaries
    column_split_positions = []
    for position, score in separator_matches:
        x_position = position[0]
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    unique_split_positions = sorted(set(column_split_positions))
    image_width = target_region_img.shape[1]
    all_column_boundaries = [0] + unique_split_positions + [image_width]
    total_columns = len(all_column_boundaries) - 1
    
    # Get OCR data if not provided
    if ocr_data is None:
        scanner = ocr_utils.TextScanner()
        success, ocr_data = scanner.get_text_data(target_region_img)
        if not success or not ocr_data or not ocr_data.get('text'):
            print("[FIND_BEGIN_DATE_COLUMN] Failed to get OCR data")
            return None
    
    # Look for "Begin" or "Begin Date" in the header row (top portion of image)
    header_height = 40  # Approximate header height
    begin_keywords = ["begin", "begin date", "begindate"]
    
    print(f"[FIND_BEGIN_DATE_COLUMN] Searching for 'Begin' column in {total_columns} columns")
    
    for i, text in enumerate(ocr_data['text']):
        if not text: continue
        
        bbox = ocr_data['bbox'][i]
        center_y = (bbox[1] + bbox[3]) // 2
        
        # Check if this text is in the header row
        if center_y < header_height:
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in begin_keywords):
                # Find which column this text belongs to
                center_x = (bbox[0] + bbox[2]) // 2
                
                for col_idx in range(total_columns):
                    if all_column_boundaries[col_idx] <= center_x < all_column_boundaries[col_idx + 1]:
                        print(f"[FIND_BEGIN_DATE_COLUMN] ✓ Found 'Begin' column at index {col_idx} (column {col_idx + 1})")
                        return col_idx
    
    print(f"[FIND_BEGIN_DATE_COLUMN] Could not find 'Begin' column in header")
    return None

# ============================================================================
# ROW UTILITIES
# ============================================================================

def determine_row_boundaries(all_boxes: List[List[int]], all_texts: List[str], 
                             min_row_height: int = 15,
                             line_tolerance: int = 5,
                             row_gap_tolerance: int = 20) -> Tuple[List[Tuple[int, int]], int]:
    """
    Determines row boundaries based on OCR boxes and texts.
    Uses selling titles (starting with instruction pattern) to identify new rows.
    
    Args:
        all_boxes: List of bounding boxes [[x1, y1, x2, y2], ...]
        all_texts: List of text strings corresponding to boxes
        min_row_height: Minimum height for a valid row (default: 15)
        line_tolerance: Y-coordinate tolerance for grouping boxes into lines (default: 5)
        row_gap_tolerance: Gap between rows to identify new row start (default: 20)
        
    Returns:
        Tuple of (row_boundaries: List[(top, bottom)], row_count: int)
    """
    if not all_boxes or not all_texts:
        return [], 0
    
    box_info = []
    for i, box in enumerate(all_boxes):
        x1, y1, x2, y2 = map(int, box)
        center_y = (y1 + y2) / 2
        box_info.append({
            'box': [x1, y1, x2, y2],
            'text': all_texts[i],
            'center_y': center_y,
            'top': y1,
            'bottom': y2,
            'left': x1
        })
    
    box_info.sort(key=lambda b: b['center_y'])
    
    # Group boxes into lines based on Y-coordinate proximity
    lines = []
    current_line = [box_info[0]]
    for box in box_info[1:]:
        if box['center_y'] - current_line[-1]['center_y'] > line_tolerance:
            lines.append(current_line)
            current_line = [box]
        else:
            current_line.append(box)
    lines.append(current_line)
    
    # Sort boxes within each line by X coordinate
    for line in lines:
        line.sort(key=lambda b: b['left'])
    
    # Group lines into rows based on instruction pattern or gap
    rows = []
    current_row = [lines[0]]
    instruction_pattern = r'^\d{7}-\d{4}-[A-Z]+'
    
    for line in lines[1:]:
        if line:
            left_text = line[0]['text'].strip()
            prev_bottom = max(b['bottom'] for b in current_row[-1])
            curr_top = min(b['top'] for b in line)
            gap = curr_top - prev_bottom
            
            if re.match(instruction_pattern, left_text) or gap > row_gap_tolerance:
                rows.append(current_row)
                current_row = [line]
            else:
                current_row.append(line)
    
    if current_row:
        rows.append(current_row)
    
    # Calculate row boundaries
    row_boundaries = []
    for row_lines in rows:
        all_boxes_in_row = [b for line in row_lines for b in line]
        if all_boxes_in_row:
            row_top = min(b['top'] for b in all_boxes_in_row)
            row_bottom = max(b['bottom'] for b in all_boxes_in_row)
            height = row_bottom - row_top
            
            if height >= min_row_height:
                row_boundaries.append((int(row_top), int(row_bottom)))
    
    row_boundaries.sort(key=lambda x: x[0])
    return row_boundaries, len(row_boundaries)

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
        
        # Take screenshot after row selection
        image = computer_vision_utils.take_screenshot()
        if image is None:
            return False, "Screenshot failed", None
        
        # Crop and process
        cropped_img = computer_vision_utils.crop_image(image, crop_x, crop_y, crop_width, crop_height)
        if cropped_img is None:
            return False, "Crop failed", None
        
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
        match_info['button'] = 'right'
        return True, f"Row found at estimate_number row position ({click_x}, {click_y})", match_info
        
    except Exception as e:
        return False, f"Error searching view: {e}", None

# ============================================================================
# NEW FUNCTIONS FOR STEP 08 (Added 2026-01-06)
# ============================================================================

def find_all_template_matches(
    source_img: np.ndarray,
    template_img: np.ndarray,
    confidence: float = 0.7,
    min_distance: int = 10 ) -> List[Tuple[Tuple[int, int], float]]:
    """
    Find all occurrences of a template in an image.
    
    This function uses template matching to find multiple instances of a template,
    masking found matches to prevent duplicates.
    
    Args:
        source_img: Source image to search
        template_img: Template image to find
        confidence: Minimum confidence threshold (0.0-1.0)
        min_distance: Minimum pixel distance between matches to prevent duplicates
        
    Returns:
        List of ((x, y), confidence) tuples, where (x, y) is the top-left corner
        
    Example:
        >>> template = cv2.imread('border_line.png')
        >>> screenshot = cv2.imread('screen.png')
        >>> matches = find_all_template_matches(screenshot, template, confidence=0.8)
        >>> print(f"Found {len(matches)} matches")
    """
    template_height, template_width = template_img.shape[:2]
    
    # Create match heatmap
    match_heatmap = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    matches = []
    
    while True:
        # Find best remaining match
        min_val, max_confidence, min_loc, best_position = cv2.minMaxLoc(match_heatmap)
        
        # Stop if below threshold
        if max_confidence < confidence:
            break
        
        # Record this match
        matches.append((best_position, max_confidence))
        
        # Mask nearby area to prevent duplicates
        mask_height = max(template_height, min_distance)
        mask_width = max(template_width, min_distance)
        
        y_start = max(0, best_position[1] - mask_height // 2)
        y_end = min(match_heatmap.shape[0], best_position[1] + mask_height // 2)
        x_start = max(0, best_position[0] - mask_width // 2)
        x_end = min(match_heatmap.shape[1], best_position[0] + mask_width // 2)
        
        match_heatmap[y_start:y_end, x_start:x_end] = 0
    
    return matches

def detect_column_separators_in_image(
    source_img: np.ndarray,
    template_img: np.ndarray,
    match_threshold: float = 0.85 ) -> List[Tuple[Tuple[int, int], float]]:
    """
    Detect column separator positions using template matching.
    
    Similar to detect_column_separators but with a simpler interface.
    
    Args:
        source_img: Source image to search
        template_img: Template image of column separator
        match_threshold: Minimum confidence threshold
        
    Returns:
        List of ((x, y), confidence) tuples
        
    Example:
        >>> template = cv2.imread('column_line.png')
        >>> table = cv2.imread('table.png')
        >>> separators = detect_column_separators_in_image(table, template)
        >>> print(f"Found {len(separators)} column separators")
    """
    return find_all_template_matches(source_img, template_img, match_threshold, min_distance=10)

def calculate_column_boundaries(
    separator_matches: List[Tuple[Tuple[int, int], float]],
    template_width: int,
    image_width: int ) -> List[int]:
    """
    Calculate column boundaries from separator positions.
    
    Takes the detected separator positions and converts them to column boundary
    x-coordinates, including the image edges.
    
    Args:
        separator_matches: List of ((x, y), confidence) tuples from template matching
        template_width: Width of separator template in pixels
        image_width: Width of source image in pixels
        
    Returns:
        List of column boundary x-coordinates (sorted), including 0 and image_width
        
    Example:
        >>> separators = [((100, 50), 0.95), ((200, 50), 0.93)]
        >>> boundaries = calculate_column_boundaries(separators, 5, 300)
        >>> print(boundaries)  # [0, 102, 202, 300]
    """
    column_split_positions = []
    
    for position, score in separator_matches:
        x_position = position[0]
        # Use center of template as split point
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    # Remove duplicates and sort
    unique_positions = sorted(set(column_split_positions))
    
    # Add image boundaries
    all_boundaries = [0] + unique_positions + [image_width]
    
    return all_boundaries

def group_ocr_by_rows(
    ocr_data: Dict[str, Any], y_tolerance: int = 10 ) -> List[Dict[str, Any]]:
    """
    Group OCR results into rows based on Y-coordinate proximity.
    
    OCR returns individual text elements. This function groups elements that are
    vertically aligned (similar Y coordinates) into logical rows.
    
    Args:
        ocr_data: OCR data dict with 'text', 'bbox', 'confidence' keys
        y_tolerance: Maximum Y distance (pixels) to consider elements in same row
        
    Returns:
        List of row dictionaries, each containing:
            - 'y_center': Average Y coordinate of the row
            - 'texts': List of text strings in the row
            - 'bboxes': List of bounding boxes in the row
            
    Example:
        >>> ocr_data = {'text': ['Name', 'Date', 'Value'], 
        ...             'bbox': [[10,10,50,30], [100,12,150,28], [200,11,250,29]]}
        >>> rows = group_ocr_by_rows(ocr_data, y_tolerance=5)
        >>> print(f"Grouped into {len(rows)} row(s)")
    """
    if not ocr_data or not ocr_data.get('text'):
        return []
    
    # Create list of (y_center, text, bbox)
    elements = []
    for i, text in enumerate(ocr_data['text']):
        if text.strip():
            bbox = ocr_data['bbox'][i]
            x1, y1, x2, y2 = map(int, bbox)
            y_center = (y1 + y2) // 2
            elements.append({
                'y_center': y_center,
                'text': text,
                'bbox': bbox
            })
    
    # Sort by Y coordinate
    elements.sort(key=lambda e: e['y_center'])
    
    # Group into rows
    rows = []
    current_row = None
    
    for elem in elements:
        if current_row is None:
            current_row = {
                'y_center': elem['y_center'],
                'texts': [elem['text']],
                'bboxes': [elem['bbox']]
            }
        else:
            # Check if within tolerance of current row
            if abs(elem['y_center'] - current_row['y_center']) <= y_tolerance:
                current_row['texts'].append(elem['text'])
                current_row['bboxes'].append(elem['bbox'])
            else:
                # Start new row
                rows.append(current_row)
                current_row = {
                    'y_center': elem['y_center'],
                    'texts': [elem['text']],
                    'bboxes': [elem['bbox']]
                }
    
    # Add last row
    if current_row:
        rows.append(current_row)
    
    return rows

def find_date_bbox_in_row(
    row_data: Dict[str, Any], begin_date_str: str, 
    begin_date_normalized: str, column_boundaries: List[int] ) -> Optional[Tuple[int, int, int, int]]:
    """
    Find the bounding box of the date within a row.
    
    Searches through text elements in a row to find one that matches the target date.
    
    Args:
        row_data: Row data dict with 'texts' and 'bboxes' keys
        begin_date_str: Original date string (e.g., "1/5/2026")
        begin_date_normalized: Normalized date string (e.g., "152026")
        column_boundaries: List of column boundary x-coordinates (currently unused)
        
    Returns:
        Bounding box (x1, y1, x2, y2) or None if not found
        
    Example:
        >>> row = {'texts': ['ESPN', '1/5/2026', 'Active'], 
        ...        'bboxes': [[10,10,50,30], [60,10,120,30], [130,10,180,30]]}
        >>> bbox = find_date_bbox_in_row(row, '1/5/2026', '152026', [])
        >>> print(bbox)  # (60, 10, 120, 30)
    """
    from src.workflow_module.actions.helpers import date_utils
    
    for i, text in enumerate(row_data['texts']):
        text_normalized = date_utils.normalize_date(text)
        
        if begin_date_normalized in text_normalized or begin_date_str in text:
            return row_data['bboxes'][i]
    
    return None

def search_date_in_cropped_table(
    cropped_table: np.ndarray, column_boundaries: List[int], begin_date: str,
    crop_x: int, crop_y: int ) -> Tuple[bool, Optional[int], Optional[int], str]:
    """
    Search for the first row containing the begin_date in a cropped table.
    
    This is a high-level function that:
    1. Performs OCR on the table
    2. Groups results into rows
    3. Searches for matching date
    4. Returns click coordinates
    
    Args:
        cropped_table: Cropped table image
        column_boundaries: List of column boundary x-coordinates
        begin_date: Date string to search for
        crop_x, crop_y: Offset coordinates for converting to screen coordinates
        
    Returns:
        Tuple of (found: bool, click_x: Optional[int], click_y: Optional[int], message: str)
        
    Example:
        >>> table_img = cv2.imread('cropped_table.png')
        >>> found, x, y, msg = search_date_in_cropped_table(table_img, [], '1/5/2026', 205, 280)
        >>> if found:
        ...     print(f"Date found at ({x}, {y})")
    """
    from src.workflow_module.actions.helpers import ocr_utils
    from src.workflow_module.actions.helpers import date_utils
    
    print(f"[TABLE_UTILS] Searching for begin_date '{begin_date}' in cropped table...")
    
    # Perform OCR on the entire table
    scanner = ocr_utils.TextScanner()
    ocr_success, ocr_data = scanner.get_text_data(cropped_table)
    
    if not ocr_success or not ocr_data or not ocr_data.get('text'):
        return False, None, None, "OCR failed on table"
    
    print(f"[TABLE_UTILS] OCR found {len(ocr_data['text'])} text elements")
    
    # Normalize the target date
    begin_date_str = str(begin_date)
    begin_date_normalized = date_utils.normalize_date(begin_date_str)
    
    # Group OCR results by rows
    rows = group_ocr_by_rows(ocr_data)
    print(f"[TABLE_UTILS] Grouped OCR into {len(rows)} rows")
    
    # Search for matching date in each row
    header_height = 40  # Skip header row
    
    for row_idx, row_data in enumerate(rows):
        row_y_center = row_data['y_center']
        
        # Skip header row
        if row_y_center < header_height:
            continue
        
        # Check if this row contains the begin_date
        row_texts = row_data['texts']
        row_text_combined = ' '.join(row_texts)
        
        # Normalize and check for match
        row_text_normalized = date_utils.normalize_date(row_text_combined)
        
        if begin_date_normalized in row_text_normalized or begin_date_str in row_text_combined:
            print(f"[TABLE_UTILS] ✓ Found matching date in row {row_idx}: '{row_text_combined}'")
            
            # Find the date column
            date_bbox = find_date_bbox_in_row(
                row_data, 
                begin_date_str, 
                begin_date_normalized, 
                column_boundaries
            )
            
            if date_bbox:
                x1, y1, x2, y2 = date_bbox
                click_x_local = (x1 + x2) // 2
                click_y_local = (y1 + y2) // 2
            else:
                # Fallback: use row center
                click_x_local = cropped_table.shape[1] // 2
                click_y_local = row_y_center
            
            # Convert to screen coordinates
            click_x = click_x_local + crop_x
            click_y = click_y_local + crop_y
            
            print(f"[TABLE_UTILS] Click coordinates: local=({click_x_local}, {click_y_local}), "
                  f"screen=({click_x}, {click_y})")
            
            return True, click_x, click_y, f"Date found in row {row_idx}"
    
    print(f"[TABLE_UTILS] ✗ Date '{begin_date}' not found in table")
    return False, None, None, f"Date '{begin_date}' not found"

def extract_table_with_column_splits(
    screenshot: np.ndarray, crop_x: int, crop_y: int,
    crop_width: int, crop_height: int, column_template_path: str,
    match_threshold: float = 0.85 ) -> Tuple[Optional[np.ndarray], List[int]]:
    """
    Extract a table region and detect column boundaries using a template.
    
    This function:
    1. Crops the specified region from the screenshot
    2. Loads the column separator template
    3. Finds all column separators
    4. Calculates column boundaries
    
    Args:
        screenshot: Current screenshot
        crop_x, crop_y: Top-left coordinates of table region
        crop_width, crop_height: Dimensions of table region
        column_template_path: Path to column separator template image
        match_threshold: Minimum confidence for template matching
        
    Returns:
        Tuple of (cropped_table: np.ndarray, column_boundaries: List[int])
        
    Example:
        >>> screenshot = take_screenshot()
        >>> table, boundaries = extract_table_with_column_splits(
        ...     screenshot, 205, 280, 1500, 200, 'column_template.png'
        ... )
        >>> print(f"Found {len(boundaries)} column boundaries")
    """
    
    print("[CV_UTILS] Extracting table and detecting column splits...")
    
    # Validate crop dimensions
    if crop_width <= 0 or crop_height <= 0:
        print(f"[CV_UTILS] ✗ Invalid crop dimensions: {crop_width}x{crop_height}")
        return None, []
    
    # Crop the table region
    cropped_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
    
    if cropped_table is None:
        print(f"[CV_UTILS] ✗ Failed to crop table region")
        return None, []
    
    print(f"[CV_UTILS] ✓ Cropped table: {crop_width}x{crop_height}")
    
    # Load column separator template
    column_template = computer_vision_utils.load_image(column_template_path)
    
    if column_template is None:
        print(f"[CV_UTILS] ⚠ Column template not found, using empty boundaries")
        return cropped_table, []
    
    template_height, template_width = column_template.shape[:2]
    print(f"[CV_UTILS] Column template loaded: {template_width}x{template_height}")
    
    # Find all column separators
    
    separator_matches = find_all_template_matches(
        cropped_table,
        column_template,
        confidence=match_threshold,
        min_distance=10
    )
    
    print(f"[CV_UTILS] Found {len(separator_matches)} column separator(s)")
    
    # Calculate column boundaries

    column_boundaries = calculate_column_boundaries(
        separator_matches,
        template_width,
        crop_width
    )
    
    print(f"[CV_UTILS] Calculated {len(column_boundaries)} column boundaries: {column_boundaries}")
    
    return cropped_table, column_boundaries
    
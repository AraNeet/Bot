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

# Import dependencies
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import column_detection
from src.workflow_module.actions.helpers import date_utils
from src.workflow_module.actions.helpers import row_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner

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
        # Take screenshot
        image = computer_vision_utils.take_screenshot()
        if image is None:
            print("[GET_RESULTS] Screenshot failed")
            return None
        
        # Crop results region (x, y, width, height)
        results_region = computer_vision_utils.crop_image(image, 206, 225, 225, 25)
        if results_region is None:
            print("[GET_RESULTS] Failed to crop results region")
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

def search_second_table_by_date(begin_date: str, crop_x: int, crop_y: int, 
                                crop_width: int, crop_height: int,
                                template_path: Optional[str] = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Search for rows in the second table (within expanded row) by begin_date.
    Uses column separator template to detect columns, then row boundary detection to handle variable height rows.
    Returns all matches.
    
    Args:
        begin_date: Begin date to match (e.g., "01/01/2024" or "2024-01-01")
        crop_x, crop_y: Crop coordinates for the second table region
        crop_width, crop_height: Crop dimensions
        template_path: Optional path to column separator template. 
                      If None, uses default from assets folder.
        
    Returns:
        Tuple of (found: bool, message: str, matches: List[Dict])
        Each match contains: {
            'click_x': int, 'click_y': int,
            'row_top': int, 'row_bottom': int,
            'matched_text': str, 'row_index': int
        }
    """
    try:
        # Convert begin_date to string to handle integers
        begin_date_str = str(begin_date)
        print(f"[SEARCH_SECOND_TABLE] Searching for begin_date: '{begin_date_str}'")
        
        # Load column separator template for second table
        if template_path is None:
            template_path = "src/workflow_module/actions/assets/ColumnLineSecondTable.png"
        template = computer_vision_utils.load_image(template_path)
        if template is None:
            return False, f"Failed to load ColumnLineSecondTable template from {template_path}", []
        
        time.sleep(2)
        # Take screenshot
        image = computer_vision_utils.take_screenshot()
        if image is None:
            return False, "Screenshot failed", []
        
        # Crop to second table region
        cropped_img = computer_vision_utils.crop_image(image, crop_x, crop_y, crop_width, crop_height)
        if cropped_img is None:
            return False, "Crop failed", []
        
        # Store original cropped image dimensions for coordinate conversion
        original_cropped_height, original_cropped_width = cropped_img.shape[:2]
        
        # Detect column separators using template
        print(f"[SEARCH_SECOND_TABLE] Detecting column separators...")
        matches = column_detection.detect_column_separators(cropped_img, template)
        if not matches:
            print(f"[SEARCH_SECOND_TABLE] No column separators found, proceeding with direct OCR")
            using_separated_columns = False
        else:
            print(f"[SEARCH_SECOND_TABLE] Found {len(matches)} column separators")
            
            # Create separated columns image
            separated_columns_img = column_detection.create_separated_columns_image(cropped_img, matches, template.shape[1])
            if separated_columns_img is not None:
                print(f"[SEARCH_SECOND_TABLE] Using separated columns image for OCR")
                cropped_img = separated_columns_img
                using_separated_columns = True
            else:
                print(f"[SEARCH_SECOND_TABLE] Column separation failed, using original cropped image")
                using_separated_columns = False
        
        # Get the actual dimensions of the image used for OCR
        ocr_img_height, ocr_img_width = cropped_img.shape[:2]
        print(f"[SEARCH_SECOND_TABLE] OCR image dimensions: {ocr_img_width}x{ocr_img_height} (original cropped: {original_cropped_width}x{original_cropped_height})")
        
        # Perform OCR on the processed image
        success, data = scanner.get_text_data(cropped_img)
        if not success or not data['text']:
            return False, "OCR failed or no text", []
        
        print(f"[SEARCH_SECOND_TABLE] OCR found {len(data['text'])} text elements")
        
        # Determine row boundaries
        row_boundaries, row_count = row_utils.determine_row_boundaries(
            data['bbox'], 
            data['text'],
            min_row_height=15,
            line_tolerance=5,
            row_gap_tolerance=20
        )
        
        print(f"[SEARCH_SECOND_TABLE] Detected {row_count} rows")
        
        if row_count == 0:
            return False, "No rows detected", []
        
        # Normalize begin_date for matching by removing leading zeros
        # Example: 09/16/2025 → 9/16/2025
        begin_date_normalized = date_utils.normalize_date(begin_date_str)
        print(f"[SEARCH_SECOND_TABLE] Searching for begin_date: '{begin_date_str}' → normalized: '{begin_date_normalized}'")
        
        # Also create a version without separators for flexible matching
        date_normalized = begin_date_normalized.replace('/', '').replace('-', '').replace(' ', '')
        
        # Extract digits from begin_date to help identify date values
        date_digits = re.sub(r'[^\d]', '', begin_date_normalized)
        print(f"[SEARCH_SECOND_TABLE] Date digits: '{date_digits}'")
        
        # Words to exclude (like "begin", "date", "end")
        exclude_words = ['begin', 'date', 'end', 'start', 'from', 'to']
        
        # Search for begin_date in each row (skip first row which is the header)
        all_matches = []
        for row_idx, (row_top, row_bottom) in enumerate(row_boundaries):
            # Skip the first row (header row) - only search data rows
            if row_idx == 0:
                print(f"[SEARCH_SECOND_TABLE] Skipping row {row_idx + 1} (header row)")
                continue
            # Find all texts in this row
            row_texts = []
            row_boxes = []
            for i, bbox in enumerate(data['bbox']):
                x1, y1, x2, y2 = map(int, bbox)
                center_y = (y1 + y2) / 2
                
                # Check if this box is within the row boundaries
                if row_top <= center_y <= row_bottom:
                    row_texts.append(data['text'][i])
                    row_boxes.append(bbox)
            
            # Check if any text in this row matches the begin_date
            row_text_combined = ' '.join(row_texts)
            # Normalize row text for comparison (remove leading zeros too)
            row_text_normalized_with_sep = date_utils.normalize_date(row_text_combined)
            row_text_normalized = row_text_normalized_with_sep.replace('/', '').replace('-', '').replace(' ', '')
            
            # Check if the normalized date is in the normalized row text
            # Also check with separators for more flexible matching
            if date_normalized in row_text_normalized or begin_date_normalized in row_text_normalized_with_sep:
                print(f"[SEARCH_SECOND_TABLE] Found matching row {row_idx + 1}/{row_count}")
                print(f"[SEARCH_SECOND_TABLE] Row text: '{row_text_combined}'")
                print(f"[SEARCH_SECOND_TABLE] Looking for begin_date: '{begin_date_str}' (normalized: '{date_normalized}')")
                
                # Find the actual bbox that contains the begin_date VALUE (not the word "begin" or "date")
                # Prioritize text that contains digits and matches the date
                begin_date_bbox = None
                best_match_score = 0
                
                # First, try to find exact match or closest match that contains digits
                for i, text in enumerate(data['text']):
                    bbox = data['bbox'][i]
                    x1, y1, x2, y2 = map(int, bbox)
                    center_y = (y1 + y2) / 2
                    
                    # Check if this box is in the matching row
                    if row_top <= center_y <= row_bottom:
                        # Normalize OCR text (remove leading zeros too)
                        text_normalized_with_sep = date_utils.normalize_date(text)
                        text_normalized = text_normalized_with_sep.replace('/', '').replace('-', '').replace(' ', '')
                        text_lower = text.lower()
                        
                        # Skip if this is a label word like "begin", "date", etc.
                        if any(exclude_word in text_lower for exclude_word in exclude_words):
                            continue
                        
                        # Check if text contains digits (dates have numbers)
                        text_digits = re.sub(r'[^\d]', '', text)
                        if not text_digits:
                            continue  # Skip text without digits
                        
                        # Check for exact match (with or without separators)
                        if date_normalized == text_normalized or begin_date_normalized == text_normalized_with_sep:
                            begin_date_bbox = (x1, y1, x2, y2)
                            print(f"[SEARCH_SECOND_TABLE] Found exact begin_date match: '{text}' at bbox ({x1}, {y1}, {x2}, {y2})")
                            break
                        elif date_normalized in text_normalized or begin_date_normalized in text_normalized_with_sep:
                            # Partial match - check how many digits match
                            matching_digits = sum(1 for d in date_digits if d in text_digits)
                            if matching_digits > best_match_score:
                                best_match_score = matching_digits
                                begin_date_bbox = (x1, y1, x2, y2)
                                print(f"[SEARCH_SECOND_TABLE] Found partial begin_date match: '{text}' (matched digits: {matching_digits}/{len(date_digits)})")
                
                # If no single box match, try to find the box that contains the most matching digits
                if begin_date_bbox is None:
                    print(f"[SEARCH_SECOND_TABLE] No single box match, searching for best date match...")
                    for i, text in enumerate(data['text']):
                        bbox = data['bbox'][i]
                        x1, y1, x2, y2 = map(int, bbox)
                        center_y = (y1 + y2) / 2
                        
                        if row_top <= center_y <= row_bottom:
                            text_lower = text.lower()
                            
                            # Skip label words
                            if any(exclude_word in text_lower for exclude_word in exclude_words):
                                continue
                            
                            # Check if text contains digits
                            text_digits = re.sub(r'[^\d]', '', text)
                            if not text_digits:
                                continue
                            
                            # Count matching digits
                            matching_digits = sum(1 for d in date_digits if d in text_digits)
                            if matching_digits > best_match_score:
                                best_match_score = matching_digits
                                begin_date_bbox = (x1, y1, x2, y2)
                                print(f"[SEARCH_SECOND_TABLE] Best date match so far: '{text}' (matched digits: {matching_digits}/{len(date_digits)})")
                
                if begin_date_bbox is None:
                    # Fallback: use center of row
                    print(f"[SEARCH_SECOND_TABLE] WARNING: Could not find begin_date bbox, using row center")
                    click_x_ocr = ocr_img_width // 2
                    click_y_ocr = row_top + (row_bottom - row_top) // 2
                else:
                    # Use the exact center of the begin_date bbox (no modification)
                    x1, y1, x2, y2 = begin_date_bbox
                    click_x_ocr = (x1 + x2) // 2  # Center X of the date bbox
                    click_y_ocr = (y1 + y2) // 2  # Center Y of the date bbox
                    print(f"[SEARCH_SECOND_TABLE] Using begin_date bbox center: bbox=({x1}, {y1}, {x2}, {y2}), center=({click_x_ocr}, {click_y_ocr})")
                
                # Convert OCR image coordinates to original cropped image coordinates
                # OCR bbox coordinates are relative to the OCR image (cropped_img or separated_columns_img)
                # We need to convert them to coordinates relative to the original cropped image
                
                # Y coordinates: Height doesn't change between cropped_img and separated_columns_img
                # So Y coordinates are always relative to the original cropped image
                click_y_cropped = int(click_y_ocr)
                
                # X coordinates: Need conversion if using separated columns (width changes)
                if using_separated_columns:
                    # Separated columns image has different width due to padding
                    # Map X coordinate from separated_columns_img back to original cropped_img
                    # Using proportional scaling based on width ratio
                    scale_factor = original_cropped_width / ocr_img_width
                    click_x_cropped = int(click_x_ocr * scale_factor)
                    print(f"[SEARCH_SECOND_TABLE] X coordinate conversion (separated columns): OCR={click_x_ocr}, scale={scale_factor:.4f}, cropped={click_x_cropped}")
                else:
                    # No conversion needed - OCR image is the same as cropped image
                    click_x_cropped = int(click_x_ocr)
                    print(f"[SEARCH_SECOND_TABLE] X coordinate (no conversion needed): {click_x_cropped}")
                
                print(f"[SEARCH_SECOND_TABLE] Coordinates after OCR→Cropped conversion: ({click_x_cropped}, {click_y_cropped})")
                
                # Convert cropped coordinates to screen coordinates
                # Add the crop offset to get absolute screen coordinates
                click_x = click_x_cropped + crop_x
                click_y = click_y_cropped + crop_y
                
                print(f"[SEARCH_SECOND_TABLE] Final screen coordinates: ({click_x}, {click_y})")
                print(f"[SEARCH_SECOND_TABLE] Conversion path: OCR({click_x_ocr}, {click_y_ocr}) → Cropped({click_x_cropped}, {click_y_cropped}) → Screen({click_x}, {click_y})")
                print(f"[SEARCH_SECOND_TABLE] Crop offsets applied: crop_x={crop_x}, crop_y={crop_y}")
                
                match_info = {
                    'click_x': click_x,
                    'click_y': click_y,
                    'row_top': row_top + crop_y,
                    'row_bottom': row_bottom + crop_y,
                    'matched_text': row_text_combined,
                    'row_index': row_idx
                }
                
                all_matches.append(match_info)
        
        if all_matches:
            print(f"[SEARCH_SECOND_TABLE] Found {len(all_matches)} matching rows")
            return True, f"Found {len(all_matches)} matching rows", all_matches
        else:
            return False, f"Begin date '{begin_date_str}' not found in any row", []
        
    except Exception as e:
        return False, f"Error searching second table: {e}", []


# ============================================================================
# TABLE SCROLLING AND ROW POSITIONING
# ============================================================================

def scroll_to_table_top(table_center_x: int, table_center_y: int, 
                        table_crop_x: int, table_crop_y: int, table_crop_width: int) -> None:
    """
    Scroll the table to the top position by looking for 'Network Code' or 'Estimate' text.
    Stops scrolling when either of these texts is found (indicating we're at the top).
    
    Args:
        table_center_x: X coordinate for mouse position during scrolling
        table_center_y: Y coordinate for mouse position during scrolling
        table_crop_x: X coordinate of table crop region
        table_crop_y: Y coordinate of table crop region
        table_crop_width: Width of table crop region
    """
    print(f"[TABLE_UTILS] Scrolling up to beginning (looking for 'Network Code' or 'Estimate')...")
    
    scanner = TextScanner()
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.2)
    
    max_scroll_attempts = 200
    at_top = False
    
    for scroll_num in range(1, max_scroll_attempts + 1):
        pyautogui.scroll(50)  # Positive value scrolls up
        time.sleep(0.05)
        
        check_screenshot = computer_vision_utils.take_screenshot()
        if check_screenshot is not None:
            # Crop the table header region to search for text
            header_region = check_screenshot[table_crop_y:table_crop_y+100, table_crop_x:table_crop_x+table_crop_width]
            
            # Extract text from the header region
            success, extracted_text = scanner.extract_text(header_region)
            
            if success:
                # Check if we found either "Network Code" or "Estimate"
                found_network_code = "network code" in extracted_text.lower()
                found_estimate = "estimate" in extracted_text.lower()
                
                if found_network_code or found_estimate:
                    found_text = []
                    if found_network_code:
                        found_text.append("'Network Code'")
                    if found_estimate:
                        found_text.append("'Estimate'")
                    print(f"[TABLE_UTILS] ✓ Found {' and '.join(found_text)} - reached top position after {scroll_num} scroll(s)")
                    at_top = True
                    break
                elif scroll_num % 10 == 0:
                    print(f"[TABLE_UTILS] Not at top yet (no 'Network Code' or 'Estimate' found), scrolled {scroll_num} times, continuing...")
            elif scroll_num % 10 == 0:
                print(f"[TABLE_UTILS] Warning: OCR extraction failed at scroll {scroll_num}, continuing...")
        else:
            print(f"[TABLE_UTILS] Warning: Failed to take screenshot at scroll {scroll_num}")
    
    if at_top:
        print(f"[TABLE_UTILS] ✓ Successfully scrolled to top of table")
    else:
        print(f"[TABLE_UTILS] Warning: Reached max scroll attempts ({max_scroll_attempts}), assuming at top")


def position_row_in_target_region(click_x: int, click_y: int, 
                                   table_center_x: int, table_center_y: int,
                                   crop_x: int, crop_y: int, crop_width: int, crop_height: int,
                                   template, target_texts, estimate_number: str,
                                   target_region_y: int, target_region_height: int,
                                   scrollbar_check_region: Tuple[int, int, int, int],
                                   scrollbar_confidence: float = 0.95) -> Tuple[bool, str]:
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
        scrollbar_check_region: Region to check for scrollbar end (x, y, width, height)
        scrollbar_confidence: Confidence threshold for scrollbar detection
        
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
    
    # Load end scrollbar template to detect when we can't scroll anymore
    end_scrollbar_template = computer_vision_utils.load_image("src/workflow_module/actions/assets/EndScrollbar.png")
    if end_scrollbar_template is None:
        print(f"[TABLE_UTILS] Warning: EndScrollbar template not found")
    
    pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
    time.sleep(0.2)
    
    max_position_scrolls = 100
    scroll_amount = -20  # Scroll down slowly (negative value)
    
    for scroll_num in range(1, max_position_scrolls + 1):
        pyautogui.scroll(scroll_amount)
        time.sleep(0.05)
        
        check_screenshot = computer_vision_utils.take_screenshot()
        if check_screenshot is None:
            if scroll_num % 10 == 0:
                print(f"[TABLE_UTILS] Warning: Screenshot failed at scroll {scroll_num}")
            continue
        
        # Check if scrollbar is at the end (can't scroll anymore)
        if end_scrollbar_template is not None:
            end_found, _, _ = computer_vision_utils.match_template_in_region(
                check_screenshot, end_scrollbar_template, scrollbar_check_region, confidence=scrollbar_confidence
            )
            
            if end_found:
                print(f"[TABLE_UTILS] ✓ Scrollbar at end position, can't scroll further. Continuing with current position.")
                return True, "Scrollbar at end, continuing with current row position"
        
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
            elif scroll_num % 10 == 0:
                print(f"[TABLE_UTILS] Positioning scroll {scroll_num}: blue row at y={new_blue_center_y}, continuing...")
        elif scroll_num % 10 == 0:
            print(f"[TABLE_UTILS] Warning: Blue row not detected at scroll {scroll_num}, continuing...")
    
    print(f"[TABLE_UTILS] Warning: Reached max positioning scrolls ({max_position_scrolls}), continuing anyway")
    return True, "Reached max positioning scrolls, continuing with current position"


def click_and_position_row(match_info: Dict, table_center_x: int, table_center_y: int,
                           crop_x: int, crop_y: int, crop_width: int, crop_height: int,
                           template, target_texts, estimate_number: str,
                           target_region_y: int, target_region_height: int,
                           scrollbar_check_region: Tuple[int, int, int, int],
                           scrollbar_confidence: float = 0.95) -> Tuple[bool, str]:
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
        scrollbar_check_region: Region to check for scrollbar end (x, y, width, height)
        scrollbar_confidence: Confidence threshold for scrollbar detection
        
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
        target_region_y, target_region_height,
        scrollbar_check_region, scrollbar_confidence
    )
    
    if not position_success:
        print(f"[TABLE_UTILS] Warning: {position_msg}")
    
    return True, f"Row found and clicked! Matched {matched_count}/{len(target_texts)} targets"



#!/usr/bin/env python3
"""
Table Utilities Module

This module provides utilities for working with tables:
- Column separator detection and processing
- Table row searching and matching
- Results count extraction
"""

import cv2
import numpy as np
import re
import time
from typing import Tuple, Dict, Any, Optional, List
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner, match_text_positions

scanner = TextScanner()

# ============================================================================
# DATE UTILITIES
# ============================================================================

def normalize_date(date_str: str) -> str:
    """
    Remove leading zeros from date components for flexible date matching.
    
    Example: 09/16/2025 → 9/16/2025
    
    Args:
        date_str: Date string to normalize
        
    Returns:
        Normalized date string with leading zeros removed
    """
    # Remove leading zeros from each numeric component
    normalized = re.sub(r'\b0+(\d)', r'\1', date_str)
    return normalized.lower()

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
# COLUMN SEPARATOR DETECTION
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

# ============================================================================
# TABLE ROW SEARCHING
# ============================================================================

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
        row_expander_template = computer_vision_utils.load_image("src/workflow_module/actions/assets/RowExpander.png")
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
# ROW BOUNDARY DETECTION FOR VARIABLE HEIGHT ROWS
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

# ============================================================================
# SECOND TABLE SEARCHING (WITHIN EXPANDED ROW)
# ============================================================================

def search_second_table_by_date(begin_date: str, crop_x: int, crop_y: int, 
                                crop_width: int, crop_height: int) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Search for rows in the second table (within expanded row) by begin_date.
    Uses column separator template to detect columns, then row boundary detection to handle variable height rows.
    Returns all matches.
    
    Args:
        begin_date: Begin date to match (e.g., "01/01/2024" or "2024-01-01")
        crop_x, crop_y: Crop coordinates for the second table region
        crop_width, crop_height: Crop dimensions
        
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
        template = computer_vision_utils.load_image("src/workflow_module/actions/assets/ColumnLineSecondTable.png")
        if template is None:
            return False, "Failed to load ColumnLineSecondTable template", []
        
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
        matches = detect_column_separators(cropped_img, template)
        if not matches:
            print(f"[SEARCH_SECOND_TABLE] No column separators found, proceeding with direct OCR")
            using_separated_columns = False
        else:
            print(f"[SEARCH_SECOND_TABLE] Found {len(matches)} column separators")
            
            # Create separated columns image
            separated_columns_img = create_separated_columns_image(cropped_img, matches, template.shape[1])
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
        row_boundaries, row_count = determine_row_boundaries(
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
        begin_date_normalized = normalize_date(begin_date_str)
        print(f"[SEARCH_SECOND_TABLE] Searching for begin_date: '{begin_date_str}' → normalized: '{begin_date_normalized}'")
        
        # Also create a version without separators for flexible matching
        date_normalized = begin_date_normalized.replace('/', '').replace('-', '').replace(' ', '')
        
        # Extract digits from begin_date to help identify date values
        date_digits = re.sub(r'[^\d]', '', begin_date_normalized)
        print(f"[SEARCH_SECOND_TABLE] Date digits: '{date_digits}'")
        
        # Words to exclude (like "begin", "date", "end")
        exclude_words = ['begin', 'date', 'end', 'start', 'from', 'to']
        
        # Search for begin_date in each row
        all_matches = []
        for row_idx, (row_top, row_bottom) in enumerate(row_boundaries):
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
            row_text_normalized_with_sep = normalize_date(row_text_combined)
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
                        text_normalized_with_sep = normalize_date(text)
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
# TABLE BOUNDARY DETECTION (BLACK LINE DETECTION)
# ============================================================================

def detect_table_bottom_line(image: np.ndarray, start_y: int, crop_x: int, 
                             crop_width: int, min_line_thickness: int = 2,
                             dark_threshold: int = 80) -> Optional[int]:
    """
    Detects a horizontal black/dark line below the start position that marks the end of the second table.
    
    Searches from start_y downward to find a horizontal dark line that spans across the crop width.
    This line typically marks the bottom border of the table.
    
    Args:
        image: Full screenshot image (BGR format)
        start_y: Y coordinate to start searching from (top of selected row)
        crop_x: X coordinate of crop region (left edge)
        crop_width: Width of crop region to search within
        min_line_thickness: Minimum thickness of line in pixels to be considered (default: 2)
        dark_threshold: Maximum brightness value (0-255) to consider as "dark" (default: 80)
        
    Returns:
        Y coordinate of the detected line, or None if no line found
    """
    try:
        image_height, image_width = image.shape[:2]
        
        # Validate region bounds
        if start_y < 0 or start_y >= image_height:
            print(f"[DETECT_TABLE_BOTTOM] Invalid start_y: {start_y} (image height: {image_height})")
            return None
        
        # Ensure crop region is within image bounds
        end_x = min(crop_x + crop_width, image_width)
        actual_crop_width = end_x - crop_x
        
        if actual_crop_width <= 0:
            print(f"[DETECT_TABLE_BOTTOM] Invalid crop width: {actual_crop_width}")
            return None
        
        # Search region: from start_y to bottom of image, within crop_x to crop_x+crop_width
        search_start_y = start_y
        search_end_y = image_height
        
        print(f"[DETECT_TABLE_BOTTOM] Searching for dark line from Y={search_start_y} to Y={search_end_y}")
        print(f"[DETECT_TABLE_BOTTOM] Search region: X={crop_x} to X={end_x} (width={actual_crop_width})")
        
        # Crop the search region
        search_region = image[search_start_y:search_end_y, crop_x:end_x]
        
        if search_region.size == 0:
            print(f"[DETECT_TABLE_BOTTOM] Empty search region")
            return None
        
        # Convert to grayscale for easier dark line detection
        gray = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
        
        # Detect dark horizontal lines by:
        # 1. Find rows where most pixels are dark
        # 2. Check if consecutive dark rows form a line of sufficient thickness
        
        dark_line_positions = []
        
        # Scan each row from top to bottom
        for y_offset in range(gray.shape[0]):
            row = gray[y_offset]
            
            # Count how many pixels in this row are dark (below threshold)
            dark_pixel_count = np.sum(row < dark_threshold)
            total_pixels = len(row)
            dark_ratio = dark_pixel_count / total_pixels
            
            # If a significant portion of the row is dark (e.g., >70%), mark it
            if dark_ratio > 0.7:
                absolute_y = search_start_y + y_offset
                dark_line_positions.append(absolute_y)
        
        if not dark_line_positions:
            print(f"[DETECT_TABLE_BOTTOM] No dark line found below Y={start_y}")
            return None
        
        # Group consecutive dark rows into lines
        lines = []
        current_line_start = dark_line_positions[0]
        current_line_end = dark_line_positions[0]
        
        for i in range(1, len(dark_line_positions)):
            if dark_line_positions[i] - current_line_end <= min_line_thickness + 1:
                # Continuation of current line
                current_line_end = dark_line_positions[i]
            else:
                # Gap detected - save current line and start new one
                line_thickness = current_line_end - current_line_start + 1
                if line_thickness >= min_line_thickness:
                    lines.append((current_line_start, current_line_end))
                current_line_start = dark_line_positions[i]
                current_line_end = dark_line_positions[i]
        
        # Don't forget the last line
        line_thickness = current_line_end - current_line_start + 1
        if line_thickness >= min_line_thickness:
            lines.append((current_line_start, current_line_end))
        
        if not lines:
            print(f"[DETECT_TABLE_BOTTOM] No lines found with sufficient thickness (>= {min_line_thickness}px)")
            return None
        
        # Return the Y position of the first (topmost) line's center
        # This is the table bottom border
        first_line_top, first_line_bottom = lines[0]
        first_line_center = (first_line_top + first_line_bottom) // 2
        
        print(f"[DETECT_TABLE_BOTTOM] Found dark line at Y={first_line_center} (line from {first_line_top} to {first_line_bottom}, thickness={first_line_bottom - first_line_top + 1}px)")
        print(f"[DETECT_TABLE_BOTTOM] Total lines detected: {len(lines)}")
        
        return first_line_center
        
    except Exception as e:
        print(f"[DETECT_TABLE_BOTTOM] Error detecting table bottom line: {e}")
        return None


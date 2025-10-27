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
from src.workflow_module.actions_2.helpers import actions
from src.workflow_module.actions_2.helpers import computer_vision_utils
from src.workflow_module.actions_2.helpers.ocr_utils import TextScanner, match_text_positions

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
    Creates separated columns image with filtering.
    
    Processing steps:
    1. Calculate column boundaries from separator positions
    2. Crop all columns
    3. Filter out first column and last 3 columns
    4. Add white padding between columns
    5. Combine into single image
    
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
    
    # Filter columns (remove first and last 3 columns)
    total_columns = len(all_columns)
    print(f"[CREATE_COLUMNS] Filtering columns (total: {total_columns})")
    
    filtered_columns = all_columns
    
    # Remove last 3 columns
    if len(filtered_columns) >= 3:
        filtered_columns = filtered_columns[:-3]
        print(f"[CREATE_COLUMNS] Removed last 3 columns (totals/empty space)")
    else:
        print(f"[CREATE_COLUMNS] Warning: Not enough columns to remove last 3")
    
    if not filtered_columns:
        print("[CREATE_COLUMNS] No columns remaining after filtering")
        return None
    
    print(f"[CREATE_COLUMNS] Keeping {len(filtered_columns)} columns")
    
    # Create white padding
    image_height = source_img.shape[0]
    white_padding = np.full((image_height, padding_width, 3), 255, dtype=np.uint8)
    
    # Combine columns with padding
    final_parts = [filtered_columns[0]]
    for next_column in filtered_columns[1:]:
        final_parts.append(white_padding)
        final_parts.append(next_column)
    
    separated_columns_image = np.hstack(final_parts)
    
    final_width = separated_columns_image.shape[1]
    print(f"[CREATE_COLUMNS] Created separated columns image: {final_width}px wide, {len(filtered_columns)} columns")
    
    if debug:
        cv2.imwrite('separated_columns.png', separated_columns_image)
        print("[CREATE_COLUMNS] Saved debug image: 'separated_columns.png'")
    
    return separated_columns_image

# ============================================================================
# TABLE ROW SEARCHING
# ============================================================================

def search_current_view(target_texts: List[str], deal_number: str, crop_x: int, crop_y: int, 
                       crop_width: int, crop_height: int, template) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Search for target row in the current visible table view.
    
    Args:
        target_texts: List of texts to search for [deal_number, advertiser_name, begin_date, end_date]
        deal_number: Deal number to find
        crop_x, crop_y: Crop coordinates
        crop_width, crop_height: Crop dimensions
        template: Column separator template
        
    Returns:
        Tuple of (found: bool, message: str, match_info: Optional[Dict])
        match_info contains: {
            'click_x': int, 'click_y': int, 'button': str,
            'matched_count': int, 'matched_texts': List[str],
            'all_texts': List[str]
        }
    """
    try:
        # Select a row within the separator region
        select_row_x = crop_x + crop_width // 2
        select_row_y = crop_y + 100
        
        print(f"[SEARCH_VIEW] Clicking row at ({select_row_x}, {select_row_y}) to select for separator detection")
        success, msg = actions.click_at_position(select_row_x, select_row_y, clicks=1, button='left')
        if success:
            time.sleep(0.3)  # Wait for row selection
        
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
        
        # Check if deal_number exists
        if not (positions and deal_number and any(deal_number.lower() in text.lower() for text in data['text'] if text)):
            return False, "Deal number not found in view", None
        
        # Count how many target texts were matched
        matched_texts = []
        for target in target_texts:
            if target and any(target.lower() in text.lower() for text in data['text'] if text):
                matched_texts.append(target)
        
        matched_count = len(matched_texts)
        print(f"[SEARCH_VIEW] Matched {matched_count}/{len(target_texts)} target texts: {matched_texts}")
        
        # Found the row - now find RowExpander
        x, y, w, h = positions[0]
        screen_x = x + crop_x
        screen_y = y + crop_y
        
        # Load RowExpander template
        row_expander_template = computer_vision_utils.load_image("src/workflow_module/actions_2/assets/RowExpander.png")
        if row_expander_template is None:
            return False, "Failed to load RowExpander template", None
        
        # Define search region along X axis of deal number
        search_region_x = crop_x
        search_region_y = screen_y - h
        search_region_width = image.shape[1] - crop_x
        search_region_height = h * 3
        search_region = (search_region_x, search_region_y, search_region_width, search_region_height)
        
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
            click_x, click_y = expander_position
            print(f"[SEARCH_VIEW] Found RowExpander at ({click_x}, {click_y}) with confidence {confidence:.2f}")
            match_info['click_x'] = click_x
            match_info['click_y'] = click_y
            match_info['button'] = 'left'
            return True, f"Row found with RowExpander at ({click_x}, {click_y})", match_info
        else:
            # Fallback to deal_number position
            click_x = screen_x + w // 2 - 20
            click_y = screen_y + h // 2
            print(f"[SEARCH_VIEW] RowExpander not found, using deal_number position ({click_x}, {click_y})")
            match_info['click_x'] = click_x
            match_info['click_y'] = click_y
            match_info['button'] = 'right'
            return True, f"Row found at deal_number position ({click_x}, {click_y})", match_info
        
    except Exception as e:
        return False, f"Error searching view: {e}", None


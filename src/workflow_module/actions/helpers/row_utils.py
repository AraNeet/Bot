#!/usr/bin/env python3
"""
Row Utilities Module

This module provides utilities for working with table rows:
- Row boundary detection for variable height rows
- Current view row searching
"""

import re
import time
from typing import Tuple, Dict, Any, Optional, List
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import column_detection
from src.workflow_module.actions.helpers.ocr_utils import TextScanner, match_text_positions

scanner = TextScanner()


# ============================================================================
# ROW BOUNDARY DETECTION
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
# ROW SEARCHING
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
        
        matches = column_detection.detect_column_separators(cropped_img, template)
        if not matches:
            return False, "No separators found", None
        
        separated_columns_img = column_detection.create_separated_columns_image(cropped_img, matches, template.shape[1])
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


#!/usr/bin/env python3
"""
Helper functions for Step 08: Open Multinetwork Row by Date

This module contains utility functions for:
- Template matching
- Column boundary detection
- OCR row grouping
- Date searching in tables
"""

import cv2
import numpy as np
import re
import time
import pyautogui
from typing import List, Tuple, Dict, Any, Optional
# Import dependencies
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.computer_vision_utils import find_blue_highlighted_row, take_screenshot
from src.workflow_module.actions.helpers import ocr_utils

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
    # Step 1: Get template dimensions
    template_height, template_width = template_img.shape[:2]
    
    # Step 2: Create match heatmap using template matching
    match_heatmap = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    matches = []
    
    # Step 3: Iteratively find all matches above threshold
    while True:
        # Step 3a: Find best remaining match
        min_val, max_confidence, min_loc, best_position = cv2.minMaxLoc(match_heatmap)
        
        # Step 3b: Stop if below threshold
        if max_confidence < confidence:
            break
        
        # Step 3c: Record this match
        matches.append((best_position, max_confidence))
        
        # Step 3d: Calculate mask dimensions
        mask_height = max(template_height, min_distance)
        mask_width = max(template_width, min_distance)
        
        # Step 3e: Calculate mask bounds
        y_start = max(0, best_position[1] - mask_height // 2)
        y_end = min(match_heatmap.shape[0], best_position[1] + mask_height // 2)
        x_start = max(0, best_position[0] - mask_width // 2)
        x_end = min(match_heatmap.shape[1], best_position[0] + mask_width // 2)
        
        # Step 3f: Mask nearby area to prevent duplicates
        match_heatmap[y_start:y_end, x_start:x_end] = 0
    
    return matches

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
    # Step 1: Validate input
    if not ocr_data or not ocr_data.get('text'):
        return []
    
    # Step 2: Create list of elements with y_center, text, and bbox
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
    
    # Step 3: Sort elements by Y coordinate
    elements.sort(key=lambda e: e['y_center'])
    
    # Step 4: Group elements into rows based on Y proximity
    rows = []
    current_row = None
    
    for elem in elements:
        if current_row is None:
            # Step 4a: Start first row
            current_row = {
                'y_center': elem['y_center'],
                'texts': [elem['text']],
                'bboxes': [elem['bbox']]
            }
        else:
            # Step 4b: Check if within tolerance of current row
            if abs(elem['y_center'] - current_row['y_center']) <= y_tolerance:
                # Add to current row
                current_row['texts'].append(elem['text'])
                current_row['bboxes'].append(elem['bbox'])
            else:
                # Step 4c: Start new row
                rows.append(current_row)
                current_row = {
                    'y_center': elem['y_center'],
                    'texts': [elem['text']],
                    'bboxes': [elem['bbox']]
                }
    
    # Step 5: Add last row
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
    for i, text in enumerate(row_data['texts']):
        text_normalized = normalize_date(text)
        
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
    print(f"[08_HELPERS] Searching for begin_date '{begin_date}' in cropped table...")
    
    # Step 1: Perform OCR on the entire table
    scanner = ocr_utils.TextScanner()
    ocr_success, ocr_data = scanner.get_text_data(cropped_table)
    
    # Step 2: Validate OCR results
    if not ocr_success or not ocr_data or not ocr_data.get('text'):
        return False, None, None, "OCR failed on table"
    
    print(f"[08_HELPERS] OCR found {len(ocr_data['text'])} text elements")
    
    # Step 3: Normalize the target date
    begin_date_str = str(begin_date)
    begin_date_normalized = normalize_date(begin_date_str)
    
    # Step 4: Group OCR results by rows
    rows = group_ocr_by_rows(ocr_data)
    print(f"[08_HELPERS] Grouped OCR into {len(rows)} rows")
    
    # Step 5: Search for matching date in each row
    header_height = 40  # Skip header row
    
    for row_idx, row_data in enumerate(rows):
        row_y_center = row_data['y_center']
        
        # Step 5a: Skip header row
        if row_y_center < header_height:
            continue
        
        # Step 5b: Get row texts and combine
        row_texts = row_data['texts']
        row_text_combined = ' '.join(row_texts)
        
        # Step 5c: Normalize and check for match
        row_text_normalized = normalize_date(row_text_combined)
        
        if begin_date_normalized in row_text_normalized or begin_date_str in row_text_combined:
            print(f"[08_HELPERS] ✓ Found matching date in row {row_idx}: '{row_text_combined}'")
            
            # Step 5d: Find the date column bounding box
            date_bbox = find_date_bbox_in_row(
                row_data, 
                begin_date_str, 
                begin_date_normalized, 
                column_boundaries
            )
            
            # Step 5e: Calculate click coordinates
            if date_bbox:
                x1, y1, x2, y2 = date_bbox
                click_x_local = (x1 + x2) // 2
                click_y_local = (y1 + y2) // 2
            else:
                # Fallback: use row center
                click_x_local = cropped_table.shape[1] // 2
                click_y_local = row_y_center
            
            # Step 5f: Convert to screen coordinates
            click_x = click_x_local + crop_x
            click_y = click_y_local + crop_y
            
            print(f"[08_HELPERS] Click coordinates: local=({click_x_local}, {click_y_local}), "
                  f"screen=({click_x}, {click_y})")
            
            return True, click_x, click_y, f"Date found in row {row_idx}"
    
    # Step 6: Return failure if date not found
    print(f"[08_HELPERS] ✗ Date '{begin_date}' not found in table")
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
    
    print("[08_HELPERS] Extracting table and detecting column splits...")
    
    # Step 1: Validate crop dimensions
    if crop_width <= 0 or crop_height <= 0:
        print(f"[08_HELPERS] ✗ Invalid crop dimensions: {crop_width}x{crop_height}")
        return None, []
    
    # Step 2: Crop the table region
    cropped_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
    
    if cropped_table is None:
        print(f"[08_HELPERS] ✗ Failed to crop table region")
        return None, []
    
    print(f"[08_HELPERS] ✓ Cropped table: {crop_width}x{crop_height}")
    
    # Step 3: Load column separator template
    column_template = computer_vision_utils.load_image(column_template_path)
    
    if column_template is None:
        print(f"[08_HELPERS] ⚠ Column template not found, using empty boundaries")
        return cropped_table, []
    
    template_height, template_width = column_template.shape[:2]
    print(f"[08_HELPERS] Column template loaded: {template_width}x{template_height}")
    
    # Step 4: Find all column separators via template matching
    separator_matches = find_all_template_matches(
        cropped_table,
        column_template,
        confidence=match_threshold,
        min_distance=10
    )
    
    print(f"[08_HELPERS] Found {len(separator_matches)} column separator(s)")
    
    # Step 5: Calculate column boundaries from separator positions
    column_boundaries = calculate_column_boundaries(
        separator_matches,
        template_width,
        crop_width
    )
    
    print(f"[08_HELPERS] Calculated {len(column_boundaries)} column boundaries: {column_boundaries}")
    
    # Step 6: Return cropped table and column boundaries
    return cropped_table, column_boundaries

def detect_blue_highlighted_expanded_row(screenshot: np.ndarray, exclude_bottom_pixels: int = 100) -> Tuple[bool, Optional[Dict[str, int]]]:
    """
    Detect the blue highlighted expanded row in the first table.
    
    This function identifies an expanded row by detecting blue color regions.
    The expanded row contains nested content (second table) inside it.
    
    Args:
        screenshot: Current screenshot as numpy array
        exclude_bottom_pixels: Number of pixels to exclude from bottom (taskbar area)
        
    Returns:
        Tuple of (found: bool, row_info: Optional[Dict])
        row_info contains: {'x': int, 'y': int, 'width': int, 'height': int}
        
    Example:
        >>> screenshot = take_screenshot()
        >>> found, info = detect_blue_highlighted_expanded_row(screenshot)
        >>> if found:
        ...     print(f"Blue row at ({info['x']}, {info['y']})")
    """
    print("[08_HELPERS] Detecting blue highlighted expanded row...")
    
    found, row_info_data = find_blue_highlighted_row(screenshot)
    
    if not found or row_info_data is None:
        print("[08_HELPERS] ✗ Blue highlighted row not found")
        return False, None
    
    x = row_info_data['x']
    y = row_info_data['y']
    width = row_info_data['width']
    height = row_info_data['height']
    
    row_info = {
        'x': x,
        'y': y,
        'width': width,
        'height': height
    }
    
    print(f"[08_HELPERS] ✓ Found blue row at ({x}, {y}) with size {width}x{height}")
    
    return True, row_info

def calculate_crop_region_from_expanded_row(screenshot: np.ndarray, blue_row_info: Optional[Dict[str, int]]) -> Tuple[int, int, int, int]:
    """
    Calculate the crop region to capture the highlighted row AND the nested table below it.
    
    The color detection only finds the highlighted ROW HEADER (yellow/gold, ~40-50px tall).
    The nested second table below it has a WHITE/GRAY background, so it's not detected.
    
    We need to extend the crop region downward to include:
    - The highlighted row header (~40-50px)
    - The nested second table below (~80-150px depending on number of rows)
    
    Args:
        screenshot: Current screenshot
        blue_row_info: Information about the highlighted row header
                      Dict with keys: 'x', 'y', 'width', 'height'
        
    Returns:
        Tuple of (crop_x, crop_y, crop_width, crop_height)
        
    Example:
        >>> found, row_info = detect_blue_highlighted_expanded_row(screenshot)
        >>> if found:
        ...     x, y, w, h = calculate_crop_region_from_expanded_row(screenshot, row_info)
        ...     cropped = screenshot[y:y+h, x:x+w]
    """
    print("[08_HELPERS] Calculating crop region for expanded row area...")
    
    # Step 1: Get screen dimensions
    screen_height, screen_width = screenshot.shape[:2]
    
    # Step 2: Define extension height for nested table
    # The nested table has: header row (~25px) + 1-5 data rows (~25px each)
    NESTED_TABLE_EXTENSION = 120  # Conservative estimate to capture nested table
    
    # Step 3: Calculate crop region based on blue row info
    if blue_row_info:
        # Step 3a: Extract row position and dimensions
        crop_x = blue_row_info['x']
        crop_y = blue_row_info['y']
        crop_width = blue_row_info['width']
        header_height = blue_row_info['height']
        
        print(f"[08_HELPERS] Highlighted row header detected:")
        print(f"[08_HELPERS]   Position: x={crop_x}, y={crop_y}")
        print(f"[08_HELPERS]   Header size: w={crop_width}, h={header_height}")
        
        # Step 3b: Extend crop height if header is small
        if header_height < 80:
            # Extend to capture nested second table below the header
            crop_height = header_height + NESTED_TABLE_EXTENSION
            print(f"[08_HELPERS] ✓ Extending crop to include nested table:")
            print(f"[08_HELPERS]   Header height: {header_height}px")
            print(f"[08_HELPERS]   Extension for nested table: {NESTED_TABLE_EXTENSION}px")
            print(f"[08_HELPERS]   Total crop height: {crop_height}px")
        else:
            # Step 3c: Header is already large enough
            crop_height = header_height
            print(f"[08_HELPERS] ✓ Using header dimensions (already large enough)")
    else:
        # Step 4: Fallback if highlighted row not detected
        crop_x = 205
        crop_y = 230
        crop_width = 1500
        crop_height = 200
        print(f"[08_HELPERS] ⚠ Highlighted row not found, using defaults:")
        print(f"[08_HELPERS]   Position: x={crop_x}, y={crop_y}")
        print(f"[08_HELPERS]   Size: w={crop_width}, h={crop_height}")
    
    # Step 5: Ensure crop region is within screen bounds
    if crop_x + crop_width > screen_width:
        crop_width = screen_width - crop_x
        print(f"[08_HELPERS]   Adjusted width to {crop_width} (screen bounds)")
    
    if crop_y + crop_height > screen_height:
        crop_height = screen_height - crop_y
        print(f"[08_HELPERS]   Adjusted height to {crop_height} (screen bounds)")
    
    # Step 6: Return final crop region
    print(f"[08_HELPERS] Final crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
    print(f"[08_HELPERS] This captures the header row + nested second table below")
    
    return crop_x, crop_y, crop_width, crop_height

def visualize_column_splits_in_table( table_img: np.ndarray, column_boundaries: List[int], save_path: Optional[str] = None ) -> np.ndarray:
    """
    Visualize column boundaries on a table image.
    
    Draws vertical lines at each column boundary with alternating colors.
    
    Args:
        table_img: Table image to annotate
        column_boundaries: List of column boundary x-coordinates
        save_path: Optional path to save the annotated image
        
    Returns:
        Annotated image with column boundaries drawn
        
    Example:
        >>> table = cv2.imread('table.png')
        >>> boundaries = [0, 100, 200, 300]
        >>> annotated = visualize_column_splits_in_table(table, boundaries, 'output.png')
    """
    print(f"[08_HELPERS] Visualizing {len(column_boundaries)} column splits...")
    
    annotated = table_img.copy()
    table_height = table_img.shape[0]
    
    # Define colors for alternating columns
    colors = [
        (255, 0, 0),    # Blue
        (0, 255, 0),    # Green
        (0, 0, 255),    # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
    ]
    
    # Draw vertical lines at each boundary
    for i, x_pos in enumerate(column_boundaries):
        color = colors[i % len(colors)]
        cv2.line(annotated, (x_pos, 0), (x_pos, table_height), color, 2)
        
        # Add label at top
        cv2.putText(
            annotated,
            f"Col {i}",
            (x_pos + 5, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1
        )
    
    if save_path:
        cv2.imwrite(save_path, annotated)
        print(f"[08_HELPERS] ✓ Saved column visualization to {save_path}")
    
    return annotated

def execute_double_click_at_position(
    click_x: int, click_y: int, screenshot: np.ndarray,
    save_path_before: Optional[str] = None, save_path_after: Optional[str] = None ) -> Tuple[bool, str]:
    """
    Execute a double-click at the specified screen coordinates.
    
    This function:
    1. Visualizes the click position (optional)
    2. Moves the mouse to the position
    3. Performs a double-click
    4. Captures the result (optional)
    
    Args:
        click_x, click_y: Screen coordinates to click
        screenshot: Current screenshot for visualization
        save_path_before: Optional path to save annotated screenshot before click
        save_path_after: Optional path to save screenshot after click
        
    Returns:
        Tuple of (success: bool, message: str)
        
    Example:
        >>> screenshot = take_screenshot()
        >>> success, msg = execute_double_click_at_position(
        ...     500, 300, screenshot, 'before.png', 'after.png'
        ... )
        >>> print(msg)
    """
    print(f"[08_HELPERS] Executing double-click at ({click_x}, {click_y})...")
    
    # Visualize click position (if save path provided)
    if save_path_before:
        annotated = screenshot.copy()
        # Draw crosshair
        cv2.drawMarker(
            annotated,
            (click_x, click_y),
            (0, 255, 0),  # Green
            cv2.MARKER_CROSS,
            30,
            2
        )
        # Draw circle
        cv2.circle(annotated, (click_x, click_y), 15, (0, 255, 0), 2)
        # Add label
        cv2.putText(
            annotated,
            f"Click: ({click_x}, {click_y})",
            (click_x + 20, click_y - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )
        cv2.imwrite(save_path_before, annotated)
        print(f"[08_HELPERS] Saved pre-click visualization to {save_path_before}")
    
    # Move mouse and double-click
    pyautogui.moveTo(click_x, click_y, duration=0.2)
    time.sleep(0.2)
    pyautogui.doubleClick()
    print(f"[08_HELPERS] ✓ Double-click executed at ({click_x}, {click_y})")
    
    # Wait and capture result (if save path provided)
    if save_path_after:
        time.sleep(0.5)
        post_click_screenshot = take_screenshot()
        if post_click_screenshot is not None:
            cv2.imwrite(save_path_after, post_click_screenshot)
            print(f"[08_HELPERS] Saved post-click screenshot to {save_path_after}")
    
    return True, f"Double-click completed at ({click_x}, {click_y})"


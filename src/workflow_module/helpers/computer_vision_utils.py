#!/usr/bin/env python3
"""
Computer Vision Helper Module

This module provides basic OpenCV functionality for image processing,
screenshot capture, and visual verification operations.

Core Functions:
- take_screenshot: Capture current screen state
- save_screenshot: Save screenshot to file
- load_image: Load image from file
- convert_color: Convert between color spaces

This module focuses on low-level CV operations that other modules can build upon.
"""

import cv2
import numpy as np
import pyautogui
from typing import Optional, Tuple, Dict
from datetime import datetime
from pathlib import Path


def take_screenshot() -> Optional[np.ndarray]:
    """
    Capture a screenshot of the entire screen.
    
    Returns:
        Screenshot as numpy array in BGR format (OpenCV standard), or None if failed
        
    Example:
        screenshot = take_screenshot()
        if screenshot is not None:
            print(f"Screenshot captured: {screenshot.shape}")
    """
    try:
        # Capture screenshot using pyautogui
        screenshot = pyautogui.screenshot()
        
        # Convert from PIL Image to numpy array
        screenshot_np = np.array(screenshot)
        
        # Convert from RGB (PIL format) to BGR (OpenCV format)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        
        print(f"[CV] Screenshot captured: {screenshot_bgr.shape[1]}x{screenshot_bgr.shape[0]}")
        return screenshot_bgr
        
    except Exception as e:
        print(f"[CV ERROR] Failed to take screenshot: {e}")
        return None

def save_screenshot(screenshot: np.ndarray, 
                   filename: Optional[str] = None,
                   output_dir: str = "screenshots") -> Tuple[bool, str]:
    """
    Save a screenshot to file.
    
    Args:
        screenshot: Screenshot image as numpy array
        filename: Optional custom filename. If None, generates timestamp-based name
        output_dir: Directory to save screenshots in
        
    Returns:
        Tuple of (success: bool, filepath or error_message)
        
    Example:
        screenshot = take_screenshot()
        success, filepath = save_screenshot(screenshot)
        if success:
            print(f"Saved to: {filepath}")
    """
    try:
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Ensure filename has .png extension
        if not filename.endswith('.png'):
            filename += '.png'
        
        # Full file path
        filepath = output_path / filename
        
        # Save the image
        cv2.imwrite(str(filepath), screenshot)
        
        print(f"[CV] Screenshot saved: {filepath}")
        return True, str(filepath)
        
    except Exception as e:
        error_msg = f"Failed to save screenshot: {e}"
        print(f"[CV ERROR] {error_msg}")
        return False, error_msg

def load_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load an image from file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Image as numpy array in BGR format, or None if failed
        
    Example:
        image = load_image("template.png")
        if image is not None:
            print(f"Image loaded: {image.shape}")
    """
    try:
        # Check if file exists
        if not Path(image_path).exists():
            print(f"[CV ERROR] Image file not found: {image_path}")
            return None
        
        # Load image
        image = cv2.imread(image_path)
        
        if image is None:
            print(f"[CV ERROR] Failed to load image: {image_path}")
            return None
        
        print(f"[CV] Image loaded: {image.shape[1]}x{image.shape[0]} from {image_path}")
        return image
        
    except Exception as e:
        print(f"[CV ERROR] Exception loading image: {e}")
        return None

def crop_image(image: np.ndarray, 
              x: int, y: int, 
              width: int, height: int,
              preprocess_for_ocr: bool = False) -> Optional[np.ndarray]:
    """
    Crop a region from an image, with optional preprocessing for OCR.
    
    Args:
        image: Input image as numpy array
        x: X-coordinate of top-left corner
        y: Y-coordinate of top-left corner
        width: Width of crop region
        height: Height of crop region
        preprocess_for_ocr: If True, apply OCR preprocessing after cropping
        
    Returns:
        Cropped (and optionally preprocessed) image, or None if failed
        
    Example:
        # Crop with preprocessing
        cropped = crop_image(screenshot, 0, 0, 200, 200, preprocess_for_ocr=True)
    """
    try:
        # Validate coordinates
        img_height, img_width = image.shape[:2]
        
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            print(f"[CV ERROR] Invalid crop coordinates")
            return None
        
        if x + width > img_width or y + height > img_height:
            print(f"[CV ERROR] Crop region exceeds image bounds")
            return None
        
        # Crop using numpy slicing
        cropped = image[y:y+height, x:x+width]
        
        print(f"[CV] Image cropped: region ({x},{y},{width},{height})")
        
        if preprocess_for_ocr:
            cropped = preprocess_image_for_ocr(cropped)
            if cropped is None:
                return None
            print(f"[CV] Applied OCR preprocessing to cropped image")
        
        return cropped
        
    except Exception as e:
        print(f"[CV ERROR] Crop failed: {e}")
        return None

def preprocess_image_for_ocr(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Preprocess an image for OCR to remove artifacts like cursors and underlines.
    
    Args:
        image: Input image to preprocess
        
    Returns:
        Preprocessed image or None if failed
    """
    try:
        if image is None:
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to binarize the image
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Apply morphological operations to remove small artifacts (e.g., cursor)
        kernel = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Dilate to enhance text
        dilated = cv2.dilate(cleaned, kernel, iterations=1)
        
        return dilated
        
    except Exception as e:
        print(f"[CV ERROR] Failed to preprocess image for OCR: {e}")
        return None

def match_template_in_region(screenshot: np.ndarray,
                             template: np.ndarray,
                             region: Tuple[int, int, int, int],
                             confidence: float = 0.8) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
    """
    Find a template within a specific region of a screenshot.
    
    Uses template matching to locate a template image within a defined region.
    Returns whether the template was found and its confidence score.
    
    Args:
        screenshot: Screenshot image as numpy array
        template: Template image to search for
        region: Region as (x, y, width, height) tuple
        confidence: Minimum confidence threshold (0-1)
        
    Returns:
        Tuple of (found: bool, confidence_score: float, position: Optional[Tuple[int, int]])
        Position is (center_x, center_y) in global coordinates if found
        
    Example:
        screenshot = take_screenshot()
        template = load_image('assets/button.png')
        region = (0, 0, 200, 200)  # Top-left corner
        
        found, score, position = match_template_in_region(
            screenshot, template, region, confidence=0.8
        )
        
        if found:
            print(f"Template found at {position} with confidence {score:.2f}")
    """
    try:
        x, y, width, height = region
        
        # Validate region bounds
        screen_height, screen_width = screenshot.shape[:2]
        if x < 0 or y < 0 or x + width > screen_width or y + height > screen_height:
            print(f"[CV ERROR] Region out of bounds: ({x}, {y}, {width}, {height})")
            return False, 0.0, None
        
        # Crop region from screenshot
        region_img = crop_image(screenshot, x, y, width, height)
        if region_img is None:
            print(f"[CV ERROR] Failed to crop region for template matching")
            return False, 0.0, None
        
        # Perform template matching
        result = cv2.matchTemplate(region_img, template, cv2.TM_CCOEFF_NORMED)
        
        # Get best match
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Check if confidence threshold met
        if max_val >= confidence:
            # Calculate center position in region coordinates
            template_height, template_width = template.shape[:2]
            center_x = max_loc[0] + template_width // 2
            center_y = max_loc[1] + template_height // 2
            
            # Convert to global coordinates
            global_x = x + center_x
            global_y = y + center_y
            
            print(f"[CV] Template found in region with confidence {max_val:.2f}")
            print(f"[CV] Position: ({global_x}, {global_y})")
            return True, max_val, (global_x, global_y)
        else:
            print(f"[CV] Template not found in region (confidence {max_val:.2f} < {confidence})")
            return False, max_val, None
            
    except Exception as e:
        print(f"[CV ERROR] Template matching failed: {e}")
        return False, 0.0, None

def find_template_in_region(screenshot: np.ndarray,
                           template_path: str,
                           region: Tuple[int, int, int, int],
                           confidence: float = 0.8) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
    """
    Find a template image within a specific region of a screenshot.
    
    Loads a template from file and searches for it within the specified region.
    Returns whether the template was found, confidence score, and position.
    
    Args:
        screenshot: Screenshot image as numpy array
        template_path: Path to the template image file
        region: Region as (x, y, width, height) tuple
        confidence: Minimum confidence threshold (0-1)
        
    Returns:
        Tuple of (found: bool, confidence_score: float, position: Optional[Tuple[int, int]])
        Position is (center_x, center_y) in global coordinates if found
        
    Example:
        screenshot = take_screenshot()
        region = (94, 46, 74, 72)  # (x, y, width, height)
        
        found, score, position = find_template_in_region(
            screenshot, 'assets/multi_network_Icon.png', region, confidence=0.8
        )
        
        if found:
            print(f"Template found at {position} with confidence {score:.2f}")
    """
    try:
        # Load template image
        template = load_image(template_path)
        if template is None:
            print(f"[CV ERROR] Failed to load template: {template_path}")
            return False, 0.0, None
        
        # Use existing match_template_in_region function
        return match_template_in_region(screenshot, template, region, confidence)
        
    except Exception as e:
        print(f"[CV ERROR] Template finding failed: {e}")
        return False, 0.0, None
    
def detect_column_separators(source_img, template_img, match_threshold=0.9, mask_size_factor=0.9, debug=False):
    """
    Detects ALL column separator positions by template matching.
    
    FLOW:
    1. Creates match heatmap using TM_CCOEFF_NORMED
    2. Finds ALL peaks above threshold (one by one)
    3. Masks nearby maxima to get UNIQUE matches only
    4. Prints details if debug=True
    
    RETURNS: List of [(x,y_position, confidence_score)] tuples
    """
    # Get template dimensions
    template_height, template_width = template_img.shape[:2]
    
    # Create match heatmap
    match_heatmap = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
    
    column_separator_positions = []  # List of (x_position, y_position, confidence)
    
    while True:
        # Find brightest remaining match
        min_val, max_confidence, min_loc, best_match_position = cv2.minMaxLoc(match_heatmap)
        
        # Stop if below threshold
        if max_confidence < match_threshold:
            break
        
        # Record this column separator
        column_separator_positions.append((best_match_position, max_confidence))
        
        # MASK nearby maxima to prevent duplicates
        mask_height = int(template_height * mask_size_factor)
        mask_width = int(template_width * mask_size_factor)
        
        y_start = max(0, best_match_position[1] - mask_height // 2)
        y_end = min(match_heatmap.shape[0], best_match_position[1] + mask_height // 2)
        x_start = max(0, best_match_position[0] - mask_width // 2)
        x_end = min(match_heatmap.shape[1], best_match_position[0] + mask_width // 2)
        
        # FLATTEN this area - no more fake matches here!
        match_heatmap[y_start:y_end, x_start:x_end] = 0
    
    # Debug: Show what we found
    if debug:
        if column_separator_positions:
            print(f"Found {len(column_separator_positions)} column separators (threshold: {match_threshold}):")
            for i, (position, confidence) in enumerate(column_separator_positions, 1):
                print(f"  Column {i}: x={position[0]}, y={position[1]}, Confidence={confidence:.3f}")
        else:
            print(f"No column separators found above threshold {match_threshold}")
    
    return column_separator_positions

def create_separated_columns_image(source_img, column_separator_positions, template_width, 
                                   padding_width=10, debug=False):
    """
    **SMART 5-STEP MAGIC**: Creates separated columns + FILTERS OUT JUNK COLUMNS!
    
    FILTERING RULES (NEW!):
    1. REMOVE: Column LEFT of FIRST separator (usually UI/headers)
    2. REMOVE: LAST 2 columns (usually totals/empty space)
    
    STEP-BY-STEP:
    1. Calculate ALL column boundaries
    2. Crop ALL columns  
    3. FILTER: Remove 1st + last 2 columns
    4. Add white padding between REMAINING columns
    5. Combine into ONE wide image
    
    INPUT: 
        - source_img: Your cropped image
        - column_separator_positions: List of [((x, y), score)]
        - template_width: Width of your ColumnLine.png
    
    RETURNS: Filtered separated columns image
    """
    
    if not column_separator_positions:
        if debug:
            print(" No column separators found!")
        return None
    
    # ===========================================
    # STEP 1: CALCULATE ALL COLUMN BOUNDARIES
    # ===========================================
    print(f" Calculating boundaries from {len(column_separator_positions)} separators...")
    
    column_split_positions = []
    for position in column_separator_positions:
        x_position = position[0]
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    unique_split_positions = sorted(set(column_split_positions))
    image_width = source_img.shape[1]
    all_column_boundaries = [0] + unique_split_positions + [image_width]
    
    if debug:
        print(f"   ALL Boundaries: {all_column_boundaries}")

    print(f" Cropping {len(all_column_boundaries)-1} TOTAL columns...")
    
    all_columns = []
    for column_index in range(len(all_column_boundaries) - 1):
        left_edge = all_column_boundaries[column_index]
        right_edge = all_column_boundaries[column_index + 1]
        single_column = source_img[:, left_edge:right_edge]
        all_columns.append(single_column)
        
        if debug:
            print(f"   TOTAL Column {column_index+1}: pixels {left_edge}→{right_edge} (width: {right_edge-left_edge}px)")
    
    if not all_columns:
        return None

    print(" **Unsused Columns**: Removing junk columns...")
    
    total_columns = len(all_columns)
    print(f"   Total columns before filtering: {total_columns}")

    filtered_columns = all_columns[1:]  # Skip index 0
    print(f"   Removed Column 1 (UI/Headers)")
    
    if len(filtered_columns) >= 3:
        filtered_columns = filtered_columns[:-3]  # Remove last 2
        print(f"   Removed Columns {total_columns-1} & {total_columns} (Totals/Empty)")
    else:
        print(f"   Not enough columns to remove last 2!")
    
    columns_to_keep = filtered_columns
    
    print(f"   KEEPING {len(columns_to_keep)} CLEAN COLUMNS!")
    
    if not columns_to_keep:
        if debug:
            print("❌ No columns left after filtering!")
        return None

    print("Creating white padding...")
    image_height = source_img.shape[0]
    white_padding = np.full((image_height, padding_width, 3), 255, dtype=np.uint8)

    print("Assembling FILTERED image...")
    
    final_parts = [columns_to_keep[0]]  # First kept column
    
    # Add padding + column for remaining kept columns
    for next_column in columns_to_keep[1:]:
        final_parts.append(white_padding)
        final_parts.append(next_column)
    
    separated_columns_image = np.hstack(final_parts)

    print(f" **PERFECT!** {len(columns_to_keep)} CLEAN COLUMNS created!")
    print(f"   Final size: {separated_columns_image.shape[1]}px wide")
    
    if debug:
        cv2.imwrite('separated_columns.png', separated_columns_image)
        print(" Saved 'separated_columns.png' - FILTERED result!")
    
    return separated_columns_image
#!/usr/bin/env python3
"""
Column Detection Module

This module provides utilities for column separator detection and processing:
- Column separator detection using template matching
- Column image creation and extraction
"""

import cv2
import numpy as np


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


def get_column_5_image(source_img, column_separator_positions, template_width, debug=False):
    """
    Extracts only column 5 from the source image using column separators.
    
    Processing steps:
    1. Calculate column boundaries from separator positions
    2. Extract column 5 (index 4, 0-based)
    3. Return the single column image
    
    Args:
        source_img: Source image to process
        column_separator_positions: List of ((x, y), confidence) tuples
        template_width: Width of separator template
        debug: Enable debug output (default: False)
    
    Returns:
        Image containing only column 5, or None if processing fails or column 5 doesn't exist
    """
    if not column_separator_positions:
        print("[GET_COLUMN_5] No column separators found")
        return None
    
    # Calculate column boundaries
    print(f"[GET_COLUMN_5] Processing {len(column_separator_positions)} separators")
    
    column_split_positions = []
    for position, score in column_separator_positions:
        x_position = position[0]
        split_center = x_position + (template_width // 2)
        column_split_positions.append(split_center)
    
    unique_split_positions = sorted(set(column_split_positions))
    image_width = source_img.shape[1]
    all_column_boundaries = [0] + unique_split_positions + [image_width]
    
    if debug:
        print(f"[GET_COLUMN_5] Column boundaries: {all_column_boundaries}")
    
    # Calculate total number of columns
    total_columns = len(all_column_boundaries) - 1
    print(f"[GET_COLUMN_5] Found {total_columns} columns")
    
    # Check if column 5 exists (index 4, 0-based)
    column_5_index = 4  # Column 5 is at index 4 (0-based indexing)
    
    if total_columns < 5:
        print(f"[GET_COLUMN_5] Column 5 does not exist. Only {total_columns} columns found")
        return None
    
    # Extract column 5
    left_edge = all_column_boundaries[column_5_index]
    right_edge = all_column_boundaries[column_5_index + 1]
    column_5_image = source_img[:, left_edge:right_edge]
    
    if debug:
        column_width = right_edge - left_edge
        print(f"[GET_COLUMN_5] Column 5: x={left_edge} to x={right_edge} (width={column_width}px)")
        cv2.imwrite('column_5_extracted.png', column_5_image)
        print("[GET_COLUMN_5] Saved debug image: 'column_5_extracted.png'")
    
    print(f"[GET_COLUMN_5] Successfully extracted column 5")
    return column_5_image


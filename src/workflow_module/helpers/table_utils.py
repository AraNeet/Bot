"""
Table Structure Detection Utilities

This module provides functions for analyzing table structure from OCR detection results.
It includes functionality for:
- Detecting table row boundaries using clustering algorithms
- Normalizing text box heights for consistent table analysis
- Counting rows in detected tables

These utilities are essential for navigating and interacting with data tables
in the automation workflow.
"""

from typing import List, Any, Tuple, Optional
import numpy as np
from sklearn.cluster import DBSCAN


def determine_row_boundaries(ocr_results: List[Any],
                           min_row_height: int = 15,
                           clustering_tolerance: int = 5,
                           normalize_heights: bool = False,
                           target_height: Optional[int] = None) -> Tuple[List[Tuple[int, int]], int]:
    """
    Determines row boundaries and counts rows from OCR detection results.

    Analyzes the vertical positions of detected text boxes to identify distinct
    table rows by clustering boxes with similar y-coordinates.

    Args:
        ocr_results: List of OCR result objects from detect_text_and_regions()
        min_row_height: Minimum height in pixels for a valid row
        clustering_tolerance: Tolerance in pixels for grouping text into same row
        normalize_heights: Whether to normalize box heights before clustering
        target_height: Target height for normalization (auto-calculated if None)

    Returns:
        Tuple of:
        - List of (top_y, bottom_y) tuples defining each row boundary
        - Number of detected rows
    """
    if not ocr_results:
        return [], 0

    # Optional height normalization for better clustering
    if normalize_heights:
        print("🔧 Applying height normalization for better row detection...")
        normalize_text_box_heights(ocr_results, target_height)

    # STEP 1: TEXT BOX EXTRACTION
    # Parse OCR results to extract all detected text boxes and their coordinates
    all_boxes = []
    all_texts = []

    for result in ocr_results:
        # Handle different result formats
        if hasattr(result, 'rec_boxes') and hasattr(result, 'rec_texts'):
            # PaddleOCR format with rec_boxes and rec_texts
            boxes = result.rec_boxes
            texts = result.rec_texts
        elif hasattr(result, 'dt_polys') and hasattr(result, 'rec_texts'):
            # Alternative format - convert dt_polys to boxes
            boxes = []
            for poly in result.dt_polys:
                # Convert polygon to bounding box [x1, y1, x2, y2]
                x_coords = [point[0] for point in poly]
                y_coords = [point[1] for point in poly]
                boxes.append([min(x_coords), min(y_coords), max(x_coords), max(y_coords)])
            texts = result.rec_texts
        else:
            # Try to extract from dictionary format
            try:
                if 'rec_boxes' in result:
                    boxes = result['rec_boxes']
                    texts = result['rec_texts']
                elif 'dt_polys' in result:
                    boxes = []
                    for poly in result['dt_polys']:
                        x_coords = [point[0] for point in poly]
                        y_coords = [point[1] for point in poly]
                        boxes.append([min(x_coords), min(y_coords), max(x_coords), max(y_coords)])
                    texts = result['rec_texts']
                else:
                    continue
            except (TypeError, KeyError):
                continue

        all_boxes.extend(boxes)
        all_texts.extend(texts)

    if not all_boxes:
        print("Warning: No text boxes found in OCR results")
        return [], 0

    print(f"Found {len(all_boxes)} text boxes for row analysis")

    # STEP 2: VERTICAL POSITION ANALYSIS
    # Extract center y-coordinates for clustering analysis
    center_y_coords = []
    box_info = []

    for i, box in enumerate(all_boxes):
        if len(box) >= 4:  # Ensure box has at least [x1, y1, x2, y2]
            x1, y1, x2, y2 = box[:4]
            # Calculate vertical center point of text box
            center_y = (y1 + y2) / 2
            center_y_coords.append([center_y])  # DBSCAN expects 2D array format

            # Store comprehensive box information for later processing
            box_info.append({
                'index': i,
                'box': box,
                'text': all_texts[i] if i < len(all_texts) else '',
                'center_y': center_y,
                'top': y1,      # Top boundary of text box
                'bottom': y2    # Bottom boundary of text box
            })

    if not center_y_coords:
        print("Warning: No valid boxes found for clustering")
        return [], 0

    # STEP 3: DBSCAN CLUSTERING
    # Group text boxes with similar vertical positions into row clusters
    # eps=clustering_tolerance: max distance between boxes in same row (default: 5px)
    # min_samples=1: allow single text boxes to form clusters (rows)
    clustering = DBSCAN(eps=clustering_tolerance, min_samples=1)
    cluster_labels = clustering.fit_predict(center_y_coords)

    # Group boxes by cluster ID (each cluster represents a potential row)
    rows = {}
    for i, label in enumerate(cluster_labels):
        if label not in rows:
            rows[label] = []
        rows[label].append(box_info[i])

    print(f"Found {len(rows)} potential rows after clustering")

    # STEP 4: ROW BOUNDARY CALCULATION
    # For each cluster, calculate the overall row boundaries
    row_boundaries = []

    for cluster_id, boxes_in_row in rows.items():
        if cluster_id == -1:  # Skip DBSCAN noise points (outliers)
            continue

        # Find the overall top and bottom boundaries of this row
        # row_top = highest point (minimum y-coordinate) of any box in row
        # row_bottom = lowest point (maximum y-coordinate) of any box in row
        row_top = min(box['top'] for box in boxes_in_row)
        row_bottom = max(box['bottom'] for box in boxes_in_row)
        row_height = row_bottom - row_top

        # STEP 5: QUALITY FILTERING
        # Filter out rows that are too small (likely OCR noise or artifacts)
        if row_height >= min_row_height:
            row_boundaries.append((int(row_top), int(row_bottom)))

            # Debug: Show what text was found in this row
            texts_in_row = [box['text'] for box in boxes_in_row]
            print(f"Row {len(row_boundaries)}: y={row_top:.1f}-{row_bottom:.1f} "
                  f"(height: {row_height:.1f}px) - {len(boxes_in_row)} boxes")
            print(f"  Sample texts: {texts_in_row[:3]}...")

    # FINAL STEP: Sort rows by vertical position (top to bottom of table)
    row_boundaries.sort(key=lambda x: x[0])

    num_rows = len(row_boundaries)
    print(f"\nFinal result: {num_rows} valid rows detected")

    return row_boundaries, num_rows


def normalize_text_box_heights(ocr_results: List[Any],
                              target_height: Optional[int] = None,
                              height_percentile: float = 50.0) -> List[Any]:
    """
    Normalizes bounding box heights to be consistent across all detected text.

    Since all text in tables typically has the same font size, OCR detection variations
    can create inconsistent box heights. This function standardizes them for better
    row detection and table structure analysis.

    Args:
        ocr_results: Original OCR results with varying box heights
        target_height: Specific height to use (if None, calculates from data)
        height_percentile: Percentile to use for automatic height calculation (default: 50th percentile)

    Returns:
        Modified OCR results with normalized box heights
    """
    if not ocr_results:
        return ocr_results

    print("Normalizing text box heights for consistent table detection...")

    # Collect all box heights to calculate target height
    all_heights = []
    all_boxes_info = []

    for result_idx, result in enumerate(ocr_results):
        # Extract boxes and texts
        if hasattr(result, 'rec_boxes') and hasattr(result, 'rec_texts'):
            boxes = result.rec_boxes
            texts = result.rec_texts
        elif hasattr(result, 'dt_polys') and hasattr(result, 'rec_texts'):
            # Convert polygons to boxes first
            boxes = []
            for poly in result.dt_polys:
                x_coords = [point[0] for point in poly]
                y_coords = [point[1] for point in poly]
                boxes.append([min(x_coords), min(y_coords), max(x_coords), max(y_coords)])
            texts = result.rec_texts
        else:
            continue

        for box_idx, box in enumerate(boxes):
            if len(box) >= 4:
                x1, y1, x2, y2 = box[:4]
                height = y2 - y1
                all_heights.append(height)
                all_boxes_info.append({
                    'result_idx': result_idx,
                    'box_idx': box_idx,
                    'original_box': box,
                    'height': height,
                    'center_x': (x1 + x2) / 2,
                    'center_y': (y1 + y2) / 2
                })

    if not all_heights:
        print("No text boxes found for height normalization")
        return ocr_results

    # Calculate target height
    if target_height is None:
        target_height = int(np.percentile(all_heights, height_percentile))

    print(f"Original height range: {min(all_heights):.1f} - {max(all_heights):.1f} pixels")
    print(f"Target normalized height: {target_height} pixels")
    print(f"Normalizing {len(all_boxes_info)} text boxes...")

    # Modify OCR results in-place to normalize heights
    for result_idx, result in enumerate(ocr_results):
        if hasattr(result, 'rec_boxes') and hasattr(result, 'rec_texts'):
            # PaddleOCR format - modify rec_boxes in place
            for box_idx, box in enumerate(result.rec_boxes):
                if len(box) >= 4:
                    x1, y1, x2, y2 = box[:4]

                    # Calculate new y coordinates centered on original center_y
                    center_y = (y1 + y2) / 2
                    half_target = target_height / 2

                    new_y1 = center_y - half_target
                    new_y2 = center_y + half_target

                    # Modify the box in place
                    box[1] = new_y1  # Update y1
                    box[3] = new_y2  # Update y2

        elif hasattr(result, 'dt_polys'):
            # Polygon format - modify dt_polys in place
            for box_idx, poly in enumerate(result.dt_polys):
                x_coords = [point[0] for point in poly]
                y_coords = [point[1] for point in poly]

                # Get bounding box
                x1, y1, x2, y2 = min(x_coords), min(y_coords), max(x_coords), max(y_coords)

                # Normalize height
                center_y = (y1 + y2) / 2
                half_target = target_height / 2
                new_y1 = center_y - half_target
                new_y2 = center_y + half_target

                # Update polygon points in place
                result.dt_polys[box_idx] = [[x1, new_y1], [x2, new_y1], [x2, new_y2], [x1, new_y2]]

    print(f"✅ Height normalization completed")
    return ocr_results
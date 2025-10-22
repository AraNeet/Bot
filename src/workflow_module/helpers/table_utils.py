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

from typing import List, Any, Tuple, Optional, Dict
import numpy as np
from sklearn.cluster import DBSCAN


# ============================================================================
# OCR FORMAT PARSING - Handle different OCR result formats
# ============================================================================

def _convert_polygon_to_box(polygon: List[List[float]]) -> List[float]:
    """
    Convert polygon coordinates to bounding box format [x1, y1, x2, y2].

    Args:
        polygon: List of [x, y] coordinate pairs

    Returns:
        Bounding box as [x1, y1, x2, y2]
    """
    x_coords = [point[0] for point in polygon]
    y_coords = [point[1] for point in polygon]
    return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]


def _extract_boxes_and_texts(ocr_result: Any) -> Tuple[List[List[float]], List[str]]:
    """
    Extract bounding boxes and text from a single OCR result object.
    Handles multiple OCR format types (PaddleOCR, polygon format, dictionary).

    Args:
        ocr_result: Single OCR result object in various formats

    Returns:
        Tuple of (boxes, texts) where boxes are in [x1, y1, x2, y2] format
    """
    # Format 1: PaddleOCR with rec_boxes and rec_texts attributes
    if hasattr(ocr_result, 'rec_boxes') and hasattr(ocr_result, 'rec_texts'):
        return ocr_result.rec_boxes, ocr_result.rec_texts

    # Format 2: Polygon format (dt_polys) - needs conversion to boxes
    if hasattr(ocr_result, 'dt_polys') and hasattr(ocr_result, 'rec_texts'):
        boxes = [_convert_polygon_to_box(poly) for poly in ocr_result.dt_polys]
        return boxes, ocr_result.rec_texts

    # Format 3: Dictionary format - try to extract from dict
    try:
        if 'rec_boxes' in ocr_result:
            return ocr_result['rec_boxes'], ocr_result['rec_texts']
        elif 'dt_polys' in ocr_result:
            boxes = [_convert_polygon_to_box(poly) for poly in ocr_result['dt_polys']]
            return boxes, ocr_result['rec_texts']
    except (TypeError, KeyError):
        pass

    # Unsupported format
    return [], []


def _parse_all_ocr_results(ocr_results: List[Any]) -> Tuple[List[List[float]], List[str]]:
    """
    Parse all OCR results and extract boxes and texts.

    Args:
        ocr_results: List of OCR result objects in various formats

    Returns:
        Tuple of (all_boxes, all_texts) flattened from all results
    """
    all_boxes = []
    all_texts = []

    for result in ocr_results:
        boxes, texts = _extract_boxes_and_texts(result)
        all_boxes.extend(boxes)
        all_texts.extend(texts)

    return all_boxes, all_texts


# ============================================================================
# ROW BOUNDARY DETECTION - Main workflow
# ============================================================================

def _create_box_info_list(boxes: List[List[float]],
                          texts: List[str]) -> List[Dict]:
    """
    Create structured box information for clustering analysis.

    Args:
        boxes: List of bounding boxes in [x1, y1, x2, y2] format
        texts: List of text strings corresponding to boxes

    Returns:
        List of dictionaries with box metadata (index, coordinates, text, etc.)
    """
    box_info = []

    for i, box in enumerate(boxes):
        if len(box) >= 4:
            x1, y1, x2, y2 = box[:4]
            box_info.append({
                'index': i,
                'box': box,
                'text': texts[i] if i < len(texts) else '',
                'center_y': (y1 + y2) / 2,
                'top': y1,
                'bottom': y2
            })

    return box_info


def _cluster_boxes_by_vertical_position(box_info: List[Dict],
                                        clustering_tolerance: int) -> Dict[int, List[Dict]]:
    """
    Group text boxes into row clusters based on vertical position using DBSCAN.

    Args:
        box_info: List of box information dictionaries
        clustering_tolerance: Maximum distance in pixels between boxes in same row

    Returns:
        Dictionary mapping cluster_id -> list of boxes in that cluster
    """
    if not box_info:
        return {}

    # Extract center y-coordinates for clustering
    center_y_coords = [[box['center_y']] for box in box_info]

    # Apply DBSCAN clustering
    # eps: maximum distance between boxes in same row
    # min_samples=1: allow single boxes to form rows
    clustering = DBSCAN(eps=clustering_tolerance, min_samples=1)
    cluster_labels = clustering.fit_predict(center_y_coords)

    # Group boxes by cluster ID
    clusters = {}
    for i, label in enumerate(cluster_labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(box_info[i])

    return clusters


def _calculate_row_boundary(boxes_in_row: List[Dict]) -> Tuple[int, int, int]:
    """
    Calculate the overall boundary for a single row from its boxes.

    Args:
        boxes_in_row: List of box info dictionaries belonging to this row

    Returns:
        Tuple of (row_top, row_bottom, row_height)
    """
    row_top = min(box['top'] for box in boxes_in_row)
    row_bottom = max(box['bottom'] for box in boxes_in_row)
    row_height = row_bottom - row_top

    return int(row_top), int(row_bottom), int(row_height)


def _filter_valid_rows(clusters: Dict[int, List[Dict]],
                      min_row_height: int,
                      verbose: bool = True) -> List[Tuple[int, int]]:
    """
    Filter clusters to valid rows and calculate boundaries.

    Args:
        clusters: Dictionary mapping cluster_id -> list of boxes
        min_row_height: Minimum height in pixels for a valid row
        verbose: Whether to print debug information

    Returns:
        List of (top_y, bottom_y) tuples for valid rows, unsorted
    """
    row_boundaries = []

    for cluster_id, boxes_in_row in clusters.items():
        # Skip DBSCAN noise points (outliers marked as -1)
        if cluster_id == -1:
            continue

        row_top, row_bottom, row_height = _calculate_row_boundary(boxes_in_row)

        # Filter out rows that are too small (likely OCR noise)
        if row_height >= min_row_height:
            row_boundaries.append((row_top, row_bottom))

            if verbose:
                texts_in_row = [box['text'] for box in boxes_in_row]
                print(f"Row {len(row_boundaries)}: y={row_top}-{row_bottom} "
                      f"(height: {row_height}px) - {len(boxes_in_row)} boxes")
                print(f"  Sample texts: {texts_in_row[:3]}...")

    return row_boundaries


def determine_row_boundaries(ocr_results: List[Any],
                           min_row_height: int = 15,
                           clustering_tolerance: int = 5,
                           normalize_heights: bool = False,
                           target_height: Optional[int] = None,
                           verbose: bool = True) -> Tuple[List[Tuple[int, int]], int]:
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
        verbose: Whether to print progress information

    Returns:
        Tuple of:
        - List of (top_y, bottom_y) tuples defining each row boundary (sorted top to bottom)
        - Number of detected rows
    """
    if not ocr_results:
        return [], 0

    # Step 1: Optional height normalization for better clustering
    if normalize_heights:
        if verbose:
            print("🔧 Applying height normalization for better row detection...")
        normalize_text_box_heights(ocr_results, target_height)

    # Step 2: Extract all text boxes and texts from OCR results
    all_boxes, all_texts = _parse_all_ocr_results(ocr_results)

    if not all_boxes:
        if verbose:
            print("Warning: No text boxes found in OCR results")
        return [], 0

    if verbose:
        print(f"Found {len(all_boxes)} text boxes for row analysis")

    # Step 3: Create structured box information for analysis
    box_info = _create_box_info_list(all_boxes, all_texts)

    if not box_info:
        if verbose:
            print("Warning: No valid boxes found for clustering")
        return [], 0

    # Step 4: Cluster boxes by vertical position (y-coordinate)
    clusters = _cluster_boxes_by_vertical_position(box_info, clustering_tolerance)

    if verbose:
        print(f"Found {len(clusters)} potential rows after clustering")

    # Step 5: Calculate boundaries and filter valid rows
    row_boundaries = _filter_valid_rows(clusters, min_row_height, verbose)

    # Step 6: Sort rows by vertical position (top to bottom)
    row_boundaries.sort(key=lambda x: x[0])

    num_rows = len(row_boundaries)
    if verbose:
        print(f"\nFinal result: {num_rows} valid rows detected")

    return row_boundaries, num_rows


# ============================================================================
# HEIGHT NORMALIZATION - Standardize text box heights
# ============================================================================

def _collect_box_heights(ocr_results: List[Any]) -> Tuple[List[float], int]:
    """
    Collect all box heights from OCR results for statistical analysis.

    Args:
        ocr_results: List of OCR result objects

    Returns:
        Tuple of (list of heights, total box count)
    """
    all_heights = []

    for result in ocr_results:
        boxes, _ = _extract_boxes_and_texts(result)

        for box in boxes:
            if len(box) >= 4:
                x1, y1, x2, y2 = box[:4]
                height = y2 - y1
                all_heights.append(height)

    return all_heights, len(all_heights)


def _calculate_normalization_target(heights: List[float],
                                    target_height: Optional[int],
                                    percentile: float) -> int:
    """
    Calculate the target height for normalization.

    Args:
        heights: List of all box heights
        target_height: Explicit target if provided
        percentile: Percentile to use for automatic calculation

    Returns:
        Target height in pixels
    """
    if target_height is not None:
        return target_height

    return int(np.percentile(heights, percentile))


def _normalize_box_coordinates(box: List[float], target_height: int) -> Tuple[float, float]:
    """
    Calculate normalized y-coordinates for a box.

    Args:
        box: Original box coordinates [x1, y1, x2, y2]
        target_height: Target height in pixels

    Returns:
        Tuple of (new_y1, new_y2)
    """
    x1, y1, x2, y2 = box[:4]
    center_y = (y1 + y2) / 2
    half_target = target_height / 2

    new_y1 = center_y - half_target
    new_y2 = center_y + half_target

    return new_y1, new_y2


def _apply_normalization_to_result(result: Any, target_height: int) -> None:
    """
    Apply height normalization to a single OCR result object (in-place).

    Args:
        result: Single OCR result object to modify
        target_height: Target height in pixels
    """
    # Format 1: rec_boxes attribute
    if hasattr(result, 'rec_boxes'):
        for box in result.rec_boxes:
            if len(box) >= 4:
                new_y1, new_y2 = _normalize_box_coordinates(box, target_height)
                box[1] = new_y1
                box[3] = new_y2

    # Format 2: dt_polys (polygon) attribute
    elif hasattr(result, 'dt_polys'):
        for idx, poly in enumerate(result.dt_polys):
            # Convert polygon to box, normalize, convert back to polygon
            box = _convert_polygon_to_box(poly)
            new_y1, new_y2 = _normalize_box_coordinates(box, target_height)
            x1 = box[0]
            x2 = box[2]

            # Update polygon as normalized rectangle
            result.dt_polys[idx] = [[x1, new_y1], [x2, new_y1],
                                   [x2, new_y2], [x1, new_y2]]


def normalize_text_box_heights(ocr_results: List[Any],
                              target_height: Optional[int] = None,
                              height_percentile: float = 50.0,
                              verbose: bool = True) -> List[Any]:
    """
    Normalizes bounding box heights to be consistent across all detected text.

    Since all text in tables typically has the same font size, OCR detection variations
    can create inconsistent box heights. This function standardizes them for better
    row detection and table structure analysis.

    Args:
        ocr_results: Original OCR results with varying box heights (modified in-place)
        target_height: Specific height to use (if None, calculates from data)
        height_percentile: Percentile to use for automatic height calculation
        verbose: Whether to print progress information

    Returns:
        Modified OCR results with normalized box heights (same object as input)
    """
    if not ocr_results:
        return ocr_results

    if verbose:
        print("Normalizing text box heights for consistent table detection...")

    # Step 1: Collect all box heights for analysis
    all_heights, box_count = _collect_box_heights(ocr_results)

    if not all_heights:
        if verbose:
            print("No text boxes found for height normalization")
        return ocr_results

    # Step 2: Calculate target normalization height
    target = _calculate_normalization_target(all_heights, target_height, height_percentile)

    if verbose:
        print(f"Original height range: {min(all_heights):.1f} - {max(all_heights):.1f} pixels")
        print(f"Target normalized height: {target} pixels")
        print(f"Normalizing {box_count} text boxes...")

    # Step 3: Apply normalization to all OCR results
    for result in ocr_results:
        _apply_normalization_to_result(result, target)

    if verbose:
        print("✅ Height normalization completed")

    return ocr_results

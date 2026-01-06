#!/usr/bin/env python3
"""
Step 08: Open Multinetwork Row by Date Handler

This handler finds and double-clicks on a row in the nested second table
within an expanded blue row, matching by begin_date.

The structure is:
1. First table with multiple rows
2. One row is expanded (blue highlighted) containing:
   - First table row data (Network Code, Order #, etc.)
   - Nested second table (Instruction, Begin Date, End Date, etc.)
3. We find the row in the nested table matching the begin_date

Author: Refactored for clean architecture
Date: 2026-01-06
"""

import os
import time
from typing import Tuple

# Import helper modules
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger


def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    """
    Find and double-click on a row in the nested second table by begin_date.
    
    This is the main entry point for the handler. It orchestrates the entire process:
    1. Detect the expanded row (blue highlighted)
    2. Calculate crop region from blue row dimensions
    3. Extract and split columns (using templates)
    4. Search for matching date
    5. Execute double-click action
    
    Args:
        begin_date: The date to search for in the table (e.g., "01/01/2024")
        estimate_number: Estimate number for reference (optional, not currently used)
        **kwargs: Additional arguments (ignored)
        
    Returns:
        Tuple of (success: bool, message: str)
        
    Example:
        >>> success, message = action(begin_date="1/5/2026")
        >>> print(f"Success: {success}, Message: {message}")
    """
    debug = Debugger(action_name="action_08_clean")
    
    try:
        print("=" * 80)
        print("[HANDLER] Starting Step 08: Open Multinetwork Row by Date")
        print(f"[HANDLER] Target begin_date: '{begin_date}'")
        print("=" * 80)
        
        # Step 1: Validate input parameters
        if not begin_date:
            return False, "begin_date parameter is required"
        
        # Step 2: Get handler directory for template paths
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Step 3: Capture initial screenshot
        print("[HANDLER] Step 3: Capturing screenshot...")
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to capture screenshot"
        
        debug.save_image(screenshot, "00_initial_screenshot.png")
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Step 4: Detect blue highlighted expanded row
        print("[HANDLER] Step 4: Detecting blue highlighted expanded row...")
        found_blue, blue_row_info = computer_vision_utils.detect_blue_highlighted_expanded_row(
            screenshot
        )
        
        if not found_blue:
            return False, "Blue highlighted expanded row not found"
        
        # Step 5: Visualize detected blue row for debugging
        annotated = screenshot.copy()
        debug.draw_rect(
            annotated,
            (blue_row_info['x'], blue_row_info['y'], blue_row_info['width'], blue_row_info['height']),
            color=(0, 255, 0),
            thickness=3,
            label=f"Blue Row: {blue_row_info['width']}x{blue_row_info['height']}"
        )
        debug.save_image(annotated, "01_blue_row_detected.png")
        
        # Step 6: Calculate crop region from blue row dimensions
        print("[HANDLER] Step 6: Calculating crop region...")
        crop_x, crop_y, crop_width, crop_height = \
            computer_vision_utils.calculate_crop_region_from_expanded_row(
                screenshot,
                blue_row_info
            )
        
        # Step 7: Validate crop dimensions
        if crop_height <= 0 or crop_width <= 0:
            return False, f"Invalid crop dimensions: {crop_width}x{crop_height}"
        
        if crop_height < 50:
            return False, f"Crop height too small ({crop_height}px). Row may not be expanded."
        
        # Step 8: Visualize crop region for debugging
        annotated = screenshot.copy()
        debug.draw_rect(
            annotated,
            (crop_x, crop_y, crop_width, crop_height),
            color=(0, 255, 0),
            thickness=3,
            label=f"Crop: {crop_width}x{crop_height}"
        )
        debug.save_image(annotated, "02_crop_region.png")
        
        # Step 9: Extract table and detect column splits
        print("[HANDLER] Step 9: Extracting table and detecting columns...")
        column_template_path = os.path.join(
            handler_dir, 
            '08_RowColumnLineSecondTable.png'
        )
        
        cropped_table, column_boundaries = \
            computer_vision_utils.extract_table_with_column_splits(
                screenshot,
                crop_x,
                crop_y,
                crop_width,
                crop_height,
                column_template_path,
                match_threshold=0.85
            )
        
        if cropped_table is None:
            return False, "Failed to extract table region"
        
        debug.save_image(cropped_table, "03_cropped_table.png")
        
        # Step 10: Visualize column splits for debugging
        if column_boundaries:
            annotated_table = computer_vision_utils.visualize_column_splits_in_table(
                cropped_table,
                column_boundaries
            )
            debug.save_image(annotated_table, "04_column_splits.png")
        
        # Step 11: Search for matching date in table
        print("[HANDLER] Step 11: Searching for date in table...")
        found_date, click_x, click_y, search_message = \
            table_utils.search_date_in_cropped_table(
                cropped_table,
                column_boundaries,
                begin_date,
                crop_x,
                crop_y
            )
        
        if not found_date:
            return False, search_message
        
        print(f"[HANDLER] ✓ Date found! Click position: ({click_x}, {click_y})")
        
        # Step 12: Visualize click position for debugging
        annotated = screenshot.copy()
        debug.draw_point(
            annotated,
            (click_x, click_y),
            color=(0, 255, 0),
            radius=15,
            label=f"Click: {begin_date}"
        )
        debug.save_image(annotated, "05_click_position.png")
        
        # Step 13: Execute double-click at found position
        print("[HANDLER] Step 13: Executing double-click...")
        save_path_before = os.path.join(debug.output_dir, "06_before_click.png")
        save_path_after = os.path.join(debug.output_dir, "07_after_click.png")
        success, click_message = computer_vision_utils.execute_double_click_at_position(
            click_x,
            click_y,
            screenshot,
            save_path_before=save_path_before,
            save_path_after=save_path_after
        )
        
        if not success:
            return False, click_message
        
        print("=" * 80)
        print(f"[HANDLER] ✓ SUCCESS: {click_message}")
        print("=" * 80)
        
        # Step 14: Return success
        return True, f"Row found and double-clicked! Begin date: '{begin_date}'"
        
    except Exception as e:
        error_msg = f"Unexpected error in action: {str(e)}"
        print(f"[HANDLER] ✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg


def error_handler(
    error_message: str,
    attempt: int,
    max_attempts: int,
    begin_date: str = "",
    **kwargs
) -> Tuple[str, dict]:
    """
    Handle errors that occur during action execution.
    
    This function determines whether to retry the action or give up based on:
    - The type of error
    - The number of attempts made
    - The specific error message
    
    Args:
        error_message: The error message from the failed action
        attempt: Current attempt number (1-indexed)
        max_attempts: Maximum number of attempts allowed
        begin_date: The begin_date parameter from the original action
        **kwargs: Additional arguments (ignored)
        
    Returns:
        Tuple of (decision: str, params: dict)
        decision can be:
            - "retry": Retry the action with the same or modified parameters
            - "skip": Skip this action and continue to the next step
            - "abort": Abort the entire workflow
        params: Dictionary of parameters to use for retry (if decision is "retry")
        
    Example:
        >>> decision, params = error_handler("Date not found", 1, 3, begin_date="1/5/2026")
        >>> print(f"Decision: {decision}")
    """
    # Step 1: Log error details
    print(f"[ERROR_HANDLER] Attempt {attempt}/{max_attempts} failed: {error_message}")
    
    # Step 2: Check if max attempts reached
    if attempt >= max_attempts:
        print(f"[ERROR_HANDLER] Max attempts reached. Aborting.")
        return "abort", {}
    
    # Step 3: Analyze error type
    error_lower = error_message.lower()
    
    # Step 4: Define error categories
    # Step 4a: Errors that suggest retrying might help
    retryable_errors = [
        "screenshot",
        "blue highlighted",
        "not found",
        "ocr failed",
        "crop height too small"
    ]
    
    # Step 4b: Errors that suggest we should skip
    skip_errors = [
        "required",
        "invalid",
        "parameter"
    ]
    
    # Step 5: Check for retryable errors
    for retryable in retryable_errors:
        if retryable in error_lower:
            wait_time = attempt * 1.0  # Exponential backoff
            print(f"[ERROR_HANDLER] Retrying in {wait_time}s...")
            time.sleep(wait_time)
            return "retry", {"begin_date": begin_date}
    
    # Step 6: Check for non-retryable errors
    for skip_error in skip_errors:
        if skip_error in error_lower:
            print(f"[ERROR_HANDLER] Error suggests skipping this step")
            return "skip", {}
    
    # Step 7: Default retry with backoff for unknown errors
    wait_time = attempt * 1.0
    print(f"[ERROR_HANDLER] Retrying in {wait_time}s...")
    time.sleep(wait_time)
    return "retry", {"begin_date": begin_date}
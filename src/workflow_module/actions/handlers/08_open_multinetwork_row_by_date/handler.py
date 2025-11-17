#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Row by Date

Find and double-click on a row in the second table (within expanded row) by begin_date.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import column_detection
from src.workflow_module.actions.helpers import date_utils
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import ocr_utils
import time
import pyautogui
import cv2
import numpy as np
import os


def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    if not begin_date:
        return False, "Missing begin_date parameter"
    
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    print(f"[ACTION_HANDLER] Estimate number for reference: '{estimate_number}'")
    
    try:
        # Create directory for step screenshots
        step_screenshots_dir = "debug_images/action_08_steps"
        os.makedirs(step_screenshots_dir, exist_ok=True)
        
        time.sleep(4)
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        # Save initial screenshot
        try:
            success, path = computer_vision_utils.save_screenshot(
                screenshot, 
                filename="01_initial_screenshot.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved initial screenshot to: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save initial screenshot: {e}")
        
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Step 1: Find blue highlighted row using computer vision utils
        print(f"[ACTION_HANDLER] Detecting blue highlighted row (expanded row)...")
        found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(screenshot, exclude_bottom_pixels=100)
        
        # Initialize blue row variables
        blue_x = None
        blue_y = None
        blue_w = None
        blue_h = None
        
        if found_blue and row_info is not None:
            blue_x = row_info['x']
            blue_y = row_info['y']
            blue_w = row_info['width']
            blue_h = row_info['height']
            print(f"[ACTION_HANDLER] Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        else:
            print(f"[ACTION_HANDLER] WARNING: Blue highlighted row not found, will use Y=230 for crop start")
        
        # Save screenshot with blue row highlighted (if found)
        try:
            annotated_screenshot = screenshot.copy()
            if found_blue and blue_x is not None:
                cv2.rectangle(annotated_screenshot, (blue_x, blue_y), (blue_x + blue_w, blue_y + blue_h), (0, 255, 0), 3)
                cv2.putText(annotated_screenshot, "Blue Highlighted Row", (blue_x, blue_y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(annotated_screenshot, "Blue Row Not Found - Using Y=230", (10, 230), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.line(annotated_screenshot, (0, 230), (screen_width, 230), (0, 0, 255), 2)
            success, path = computer_vision_utils.save_screenshot(
                annotated_screenshot,
                filename="02_blue_highlighted_row_detected.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved blue row detection screenshot to: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save blue row screenshot: {e}")
        
        # Step 2: Find "Estimate #" column header Y position using OCR
        # We need to find the Y position of the "Estimate #" header in the second table (inner table header)
        print(f"[ACTION_HANDLER] ===== FINDING ESTIMATE # HEADER POSITION =====")
        print(f"[ACTION_HANDLER] Searching for 'Estimate #' or 'Estimate' column header to determine crop Y position...")
        estimate_number_y = None
        
        # Define search region for the header - look in the expanded row area
        # The "Estimate #" header is in the second table header, which is within the expanded blue row
        if found_blue and blue_x is not None and blue_y is not None:
            # Search from the blue row down to include the header (which may be at the bottom of blue row or just below)
            # Search a region that includes the blue row and extends below it
            header_search_y = blue_y
            header_search_h = min(blue_h + 80, 150)  # Include blue row height + 80px below for header
            header_search_x = 205  # Use fixed X to match table start
            header_search_w = 1500  # Use full table width
            # Make sure we don't go beyond screen bounds
            header_search_h = min(header_search_h, screen_height - header_search_y - 100)
            search_region = screenshot[header_search_y:header_search_y + header_search_h, 
                                      header_search_x:header_search_x + header_search_w]
            print(f"[ACTION_HANDLER] Searching for header in expanded row region: Y={header_search_y}, H={header_search_h}")
        else:
            # If blue row not found, use a default search region starting at Y=230
            default_search_y = 230
            default_search_h = 50
            default_search_x = 205
            default_search_w = 1500
            search_region = screenshot[default_search_y:default_search_y + default_search_h, 
                                      default_search_x:default_search_x + default_search_w]
            header_search_y = default_search_y
            header_search_x = default_search_x
            print(f"[ACTION_HANDLER] Blue row not found, searching at default Y={header_search_y}")
        
        # Save debug image of the search region
        try:
            debug_path = "debug_images/estimate_search_region.png"
            os.makedirs("debug_images", exist_ok=True)
            cv2.imwrite(debug_path, search_region)
            abs_path = os.path.abspath(debug_path)
            print(f"[ACTION_HANDLER] DEBUG: Saved estimate search region to: {abs_path}")
            print(f"[ACTION_HANDLER] DEBUG: Search region size: {search_region.shape[1]}x{search_region.shape[0]}")
        except Exception as e:
            print(f"[ACTION_HANDLER] WARNING: Failed to save estimate search region: {e}")
        
        # Get OCR data to see what text is detected
        print(f"[ACTION_HANDLER] DEBUG: Running OCR to detect all text in search region...")
        print(f"[ACTION_HANDLER] DEBUG: Looking for estimate number: '{estimate_number}'")
        
        scanner = ocr_utils.TextScanner()
        ocr_success, ocr_data = scanner.get_text_data(search_region)
        
        if ocr_success and ocr_data and ocr_data.get('text'):
            print(f"[ACTION_HANDLER] DEBUG: OCR detected {len(ocr_data['text'])} text elements:")
            for i, (text, bbox, conf) in enumerate(zip(ocr_data['text'], ocr_data['bbox'], ocr_data['confidence'])):
                x1, y1, x2, y2 = map(int, bbox)
                print(f"[ACTION_HANDLER] DEBUG:   [{i}] Text: '{text}' | Bbox: ({x1},{y1})-({x2},{y2}) | Confidence: {conf:.2f}")
            
            # Create annotated image showing detected text
            try:
                annotated_region = search_region.copy()
                for i, (text, bbox) in enumerate(zip(ocr_data['text'], ocr_data['bbox'])):
                    x1, y1, x2, y2 = map(int, bbox)
                    # Draw bounding box
                    cv2.rectangle(annotated_region, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Add text label
                    label = f"{i}:{text[:20]}"
                    cv2.putText(annotated_region, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                debug_path = "debug_images/estimate_search_annotated.png"
                cv2.imwrite(debug_path, annotated_region)
                abs_path = os.path.abspath(debug_path)
                print(f"[ACTION_HANDLER] DEBUG: Saved annotated search region to: {abs_path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] WARNING: Failed to save annotated image: {e}")
        else:
            print(f"[ACTION_HANDLER] DEBUG: OCR failed or detected no text in search region")
            print(f"[ACTION_HANDLER] DEBUG: OCR success: {ocr_success}")
            print(f"[ACTION_HANDLER] DEBUG: OCR data: {ocr_data}")
        
        # Search for "Estimate #" or "Estimate" header text
        if ocr_success and ocr_data and ocr_data.get('text'):
            # Look for "Estimate" or "Estimate #" in the header
            estimate_header_texts = ["Estimate #", "Estimate", "estimate", "ESTIMATE"]
            estimate_header_y = None
            
            print(f"[ACTION_HANDLER] DEBUG: Searching for 'Estimate #' header in OCR results...")
            for i, text in enumerate(ocr_data['text']):
                if text:
                    # Check if this text contains "Estimate" (case insensitive)
                    text_lower = text.lower()
                    if any(header_text.lower() in text_lower for header_text in estimate_header_texts):
                        bbox = ocr_data['bbox'][i]
                        x1, y1, x2, y2 = map(int, bbox)
                        # Use the top Y position of the header text
                        estimate_header_y = y1 + header_search_y
                        print(f"[ACTION_HANDLER] ✓ Found 'Estimate #' header text: '{text}' at screen Y={estimate_header_y} (bbox Y={y1} + offset {header_search_y})")
                        break
            
            if estimate_header_y is not None:
                estimate_number_y = estimate_header_y
                print(f"[ACTION_HANDLER] ✓ Using 'Estimate #' header Y position: {estimate_number_y}")
            else:
                print(f"[ACTION_HANDLER] ✗ 'Estimate #' header not found in search region")
                print(f"[ACTION_HANDLER] DEBUG: OCR detected texts: {ocr_data['text']}")
        
        if estimate_number_y is None:
            estimate_number_y = 230
            print(f"[ACTION_HANDLER] WARNING: 'Estimate #' header not found, using default Y=230")
        
        # Save screenshot showing estimate number position
        try:
            annotated_screenshot = screenshot.copy()
            cv2.line(annotated_screenshot, (0, estimate_number_y), (screen_width, estimate_number_y), (255, 0, 0), 2)
            cv2.putText(annotated_screenshot, f"Estimate Number Y: {estimate_number_y}", (10, estimate_number_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            success, path = computer_vision_utils.save_screenshot(
                annotated_screenshot,
                filename="03_estimate_number_y_position.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved estimate number Y position screenshot to: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save estimate number screenshot: {e}")
        
        # Step 3: Detect bottom border using template matching
        print(f"[ACTION_HANDLER] Detecting black border below selected row using template matching...")
        bottom_border_y_screen = None
        
        # Determine search start Y: below blue row if found, otherwise use Y=230
        if found_blue and blue_y is not None and blue_h is not None:
            search_start_y = blue_y + blue_h
            print(f"[ACTION_HANDLER] Starting border search below blue row at Y={search_start_y}")
        else:
            search_start_y = 230
            print(f"[ACTION_HANDLER] Blue row not found, starting border search at Y={search_start_y}")
        # Expand search region to look further down (up to screen height minus taskbar area)
        search_end_y = min(search_start_y + 1000, screen_height - 100)
        crop_x_fixed = 205
        crop_width_fixed = 1500
        
        # Define search region for template matching
        search_region_x = crop_x_fixed
        search_region_y = search_start_y
        search_region_width = min(crop_width_fixed, screen_width - crop_x_fixed)
        search_region_height = search_end_y - search_start_y
        
        print(f"[ACTION_HANDLER] Searching for border template in region: x={search_region_x}, y={search_region_y}, w={search_region_width}, h={search_region_height}")
        
        # Save screenshot showing search region for template matching
        try:
            search_region_annotated = screenshot.copy()
            cv2.rectangle(search_region_annotated, (search_region_x, search_region_y), 
                         (search_region_x + search_region_width, search_region_y + search_region_height), 
                         (255, 165, 0), 2)  # Orange rectangle
            cv2.putText(search_region_annotated, "Border Template Search Region", 
                       (search_region_x, search_region_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            success, path = computer_vision_utils.save_screenshot(
                search_region_annotated,
                filename="04a_border_search_region.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved border search region screenshot to: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save border search region screenshot: {e}")
        
        # Load and match BorderLine template - use handler directory for local template
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        border_line_template_path = os.path.join(handler_dir, 'BorderLine.png')
        print(f"[ACTION_HANDLER] Loading border template from: {border_line_template_path}")
        
        found, confidence, position = computer_vision_utils.find_template_in_region(
            screenshot,
            border_line_template_path,
            (search_region_x, search_region_y, search_region_width, search_region_height),
            confidence=0.7
        )
        
        if found and position is not None:
            # Position is (center_x, center_y) in global coordinates
            _, bottom_border_y_screen = position
            print(f"[ACTION_HANDLER] ✓ Found bottom black border at screen Y={bottom_border_y_screen} (confidence: {confidence:.2f})")
        else:
            # Template not found - use full table (screen height minus taskbar area)
            max_bottom_y = max(0, screen_height - 100)
            bottom_border_y_screen = max_bottom_y
            print(f"[ACTION_HANDLER] WARNING: Black border template not found via template matching (confidence: {confidence:.2f if confidence else 'N/A'})")
            print(f"[ACTION_HANDLER] Using full table height: Y={bottom_border_y_screen} (screen_height={screen_height} - 100 for taskbar)")
        
        # Save screenshot showing bottom border position
        try:
            annotated_screenshot = screenshot.copy()
            # Draw the detected border line
            border_color = (0, 255, 0) if found else (0, 0, 255)  # Green if found, red if not
            cv2.line(annotated_screenshot, (0, bottom_border_y_screen), (screen_width, bottom_border_y_screen), border_color, 2)
            
            # Add label showing detection status
            status_text = f"Bottom Border Y: {bottom_border_y_screen}"
            if found:
                status_text += f" (Template Match, conf: {confidence:.2f})"
            else:
                status_text += " (Full Table - Template Not Found)"
            
            cv2.putText(annotated_screenshot, status_text, (10, bottom_border_y_screen - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, border_color, 2)
            
            # Also draw the search region rectangle
            cv2.rectangle(annotated_screenshot, (search_region_x, search_region_y), 
                         (search_region_x + search_region_width, search_region_y + search_region_height), 
                         (255, 165, 0), 1)  # Orange rectangle (lighter)
            
            success, path = computer_vision_utils.save_screenshot(
                annotated_screenshot,
                filename="04_bottom_border_detected.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved bottom border detection screenshot to: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save bottom border screenshot: {e}")
        
        # Step 4: Calculate crop region for inner table
        # Use estimate_number_y as the start and bottom_border_y_screen as the end
        crop_x = 205
        crop_y = estimate_number_y
        crop_width = 1500
        crop_height = bottom_border_y_screen - estimate_number_y
        
        print(f"[ACTION_HANDLER] Using estimate number Y={estimate_number_y} and bottom border Y={bottom_border_y_screen} for crop")
        print(f"[ACTION_HANDLER] === Crop Region Calculation ===")
        print(f"[ACTION_HANDLER] Screen dimensions: {screen_width}x{screen_height}")
        print(f"[ACTION_HANDLER] Blue row position: Y={blue_y}, H={blue_h}")
        print(f"[ACTION_HANDLER] Estimate number Y position: {estimate_number_y}")
        print(f"[ACTION_HANDLER] Black border detected at: Y={bottom_border_y_screen}")
        print(f"[ACTION_HANDLER] Initial crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        print(f"[ACTION_HANDLER] Max bottom Y (screen - 100): {max(0, screen_height - 100)}")
        if crop_height <= 0 or crop_width <= 0:
            return False, f"Invalid crop dimensions: width={crop_width}, height={crop_height}"
        if crop_x + crop_width > screen_width:
            crop_width = screen_width - crop_x
            print(f"[ACTION_HANDLER] Adjusted crop_width to {crop_width} to stay within screen bounds")
        if crop_y + crop_height > screen_height:
            crop_height = screen_height - crop_y
            print(f"[ACTION_HANDLER] Adjusted crop_height to {crop_height} to stay within screen bounds")
        max_bottom_y = max(0, screen_height - 100)
        if crop_y + crop_height > max_bottom_y:
            crop_height = max(0, max_bottom_y - crop_y)
            print(f"[ACTION_HANDLER] Adjusted crop_height to {crop_height} to avoid taskbar region")
        
        # Final validation after all adjustments
        print(f"[ACTION_HANDLER] === After Adjustments ===")
        print(f"[ACTION_HANDLER] Final crop region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}")
        
        if crop_height <= 0 or crop_width <= 0:
            error_msg = f"Invalid crop dimensions after adjustments: width={crop_width}, height={crop_height}. "
            error_msg += f"Estimate Y: {estimate_number_y}, Bottom border Y: {bottom_border_y_screen}. "
            error_msg += "The inner table region is too small or collapsed. The expanded row may not have enough content."
            print(f"[ACTION_HANDLER] ERROR: {error_msg}")
            return False, error_msg
        
        if crop_y < 0 or crop_x < 0:
            return False, f"Invalid crop position: x={crop_x}, y={crop_y}. Position cannot be negative."
        
        # Check minimum height requirement (at least 20 pixels for a meaningful table)
        if crop_height < 20:
            warning_msg = f"Warning: Crop height is very small ({crop_height}px). Inner table may not be fully visible."
            print(f"[ACTION_HANDLER] {warning_msg}")
        
        # Save screenshot showing crop region before cropping
        try:
            annotated_screenshot = screenshot.copy()
            cv2.rectangle(annotated_screenshot, (crop_x, crop_y), (crop_x + crop_width, crop_y + crop_height), (255, 255, 0), 3)
            
            # Add label showing crop boundaries
            label_text = f"Crop: {crop_width}x{crop_height} (Estimate Y={estimate_number_y} to Border Y={bottom_border_y_screen})"
            cv2.putText(annotated_screenshot, label_text, (crop_x, crop_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Draw lines at crop boundaries
            cv2.line(annotated_screenshot, (crop_x, crop_y), (crop_x + crop_width, crop_y), (255, 255, 0), 2)  # Top
            cv2.line(annotated_screenshot, (crop_x, crop_y + crop_height), (crop_x + crop_width, crop_y + crop_height), (255, 255, 0), 2)  # Bottom
            success, path = computer_vision_utils.save_screenshot(
                annotated_screenshot,
                filename="05_crop_region_marked.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved crop region screenshot to: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save crop region screenshot: {e}")
        
        cropped_inner_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
        
        if cropped_inner_table is None:
            error_msg = f"Failed to crop inner table region. Region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}"
            print(f"[ACTION_HANDLER] ERROR: {error_msg}")
            return False, error_msg
        
        # Save debug image (keep existing debug path for compatibility)
        try:
            debug_path = "debug_images/inner_table_cropped.png"
            os.makedirs("debug_images", exist_ok=True)
            cv2.imwrite(debug_path, cropped_inner_table)
            abs_path = os.path.abspath(debug_path)
            print(f"[ACTION_HANDLER] Saved cropped inner table image to: {abs_path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save debug image: {e}")
        
        # Save cropped inner table to step screenshots directory
        try:
            success, path = computer_vision_utils.save_screenshot(
                cropped_inner_table,
                filename="06_cropped_inner_table.png",
                output_dir=step_screenshots_dir
            )
            if success:
                print(f"[ACTION_HANDLER] Saved cropped inner table to step screenshots: {path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save cropped inner table screenshot: {e}")
        
        # Step 5: Search for date in inner table and click
        # First attempt with ColumnLineSecondTable.png
        print(f"[ACTION_HANDLER] === First check with ColumnLineSecondTable.png ===")
        # Get handler directory for local template
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        column_line_path = os.path.join(handler_dir, 'ColumnLineSecondTable.png')
        found, msg, matches = table_utils.search_second_table_by_date(
            begin_date=begin_date,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height,
            template_path=column_line_path
        )
        
        if found and matches:
            print(f"[ACTION_HANDLER] ✓ Found {len(matches)} matching row(s) in first check")
            match_to_click = matches[0]
            print(f"[ACTION_HANDLER] Using first match (row {match_to_click['row_index'] + 1})")
            click_x = match_to_click['click_x']
            click_y = match_to_click['click_y']
            print(f"[ACTION_HANDLER] Date position - X: {click_x}, Y: {click_y}")
            print(f"[ACTION_HANDLER] Match details: row_index={match_to_click.get('row_index', 'N/A')}, text='{match_to_click.get('matched_text', 'N/A')[:50]}...'")
            if click_x is None or click_y is None:
                return False, f"Invalid click coordinates: x={click_x}, y={click_y}"
            
            # Save screenshot showing the match before clicking
            try:
                annotated_screenshot = screenshot.copy()
                cv2.circle(annotated_screenshot, (click_x, click_y), 10, (0, 255, 0), -1)
                cv2.circle(annotated_screenshot, (click_x, click_y), 15, (0, 255, 0), 2)
                cv2.putText(annotated_screenshot, f"Match Found: {begin_date}", (click_x - 100, click_y - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                success, path = computer_vision_utils.save_screenshot(
                    annotated_screenshot,
                    filename="07_date_match_found_before_click.png",
                    output_dir=step_screenshots_dir
                )
                if success:
                    print(f"[ACTION_HANDLER] Saved match found screenshot to: {path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] Warning: Failed to save match screenshot: {e}")
            
            print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
            pyautogui.moveTo(click_x, click_y, duration=0.2)
            time.sleep(0.2)
            success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
            if not success:
                return False, f"Failed to double-click on date: {action_msg}"
            
            # Save screenshot after clicking
            try:
                time.sleep(0.3)  # Wait a bit for UI to update
                post_click_screenshot = computer_vision_utils.take_screenshot()
                if post_click_screenshot is not None:
                    success, path = computer_vision_utils.save_screenshot(
                        post_click_screenshot,
                        filename="08_after_double_click.png",
                        output_dir=step_screenshots_dir
                    )
                    if success:
                        print(f"[ACTION_HANDLER] Saved post-click screenshot to: {path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] Warning: Failed to save post-click screenshot: {e}")
            
            print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
            time.sleep(0.5)
            match_count_str = f"{len(matches)} match" + ("es" if len(matches) != 1 else "")
            return True, f"Row found and double-clicked! Begin date: '{begin_date}' ({match_count_str})"
        
        # No match found in first check - start scrolling with RowColumnLineSecondTable.png
        print(f"[ACTION_HANDLER] ✗ No match in first check: {msg}")
        print(f"[ACTION_HANDLER] === Starting scroll search with RowColumnLineSecondTable.png ===")
        
        # Load the scrolling column separator template from local handler folder
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        row_column_line_path = os.path.join(handler_dir, 'RowColumnLineSecondTable.png')
        scroll_template = computer_vision_utils.load_image(row_column_line_path)
        if scroll_template is None:
            return False, f"Failed to load RowColumnLineSecondTable template for scrolling from {row_column_line_path}"
        
        # Define scroll crop region for checking
        scroll_crop_x = 205
        scroll_crop_y = 230
        scroll_crop_width = 1450
        scroll_crop_height = 780
        
        # Define target region for checking - use the entire scroll crop region
        target_region_offset_y = 0  # Start checking from top of scroll crop
        target_region_height = 780  # Check entire height
        
        # Calculate center position for scrolling
        table_center_x = scroll_crop_x + scroll_crop_width // 2
        table_center_y = scroll_crop_y + scroll_crop_height // 2
        
        max_scroll_attempts = 20
        scroll_amount = -150  # Negative scrolls down (larger value = scroll farther)
        
        # Helper function to check target region
        def check_target_region(screenshot, scroll_num):
            """Check if begin_date exists in the target region."""
            # Define the target region crop coordinates using scroll crop region
            target_crop_y = scroll_crop_y + target_region_offset_y
            target_crop_height = target_region_height
            
            # Crop to target region only
            target_region_img = computer_vision_utils.crop_image(
                screenshot, scroll_crop_x, target_crop_y, scroll_crop_width, target_crop_height
            )
            
            if target_region_img is None:
                print(f"[ACTION_HANDLER] Warning: Failed to crop target region")
                return False, None, None
            
            print(f"[ACTION_HANDLER] Checking full region: x={scroll_crop_x}, y={target_crop_y}, w={scroll_crop_width}, h={target_crop_height}")
            
            # Click on a row in the region to select it
            select_row_x = scroll_crop_x + 100
            select_row_y = target_crop_y + 50  # Click near top of region
            print(f"[ACTION_HANDLER] Clicking row at ({select_row_x}, {select_row_y}) to select it")
            success, click_msg = actions.click_at_position(select_row_x, select_row_y, clicks=1, button='left')
            if not success:
                print(f"[ACTION_HANDLER] Warning: Failed to click row: {click_msg}")
            time.sleep(0.3)
            
            # Take fresh screenshot after clicking
            fresh_screenshot = computer_vision_utils.take_screenshot()
            if fresh_screenshot is None:
                print(f"[ACTION_HANDLER] Warning: Failed to take screenshot after clicking")
                return False, None, None
            
            # Crop target region from fresh screenshot
            target_region_img = computer_vision_utils.crop_image(
                fresh_screenshot, scroll_crop_x, target_crop_y, scroll_crop_width, target_crop_height
            )
            
            if target_region_img is None:
                print(f"[ACTION_HANDLER] Warning: Failed to crop target region from fresh screenshot")
                return False, None, None
            
            # Detect column separators with RowColumnLineSecondTable.png
            print(f"[ACTION_HANDLER] Separating columns with RowColumnLineSecondTable.png...")
            separator_matches = column_detection.detect_column_separators(target_region_img, scroll_template, match_threshold=0.85)
            
            if not separator_matches:
                print(f"[ACTION_HANDLER] No separators found in full region")
                return False, None, None
            
            # Extract only column 5
            column_5_img = column_detection.get_column_5_image(
                target_region_img, 
                separator_matches, 
                scroll_template.shape[1],
                debug=True
            )
            
            if column_5_img is None:
                print(f"[ACTION_HANDLER] Failed to extract column 5 from full region")
                return False, None, None
            
            # Perform OCR on column 5 only
            scanner = ocr_utils.TextScanner()
            ocr_success, ocr_data = scanner.get_text_data(column_5_img)
            
            if not ocr_success or not ocr_data or not ocr_data.get('text'):
                print(f"[ACTION_HANDLER] OCR failed in full region")
                return False, None, None
            
            print(f"[ACTION_HANDLER] OCR found {len(ocr_data['text'])} text elements in full region")
            
            # Save debug screenshot with annotations
            try:
                os.makedirs("debug_images", exist_ok=True)
                
                # Create annotated image showing all detected text
                annotated_img = column_5_img.copy()
                
                # Draw all OCR detections in green
                for i, (text, bbox, conf) in enumerate(zip(ocr_data['text'], ocr_data['bbox'], ocr_data['confidence'])):
                    x1, y1, x2, y2 = map(int, bbox)
                    # Draw bounding box in green
                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Add text label with index
                    label = f"{i}:{text[:20]}"
                    cv2.putText(annotated_img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                
                debug_path = f"debug_images/multinetwork_full_region_scroll_{scroll_num}.png"
                cv2.imwrite(debug_path, annotated_img)
                abs_path = os.path.abspath(debug_path)
                print(f"[ACTION_HANDLER] Saved annotated full region to: {abs_path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] Warning: Failed to save debug screenshot: {e}")
            
            # Check if begin_date is in the OCR results - use FIRST match only
            # Skip matches in the header row (top portion of the region)
            begin_date_str = str(begin_date)
            begin_date_normalized = date_utils.normalize_date(begin_date_str)
            
            # Estimate header height (typically 20-40 pixels from top)
            header_height_estimate = 40
            column_5_height = column_5_img.shape[0]
            
            first_match_found = False
            matched_bbox = None
            matched_text = None
            matched_index = None
            
            for i, text in enumerate(ocr_data['text']):
                if text:
                    # Get the bbox to check if it's in the header
                    bbox = ocr_data['bbox'][i]
                    x1, y1, x2, y2 = map(int, bbox)
                    center_y = (y1 + y2) // 2
                    
                    # Skip if this match is in the header row (top portion)
                    if center_y < header_height_estimate:
                        print(f"[ACTION_HANDLER] Skipping match '{text}' at Y={center_y} (likely in header row)")
                        continue
                    
                    text_normalized = date_utils.normalize_date(text)
                    if begin_date_normalized in text_normalized or begin_date_str in text:
                        print(f"[ACTION_HANDLER] ✓ Found FIRST matching date in full region: '{text}' (index {i}, Y={center_y})")
                        
                        matched_bbox = (x1, y1, x2, y2)
                        matched_text = text
                        matched_index = i
                        
                        # Convert from column 5 image coordinates to original target region coordinates
                        click_y_local = (y1 + y2) // 2
                        
                        # For X, we need to get the column 5's left edge position in the original image
                        # and add the relative X position within column 5
                        # First, calculate column boundaries to find column 5's left edge
                        column_split_positions = []
                        for position, score in separator_matches:
                            x_position = position[0]
                            split_center = x_position + (scroll_template.shape[1] // 2)
                            column_split_positions.append(split_center)
                        
                        unique_split_positions = sorted(set(column_split_positions))
                        image_width = target_region_img.shape[1]
                        all_column_boundaries = [0] + unique_split_positions + [image_width]
                        
                        # Column 5 is at index 4 (0-based)
                        if len(all_column_boundaries) >= 6:
                            column_5_left = all_column_boundaries[4]
                            # X position within column 5 image + column 5's left edge in original image
                            click_x_local = column_5_left + ((x1 + x2) // 2)
                        else:
                            # Fallback: use center of column 5 image
                            column_5_width = column_5_img.shape[1]
                            click_x_local = ((x1 + x2) // 2)
                        
                        # Convert to screen coordinates (add target region offsets)
                        click_x = click_x_local + scroll_crop_x
                        click_y = click_y_local + target_crop_y
                        
                        print(f"[ACTION_HANDLER] Using FIRST match - Click coordinates: local=({click_x_local}, {click_y_local}), screen=({click_x}, {click_y})")
                        first_match_found = True
                        
                        # Save debug screenshot highlighting the matched text
                        try:
                            matched_annotated_img = column_5_img.copy()
                            
                            # Draw all OCR detections in green
                            for j, (txt, box, conf) in enumerate(zip(ocr_data['text'], ocr_data['bbox'], ocr_data['confidence'])):
                                bx1, by1, bx2, by2 = map(int, box)
                                cv2.rectangle(matched_annotated_img, (bx1, by1), (bx2, by2), (0, 255, 0), 1)
                                lbl = f"{j}:{txt[:15]}"
                                cv2.putText(matched_annotated_img, lbl, (bx1, by1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                            
                            # Highlight the matched text in RED with thicker border
                            mx1, my1, mx2, my2 = matched_bbox
                            cv2.rectangle(matched_annotated_img, (mx1, my1), (mx2, my2), (0, 0, 255), 3)
                            match_label = f"MATCH: {matched_text}"
                            cv2.putText(matched_annotated_img, match_label, (mx1, my1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            
                            # Draw click position
                            local_click_x = (mx1 + mx2) // 2
                            local_click_y = (my1 + my2) // 2
                            cv2.circle(matched_annotated_img, (local_click_x, local_click_y), 5, (255, 0, 0), -1)
                            
                            matched_debug_path = f"debug_images/multinetwork_MATCHED_scroll_{scroll_num}.png"
                            cv2.imwrite(matched_debug_path, matched_annotated_img)
                            abs_path = os.path.abspath(matched_debug_path)
                            print(f"[ACTION_HANDLER] Saved MATCHED screenshot to: {abs_path}")
                        except Exception as e:
                            print(f"[ACTION_HANDLER] Warning: Failed to save matched debug screenshot: {e}")
                        
                        # Return immediately with first match - don't check other matches
                        return True, click_x, click_y
            
            if not first_match_found:
                print(f"[ACTION_HANDLER] No match found in full region")
            return False, None, None
        
        # Check full region before scrolling
        print(f"\n[ACTION_HANDLER] ========== Checking full region before scrolling ==========")
        initial_screenshot = computer_vision_utils.take_screenshot()
        if initial_screenshot is not None:
            # Save screenshot before checking region
            try:
                success, path = computer_vision_utils.save_screenshot(
                    initial_screenshot,
                    filename="09_before_region_check.png",
                    output_dir=step_screenshots_dir
                )
                if success:
                    print(f"[ACTION_HANDLER] Saved pre-region-check screenshot to: {path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] Warning: Failed to save pre-region-check screenshot: {e}")
            
            found_in_region, click_x, click_y = check_target_region(initial_screenshot, 0)
            if found_in_region:
                # Save screenshot showing match in full region
                try:
                    annotated_screenshot = initial_screenshot.copy()
                    cv2.circle(annotated_screenshot, (click_x, click_y), 10, (0, 255, 0), -1)
                    cv2.circle(annotated_screenshot, (click_x, click_y), 15, (0, 255, 0), 2)
                    cv2.putText(annotated_screenshot, f"Match in Full Region: {begin_date}", (click_x - 150, click_y - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    success, path = computer_vision_utils.save_screenshot(
                        annotated_screenshot,
                        filename="10_match_found_in_full_region.png",
                        output_dir=step_screenshots_dir
                    )
                    if success:
                        print(f"[ACTION_HANDLER] Saved full region match screenshot to: {path}")
                except Exception as e:
                    print(f"[ACTION_HANDLER] Warning: Failed to save full region match screenshot: {e}")
                
                print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.2)
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
                if not success:
                    return False, f"Failed to double-click on date: {action_msg}"
                
                # Save screenshot after clicking
                try:
                    time.sleep(0.3)
                    post_click_screenshot = computer_vision_utils.take_screenshot()
                    if post_click_screenshot is not None:
                        success, path = computer_vision_utils.save_screenshot(
                            post_click_screenshot,
                            filename="11_after_full_region_click.png",
                            output_dir=step_screenshots_dir
                        )
                        if success:
                            print(f"[ACTION_HANDLER] Saved post-click screenshot to: {path}")
                except Exception as e:
                    print(f"[ACTION_HANDLER] Warning: Failed to save post-click screenshot: {e}")
                
                print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
                time.sleep(0.5)
                return True, f"Row found in full region and double-clicked! Begin date: '{begin_date}'"
        
        # Not in full region - start scrolling to bring rows up
        print(f"[ACTION_HANDLER] Begin date not in full region, starting scroll to move rows up...")
        
        for scroll_attempt in range(1, max_scroll_attempts + 1):
            print(f"\n[ACTION_HANDLER] ========== Scroll attempt {scroll_attempt}/{max_scroll_attempts} ==========")
            
            # Move to table center and scroll
            pyautogui.moveTo(table_center_x, table_center_y, duration=0.2)
            time.sleep(0.2)
            pyautogui.scroll(scroll_amount)
            time.sleep(0.3)
            
            # Take screenshot after scrolling
            scroll_screenshot = computer_vision_utils.take_screenshot()
            if scroll_screenshot is None:
                print(f"[ACTION_HANDLER] Warning: Failed to take screenshot at scroll {scroll_attempt}")
                continue
            
            # Save screenshot for each scroll attempt
            try:
                success, path = computer_vision_utils.save_screenshot(
                    scroll_screenshot,
                    filename=f"12_scroll_attempt_{scroll_attempt:02d}.png",
                    output_dir=step_screenshots_dir
                )
                if success:
                    print(f"[ACTION_HANDLER] Saved scroll attempt {scroll_attempt} screenshot to: {path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] Warning: Failed to save scroll screenshot: {e}")
            
            # Check target region
            found_in_region, click_x, click_y = check_target_region(scroll_screenshot, scroll_attempt)
            
            if found_in_region:
                # Save screenshot showing match found during scroll
                try:
                    annotated_screenshot = scroll_screenshot.copy()
                    cv2.circle(annotated_screenshot, (click_x, click_y), 10, (0, 255, 0), -1)
                    cv2.circle(annotated_screenshot, (click_x, click_y), 15, (0, 255, 0), 2)
                    cv2.putText(annotated_screenshot, f"Match After Scroll {scroll_attempt}: {begin_date}", 
                               (click_x - 150, click_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    success, path = computer_vision_utils.save_screenshot(
                        annotated_screenshot,
                        filename=f"13_match_found_after_scroll_{scroll_attempt:02d}.png",
                        output_dir=step_screenshots_dir
                    )
                    if success:
                        print(f"[ACTION_HANDLER] Saved scroll match screenshot to: {path}")
                except Exception as e:
                    print(f"[ACTION_HANDLER] Warning: Failed to save scroll match screenshot: {e}")
                
                print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.2)
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
                
                if not success:
                    return False, f"Failed to double-click on date: {action_msg}"
                
                # Save screenshot after clicking
                try:
                    time.sleep(0.3)
                    post_click_screenshot = computer_vision_utils.take_screenshot()
                    if post_click_screenshot is not None:
                        success, path = computer_vision_utils.save_screenshot(
                            post_click_screenshot,
                            filename=f"14_after_scroll_{scroll_attempt:02d}_click.png",
                            output_dir=step_screenshots_dir
                        )
                        if success:
                            print(f"[ACTION_HANDLER] Saved post-scroll-click screenshot to: {path}")
                except Exception as e:
                    print(f"[ACTION_HANDLER] Warning: Failed to save post-scroll-click screenshot: {e}")
                
                print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
                time.sleep(0.5)
                return True, f"Row found and double-clicked after {scroll_attempt} scroll(s)! Begin date: '{begin_date}'"
            
            print(f"[ACTION_HANDLER] No match at scroll {scroll_attempt}, continuing...")
        
        return False, f"Begin date not found after {max_scroll_attempts} scroll attempts"
    except Exception as e:
        return False, f"Error finding row by begin_date: {e}"


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying action"
    return False, f"Failed after {max_attempts} attempts"



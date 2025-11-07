#!/usr/bin/env python3
"""
Handler for: Open Multinetwork Row by Date

Find and double-click on a row in the second table (within expanded row) by begin_date.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import table_utils
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import ocr_utils
import time
import pyautogui
import cv2
import numpy as np


def action(begin_date: str = "", estimate_number: str = "", **kwargs) -> Tuple[bool, str]:
    if not begin_date:
        return False, "Missing begin_date parameter"
    
    print(f"[ACTION_HANDLER] Searching for begin_date: '{begin_date}' in second table")
    print(f"[ACTION_HANDLER] Estimate number for reference: '{estimate_number}'")
    
    try:
        time.sleep(4)
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Step 1: Find blue highlighted row using computer vision utils
        print(f"[ACTION_HANDLER] Detecting blue highlighted row (expanded row)...")
        found_blue, row_info = computer_vision_utils.find_blue_highlighted_row(screenshot, exclude_bottom_pixels=100)
        
        if not found_blue or row_info is None:
            return False, "Could not find blue highlighted row (expanded row not visible)"
        
        blue_x = row_info['x']
        blue_y = row_info['y']
        blue_w = row_info['width']
        blue_h = row_info['height']
        
        print(f"[ACTION_HANDLER] Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        
        # Step 2: Find estimate number Y position using OCR utils
        print(f"[ACTION_HANDLER] ===== ESTIMATE NUMBER DEBUG =====")
        print(f"[ACTION_HANDLER] Estimate number parameter value: '{estimate_number}'")
        print(f"[ACTION_HANDLER] Estimate number type: {type(estimate_number)}")
        print(f"[ACTION_HANDLER] Estimate number is truthy: {bool(estimate_number)}")
        print(f"[ACTION_HANDLER] Searching for estimate number to determine crop Y position...")
        estimate_number_y = None
        
        # Always save debug images to see what OCR detects in the blue row region
        search_region = screenshot[blue_y:blue_y + blue_h, blue_x:blue_x + blue_w]
        
        # Save debug image of the search region
        try:
            import os
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
        
        # Only proceed with matching if estimate_number is provided
        if estimate_number and ocr_success and ocr_data and ocr_data.get('text'):
            # Check for exact and partial matches
            print(f"[ACTION_HANDLER] DEBUG: Checking for matches with estimate number '{estimate_number}':")
            exact_matches = []
            partial_matches = []
            for i, text in enumerate(ocr_data['text']):
                if text == estimate_number:
                    exact_matches.append((i, text))
                    print(f"[ACTION_HANDLER] DEBUG:   ✓ EXACT match at index {i}: '{text}'")
                elif estimate_number in text:
                    partial_matches.append((i, text))
                    print(f"[ACTION_HANDLER] DEBUG:   ~ Partial match at index {i}: '{text}' contains '{estimate_number}'")
                elif text in estimate_number:
                    partial_matches.append((i, text))
                    print(f"[ACTION_HANDLER] DEBUG:   ~ Partial match at index {i}: '{estimate_number}' contains '{text}'")
            
            if not exact_matches and not partial_matches:
                print(f"[ACTION_HANDLER] DEBUG:   ✗ NO MATCHES FOUND for '{estimate_number}'")
                print(f"[ACTION_HANDLER] DEBUG: Possible reasons:")
                print(f"[ACTION_HANDLER] DEBUG:   - OCR may have misread the estimate number")
                print(f"[ACTION_HANDLER] DEBUG:   - Estimate number may not be visible in the search region")
                print(f"[ACTION_HANDLER] DEBUG:   - Text may be too small, blurry, or low contrast")
                print(f"[ACTION_HANDLER] DEBUG:   - Check the saved images above to verify")
            
            # Now call the actual function to find the position
            found_text, y_pos = ocr_utils.find_topmost_text_position(
                estimate_number, 
                search_region, 
                blue_x, 
                blue_y
            )
            
            if found_text and y_pos is not None:
                estimate_number_y = y_pos
                print(f"[ACTION_HANDLER] ✓ Found estimate number at screen Y={estimate_number_y}")
            else:
                print(f"[ACTION_HANDLER] ✗ Estimate number '{estimate_number}' NOT found in search region")
        
        if estimate_number_y is None:
            estimate_number_y = 230
            print(f"[ACTION_HANDLER] WARNING: Estimate number not found, using default Y=230")
        
        # Step 3: Detect bottom border using template matching
        print(f"[ACTION_HANDLER] Detecting black border below selected row using template matching...")
        bottom_border_y_screen = None
        search_start_y = blue_y + blue_h
        search_end_y = min(search_start_y + 200, screen_height)
        crop_x_fixed = 205
        crop_width_fixed = 1500
        
        # Define search region for template matching
        search_region_x = crop_x_fixed
        search_region_y = search_start_y
        search_region_width = min(crop_width_fixed, screen_width - crop_x_fixed)
        search_region_height = search_end_y - search_start_y
        
        # Load and match BorderLine template
        border_line_template_path = "src/workflow_module/actions/handlers/open_multinetwork_row_by_date/BorderLine.png"
        found, confidence, position = computer_vision_utils.find_template_in_region(
            screenshot,
            border_line_template_path,
            (search_region_x, search_region_y, search_region_width, search_region_height),
            confidence=0.7
        )
        
        if found and position is not None:
            # Position is (center_x, center_y) in global coordinates
            _, bottom_border_y_screen = position
            print(f"[ACTION_HANDLER] Found bottom black border at screen Y={bottom_border_y_screen} (confidence: {confidence:.2f})")
        else:
            # Use default height of 780 when border not found
            bottom_border_y_screen = estimate_number_y + 780
            print(f"[ACTION_HANDLER] WARNING: Black border not found via template matching, using default height: Y={bottom_border_y_screen}")
        
        # Step 4: Calculate crop region for inner table
        crop_x = 205
        crop_y = estimate_number_y
        crop_width = 1500
        crop_height = bottom_border_y_screen - estimate_number_y
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
        
        cropped_inner_table = computer_vision_utils.crop_image(screenshot, crop_x, crop_y, crop_width, crop_height)
        
        if cropped_inner_table is None:
            error_msg = f"Failed to crop inner table region. Region: x={crop_x}, y={crop_y}, w={crop_width}, h={crop_height}"
            print(f"[ACTION_HANDLER] ERROR: {error_msg}")
            return False, error_msg
        
        # Save debug image
        try:
            import os
            debug_path = "debug_images/inner_table_cropped.png"
            os.makedirs("debug_images", exist_ok=True)
            cv2.imwrite(debug_path, cropped_inner_table)
            abs_path = os.path.abspath(debug_path)
            print(f"[ACTION_HANDLER] Saved cropped inner table image to: {abs_path}")
        except Exception as e:
            print(f"[ACTION_HANDLER] Warning: Failed to save debug image: {e}")
        
        # Step 5: Search for date in inner table and click
        # First attempt with ColumnLineSecondTable.png
        print(f"[ACTION_HANDLER] === First check with ColumnLineSecondTable.png ===")
        found, msg, matches = table_utils.search_second_table_by_date(
            begin_date=begin_date,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_width=crop_width,
            crop_height=crop_height
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
            print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
            pyautogui.moveTo(click_x, click_y, duration=0.2)
            time.sleep(0.2)
            success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
            if not success:
                return False, f"Failed to double-click on date: {action_msg}"
            print(f"[ACTION_HANDLER] ✓ Double-click on date completed successfully")
            time.sleep(0.5)
            match_count_str = f"{len(matches)} match" + ("es" if len(matches) != 1 else "")
            return True, f"Row found and double-clicked! Begin date: '{begin_date}' ({match_count_str})"
        
        # No match found in first check - start scrolling with RowColumnLineSecondTable.png
        print(f"[ACTION_HANDLER] ✗ No match in first check: {msg}")
        print(f"[ACTION_HANDLER] === Starting scroll search with RowColumnLineSecondTable.png ===")
        
        # Load the scrolling column separator template
        scroll_template = computer_vision_utils.load_image("src/workflow_module/actions/assets/RowColumnLineSecondTable.png")
        if scroll_template is None:
            return False, "Failed to load RowColumnLineSecondTable template for scrolling"
        
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
            separator_matches = table_utils.detect_column_separators(target_region_img, scroll_template, match_threshold=0.85)
            
            if not separator_matches:
                print(f"[ACTION_HANDLER] No separators found in full region")
                return False, None, None
            
            # Create separated columns image
            separated_img = table_utils.create_separated_columns_image(
                target_region_img, 
                separator_matches, 
                scroll_template.shape[1],
                padding_width=10
            )
            
            if separated_img is None:
                print(f"[ACTION_HANDLER] Failed to separate columns in full region")
                return False, None, None
            
            # Perform OCR on separated columns
            scanner = ocr_utils.TextScanner()
            ocr_success, ocr_data = scanner.get_text_data(separated_img)
            
            if not ocr_success or not ocr_data or not ocr_data.get('text'):
                print(f"[ACTION_HANDLER] OCR failed in full region")
                return False, None, None
            
            print(f"[ACTION_HANDLER] OCR found {len(ocr_data['text'])} text elements in full region")
            
            # Save debug screenshot with annotations
            try:
                import os
                os.makedirs("debug_images", exist_ok=True)
                
                # Create annotated image showing all detected text
                annotated_img = separated_img.copy()
                
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
            begin_date_str = str(begin_date)
            begin_date_normalized = table_utils.normalize_date(begin_date_str)
            
            first_match_found = False
            matched_bbox = None
            matched_text = None
            matched_index = None
            
            for i, text in enumerate(ocr_data['text']):
                if text:
                    text_normalized = table_utils.normalize_date(text)
                    if begin_date_normalized in text_normalized or begin_date_str in text:
                        print(f"[ACTION_HANDLER] ✓ Found FIRST matching date in full region: '{text}' (index {i})")
                        
                        # Get the bbox for the match
                        bbox = ocr_data['bbox'][i]
                        x1, y1, x2, y2 = map(int, bbox)
                        matched_bbox = (x1, y1, x2, y2)
                        matched_text = text
                        matched_index = i
                        
                        # Convert from separated image coordinates to original target region coordinates
                        click_y_local = (y1 + y2) // 2
                        
                        # For X, we need to scale back if the image width changed
                        original_width = target_region_img.shape[1]
                        separated_width = separated_img.shape[1]
                        scale_factor = original_width / separated_width
                        click_x_local = int(((x1 + x2) // 2) * scale_factor)
                        
                        # Convert to screen coordinates (add target region offsets)
                        click_x = click_x_local + scroll_crop_x
                        click_y = click_y_local + target_crop_y
                        
                        print(f"[ACTION_HANDLER] Using FIRST match - Click coordinates: local=({click_x_local}, {click_y_local}), screen=({click_x}, {click_y})")
                        first_match_found = True
                        
                        # Save debug screenshot highlighting the matched text
                        try:
                            matched_annotated_img = separated_img.copy()
                            
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
            found_in_region, click_x, click_y = check_target_region(initial_screenshot, 0)
            if found_in_region:
                print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.2)
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
                if not success:
                    return False, f"Failed to double-click on date: {action_msg}"
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
            
            # Check target region
            found_in_region, click_x, click_y = check_target_region(scroll_screenshot, scroll_attempt)
            
            if found_in_region:
                print(f"[ACTION_HANDLER] Double-clicking on begin_date at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.2)
                success, action_msg = actions.click_at_position(click_x, click_y, clicks=2, button='left')
                
                if not success:
                    return False, f"Failed to double-click on date: {action_msg}"
                
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



#!/usr/bin/env python3
"""
Handler for: Multinetwork Popup

Detects the Multi-Network instruction popup in the middle of the screen,
and clicks on "Open as Multi-Network Instruction" option.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import ocr_utils
import time
import pyautogui
import cv2
import os
import numpy as np


def action(**kwargs) -> Tuple[bool, str]:
    """
    Detect and handle the Multi-Network popup.
    
    Steps:
    1. Take a screenshot
    2. Look for the popup template in the middle of the screen
    3. If found, click on "Open as Multi-Network Instruction" button
    
    Returns:
        Tuple of (success: bool, message)
    """
    print("[ACTION_HANDLER] Checking for Multi-Network popup in middle of screen...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        screen_height, screen_width = screenshot.shape[:2]
        print(f"[ACTION_HANDLER] Screen size: {screen_width}x{screen_height}")
        
        # Define center region to search (middle 60% of screen)
        center_ratio = 0.6
        region_width = int(screen_width * center_ratio)
        region_height = int(screen_height * center_ratio)
        region_x = (screen_width - region_width) // 2
        region_y = (screen_height - region_height) // 2
        
        print(f"[ACTION_HANDLER] Searching center region: ({region_x}, {region_y}, {region_width}, {region_height})")
        
        # Search for the popup template
        template_path = "src/workflow_module/actions/assets/MutliNetworkPopUp.png"
        
        found, confidence, position = computer_vision_utils.find_template_in_region(
            screenshot=screenshot,
            template_path=template_path,
            region=(region_x, region_y, region_width, region_height),
            confidence=0.7
        )
        
        if not found or position is None:
            print(f"[ACTION_HANDLER] Multi-Network popup not found in center region (confidence: {confidence:.2f})")
            print(f"[ACTION_HANDLER] Continuing workflow - popup may not be required")
            return True, f"Multi-Network popup not detected, continuing workflow (confidence: {confidence:.2f})"
        
        popup_x, popup_y = position
        print(f"[ACTION_HANDLER] ✓ Multi-Network popup detected at ({popup_x}, {popup_y}) with confidence {confidence:.2f}")
        
        # Use OCR to find the exact position of "Open as Multi-Network Instruction" button
        print(f"[ACTION_HANDLER] Using OCR to locate 'Open as Multi-Network Instruction' button...")
        
        # Load template to get popup dimensions
        template = computer_vision_utils.load_image(template_path)
        if template is None:
            return False, "Failed to load popup template for dimension calculation"
        
        template_height, template_width = template.shape[:2]
        
        # Define search region around the popup (expand a bit to ensure we capture the buttons)
        search_padding = 50
        search_x = max(0, popup_x - template_width // 2 - search_padding)
        search_y = max(0, popup_y - template_height // 2 - search_padding)
        search_w = min(template_width + 2 * search_padding, screen_width - search_x)
        search_h = min(template_height + 2 * search_padding, screen_height - search_y)
        
        popup_region = screenshot[search_y:search_y + search_h, search_x:search_x + search_w]
        
        # Save popup region for debugging
        try:
            debug_dir = "debug_images"
            os.makedirs(debug_dir, exist_ok=True)
            popup_region_path = os.path.join(debug_dir, "multinetwork_popup_region.png")
            cv2.imwrite(popup_region_path, popup_region)
            print(f"[ACTION_HANDLER] DEBUG: Saved popup region to: {os.path.abspath(popup_region_path)}")
            print(f"[ACTION_HANDLER] DEBUG: Popup region crop: x={search_x}, y={search_y}, w={search_w}, h={search_h}")
        except Exception as e:
            print(f"[ACTION_HANDLER] WARNING: Failed to save popup region: {e}")
        
        # Use OCR to find all text in the popup region
        scanner = ocr_utils.TextScanner()
        ocr_success, ocr_data = scanner.get_text_data(popup_region)
        
        if not ocr_success or not ocr_data or not ocr_data.get('text'):
            print(f"[ACTION_HANDLER] WARNING: OCR failed to detect text in popup region")
            print(f"[ACTION_HANDLER] Falling back to fixed offset method")
            click_offset_y = 70
            click_x = popup_x
            click_y = popup_y + click_offset_y
        else:
            print(f"[ACTION_HANDLER] DEBUG: OCR detected {len(ocr_data['text'])} text elements in popup:")
            for i, (text, bbox, conf) in enumerate(zip(ocr_data['text'], ocr_data['bbox'], ocr_data['confidence'])):
                x1, y1, x2, y2 = map(int, bbox)
                print(f"[ACTION_HANDLER] DEBUG:   [{i}] Text: '{text}' | Bbox: ({x1},{y1})-({x2},{y2}) | Confidence: {conf:.2f}")
            
            # Create annotated popup region showing detected text
            try:
                annotated_popup = popup_region.copy()
                for i, (text, bbox) in enumerate(zip(ocr_data['text'], ocr_data['bbox'])):
                    x1, y1, x2, y2 = map(int, bbox)
                    # Draw box around text
                    cv2.rectangle(annotated_popup, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Add index label
                    cv2.putText(annotated_popup, f"{i}", (x1, y1-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                annotated_path = os.path.join(debug_dir, "multinetwork_popup_region_annotated.png")
                cv2.imwrite(annotated_path, annotated_popup)
                print(f"[ACTION_HANDLER] DEBUG: Saved annotated popup region to: {os.path.abspath(annotated_path)}")
            except Exception as e:
                print(f"[ACTION_HANDLER] WARNING: Failed to save annotated popup region: {e}")
            
            # Look for "Open as Multi-Network Instruction" button
            # IMPORTANT: Must contain "Open" to avoid matching the title "Multi-Network Instruction"
            target_phrases = [
                "Open as Multi-Network Instruction",
                "Open as Multi-Network",
                "Open as MultiNetwork Instruction",  # In case hyphen is missing
                "Open as MultiNetwork"
            ]
            
            button_found = False
            click_x = None
            click_y = None
            best_match = None
            best_match_score = 0
            
            # Find the best match (longest/most specific match)
            for i, text in enumerate(ocr_data['text']):
                text_lower = text.lower()
                
                # MUST contain "open" to avoid matching the title
                if "open" not in text_lower:
                    continue
                
                # Check each phrase
                for phrase in target_phrases:
                    phrase_lower = phrase.lower()
                    
                    # Case-insensitive partial match
                    if phrase_lower in text_lower or text_lower in phrase_lower:
                        # Score based on length of match (prefer longer/more specific matches)
                        match_score = len(text)
                        
                        if match_score > best_match_score:
                            best_match = i
                            best_match_score = match_score
                            print(f"[ACTION_HANDLER] DEBUG: Found better match at index {i}: '{text}' (score: {match_score})")
            
            if best_match is not None:
                i = best_match
                text = ocr_data['text'][i]
                x1, y1, x2, y2 = map(int, ocr_data['bbox'][i])
                
                # Calculate center of text box in LOCAL (cropped region) coordinates
                local_center_x = (x1 + x2) // 2
                local_center_y = (y1 + y2) // 2
                
                print(f"[ACTION_HANDLER] DEBUG: Using match at index {i}: '{text}'")
                print(f"[ACTION_HANDLER] DEBUG: Text bbox in local coords: ({x1},{y1})-({x2},{y2})")
                print(f"[ACTION_HANDLER] DEBUG: Text center in local coords: ({local_center_x}, {local_center_y})")
                print(f"[ACTION_HANDLER] DEBUG: Crop offset (search region): ({search_x}, {search_y})")
                
                # Convert to SCREEN coordinates by adding crop offset
                click_x = search_x + local_center_x
                click_y = search_y + local_center_y
                
                print(f"[ACTION_HANDLER] ✓ Found 'Open as Multi-Network Instruction' button: '{text}'")
                print(f"[ACTION_HANDLER] ✓ Click position in SCREEN coordinates: ({click_x}, {click_y})")
                
                button_found = True
            
            if not button_found:
                print(f"[ACTION_HANDLER] WARNING: Could not find 'Multi-Network Instruction' text via OCR")
                print(f"[ACTION_HANDLER] Falling back to fixed offset method")
                click_offset_y = 70
                click_x = popup_x
                click_y = popup_y + click_offset_y
        
        # Create debug screenshot with annotations
        try:
            print(f"[ACTION_HANDLER] Creating debug screenshot...")
            print(f"[ACTION_HANDLER] DEBUG: Variables for visualization:")
            print(f"[ACTION_HANDLER] DEBUG:   - search_x={search_x}, search_y={search_y}")
            print(f"[ACTION_HANDLER] DEBUG:   - search_w={search_w}, search_h={search_h}")
            print(f"[ACTION_HANDLER] DEBUG:   - ocr_success={ocr_success}")
            print(f"[ACTION_HANDLER] DEBUG:   - click_x={click_x}, click_y={click_y}")
            
            debug_screenshot = screenshot.copy()
            
            template_height, template_width = template.shape[:2]
            print(f"[ACTION_HANDLER] Template size: {template_width}x{template_height}")
            
            # Draw rectangle showing the OCR search region/crop (yellow dashed-style)
            print(f"[ACTION_HANDLER] DEBUG: Drawing OCR search region box...")
            for offset in [0, 4, 8]:
                cv2.rectangle(debug_screenshot,
                            (search_x + offset, search_y + offset),
                            (search_x + search_w - offset, search_y + search_h - offset),
                            (0, 255, 255), 1)
            cv2.putText(debug_screenshot, "OCR Search Region", 
                       (search_x + 10, search_y + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # Draw rectangle around detected popup template (green)
            top_left_x = popup_x - template_width // 2
            top_left_y = popup_y - template_height // 2
            bottom_right_x = popup_x + template_width // 2
            bottom_right_y = popup_y + template_height // 2
            cv2.rectangle(debug_screenshot, 
                        (top_left_x, top_left_y), 
                        (bottom_right_x, bottom_right_y), 
                        (0, 255, 0), 3)  # Green rectangle
            
            # Draw OCR detected text boxes (cyan)
            print(f"[ACTION_HANDLER] DEBUG: Drawing OCR text boxes...")
            if ocr_success and ocr_data and ocr_data.get('text'):
                print(f"[ACTION_HANDLER] DEBUG: Drawing {len(ocr_data['text'])} text boxes...")
                for i, (text, bbox) in enumerate(zip(ocr_data['text'], ocr_data['bbox'])):
                    x1, y1, x2, y2 = map(int, bbox)
                    # Convert local coordinates to screen coordinates
                    screen_x1 = search_x + x1
                    screen_y1 = search_y + y1
                    screen_x2 = search_x + x2
                    screen_y2 = search_y + y2
                    
                    # Draw cyan box around all detected text
                    cv2.rectangle(debug_screenshot, (screen_x1, screen_y1), (screen_x2, screen_y2), (255, 255, 0), 2)
                    
                    # Highlight the target button text in magenta if found
                    if "multi-network" in text.lower() and "open" in text.lower():
                        print(f"[ACTION_HANDLER] DEBUG: Found target text, drawing magenta box at ({screen_x1},{screen_y1})-({screen_x2},{screen_y2})")
                        cv2.rectangle(debug_screenshot, (screen_x1, screen_y1), (screen_x2, screen_y2), (255, 0, 255), 3)
                        cv2.putText(debug_screenshot, "TARGET", (screen_x1, screen_y1 - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            else:
                print(f"[ACTION_HANDLER] DEBUG: Not drawing text boxes - ocr_success={ocr_success}, has data={ocr_data is not None and ocr_data.get('text') is not None}")
            
            # Draw circle at popup center (blue)
            cv2.circle(debug_screenshot, (popup_x, popup_y), 10, (255, 0, 0), -1)
            
            # Draw circle at click position (red)
            cv2.circle(debug_screenshot, (click_x, click_y), 15, (0, 0, 255), -1)
            
            # Draw line from popup center to click position (yellow)
            cv2.line(debug_screenshot, (popup_x, popup_y), (click_x, click_y), (0, 255, 255), 2)
            
            # Add text labels
            cv2.putText(debug_screenshot, f"Popup detected ({confidence:.2f})", 
                       (top_left_x, top_left_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(debug_screenshot, f"Click: ({click_x},{click_y})", 
                       (click_x + 20, click_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Save debug screenshot
            print(f"[ACTION_HANDLER] DEBUG: All annotations drawn, preparing to save...")
            debug_dir = "debug_images"
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, "multinetwork_popup_detected.png")
            
            print(f"[ACTION_HANDLER] DEBUG: Saving debug screenshot to: {debug_path}")
            # Save with error checking
            save_result = cv2.imwrite(debug_path, debug_screenshot)
            print(f"[ACTION_HANDLER] DEBUG: Save result: {save_result}")
            if save_result:
                abs_path = os.path.abspath(debug_path)
                print(f"[ACTION_HANDLER] ✓ Debug screenshot saved to: {abs_path}")
                print(f"[ACTION_HANDLER]   Legend:")
                print(f"[ACTION_HANDLER]   - Yellow box: OCR search region (crop area)")
                print(f"[ACTION_HANDLER]   - Green box: Detected popup template area")
                print(f"[ACTION_HANDLER]   - Cyan boxes: OCR detected text (in screen coordinates)")
                print(f"[ACTION_HANDLER]   - Magenta box: Target button text (Multi-Network)")
                print(f"[ACTION_HANDLER]   - Blue dot: Popup center ({popup_x}, {popup_y})")
                print(f"[ACTION_HANDLER]   - Red dot: Click position ({click_x}, {click_y})")
                print(f"[ACTION_HANDLER]   - Yellow line: Path from popup center to click")
            else:
                print(f"[ACTION_HANDLER] ✗ Failed to save debug screenshot to: {debug_path}")
        except Exception as e:
            import traceback
            print(f"[ACTION_HANDLER] Warning: Failed to save debug screenshot: {e}")
            print(f"[ACTION_HANDLER] Traceback: {traceback.format_exc()}")
        
        print(f"[ACTION_HANDLER] Clicking 'Open as Multi-Network Instruction' at ({click_x}, {click_y})")
        
        # Move mouse to position and click
        pyautogui.moveTo(click_x, click_y, duration=0.3)
        time.sleep(0.2)
        
        success, click_msg = actions.click_at_position(click_x, click_y, clicks=1, button='left')
        if not success:
            return False, f"Failed to click on Multi-Network button: {click_msg}"
        
        print(f"[ACTION_HANDLER] ✓ Successfully clicked 'Open as Multi-Network Instruction'")
        time.sleep(0.5)
        
        return True, f"Multi-Network popup detected and 'Open as Multi-Network Instruction' clicked successfully"
        
    except Exception as e:
        return False, f"Error handling Multi-Network popup: {e}"


def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the network page is loading by detecting the loading circle.
    
    This verifier checks for a loading spinner in the center of the screen,
    which indicates that the multi-network instruction page is loading.
    
    Returns:
        Tuple of (success: bool, message, verification_data)
    """
    print("[VERIFIER_HANDLER] Verifying network page is loading by detecting loading circle...")
    
    try:
        time.sleep(1.0)
        
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Method 1: Try template matching first (allows for variations)
        screen_height, screen_width = screenshot.shape[:2]
        
        # Focus on content area center (offset from screen center)
        # The content area is typically offset to the right due to sidebar
        center_region_ratio = 0.35  # Smaller focused region
        region_width = int(screen_width * center_region_ratio)
        region_height = int(screen_height * center_region_ratio)
        # Offset region to the right and up to focus on content area
        region_x = int(screen_width * 0.40)  # Start at 40% from left (past sidebar)
        region_y = int(screen_height * 0.25)  # Start at 25% from top
        
        template_path = "src/workflow_module/actions/assets/loading_template.png"
        template_found, template_confidence, template_position = computer_vision_utils.find_template_in_region(
            screenshot,
            template_path,
            (region_x, region_y, region_width, region_height),
            confidence=0.4  # Lower threshold since spinner is animated
        )
        
        print(f"[VERIFIER_HANDLER] Template matching result: found={template_found}, confidence={template_confidence:.2f}")
        
        # Method 2: Look for loading circle in center region using circle detection
        # Adjusted parameters for the specific dot-based loading spinner
        circle_found, circle_info = computer_vision_utils.detect_loading_circle(
            screenshot,
            center_region_ratio=0.35,  # Focused search area
            min_radius=10,             # Small spinner (15-20px typical)
            max_radius=25,             # Prevent detecting large false positives
            brightness_threshold=100   # Lower threshold for dark dot spinner
        )
        
        print(f"[VERIFIER_HANDLER] Circle detection result: found={circle_found}, circle_info={circle_info}")
        
        # Validate circle position - reject if in table area (left side)
        circle_position_valid = False
        if circle_found and circle_info:
            x, y, radius = circle_info
            # Reject circles on the far left (table area) or far right (sidebar)
            # Valid range: 30-70% horizontally, 20-80% vertically
            horizontal_valid = (screen_width * 0.30) < x < (screen_width * 0.70)
            vertical_valid = (screen_height * 0.20) < y < (screen_height * 0.80)
            size_valid = 10 <= radius <= 25  # Strict size validation
            
            circle_position_valid = horizontal_valid and vertical_valid and size_valid
            
            print(f"[VERIFIER_HANDLER] Circle validation: pos=({x},{y}), r={radius}")
            print(f"[VERIFIER_HANDLER]   - horizontal_valid: {horizontal_valid}")
            print(f"[VERIFIER_HANDLER]   - vertical_valid: {vertical_valid}")
            print(f"[VERIFIER_HANDLER]   - size_valid: {size_valid}")
            print(f"[VERIFIER_HANDLER]   - overall_valid: {circle_position_valid}")
            
            if not circle_position_valid:
                print(f"[VERIFIER_HANDLER] Rejecting circle - likely false positive")
                circle_found = False
                circle_info = None
        
        # Prioritize template matching, then use validated circle detection
        found = template_found or (circle_found and circle_position_valid)
        
        # Use template position if found, otherwise use validated circle info
        if template_found and template_position:
            x, y = template_position
            radius = 18  # Approximate radius for template match
            circle_info = (x, y, radius)
        
        verification_data = {
            "loading_circle_found": circle_found and circle_position_valid,
            "template_found": template_found,
            "template_confidence": template_confidence,
            "circle_info": circle_info,
            "circle_position_valid": circle_position_valid if circle_found else None,
            "screenshot_taken": True,
            "detection_method": "template" if template_found else ("circle" if (circle_found and circle_position_valid) else "none")
        }
        
        if found and circle_info:
            x, y, radius = circle_info
            detection_method = verification_data["detection_method"]
            success_msg = f"✓ Network page is loading. Loading indicator detected via {detection_method} at ({x}, {y}), radius: {radius}px"
            if template_found:
                success_msg += f" (template confidence: {template_confidence:.2f})"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            
            # Save debug screenshot with loading circle highlighted
            try:
                print(f"[VERIFIER_HANDLER] Creating debug screenshot for loading circle...")
                debug_screenshot = screenshot.copy()
                
                # Draw filled circle to show detected area (semi-transparent green)
                overlay = debug_screenshot.copy()
                cv2.circle(overlay, (x, y), radius, (0, 255, 0), -1)
                cv2.addWeighted(overlay, 0.1, debug_screenshot, 0.9, 0, debug_screenshot)
                
                # Draw circles around detected loading spinner (bright green)
                cv2.circle(debug_screenshot, (x, y), radius, (0, 255, 0), 4)
                cv2.circle(debug_screenshot, (x, y), radius - 3, (0, 200, 0), 2)
                cv2.circle(debug_screenshot, (x, y), radius + 3, (0, 200, 0), 2)
                
                # Draw center point (red)
                cv2.circle(debug_screenshot, (x, y), 10, (0, 0, 255), -1)
                cv2.circle(debug_screenshot, (x, y), 8, (255, 255, 255), -1)
                cv2.circle(debug_screenshot, (x, y), 3, (0, 0, 255), -1)
                
                # Draw crosshairs at center (yellow)
                cv2.line(debug_screenshot, (x - 20, y), (x + 20, y), (0, 255, 255), 3)
                cv2.line(debug_screenshot, (x, y - 20), (x, y + 20), (0, 255, 255), 3)
                
                # Add text label with background for better visibility
                label_text = f"Spinner Center"
                label_text2 = f"Radius: {radius}px"
                label_x = x + radius + 20
                label_y = y - 10
                
                # Draw text background
                text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                text_size2 = cv2.getTextSize(label_text2, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                max_width = max(text_size[0], text_size2[0])
                
                cv2.rectangle(debug_screenshot, 
                            (label_x - 5, label_y - text_size[1] - 5),
                            (label_x + max_width + 10, label_y + text_size2[1] + 20),
                            (0, 0, 0), -1)
                cv2.rectangle(debug_screenshot, 
                            (label_x - 5, label_y - text_size[1] - 5),
                            (label_x + max_width + 10, label_y + text_size2[1] + 20),
                            (0, 255, 0), 2)
                
                # Draw text
                cv2.putText(debug_screenshot, label_text, 
                           (label_x, label_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(debug_screenshot, label_text2, 
                           (label_x, label_y + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Save
                debug_dir = "debug_images"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, "loading_circle_detected.png")
                
                save_result = cv2.imwrite(debug_path, debug_screenshot)
                if save_result:
                    abs_path = os.path.abspath(debug_path)
                    print(f"[VERIFIER_HANDLER] ✓ Debug screenshot saved to: {abs_path}")
                    print(f"[VERIFIER_HANDLER]   - Green circles: Spinner boundary")
                    print(f"[VERIFIER_HANDLER]   - Red crosshair: Spinner center")
                else:
                    print(f"[VERIFIER_HANDLER] ✗ Failed to save debug screenshot to: {debug_path}")
            except Exception as e:
                import traceback
                print(f"[VERIFIER_HANDLER] Warning: Failed to save debug screenshot: {e}")
                print(f"[VERIFIER_HANDLER] Traceback: {traceback.format_exc()}")
            
            verification_data["message"] = success_msg
            return True, success_msg, verification_data
        else:
            # Try again after a short delay
            print(f"[VERIFIER_HANDLER] Loading circle not found on first attempt, waiting and checking again...")
            time.sleep(1.5)
            
            screenshot2 = computer_vision_utils.take_screenshot()
            if screenshot2 is not None:
                # Use same improved parameters as first check
                found2, circle_info2 = computer_vision_utils.detect_loading_circle(
                    screenshot2,
                    center_region_ratio=0.35,  # Focused search area
                    min_radius=10,             # Small spinner (15-20px typical)
                    max_radius=25,             # Prevent detecting large false positives
                    brightness_threshold=100   # Lower threshold for dark dot spinner
                )
                
                # Apply same validation as first check
                circle_position_valid2 = False
                if found2 and circle_info2:
                    x2, y2, radius2 = circle_info2
                    screen_height2, screen_width2 = screenshot2.shape[:2]
                    horizontal_valid2 = (screen_width2 * 0.30) < x2 < (screen_width2 * 0.70)
                    vertical_valid2 = (screen_height2 * 0.20) < y2 < (screen_height2 * 0.80)
                    size_valid2 = 10 <= radius2 <= 25
                    
                    circle_position_valid2 = horizontal_valid2 and vertical_valid2 and size_valid2
                    
                    print(f"[VERIFIER_HANDLER] Second check validation: pos=({x2},{y2}), r={radius2}")
                    print(f"[VERIFIER_HANDLER]   - valid: {circle_position_valid2}")
                    
                    if not circle_position_valid2:
                        print(f"[VERIFIER_HANDLER] Rejecting circle on second check - false positive")
                        found2 = False
                        circle_info2 = None
                
                verification_data["second_check"] = {
                    "loading_circle_found": found2 and circle_position_valid2,
                    "circle_info": circle_info2,
                    "circle_position_valid": circle_position_valid2 if found2 else None
                }
                
                if found2 and circle_info2 and circle_position_valid2:
                    x, y, radius = circle_info2
                    success_msg = f"✓ Network page is loading. Loading circle detected on second check at ({x}, {y}), radius: {radius}px"
                    print(f"[VERIFIER_HANDLER] {success_msg}")
                    
                    # Save debug screenshot with loading circle highlighted (second check)
                    try:
                        print(f"[VERIFIER_HANDLER] Creating debug screenshot for loading circle (2nd check)...")
                        debug_screenshot = screenshot2.copy()
                        
                        # Draw circles around detected loading spinner (green)
                        cv2.circle(debug_screenshot, (x, y), radius, (0, 255, 0), 3)
                        cv2.circle(debug_screenshot, (x, y), radius + 10, (0, 255, 0), 1)
                        
                        # Draw center point (red)
                        cv2.circle(debug_screenshot, (x, y), 8, (0, 0, 255), -1)
                        
                        # Draw crosshairs at center
                        cv2.line(debug_screenshot, (x - 15, y), (x + 15, y), (0, 0, 255), 2)
                        cv2.line(debug_screenshot, (x, y - 15), (x, y + 15), (0, 0, 255), 2)
                        
                        # Add text label with background
                        label_text = f"Dotted Spinner (r={radius}px) - 2nd check"
                        label_x = x + radius + 15
                        label_y = y
                        
                        # Draw text background
                        text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                        cv2.rectangle(debug_screenshot, 
                                    (label_x - 5, label_y - text_size[1] - 5),
                                    (label_x + text_size[0] + 5, label_y + 5),
                                    (0, 0, 0), -1)
                        
                        # Draw text
                        cv2.putText(debug_screenshot, label_text, 
                                   (label_x, label_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Save
                        debug_dir = "debug_images"
                        os.makedirs(debug_dir, exist_ok=True)
                        debug_path = os.path.join(debug_dir, "loading_circle_detected_second_check.png")
                        
                        save_result = cv2.imwrite(debug_path, debug_screenshot)
                        if save_result:
                            abs_path = os.path.abspath(debug_path)
                            print(f"[VERIFIER_HANDLER] ✓ Debug screenshot saved to: {abs_path}")
                            print(f"[VERIFIER_HANDLER]   - Green circles: Spinner boundary")
                            print(f"[VERIFIER_HANDLER]   - Red crosshair: Spinner center")
                        else:
                            print(f"[VERIFIER_HANDLER] ✗ Failed to save debug screenshot to: {debug_path}")
                    except Exception as e:
                        import traceback
                        print(f"[VERIFIER_HANDLER] Warning: Failed to save debug screenshot: {e}")
                        print(f"[VERIFIER_HANDLER] Traceback: {traceback.format_exc()}")
                    
                    verification_data["message"] = success_msg
                    return True, success_msg, verification_data
        
        # Loading circle not detected, but this might be okay if page loaded quickly
        warning_msg = f"⚠ Loading circle not detected. Page may have loaded very quickly, or loading indicator may not be visible."
        print(f"[VERIFIER_HANDLER] {warning_msg}")
        verification_data["message"] = warning_msg
        return True, warning_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying network page loading: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors during popup detection/handling.
    
    Args:
        error_msg: Error message from failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts allowed
        
    Returns:
        Tuple of (should_retry: bool, message)
    """
    if attempt < max_attempts:
        wait_time = 1.0
        print(f"[ERROR_HANDLER] Attempt {attempt}/{max_attempts} failed. Waiting {wait_time}s before retry...")
        time.sleep(wait_time)
        return True, "Retrying popup detection"
    
    return False, f"Failed to handle Multi-Network popup after {max_attempts} attempts"


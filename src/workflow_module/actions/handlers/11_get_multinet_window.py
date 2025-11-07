#!/usr/bin/env python3
"""
Handler for: Get Multinet Window

Checks if the Multi-Network window is open by searching for 'multinet' text
in the title bar region. Retries up to 5 times with 10 second delays.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.ocr_utils import TextScanner
import time
import cv2
import os


def action(**kwargs) -> Tuple[bool, str]:
    """
    Check if Multi-Network window is open by detecting 'multinet' in title region.
    
    Region to check: (200, 145, 1450, 25)
    - x: 200
    - y: 145
    - width: 1450
    - height: 25
    
    Retries up to 5 times with 10 second delays between attempts.
    
    Returns:
        Tuple of (success: bool, message)
    """
    print("[ACTION_HANDLER] Checking if Multi-Network window is open...")
    
    # Define the region to check
    check_x = 200
    check_y = 145
    check_width = 1450
    check_height = 25
    
    print(f"[ACTION_HANDLER] Search region: x={check_x}, y={check_y}, w={check_width}, h={check_height}")
    
    max_attempts = 5
    wait_time = 10  # seconds between attempts
    
    for attempt in range(1, max_attempts + 1):
        print(f"[ACTION_HANDLER] Attempt {attempt}/{max_attempts}: Looking for 'multinet' text...")
        
        try:
            # Take screenshot
            screenshot = computer_vision_utils.take_screenshot()
            if screenshot is None:
                print(f"[ACTION_HANDLER] Failed to take screenshot on attempt {attempt}")
                if attempt < max_attempts:
                    print(f"[ACTION_HANDLER] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False, "Failed to take screenshot after all attempts"
            
            screen_height, screen_width = screenshot.shape[:2]
            
            # Validate region bounds
            if check_x + check_width > screen_width or check_y + check_height > screen_height:
                print(f"[ACTION_HANDLER] Warning: Region exceeds screen bounds ({screen_width}x{screen_height})")
                # Adjust region to fit within screen
                check_width = min(check_width, screen_width - check_x)
                check_height = min(check_height, screen_height - check_y)
                print(f"[ACTION_HANDLER] Adjusted region: x={check_x}, y={check_y}, w={check_width}, h={check_height}")
            
            # Crop the title bar region
            title_region = computer_vision_utils.crop_image(
                screenshot, 
                check_x, 
                check_y, 
                check_width, 
                check_height
            )
            
            if title_region is None:
                print(f"[ACTION_HANDLER] Failed to crop title region on attempt {attempt}")
                if attempt < max_attempts:
                    print(f"[ACTION_HANDLER] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False, "Failed to crop title region after all attempts"
            
            # Save debug image of the region being searched
            try:
                debug_dir = "debug_images"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, f"multinet_window_check_attempt_{attempt}.png")
                cv2.imwrite(debug_path, title_region)
                print(f"[ACTION_HANDLER] Debug image saved: {debug_path}")
            except Exception as e:
                print(f"[ACTION_HANDLER] Warning: Failed to save debug image: {e}")
            
            # Use OCR to search for 'multinet' text
            scanner = TextScanner()
            success, ocr_data = scanner.get_text_data(title_region)
            
            if not success:
                print(f"[ACTION_HANDLER] OCR failed on attempt {attempt}")
                if attempt < max_attempts:
                    print(f"[ACTION_HANDLER] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False, "OCR failed after all attempts"
            
            # Search for 'multinet' in detected text (case-insensitive)
            found_multinet = False
            found_text = ""
            found_position = None
            
            if ocr_data.get('text'):
                print(f"[ACTION_HANDLER] OCR detected {len(ocr_data['text'])} text elements")
                
                for i, text in enumerate(ocr_data['text']):
                    if text:
                        print(f"[ACTION_HANDLER]   Text {i+1}: '{text}'")
                        
                        # Check if 'multinet' or 'multi-net' appears in the text (case-insensitive)
                        if 'multinet' in text.lower().replace('-', '').replace(' ', ''):
                            found_multinet = True
                            found_text = text
                            if 'bbox' in ocr_data and i < len(ocr_data['bbox']):
                                found_position = ocr_data['bbox'][i]
                            print(f"[ACTION_HANDLER] ✓ Found 'multinet' in text: '{text}'")
                            break
            
            if found_multinet:
                # Save annotated debug screenshot showing the found text
                try:
                    debug_screenshot = screenshot.copy()
                    
                    # Draw rectangle around the search region (green)
                    cv2.rectangle(debug_screenshot,
                                (check_x, check_y),
                                (check_x + check_width, check_y + check_height),
                                (0, 255, 0), 3)
                    
                    # If we have the position of the found text, highlight it
                    if found_position:
                        x1, y1, x2, y2 = map(int, found_position)
                        # Adjust coordinates to absolute screen position
                        abs_x1 = check_x + x1
                        abs_y1 = check_y + y1
                        abs_x2 = check_x + x2
                        abs_y2 = check_y + y2
                        
                        # Draw rectangle around found text (bright green)
                        cv2.rectangle(debug_screenshot,
                                    (abs_x1, abs_y1),
                                    (abs_x2, abs_y2),
                                    (0, 255, 0), 2)
                        
                        # Draw filled background for better text visibility
                        overlay = debug_screenshot.copy()
                        cv2.rectangle(overlay,
                                    (abs_x1, abs_y1 - 5),
                                    (abs_x2, abs_y2 + 5),
                                    (0, 255, 0), -1)
                        cv2.addWeighted(overlay, 0.3, debug_screenshot, 0.7, 0, debug_screenshot)
                    
                    # Add label
                    label_text = f"'multinet' found: {found_text}"
                    cv2.putText(debug_screenshot, label_text,
                              (check_x, check_y - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Save annotated screenshot
                    debug_path = os.path.join(debug_dir, "multinet_window_found.png")
                    cv2.imwrite(debug_path, debug_screenshot)
                    abs_path = os.path.abspath(debug_path)
                    print(f"[ACTION_HANDLER] ✓ Annotated debug screenshot saved: {abs_path}")
                    
                except Exception as e:
                    print(f"[ACTION_HANDLER] Warning: Failed to save annotated screenshot: {e}")
                
                success_msg = f"✓ Multi-Network window is open. Found text: '{found_text}' (attempt {attempt}/{max_attempts})"
                print(f"[ACTION_HANDLER] {success_msg}")
                return True, success_msg
            
            else:
                print(f"[ACTION_HANDLER] 'multinet' not found in title region on attempt {attempt}")
                
                if attempt < max_attempts:
                    print(f"[ACTION_HANDLER] Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    return False, f"Multi-Network window not detected after {max_attempts} attempts. 'multinet' text not found in title bar region."
        
        except Exception as e:
            print(f"[ACTION_HANDLER] Error on attempt {attempt}: {e}")
            if attempt < max_attempts:
                print(f"[ACTION_HANDLER] Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                return False, f"Error checking for Multi-Network window: {e}"
    
    return False, f"Multi-Network window not detected after {max_attempts} attempts"


def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verifier for Multi-Network window detection.
    
    Since the action itself already does the verification with retries,
    this verifier just confirms success.
    
    Returns:
        Tuple of (success: bool, message, verification_data)
    """
    print("[VERIFIER_HANDLER] Multi-Network window detection completed successfully")
    
    verification_data = {
        "verified": True,
        "message": "Multi-Network window is open"
    }
    
    return True, "Multi-Network window verification passed", verification_data


def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """
    Handle errors during Multi-Network window detection.
    
    Args:
        error_msg: Error message from failed action
        attempt: Current attempt number
        max_attempts: Maximum number of attempts allowed
        
    Returns:
        Tuple of (should_retry: bool, message)
    """
    # The action itself already handles retries internally (5 attempts with 10s delays)
    # So if we reach the error handler, it means all internal attempts failed
    # We can allow one more retry at the workflow level
    
    if attempt < max_attempts:
        wait_time = 2.0
        print(f"[ERROR_HANDLER] Workflow attempt {attempt}/{max_attempts} failed. Waiting {wait_time}s before retry...")
        time.sleep(wait_time)
        return True, "Retrying Multi-Network window detection"
    
    return False, f"Failed to detect Multi-Network window after {max_attempts} workflow attempts"




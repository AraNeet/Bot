#!/usr/bin/env python3
"""
Handler for: Multinetwork Popup

Detects the Multi-Network instruction popup in the middle of the screen,
and clicks on "Open as Multi-Network Instruction" option.
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
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
        
        # The "Open as Multi-Network Instruction" button is approximately 
        # 140 pixels below the center of the popup template
        # and centered horizontally
        click_offset_y = 70  # Offset from popup center to button
        click_x = popup_x
        click_y = popup_y + click_offset_y
        
        # Create debug screenshot with annotations
        try:
            print(f"[ACTION_HANDLER] Creating debug screenshot...")
            debug_screenshot = screenshot.copy()
            
            # Load template to get its dimensions
            template = computer_vision_utils.load_image(template_path)
            if template is not None:
                template_height, template_width = template.shape[:2]
                print(f"[ACTION_HANDLER] Template size: {template_width}x{template_height}")
                
                # Draw rectangle around detected popup (green)
                top_left_x = popup_x - template_width // 2
                top_left_y = popup_y - template_height // 2
                bottom_right_x = popup_x + template_width // 2
                bottom_right_y = popup_y + template_height // 2
                cv2.rectangle(debug_screenshot, 
                            (top_left_x, top_left_y), 
                            (bottom_right_x, bottom_right_y), 
                            (0, 255, 0), 3)  # Green rectangle
                
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
                cv2.putText(debug_screenshot, "Click position", 
                           (click_x + 20, click_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Save debug screenshot
                debug_dir = "debug_images"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, "multinetwork_popup_detected.png")
                
                # Save with error checking
                save_result = cv2.imwrite(debug_path, debug_screenshot)
                if save_result:
                    abs_path = os.path.abspath(debug_path)
                    print(f"[ACTION_HANDLER] ✓ Debug screenshot saved to: {abs_path}")
                    print(f"[ACTION_HANDLER]   - Green box: Detected popup area")
                    print(f"[ACTION_HANDLER]   - Blue dot: Popup center ({popup_x}, {popup_y})")
                    print(f"[ACTION_HANDLER]   - Red dot: Click position ({click_x}, {click_y})")
                else:
                    print(f"[ACTION_HANDLER] ✗ Failed to save debug screenshot to: {debug_path}")
            else:
                print(f"[ACTION_HANDLER] Warning: Could not load template for debug visualization")
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
        
        # Look for loading circle in center region
        # Adjusted parameters for typical dot-based loading spinners
        found, circle_info = computer_vision_utils.detect_loading_circle(
            screenshot,
            center_region_ratio=0.5,  # Search larger area
            min_radius=8,              # Smaller minimum for compact spinners
            max_radius=40,             # Smaller maximum - most spinners are 20-30px
            brightness_threshold=180
        )
        
        verification_data = {
            "loading_circle_found": found,
            "circle_info": circle_info,
            "screenshot_taken": True
        }
        
        if found and circle_info:
            x, y, radius = circle_info
            success_msg = f"✓ Network page is loading. Loading circle detected at ({x}, {y}), radius: {radius}px"
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
                found2, circle_info2 = computer_vision_utils.detect_loading_circle(
                    screenshot2,
                    center_region_ratio=0.5,  # Search larger area
                    min_radius=8,              # Smaller minimum for compact spinners
                    max_radius=40,             # Smaller maximum - most spinners are 20-30px
                    brightness_threshold=180
                )
                
                verification_data["second_check"] = {
                    "loading_circle_found": found2,
                    "circle_info": circle_info2
                }
                
                if found2 and circle_info2:
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


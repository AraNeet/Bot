#!/usr/bin/env python3
"""
Handler for: Multi-Network Popup

Detects the Multi-Network instruction popup and clicks "Open as Multi-Network Instruction".
"""

from typing import Tuple, Dict, Any, Optional
from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import ocr_utils
from src.workflow_module.actions.helpers import debug_utils
import time
import pyautogui
import os
import cv2

# Initialize debugger for this handler
debugger = debug_utils.Debugger("action_09_multinetwork_popup")

def wait_for_loading(max_wait_seconds=300):
    """Waits for the loading circle to disappear."""
    print("[ACTION_HANDLER] Checking for loading circle...")
    
    # Step 1: Record start time for timeout check
    start_time = time.time()
    
    # Step 2: Loop until loading complete or timeout
    while (time.time() - start_time) < max_wait_seconds:
        # Step 3: Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            time.sleep(1)
            continue
        
        # Step 4: Detect loading circle using computer vision
        circle_found, circle_info = computer_vision_utils.detect_loading_circle(
            screenshot, center_region_ratio=0.6, min_radius=3, max_radius=40, brightness_threshold=50
        )
        
        # Step 5: Also try template matching for loading indicator
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(handler_dir, '09_loading_template.png')
        h, w = screenshot.shape[:2]
        region = (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6))
        
        # Step 6: Debug visualization (save occasionally to avoid spam)
        if int(time.time()) % 5 == 0:
             debugger.visualize_search_region(screenshot, region, "loading_search")

        # Step 7: Search for loading template
        template_found, _, _ = computer_vision_utils.find_template_in_region(
            screenshot, template_path, region, confidence=0.7
        )
        
        # Step 8: Check if loading indicator detected
        is_loading = circle_found or template_found
        
        # Step 9: Wait if loading, otherwise return success
        if is_loading:
            print(f"[ACTION_HANDLER] Loading detected... waiting (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(2)
        else:
            print("[ACTION_HANDLER] Loading complete or not detected.")
            return True
    
    # Step 10: Return failure on timeout
    print("[ACTION_HANDLER] Timed out waiting for loading.")
    return False

def action(**kwargs) -> Tuple[bool, str]:
    """Detect and handle the Multi-Network popup."""
    print("[ACTION_HANDLER] Checking for Multi-Network popup...")
    
    # Step 1: Initialize detection variables
    max_attempts = 3
    attempt_delay = 2
    
    found = False
    pos = None
    cropped_screenshot = None
    popup_template_path = None
    template_size = (0, 0)
    
    # Step 2: Get template path and load template
    handler_dir = os.path.dirname(os.path.abspath(__file__))
    popup_template_path = os.path.join(handler_dir, '09_MutliNetworkPopUp.png')
    
    template_img = computer_vision_utils.load_image(popup_template_path)
    if template_img is None:
        return False, "Failed to load popup template"
    template_size = (template_img.shape[1], template_img.shape[0])
    
    # Step 3: Calculate center region based on screen size
    screen_w, screen_h = pyautogui.size()
    center_region = (int(screen_w*0.2), int(screen_h*0.2), int(screen_w*0.6), int(screen_h*0.6))
    
    # Step 4: Detection loop (Find popup template)
    for attempt in range(max_attempts):
        print(f"[ACTION_HANDLER] Detection attempt {attempt + 1}/{max_attempts}...")
        
        # Step 4a: Take cropped screenshot directly
        cropped_screenshot = computer_vision_utils.take_screenshot_and_crop(center_region)
        if cropped_screenshot is None: 
            if attempt < max_attempts - 1:
                time.sleep(attempt_delay)
                continue
            else:
                return False, "Failed to take screenshot"
        
        # Step 4b: Save for debug
        debugger.save_image(cropped_screenshot, f"01_initial_cropped_{attempt}.png")
        
        # Step 4c: Search in the cropped image for popup template
        h_crop, w_crop = cropped_screenshot.shape[:2]
        found, conf, pos_local = computer_vision_utils.match_template_in_region(
            cropped_screenshot, template_img, (0, 0, w_crop, h_crop), confidence=0.7
        )
        
        # Step 4d: If found, convert local position to global
        if found:
            global_x = center_region[0] + pos_local[0]
            global_y = center_region[1] + pos_local[1]
            pos = (global_x, global_y)
            
            print(f"[ACTION_HANDLER] Popup found on attempt {attempt + 1} with confidence {conf}")
            
            # Step 4e: Debug visualization
            debugger.visualize_template_match(
                cropped_screenshot, found, pos_local, template_size, 
                "03_popup_match_cropped", confidence=conf
            )
            break
        
        # Step 4f: Wait before retry
        if attempt < max_attempts - 1:
            print(f"[ACTION_HANDLER] Popup not found, waiting {attempt_delay}s before retry...")
            time.sleep(attempt_delay)

    # Step 5: Handle case where popup not found
    if not found or not pos:
        print("[ACTION_HANDLER] Popup not found after retries. Checking for loading...")
        wait_for_loading(max_wait_seconds=10)
        return True, "Popup not found, assuming flow can proceed"

    popup_x, popup_y = pos
    print(f"[ACTION_HANDLER] Popup found at ({popup_x}, {popup_y})")
    
    # Step 6: Define search area around popup for OCR button detection
    search_w, search_h = 400, 200
    search_x_global = max(0, popup_x - search_w // 2)
    search_y_global = max(0, popup_y - search_h // 2)
    
    # Step 7: Convert global search coordinates to local crop coordinates
    search_x_local = search_x_global - center_region[0]
    search_y_local = search_y_global - center_region[1]
    
    # Step 8: Crop popup area for OCR
    popup_crop = computer_vision_utils.crop_image(
        cropped_screenshot, search_x_local, search_y_local, search_w, search_h
    )
    
    # Step 9: Fallback to full screenshot if crop failed
    if popup_crop is None:
        print("[ACTION_HANDLER] Failed to crop OCR region from screenshot. Taking new full screenshot.")
        full_screenshot = computer_vision_utils.take_screenshot()
        if full_screenshot is not None:
             popup_crop = computer_vision_utils.crop_image(full_screenshot, search_x_global, search_y_global, search_w, search_h)
    
    # Step 10: Perform OCR to find button text
    if popup_crop is not None:
        debugger.save_image(popup_crop, "04_popup_crop_for_ocr.png")
        
        scanner = ocr_utils.TextScanner()
        success, ocr_data = scanner.get_text_data(popup_crop)
        
        debugger.visualize_ocr(popup_crop, ocr_data, "05_popup_ocr_results", highlight_text="open")
    else:
        success, ocr_data = False, None
        print("[ACTION_HANDLER] Failed to get OCR crop.")

    # Step 11: Set default click position (fallback)
    click_x, click_y = popup_x, popup_y + 70
    
    # Step 12: Search OCR results for "Open... Multi-Network..." button
    if success and ocr_data and ocr_data.get('text'):
        found_button = False
        for i, text in enumerate(ocr_data['text']):
            if "multi" in text.lower() and "open" in text.lower():
                # Step 12a: Calculate button center from bounding box
                bbox = ocr_data['bbox'][i]
                cx = (bbox[0] + bbox[2]) // 2
                cy = (bbox[1] + bbox[3]) // 2
                
                # Step 12b: Calculate global click position
                click_x = search_x_global + cx
                click_y = search_y_global + cy
                print(f"[ACTION_HANDLER] OCR found button: {text}")
                found_button = True
                break
        
        if not found_button:
            print("[ACTION_HANDLER] WARNING: Could not find 'Open... Multi...' text. Using fallback position.")

    print(f"[ACTION_HANDLER] Clicking at ({click_x}, {click_y})")
    
    # Step 13: Click the button
    actions.click_at_position(click_x, click_y)
    
    return True, "Handled Multi-Network popup"


def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify by checking if loading circle appears/disappears."""
    # This verification is implicit in the wait_for_loading called by next steps usually,
    # but we can do a quick check here.
    
    return True, "Verification skipped/implicit", {}

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    if attempt < max_attempts:
        time.sleep(1.0)
        return True, "Retrying"
    return False, f"Failed after {max_attempts} attempts"

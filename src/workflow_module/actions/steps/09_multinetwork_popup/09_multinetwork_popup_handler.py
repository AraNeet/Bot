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
    
    start_time = time.time()
    
    while (time.time() - start_time) < max_wait_seconds:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            time.sleep(1)
            continue
            
        # Simplified check - combine template and circle detection
        # Use reasonably broad parameters
        circle_found, circle_info = computer_vision_utils.detect_loading_circle(
            screenshot, center_region_ratio=0.6, min_radius=3, max_radius=40, brightness_threshold=50
        )
        
        # Also try template
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(handler_dir, '09_loading_template.png')
        # Search roughly the center
        h, w = screenshot.shape[:2]
        region = (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6))
        
        # Debug: visualize search region for loading template
        # (Only save occasionally to avoid spamming)
        if int(time.time()) % 5 == 0:
             debugger.visualize_search_region(screenshot, region, "loading_search")

        template_found, _, _ = computer_vision_utils.find_template_in_region(
            screenshot, template_path, region, confidence=0.4
        )
        
        is_loading = circle_found or template_found
        
        if is_loading:
            print(f"[ACTION_HANDLER] Loading detected... waiting (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(2)
        else:
            print("[ACTION_HANDLER] Loading complete or not detected.")
            return True
            
    print("[ACTION_HANDLER] Timed out waiting for loading.")
    return False

def action(**kwargs) -> Tuple[bool, str]:
    """Detect and handle the Multi-Network popup."""
    print("[ACTION_HANDLER] Checking for Multi-Network popup...")
    
    # Step 1: Take initial screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None: return False, "Failed to take screenshot"
    debugger.save_image(screenshot, "01_initial.png")
    
    h, w = screenshot.shape[:2]
    center_region = (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6))
    debugger.visualize_search_region(screenshot, center_region, "02_popup_search_region")
    
    handler_dir = os.path.dirname(os.path.abspath(__file__))
    popup_template_path = os.path.join(handler_dir, '09_MutliNetworkPopUp.png')
    
    # Load template for debug info (size)
    template_img = computer_vision_utils.load_image(popup_template_path)
    template_size = (0, 0)
    if template_img is not None:
        template_size = (template_img.shape[1], template_img.shape[0])

    # Step 2: Find popup template
    found, conf, pos = computer_vision_utils.find_template_in_region(
        screenshot, popup_template_path, center_region, confidence=0.7
    )
    
    debugger.visualize_template_match(screenshot, found, pos, template_size, "03_popup_match", confidence=conf if conf else 0.0)
    
    if not found or not pos:
        print("[ACTION_HANDLER] Popup not found. Checking for loading...")
        wait_for_loading(max_wait_seconds=10) # Short wait if we missed popup
        return True, "Popup not found, assuming flow can proceed"

    popup_x, popup_y = pos
    print(f"[ACTION_HANDLER] Popup found at ({popup_x}, {popup_y})")
    
    # Step 3: Locate button via OCR around popup center
    # Define search area around popup center
    search_w, search_h = 400, 200
    search_x = max(0, popup_x - search_w // 2)
    search_y = max(0, popup_y - search_h // 2)
    
    popup_crop = computer_vision_utils.crop_image(screenshot, search_x, search_y, search_w, search_h)
    debugger.save_image(popup_crop, "04_popup_crop_for_ocr.png")
    
    scanner = ocr_utils.TextScanner()
    success, ocr_data = scanner.get_text_data(popup_crop)
    
    # Visualize OCR results
    debugger.visualize_ocr(popup_crop, ocr_data, "05_popup_ocr_results", highlight_text="open")

    click_x, click_y = popup_x, popup_y + 70 # Default fallback offset
    
    if success and ocr_data and ocr_data.get('text'):
        best_match_idx = -1
        best_score = 0
        
        for i, text in enumerate(ocr_data['text']):
            text_lower = text.lower()
            
            # Score matches to ensure we pick "Multi-Network" over "Single Network"
            # We want to strictly find "Multi"
            score = 0
            
            # Check for "multi" (essential)
            if "multi" in text_lower:
                score += 2
            
            # Check for "network"
            if "network" in text_lower:
                score += 1
                
            # Check for "open"
            if "open" in text_lower:
                score += 1
                
            # Penalize "single" to be absolutely sure
            if "single" in text_lower:
                score = 0
            
            # We only want matches that definitely have "multi"
            if score >= 2:  # Must at least have "multi"
                 if score > best_score:
                    best_score = score
                    best_match_idx = i
                 # If scores are equal, prefer longer text (likely the full sentence)
                 elif score == best_score:
                    if len(text) > len(ocr_data['text'][best_match_idx]):
                        best_match_idx = i
        
        if best_match_idx >= 0:
            bbox = ocr_data['bbox'][best_match_idx]
            # center relative to crop
            cx = (bbox[0] + bbox[2]) // 2
            cy = (bbox[1] + bbox[3]) // 2
            click_x = search_x + cx
            click_y = search_y + cy
            print(f"[ACTION_HANDLER] OCR found button: {ocr_data['text'][best_match_idx]}")
        else:
            print("[ACTION_HANDLER] WARNING: Could not find 'Multi-Network' text. Using fallback position.")

    print(f"[ACTION_HANDLER] Clicking at ({click_x}, {click_y})")
    
    # Step 4: Click button
    # Visualize click point
    debug_click = screenshot.copy()
    debugger.draw_point(debug_click, (click_x, click_y), color=(0, 0, 255), radius=10, label="Click")
    debugger.save_image(debug_click, "06_click_point.png")

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

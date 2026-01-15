#!/usr/bin/env python3
"""
Handler for: Edit Definition (Step 11)

This module implements the logic to:
1. Locate the Definition sub-window
2. Extract and compare Begin Date with System Date (Mountain Time)
3. Update Begin Date (if applicable) and End Date
4. Update Comment field with revision details
"""

from typing import Tuple, Dict, Any, Optional
import time
import pyautogui

from src.workflow_module.actions.helpers import actions
from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers import debug_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger

# Import helpers (using importlib since module name starts with number)
import importlib.util
import os
spec = importlib.util.spec_from_file_location("helpers", os.path.join(os.path.dirname(__file__), "11_helper.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

# ============================================================================
# ACTION
# ============================================================================

def action(begin_date: str = "", end_date: str = "", revision_number: str = "", agent_name: str = "", **kwargs) -> Tuple[bool, str]:
    """Execute Step 11 logic."""
    print(f"[ACTION_HANDLER] Starting Step 11: Edit Definition")
    print(f"  Start: {begin_date}, End: {end_date}, Rev: {revision_number}, Agent: {agent_name}")

    if not all([begin_date, end_date, revision_number, agent_name]):
        print("[ACTION_HANDLER] Warning: Some required arguments are empty.")


    # Initialize debugger
    debug = Debugger(action_name="action_11_edit_definition")
    
    # 1. Take initial screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    debug.save_image(screenshot, "00_initial_screenshot.png")

    # 2. Extract and compare Begin Date with System Date (Mountain Time)
    should_update_begin = True
    begin_date_pos = helpers.find_field_input_box(screenshot, "Begin Date", helpers.DEFINITION_WINDOW_REGION, 
                                                   offset_y=15, debugger=debug, step_name="01_begin_date")
    
    if begin_date_pos:
        extracted_begin_date_str = helpers.extract_field_value(screenshot, begin_date_pos)
        print(f"[ACTION_HANDLER] Extracted Begin Date: '{extracted_begin_date_str}'")
        
        if extracted_begin_date_str:
            debug_img = screenshot.copy()
            debug.draw_point(debug_img, begin_date_pos, color=debug_utils.COLOR_CYAN, 
                           label=f"Extracted: {extracted_begin_date_str}")
            debug.save_image(debug_img, "02_begin_date_extracted.png")
        
        current_begin_date = helpers.parse_date_string(extracted_begin_date_str)
        if current_begin_date:
            system_date = helpers.get_current_mountain_date()
            print(f"[ACTION_HANDLER] System Date (Mountain): {system_date}")
            should_update_begin = system_date < current_begin_date
            if not should_update_begin:
                print("[ACTION_HANDLER] System date >= Begin Date. Skipping Begin Date update.")

    # 3. Update Begin Date (if system date < begin date)
    if should_update_begin:
        print(f"[ACTION_HANDLER] Updating Begin Date to '{begin_date}'...")
        success, msg = helpers.update_and_verify_date("Begin Date", begin_date, debugger=debug, step_name="03_begin_date")
        if not success:
            return False, msg

    # 4. Update End Date (always required)
    print(f"[ACTION_HANDLER] Updating End Date to '{end_date}'...")
    success, msg = helpers.update_and_verify_date("End Date", end_date, debugger=debug, step_name="04_end_date")
    if not success:
        return False, msg

    # 5. Update Comment Field (preserve existing text, then append)
    print(f"[ACTION_HANDLER] Updating Comment field...")
    screenshot = computer_vision_utils.take_screenshot()
    comment_pos = helpers.find_field_input_box(screenshot, "Comment", helpers.DEFINITION_WINDOW_REGION, 
                                                offset_y=15, debugger=debug, step_name="06_comment")
    
    if not comment_pos:
        return False, "Could not locate 'Comment' field"
    
    # Extract and store original comment in local variable
    original_comment = helpers.extract_field_value(screenshot, comment_pos, field_type="comment")
    print(f"[ACTION_HANDLER] Original comment: '{original_comment}'")
    
    # Update comment: click to focus, move to END, then append new text
    actions.click_at_position(*comment_pos)
    time.sleep(0.3)
    
    # Press End key to move cursor to end of the text
    pyautogui.press('end')
    time.sleep(0.2)
    
    if not agent_name:
        agent_name = "test agent"
    
    current_date_str = helpers.get_current_mountain_date().strftime("%m/%d")
    comment_text = f" {agent_name} {revision_number} {current_date_str}"
    print(f"[ACTION_HANDLER] Appending comment: '{comment_text}'")
    
    actions.type_text(comment_text)
    actions.press_key('tab', 1)
    time.sleep(0.3)
    
    screenshot_after = computer_vision_utils.take_screenshot()
    if screenshot_after is not None:
        debug.save_image(screenshot_after, "07_comment_updated.png")

    print(f"[ACTION_HANDLER] [OK] Step 11 completed successfully")
    return True, "Definition updated successfully"

# ============================================================================
# VERIFIER
# ============================================================================

def verifier(begin_date: str = "", end_date: str = "", revision_number: str = "", 
             agent_name: str = "", original_comment: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Comprehensive verification of Begin Date, End Date, and Comment."""
    print("[VERIFIER_HANDLER] Starting comprehensive verification...")
    
    debug = Debugger(action_name="action_11_edit_definition_verification")
    verification_results = {}
    all_passed = True
    error_messages = []
    
    # Verify Begin Date
    if begin_date:
        begin_success, begin_msg = helpers.verify_date_field("Begin Date", begin_date, debugger=debug)
        verification_results["begin_date"] = {"success": begin_success, "message": begin_msg}
        if not begin_success:
            all_passed = False
            error_messages.append(f"Begin Date: {begin_msg}")
    else:
        verification_results["begin_date"] = {"success": True, "message": "Skipped (no begin_date provided)"}
    
    # Verify End Date
    if end_date:
        end_success, end_msg = helpers.verify_date_field("End Date", end_date, debugger=debug)
        verification_results["end_date"] = {"success": end_success, "message": end_msg}
        if not end_success:
            all_passed = False
            error_messages.append(f"End Date: {end_msg}")
    else:
        verification_results["end_date"] = {"success": True, "message": "Skipped (no end_date provided)"}
    
    # Verify Comment
    comment_success, comment_msg = helpers.verify_comment(agent_name, revision_number, original_comment, debugger=debug)
    verification_results["comment"] = {"success": comment_success, "message": comment_msg}
    if not comment_success:
        all_passed = False
        error_messages.append(f"Comment: {comment_msg}")
    
    # Summary
    if all_passed:
        summary_msg = "All verifications passed: Begin Date, End Date, and Comment verified successfully"
        print(f"[VERIFIER_HANDLER] [PASS] {summary_msg}")
        return True, summary_msg, verification_results
    else:
        summary_msg = f"Verification failed: {'; '.join(error_messages)}"
        print(f"[VERIFIER_HANDLER] [FAIL] {summary_msg}")
        return False, summary_msg, verification_results

# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors."""
    print(f"[ERROR_HANDLER] Error in Edit Definition: {error_msg}")
    if attempt < max_attempts:
        time.sleep(1)
        return True, "Retrying..."
    return False, error_msg

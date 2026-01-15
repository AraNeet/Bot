#!/usr/bin/env python3
"""
Handler for: Edit Media Details (Step 12)

This module implements the logic to:
1. Locate the Media Details sub-window
2. Delete all existing ISCI/Ad-ID entries (A, B, C, etc.)
3. Enter new ISCI values from the instruction
4. Verify the entries were saved correctly
"""

from typing import Tuple, Dict, Any, Optional, List
import time

from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger

# Import helpers (using importlib since module name starts with number)
import importlib.util
import os
spec = importlib.util.spec_from_file_location("helpers", os.path.join(os.path.dirname(__file__), "12_helper.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

# ============================================================================
# ACTION
# ============================================================================

def action(isci_list: List[str] = None, **kwargs) -> Tuple[bool, str]:
    """
    Execute Step 12: Edit Media Details
    
    Parameters:
        isci_list: List of ISCI values to enter (e.g., ["BADTAA30ENH", "BADTSA30ENH"])
    """
    print(f"[ACTION_HANDLER] Starting Step 12: Edit Media Details")
    
    if isci_list is None:
        isci_list = []
    
    # Handle case where isci_list might be passed as a string
    if isinstance(isci_list, str):
        isci_list = [isci_list] if isci_list else []
    
    print(f"  ISCI values to enter: {isci_list}")
    
    # Initialize debugger
    debug = Debugger(action_name="action_12_edit_media_details")
    
    # 1. Take initial screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    debug.save_image(screenshot, "00_initial_screenshot.png")
    
    # 2. Scroll to Media Details sub-window
    print("[ACTION_HANDLER] Scrolling to Media Details...")
    success, msg = helpers.scroll_to_media_details(debug)
    if not success:
        print(f"[ACTION_HANDLER] Warning: {msg}")
        # Continue anyway - Media Details might already be visible
    
    # 3. Delete all existing media entries
    print("[ACTION_HANDLER] Deleting existing media entries...")
    success, msg, deleted_count = helpers.delete_all_existing_media(debug)
    if not success:
        return False, f"Failed to delete existing media: {msg}"
    print(f"[ACTION_HANDLER] Deleted {deleted_count} existing entries")
    
    # 4. Enter new ISCI values
    if isci_list:
        print(f"[ACTION_HANDLER] Entering {len(isci_list)} new ISCI values...")
        success, msg, entered_count = helpers.enter_all_isci_values(isci_list, debug)
        if not success:
            return False, f"Failed to enter ISCI values: {msg}"
        print(f"[ACTION_HANDLER] Entered {entered_count} ISCI values")
    else:
        print("[ACTION_HANDLER] No ISCI values to enter")
    
    # 5. Take final screenshot
    screenshot_after = computer_vision_utils.take_screenshot()
    if screenshot_after is not None:
        debug.save_image(screenshot_after, "99_final_screenshot.png")
    
    print(f"[ACTION_HANDLER] [OK] Step 12 completed successfully")
    return True, f"Media Details updated: deleted {deleted_count}, entered {len(isci_list)} ISCI values"


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(isci_list: List[str] = None, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that all ISCI values were entered correctly.
    """
    print("[VERIFIER_HANDLER] Starting verification...")
    
    if isci_list is None:
        isci_list = []
    
    if isinstance(isci_list, str):
        isci_list = [isci_list] if isci_list else []
    
    if not isci_list:
        return True, "No ISCI values to verify", {"verified": True, "count": 0}
    
    debug = Debugger(action_name="action_12_verification")
    
    # Verify all ISCI entries
    success, msg, results = helpers.verify_isci_entries(isci_list, debug)
    
    verification_data = {
        "verified": success,
        "expected_count": len(isci_list),
        "results": results
    }
    
    if success:
        print(f"[VERIFIER_HANDLER] [PASS] {msg}")
        return True, msg, verification_data
    else:
        print(f"[VERIFIER_HANDLER] [FAIL] {msg}")
        return False, msg, verification_data


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors during Media Details editing."""
    print(f"[ERROR_HANDLER] Error in Edit Media Details: {error_msg}")
    
    if attempt < max_attempts:
        # Try to recover by scrolling to top
        print("[ERROR_HANDLER] Attempting recovery - scrolling to top...")
        helpers.scroll_media_details_to_top()
        time.sleep(1)
        return True, "Retrying..."
    
    return False, error_msg

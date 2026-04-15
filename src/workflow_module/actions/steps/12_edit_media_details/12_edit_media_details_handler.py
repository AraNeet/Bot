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
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify multinet window is open before editing media details."""
    from src.workflow_module.actions.helpers.precheck_utils import verify_page
    return verify_page("multinetwork_page")

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
    
    # Step 1: Initialize ISCI list (handle None and string cases)
    if isci_list is None:
        isci_list = []
    
    if isinstance(isci_list, str):
        isci_list = [isci_list] if isci_list else []
    
    print(f"  ISCI values to enter: {isci_list}")
    
    # Step 2: Initialize debugger
    debug = Debugger(action_name="action_12_edit_media_details")
    
    # Step 3: Take initial screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    debug.save_image(screenshot, "00_initial_screenshot.png")
    
    # Step 4: Process Rows (Delete & Enter per row)
    # Note: process_media_rows handles scrolling to Media Details internally
    if isci_list:
        print(f"[ACTION_HANDLER] Processing {len(isci_list)} ISCI rows...")
        success, msg, errors = helpers.process_media_rows(isci_list, debug)
        if not success:
            error_details = "; ".join(errors) if errors else msg
            return False, f"Failed to process media rows: {msg} Details: {error_details}"
        print(f"[ACTION_HANDLER] Media processing complete: {msg}")
    else:
        print("[ACTION_HANDLER] No ISCI values to enter - clearing only?")
        # Fallback to clear if list is empty? Or just return success.
        # Assuming empty list means "clear everything", we might need a separate clear function.
        # But per user request "row by row", if input is empty, maybe nothing to do?
        # Let's assume user always provides ISCIs.
        pass
    
    # Step 6: Take final screenshot
    screenshot_after = computer_vision_utils.take_screenshot()
    if screenshot_after is not None:
        debug.save_image(screenshot_after, "final_screenshot.png")
    
    print(f"[ACTION_HANDLER] [OK] Step 12 completed successfully")
    return True, f"Media Details updated successfully. Processed {len(isci_list)} items."


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(isci_list: List[str] = None, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that all ISCI values were entered correctly.
    """
    print("[VERIFIER_HANDLER] Starting verification...")
    
    # Step 1: Initialize ISCI list (handle None and string cases)
    if isci_list is None:
        isci_list = []
    
    if isinstance(isci_list, str):
        isci_list = [isci_list] if isci_list else []
    
    # Step 2: Handle empty ISCI list
    if not isci_list:
        return True, "No ISCI values to verify", {"verified": True, "count": 0}
    
    # Step 3: Initialize debugger
    debug = Debugger(action_name="action_12_verification")
    
    # Step 4: Verify all ISCI entries
    success, msg, results = helpers.verify_isci_entries(isci_list, debug)
    
    # Step 5: Build verification data
    verification_data = {
        "verified": success,
        "expected_count": len(isci_list),
        "results": results
    }
    
    # Step 6: Return verification result
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
        # Try to recover by scrolling to Media Details
        print("[ERROR_HANDLER] Attempting recovery - scrolling to Media Details...")
        helpers.scroll_to_media_details()
        time.sleep(1)
        return True, "Retrying..."
    
    return False, error_msg

#!/usr/bin/env python3
"""
Handler for: Edit Assignment Percentage (Step 13)

ACTION: Identifies the Assignment area (from "Assignment" header to end of work area).
VERIFIER: Passes (no verification logic).
"""

from typing import Tuple, Dict, Any, Optional
import importlib.util
import os

from src.workflow_module.actions.helpers import computer_vision_utils
from src.workflow_module.actions.helpers.debug_utils import Debugger

# Import helpers dynamically
spec = importlib.util.spec_from_file_location("helpers", os.path.join(os.path.dirname(__file__), "13_helper.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


# ============================================================================
# PRECHECK
# ============================================================================

def precheck(**kwargs) -> Tuple[bool, str]:
    """Verify multinet window is open before editing assignment percentages."""
    from src.workflow_module.actions.helpers.precheck_utils import verify_page
    return verify_page("multinetwork_page")

# ============================================================================
# ACTION
# ============================================================================

def action(assignment_data: Dict[str, str] = None, **kwargs) -> Tuple[bool, str]:
    """
    Execute Step 13: Edit Assignment Percentage
    
    Parameters:
        assignment_data: Dict mapping Alias to Percentage (e.g., {'A': '50', 'B': '50'})
    """
    print("[ACTION] Starting Step 13: Edit Assignment Percentage")
    
    if assignment_data is None:
        assignment_data = {}
    print(f"[ACTION] Assignment Data: {assignment_data}")
    
    if not assignment_data:
        print("[ACTION] No assignment data provided. Skipping.")
        return True, "No assignment data provided."
    
    debug = Debugger(action_name="action_13_edit_assignment")
    
    # Take screenshot and identify Assignment area
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    
    if debug:
        work_area_crop = computer_vision_utils.crop_image(screenshot, *helpers.WORK_AREA)
        if work_area_crop is not None:
            debug.save_image(work_area_crop, "00_initial_screenshot.png")
    
    # Ensure assignment area has Total or 10+ aliases in view (scrolls if needed).
    success, region, aliases = helpers.ensure_assignment_aliases_in_view(debug)
    if not success:
        return False, "Could not get Assignment area with Total or 10+ aliases in view"
    
    # Two sets: all aliases (letters), and complete aliases (for later use).
    all_aliases = set(a["alias"] for a in aliases)
    complete_aliases = set()
    
    # For each alias: select all, delete, then input the value (order matches aliases / assignment_data).
    for alias in aliases:
        helpers.select_all_in_alias_input_fields([alias], debug)
        helpers.right_click_delete_field(alias, debug)
        value = assignment_data.get(alias["alias"], "")
        helpers.input_value_in_field(alias, value, debug)
    
    return True, f"Assignment area ready: {len(aliases)} aliases in view"


# ============================================================================
# VERIFIER
# ============================================================================

def verifier(assignment_data: Dict[str, str] = None, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify: (1) Total is 100%, (2) all assignment fields have a number value.
    """
    print("[VERIFIER] Starting Step 13 verification...")
    debug = Debugger(action_name="action_13_verification")
    assignment_data = assignment_data or {}

    # Get assignment area in view so we can read Total and field values.
    success, region, aliases = helpers.ensure_assignment_aliases_in_view(debug)
    if not success:
        return False, "Verification failed: could not get Assignment area in view", {}

    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Verification failed: could not take screenshot", {}

    details = {}

    # Check 1: Total is 100%
    total = helpers.get_total_percentage(screenshot)
    details["total"] = total
    if total is None:
        return False, "Verification failed: could not read Total percentage", details
    if total != 100:
        return False, f"Verification failed: Total is {total}% (expected 100%)", details
    print(f"[VERIFIER] Total is 100%")

    # Check 2: All fields have a number value
    all_ok, invalid_aliases = helpers.verify_all_fields_have_numbers(screenshot, aliases)
    details["invalid_fields"] = invalid_aliases
    if not all_ok:
        return False, f"Verification failed: fields with no number: {invalid_aliases}", details
    print(f"[VERIFIER] All fields have number values")

    return True, "Verification passed: Total is 100% and all fields have number values", details


# ============================================================================
# ERROR HANDLER
# ============================================================================

def error_handler(error_msg: str, attempt: int, max_attempts: int, **kwargs) -> Tuple[bool, str]:
    """Handle errors."""
    print(f"[ERROR] Error in Edit Assignment: {error_msg}")
    return False, error_msg

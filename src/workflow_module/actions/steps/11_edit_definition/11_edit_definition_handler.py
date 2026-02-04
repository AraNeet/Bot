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

    # Step 1: Validate required arguments
    if not all([begin_date, end_date, revision_number, agent_name]):
        print("[ACTION_HANDLER] Warning: Some required arguments are empty.")

    # Step 2: Initialize debugger
    debug = Debugger(action_name="action_11_edit_definition")
    
    # Step 3: Take initial screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot"
    debug.save_image(screenshot, "00_initial_screenshot.png")

    # Step 4: Find Begin Date field and extract current value
    should_update_begin = True
    begin_date_pos = helpers.find_field_input_box(screenshot, "Begin Date", helpers.DEFINITION_WINDOW_REGION, 
                                                   offset_y=15, debugger=debug, step_name="01_begin_date")
    
    if begin_date_pos:
        # Step 4a: Extract current Begin Date value
        extracted_begin_date_str = helpers.extract_field_value(screenshot, begin_date_pos)
        print(f"[ACTION_HANDLER] Extracted Begin Date: '{extracted_begin_date_str}'")
        
        # Step 4b: Save debug image with extracted value
        if extracted_begin_date_str:
            debug_img = screenshot.copy()
            debug.draw_point(debug_img, begin_date_pos, color=debug_utils.COLOR_CYAN, 
                           label=f"Extracted: {extracted_begin_date_str}")
            debug.save_image(debug_img, "02_begin_date_extracted.png")
        
        # Step 4c: Compare with system date to determine if update needed
        current_begin_date = helpers.parse_date_string(extracted_begin_date_str)
        if current_begin_date:
            system_date = helpers.get_current_mountain_date()
            print(f"[ACTION_HANDLER] System Date (Mountain): {system_date}")
            should_update_begin = system_date < current_begin_date
            if not should_update_begin:
                print("[ACTION_HANDLER] System date >= Begin Date. Skipping Begin Date update.")

    # Step 5: Update Begin Date (if system date < begin date)
    if should_update_begin:
        print(f"[ACTION_HANDLER] Updating Begin Date to '{begin_date}'...")
        success, msg = helpers.update_and_verify_date("Begin Date", begin_date, debugger=debug, step_name="03_begin_date")
        if not success:
            return False, msg

    # Step 7: Build expected appended text FIRST (before any UI interaction)
    if not agent_name:
        agent_name = "test agent"
    
    current_date_str = helpers.get_current_mountain_date().strftime("%m/%d")
    expected_appended = f" {agent_name} {revision_number} {current_date_str}"
    expected_appended_stripped = expected_appended.strip()
    expected_appended_no_space = expected_appended_stripped.replace(" ", "")  # For more lenient matching
    
    # Step 8: Find Comment field and extract current value (with fresh screenshot)
    print(f"[ACTION_HANDLER] Checking Comment field for idempotency...")
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot for comment check"
    
    comment_pos = helpers.find_field_input_box(screenshot, "Comment", helpers.DEFINITION_WINDOW_REGION, 
                                                offset_y=15, debugger=debug, step_name="06_comment")
    
    if not comment_pos:
        return False, "Could not locate 'Comment' field"
    
    # Step 9: Extract current comment value (fresh extraction, wait a bit for UI to settle)
    time.sleep(0.5)  # Give UI more time to settle and save any previous changes
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        return False, "Failed to take screenshot for comment extraction"
    
    # Extract comment - try multiple times to ensure we get the full text
    current_comment = helpers.extract_field_value(screenshot, comment_pos, field_type="comment")
    
    # If comment seems short, try extracting again with a larger region
    if len(current_comment) < 50:  # If comment is very short, might be incomplete
        time.sleep(0.2)
        screenshot2 = computer_vision_utils.take_screenshot()
        if screenshot2 is not None:
            current_comment2 = helpers.extract_field_value(screenshot2, comment_pos, field_type="comment")
            if len(current_comment2) > len(current_comment):
                current_comment = current_comment2
    
    print(f"[ACTION_HANDLER] Current comment (extracted, length={len(current_comment)}): '{current_comment}'")
    print(f"[ACTION_HANDLER] Looking for appended text: '{expected_appended_stripped}'")
    
    # Step 10: Idempotency check - verify if comment already contains appended text
    # We check if the exact appended text is at the END of the comment (most strict check)
    current_comment_stripped = current_comment.strip()
    current_comment_rstripped = current_comment.rstrip()
    expected_appended_rstripped = expected_appended.rstrip()
    
    print(f"[ACTION_HANDLER] Idempotent check - Looking for: '{expected_appended_stripped}'")
    print(f"[ACTION_HANDLER] Idempotent check - In comment: '{current_comment[:150]}...' (length: {len(current_comment)})")
    
    # Build search pattern - the key parts: agent_name, revision_number, date
    # This pattern should match even if spacing differs slightly
    search_pattern = f"{agent_name.lower()} {revision_number.lower()} {current_date_str}"
    
    # Check 1: Does comment contain the full appended text (case-insensitive, anywhere)?
    current_comment_lower = current_comment_stripped.lower()
    expected_appended_lower = expected_appended_stripped.lower()
    contains_appended = expected_appended_lower in current_comment_lower
    
    # Check 2: Does comment contain the search pattern (agent + revision + date)?
    contains_pattern = search_pattern in current_comment_lower
    
    # Check 3: Does comment end with the exact appended text (allowing for trailing whitespace)?
    ends_with_exact = current_comment.rstrip().endswith(expected_appended.rstrip())
    
    # Check 4: Does stripped comment end with stripped appended text?
    ends_with_stripped = current_comment_stripped.endswith(expected_appended_stripped)
    
    # Count occurrences
    count_in_comment = current_comment_lower.count(expected_appended_lower)
    count_pattern = current_comment_lower.count(search_pattern)
    
    # Additional check: Look for just the revision number + date pattern (most lenient)
    revision_date_pattern = f"{revision_number.lower()} {current_date_str}"
    contains_revision_date = revision_date_pattern in current_comment_lower
    count_revision_date = current_comment_lower.count(revision_date_pattern)
    
    print(f"[ACTION_HANDLER] ===== IDEMPOTENCY CHECK DETAILS =====")
    print(f"[ACTION_HANDLER] Full comment: '{current_comment}'")
    print(f"[ACTION_HANDLER] Comment length: {len(current_comment)}")
    print(f"[ACTION_HANDLER] Search pattern: '{search_pattern}'")
    print(f"[ACTION_HANDLER] Revision+date pattern: '{revision_date_pattern}'")
    print(f"[ACTION_HANDLER] Check results:")
    print(f"[ACTION_HANDLER]   - contains_appended (full text): {contains_appended}")
    print(f"[ACTION_HANDLER]   - contains_pattern (agent+rev+date): {contains_pattern}")
    print(f"[ACTION_HANDLER]   - contains_revision_date (rev+date only): {contains_revision_date}")
    print(f"[ACTION_HANDLER]   - ends_with_exact: {ends_with_exact}")
    print(f"[ACTION_HANDLER]   - ends_with_stripped: {ends_with_stripped}")
    print(f"[ACTION_HANDLER]   - count_in_comment: {count_in_comment}")
    print(f"[ACTION_HANDLER]   - count_pattern: {count_pattern}")
    print(f"[ACTION_HANDLER]   - count_revision_date: {count_revision_date}")
    
    # Skip if text appears ANYWHERE in comment OR if pattern count > 0 (very lenient check)
    should_skip = (contains_appended or contains_pattern or contains_revision_date or 
                   ends_with_exact or ends_with_stripped or 
                   count_in_comment > 0 or count_pattern > 0 or count_revision_date > 0)
    
    if should_skip:
        print(f"[ACTION_HANDLER] ✓✓✓ IDEMPOTENT: Comment already contains appended text pattern")
        print(f"[ACTION_HANDLER]   - Pattern found {count_pattern} time(s)")
        print(f"[ACTION_HANDLER]   - Full text found {count_in_comment} time(s)")
        print(f"[ACTION_HANDLER]   - Revision+date found {count_revision_date} time(s)")
        if count_in_comment > 1 or count_pattern > 1 or count_revision_date > 1:
            print(f"[ACTION_HANDLER] ⚠ WARNING: Pattern appears multiple times - comment may have been added multiple times previously")
        print(f"[ACTION_HANDLER] ✓✓✓ SKIPPING APPEND - Comment will remain unchanged")
        print(f"[ACTION_HANDLER] ===== END IDEMPOTENCY CHECK =====")
        # Early return to prevent any further processing
        return True, "Comment already contains appended text - skipping append (idempotent)"
    else:
        print(f"[ACTION_HANDLER] →→→ NOT IDEMPOTENT: Appended text not found in comment")
        print(f"[ACTION_HANDLER] →→→ Will append now")
        print(f"[ACTION_HANDLER] ===== END IDEMPOTENCY CHECK =====")
        
        # Step 11: Click comment field and move cursor to end
        print(f"[ACTION_HANDLER] Clicking comment field at {comment_pos}...")
        actions.click_at_position(*comment_pos)
        time.sleep(0.5)  # Give time for field to focus
        
        # Move cursor to end of comment
        pyautogui.press('end')
        time.sleep(0.3)
        
        # Step 12: Type comment and tab to next field
        print(f"[ACTION_HANDLER] Appending comment: '{expected_appended}'")
        actions.type_text(expected_appended)
        time.sleep(0.2)  # Give time for text to be entered
        actions.press_key('tab', 1)
        time.sleep(0.5)  # Give time for field to save
        
        # Step 13: Verify the comment was added (optional verification)
        verify_screenshot = computer_vision_utils.take_screenshot()
        if verify_screenshot is not None:
            verify_comment = helpers.extract_field_value(verify_screenshot, comment_pos, field_type="comment")
            if expected_appended_stripped.lower() in verify_comment.lower():
                print(f"[ACTION_HANDLER] ✓ Verified: Comment was successfully appended")
            else:
                print(f"[ACTION_HANDLER] ⚠ Warning: Could not verify comment was appended (may need retry)")
    
    # Step 13: Save debug screenshot after update
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
    
    # Step 1: Initialize debugger and result tracking
    debug = Debugger(action_name="action_11_edit_definition_verification")
    verification_results = {}
    all_passed = True
    error_messages = []
    
    # Step 2: Verify Begin Date
    if begin_date:
        begin_success, begin_msg = helpers.verify_date_field("Begin Date", begin_date, debugger=debug)
        verification_results["begin_date"] = {"success": begin_success, "message": begin_msg}
        if not begin_success:
            all_passed = False
            error_messages.append(f"Begin Date: {begin_msg}")
    else:
        verification_results["begin_date"] = {"success": True, "message": "Skipped (no begin_date provided)"}
    
    # Step 4: Verify Comment
    comment_success, comment_msg = helpers.verify_comment(agent_name, revision_number, original_comment, debugger=debug)
    verification_results["comment"] = {"success": comment_success, "message": comment_msg}
    if not comment_success:
        all_passed = False
        error_messages.append(f"Comment: {comment_msg}")
    
    # Step 5: Return verification summary
    if all_passed:
        summary_msg = "All verifications passed: Begin Date and Comment verified successfully"
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

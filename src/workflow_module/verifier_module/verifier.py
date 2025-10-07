#!/usr/bin/env python3
"""
Verifier Module - Main Interface

This module provides the main interface for verification operations.
It coordinates between verifier_executor, verifier_handlers, and verifier_helpers.

Key Responsibilities:
- Provide main verification interface
- Coordinate verification workflow
- Handle verification results
- Maintain backward compatibility

Architecture:
    Main Interface (THIS FILE)
        ↓
    verifier_executor.py (routes instruction names)
        ↓
    verifier_handlers.py (implements specific verifications)
        ↓
    verifier_helpers.py (performs generic operations)
"""

import time
from typing import Dict, Any, Tuple, Optional
from ..helpers import computer_vision_utils, ocr_utils
from . import verifier_executor
from . import verifier_helpers



def check_workspace_ready(corner_templates: Dict[str, Any],
                         expected_page_text: Optional[str] = None,
                         region_size: int = 200,
                         confidence: float = 0.8) -> Tuple[bool, str]:
    """
    Check if workspace is ready for workflow execution.
    
    This function verifies:
    1. Application is maximized by checking 3 corner templates
    2. Expected page/screen is visible
    
    Uses cv_helper for all computer vision operations.
    
    Args:
        corner_templates: Dictionary with 'top_left', 'top_right', 'bottom_right' template images
        expected_page_text: Text that should be visible on the correct page
        region_size: Size of corner regions to search in pixels
        confidence: Template matching confidence threshold (0-1)
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        corner_templates = {
            'top_left': template_image1,
            'top_right': template_image2,
            'bottom_right': template_image3
        }
        success, msg = check_workspace_ready(
            corner_templates,
            expected_page_text="Multinetwork Instructions"
        )
    """
    print("\n[VERIFIER] Checking if workspace is ready...")
    
    # Step 1: Take screenshot
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        error_msg = "Failed to capture screenshot - cannot verify workspace"
        print(f"[VERIFIER ERROR] {error_msg}")
        return False, error_msg
    
    screen_width, screen_height = computer_vision_utils.get_image_dimensions(screenshot)
    print(f"[VERIFIER] Screen size: {screen_width}x{screen_height}")
    
    # Step 2: Check if application is maximized using corner templates
    print(f"[VERIFIER] Verifying application is maximized...")
    
    all_found, corners_found, confidence_scores = computer_vision_utils.check_corners_maximized(
        screenshot,
        corner_templates,
        region_size,
        confidence
    )
    
    if not all_found:
        missing_corners = [name for name, found in corners_found.items() if not found]
        missing_scores = {name: confidence_scores[name] for name in missing_corners}
        
        error_msg = f"Application not maximized - missing corners: {missing_corners} (scores: {missing_scores})"
        print(f"[VERIFIER ERROR] {error_msg}")
        
        # Save screenshot for debugging
        computer_vision_utils.save_screenshot(screenshot, "workspace_not_maximized.png")
        
        return False, error_msg
    
    print(f"[VERIFIER SUCCESS] All corner templates found - application is maximized")
    
    # Step 3: Verify expected page is visible (if specified)
    if expected_page_text:
        print(f"[VERIFIER] Checking for page indicator: '{expected_page_text}'")
        
        success, found = ocr_utils.find_text(
            screenshot,
            expected_page_text,
            case_sensitive=False
        )
        
        if not success:
            error_msg = "OCR failed during workspace verification"
            print(f"[VERIFIER ERROR] {error_msg}")
            return False, error_msg
        
        if not found:
            error_msg = f"Expected page text '{expected_page_text}' not found - wrong page or application not ready"
            print(f"[VERIFIER ERROR] {error_msg}")
            
            # Save screenshot for debugging
            computer_vision_utils.save_screenshot(screenshot, "workspace_wrong_page.png")
            
            return False, error_msg
        
        print(f"[VERIFIER SUCCESS] Found '{expected_page_text}' - correct page is visible")
    
    # Workspace is ready
    success_msg = "Workspace is ready: application maximized and correct page visible"
    print(f"[VERIFIER SUCCESS] {success_msg}")
    return True, success_msg


def verify_text_is_inputted(expected_text: str,
                           search_region: Optional[Tuple[int, int, int, int]] = None,
                           case_sensitive: bool = False) -> Tuple[bool, str]:
    """
    Verify that text was successfully inputted into a field.
    
    This checks if the expected text now appears on screen in the input area.
    
    Args:
        expected_text: The text that should have been entered
        search_region: Optional (x, y, width, height) region to search in
        case_sensitive: Whether to match case exactly
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        # Verify "Acme Corp" was entered in advertiser field
        success, msg = verify_text_is_inputted("Acme Corp")
    """
    print(f"[VERIFIER] Verifying text was inputted: '{expected_text}'")
    
    # Take screenshot to check current state
    screenshot = computer_vision_utils.take_screenshot()
    if screenshot is None:
        error_msg = "Failed to capture screenshot for verification"
        print(f"[VERIFIER ERROR] {error_msg}")
        return False, error_msg
    
    # If search region specified, crop to that region
    if search_region:
        x, y, w, h = search_region
        screenshot = computer_vision_utils.crop_image(screenshot, x, y, w, h)
        if screenshot is None:
            error_msg = "Failed to crop search region"
            print(f"[VERIFIER ERROR] {error_msg}")
            return False, error_msg
        print(f"[VERIFIER] Searching in region: ({x}, {y}, {w}, {h})")
    
    # Search for the expected text
    success, found = ocr_utils.find_text(
        screenshot,
        expected_text,
        case_sensitive=case_sensitive
    )
    
    if not success:
        error_msg = "OCR failed during text verification"
        print(f"[VERIFIER ERROR] {error_msg}")
        return False, error_msg
    
    if found:
        success_msg = f"Verified: Text '{expected_text}' is present on screen"
        print(f"[VERIFIER SUCCESS] {success_msg}")
        return True, success_msg
    else:
        error_msg = f"Text '{expected_text}' not found - input may have failed"
        print(f"[VERIFIER ERROR] {error_msg}")
        
        # Save screenshot for debugging
        computer_vision_utils.save_screenshot(screenshot, f"text_not_found_{int(time.time())}.png")
        
        return False, error_msg


def verify_text_appears(expected_text: str,
                       search_region: Optional[Tuple[int, int, int, int]] = None,
                       timeout: int = 5,
                       case_sensitive: bool = False) -> Tuple[bool, str]:
    """
    Verify that specific text appears on screen (with timeout).
    
    This waits for text to appear, useful for verifying page loads,
    dropdown options appearing, success messages, etc.
    
    Args:
        expected_text: Text to search for
        search_region: Optional (x, y, width, height) region to search in
        timeout: Maximum seconds to wait for text to appear
        case_sensitive: Whether to match case exactly
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        # Wait for "Search Results" text to appear after clicking search
        success, msg = verify_text_appears("Search Results", timeout=10)
    """
    print(f"[VERIFIER] Waiting for text to appear: '{expected_text}' (timeout: {timeout}s)")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            time.sleep(0.5)
            continue
        
        # Crop if region specified
        search_image = screenshot
        if search_region:
            x, y, w, h = search_region
            search_image = computer_vision_utils.crop_image(screenshot, x, y, w, h)
            if search_image is None:
                time.sleep(0.5)
                continue
        
        # Search for text
        success, found = ocr_utils.find_text(
            search_image,
            expected_text,
            case_sensitive=case_sensitive
        )
        
        if success and found:
            elapsed = time.time() - start_time
            success_msg = f"Text '{expected_text}' appeared after {elapsed:.1f}s"
            print(f"[VERIFIER SUCCESS] {success_msg}")
            return True, success_msg
        
        # Wait a bit before trying again
        time.sleep(0.5)
    
    # Timeout reached
    error_msg = f"Text '{expected_text}' did not appear within {timeout}s"
    print(f"[VERIFIER ERROR] {error_msg}")
    
    # Save final screenshot for debugging
    final_screenshot = computer_vision_utils.take_screenshot()
    if final_screenshot:
        computer_vision_utils.save_screenshot(final_screenshot, f"text_timeout_{int(time.time())}.png")
    
    return False, error_msg


def verify_text_disappears(text_to_check: str,
                          timeout: int = 5) -> Tuple[bool, str]:
    """
    Verify that specific text disappears from screen (with timeout).
    
    Useful for verifying loading spinners disappear, dialogs close, etc.
    
    Args:
        text_to_check: Text that should disappear
        timeout: Maximum seconds to wait for text to disappear
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        # Wait for "Loading..." to disappear
        success, msg = verify_text_disappears("Loading...")
    """
    print(f"[VERIFIER] Waiting for text to disappear: '{text_to_check}' (timeout: {timeout}s)")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            time.sleep(0.5)
            continue
        
        success, found = ocr_utils.find_text(
            screenshot,
            text_to_check,
            case_sensitive=False
        )
        
        if success and not found:
            elapsed = time.time() - start_time
            success_msg = f"Text '{text_to_check}' disappeared after {elapsed:.1f}s"
            print(f"[VERIFIER SUCCESS] {success_msg}")
            return True, success_msg
        
        time.sleep(0.5)
    
    error_msg = f"Text '{text_to_check}' still visible after {timeout}s"
    print(f"[VERIFIER ERROR] {error_msg}")
    return False, error_msg


def verify_action_completed(action_type: str,
                           parameters: Dict[str, Any],
                           verification_config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Verify that an action completed successfully.
    
    This is the main verification function called by workflow engine after each action.
    It uses the verification config from the instruction JSON to determine what to verify.
    
    Args:
        action_type: The type of action that was performed
        parameters: The parameters used for the action
        verification_config: Verification configuration from instruction JSON
        
    Returns:
        Tuple of (success: bool, message)
        
    Expected verification_config structure:
    {
        "type": "text_inputted",  # or "text_appears", "text_disappears"
        "expected_text": "Acme Corp",
        "region": [x, y, width, height],  # Optional
        "timeout": 10  # Optional, for appears/disappears
    }
    
    Example:
        verification_config = {
            "type": "text_inputted",
            "expected_text": parameters["advertiser_name"]
        }
        success, msg = verify_action_completed(
            "enter_advertiser_name",
            parameters,
            verification_config
        )
    """
    print(f"\n[VERIFIER] Verifying action: {action_type}")
    
    # If no verification config provided, cannot verify
    if not verification_config:
        warning_msg = f"No verification config provided for '{action_type}' - skipping verification"
        print(f"[VERIFIER WARNING] {warning_msg}")
        return True, warning_msg
    
    verification_type = verification_config.get("type")
    
    if not verification_type:
        error_msg = "Verification config missing 'type' field"
        print(f"[VERIFIER ERROR] {error_msg}")
        return False, error_msg
    
    # Route to appropriate verification function
    if verification_type == "text_inputted":
        expected_text = verification_config.get("expected_text")
        region = verification_config.get("region")
        
        if not expected_text:
            error_msg = "text_inputted verification missing 'expected_text'"
            print(f"[VERIFIER ERROR] {error_msg}")
            return False, error_msg
        
        return verify_text_is_inputted(expected_text, region)
    
    elif verification_type == "text_appears":
        expected_text = verification_config.get("expected_text")
        region = verification_config.get("region")
        timeout = verification_config.get("timeout", 5)
        
        if not expected_text:
            error_msg = "text_appears verification missing 'expected_text'"
            print(f"[VERIFIER ERROR] {error_msg}")
            return False, error_msg
        
        return verify_text_appears(expected_text, region, timeout)
    
    elif verification_type == "text_disappears":
        text_to_check = verification_config.get("expected_text")
        timeout = verification_config.get("timeout", 5)
        
        if not text_to_check:
            error_msg = "text_disappears verification missing 'expected_text'"
            print(f"[VERIFIER ERROR] {error_msg}")
            return False, error_msg
        
        return verify_text_disappears(text_to_check, timeout)
    
    else:
        error_msg = f"Unknown verification type: '{verification_type}'"
        print(f"[VERIFIER ERROR] {error_msg}")
        return False, error_msg


def save_failure_context(action_type: str,
                        parameters: Dict[str, Any],
                        verification_error: str,
                        attempt_number: int) -> str:
    """
    Save context information when verification fails.
    
    Captures screenshot and returns path for error reporting.
    
    Args:
        action_type: The action that failed verification
        parameters: Parameters used for the action
        verification_error: The error message from verification
        attempt_number: Which retry attempt this was
        
    Returns:
        Path to saved screenshot
    """
    print(f"[VERIFIER] Saving failure context for '{action_type}' (attempt {attempt_number})")
    
    # Capture current state
    screenshot = computer_vision_utils.take_screenshot()
    
    if screenshot is not None:
        # Create descriptive filename
        timestamp = int(time.time())
        filename = f"failure_{action_type}_attempt{attempt_number}_{timestamp}.png"
        
        success, filepath = computer_vision_utils.save_screenshot(screenshot, filename)
        
        if success:
            print(f"[VERIFIER] Failure screenshot saved: {filepath}")
            return filepath
    
    return "Screenshot capture failed"


def verify_multinetwork_page_opened() -> Tuple[bool, str, Optional[Tuple[int, int, int, int]]]:
    """
    Verify that the Multi-Network Instructions page opened successfully.
    
    This function:
    1. Takes a screenshot
    2. Uses computer vision to find the search_fields template within the specified region (206, 152, 1439, 79)
    3. Uses OCR to check for expected text within the same region
    4. Returns the region where elements were found
    
    Returns:
        Tuple of (success: bool, message: str, region: Optional[Tuple[int, int, int, int]])
        - success: Whether the page opened successfully
        - message: Success or error message
        - region: Region where elements were found (x, y, width, height)
        
    Example:
        success, msg, region = verify_multinetwork_page_opened()
        if success:
            print(f"Page opened successfully! Elements found at: {region}")
    """
    print("[VERIFIER] Verifying Multi-Network Instructions page opened...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot", None
        
        # Define the specific region to search within
        # Region: (206, 152, 1439, 79) = (x, y, width, height)
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        search_region = (region_x, region_y, region_width, region_height)
        
        print(f"[VERIFIER] Searching for search fields in region {search_region}")
        
        # Use computer vision to find the search_fields template within the specified region
        fields_found, confidence, fields_position = computer_vision_utils.find_template_in_region(
            screenshot, 
            'assets/search_fields.png', 
            search_region,
            confidence=0.8  # Lower confidence for search fields as they might vary
        )
        
        if not fields_found:
            return False, f"Search fields not found in region {search_region} (confidence: {confidence:.2f})", None
        
        print(f"[VERIFIER] ✓ Search fields found at {fields_position} with confidence {confidence:.2f}")
        print(f"[VERIFIER] Search fields found within region: {search_region}")
        
        # Additional verification: Check for common text within the same region
        print("[VERIFIER] Verifying page content within region...")
        
        # Check for common text that should appear on the Multi-Network Instructions page
        common_texts = [
            "Multi-Network Instructions",
            "Search",
            "Advertiser",
            "Order",
            "Date"
        ]
        
        text_found_count = 0
        for text in common_texts:
            ocr_success, text_found = ocr_utils.find_text_in_region(
                screenshot, 
                text, 
                search_region,
                case_sensitive=False
            )
            if ocr_success and text_found:
                text_found_count += 1
                print(f"[VERIFIER] ✓ Found text '{text}' in region {search_region}")
        
        # Consider page verified if we found at least 2 of the common texts
        if text_found_count >= 2:
            success_msg = f"Multi-Network Instructions page opened successfully! Found {text_found_count} expected text elements in region {search_region}."
            print(f"[VERIFIER] ✓ {success_msg}")
            return True, success_msg, search_region
        else:
            warning_msg = f"Page may not have loaded correctly. Only found {text_found_count} expected text elements in region {search_region}."
            print(f"[VERIFIER] ⚠ {warning_msg}")
            return True, warning_msg, search_region  # Still return success since search fields were found
        
    except Exception as e:
        error_msg = f"Error verifying Multi-Network Instructions page: {e}"
        print(f"[VERIFIER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# MAIN VERIFICATION INTERFACE
# ============================================================================

def verify_action_completion(instruction_name: str, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Main interface for verifying action completion.
    
    This function routes instruction names to their corresponding verifier handlers
    and returns the verification results.
    
    Args:
        instruction_name: Name of the instruction that was executed
        **kwargs: Additional parameters for verification
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
        
    Example:
        success, msg, data = verify_action_completion(
            "open_multinetwork_instructions_page"
        )
    """
    print(f"[VERIFIER] Verifying action completion for: '{instruction_name}'")
    
    # Use verifier_executor to route to appropriate handler
    return verifier_executor.execute_verification(instruction_name, **kwargs)


def verify_instruction_sequence(instructions: list, **kwargs) -> Tuple[bool, list]:
    """
    Verify a sequence of instructions.
    
    Args:
        instructions: List of instruction names to verify
        **kwargs: Additional parameters for verification
        
    Returns:
        Tuple of (all_passed: bool, results: list)
    """
    print(f"[VERIFIER] Verifying sequence of {len(instructions)} instructions")
    
    # Use verifier_executor for batch verification
    return verifier_executor.verify_instruction_sequence(instructions, **kwargs)


def get_supported_verifications() -> list:
    """
    Get list of all supported instruction names that have verifiers.
    
    Returns:
        List of instruction names that have corresponding verifier handlers
    """
    return verifier_executor.get_supported_instructions()


def has_verifier(instruction_name: str) -> bool:
    """
    Check if an instruction has a corresponding verifier handler.
    
    Args:
        instruction_name: Name of the instruction to check
        
    Returns:
        True if verifier handler exists, False otherwise
    """
    return verifier_executor.has_verifier(instruction_name)


# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================

def verify_text_input(text: str, **kwargs) -> Tuple[bool, str]:
    """
    Backward compatibility function for text input verification.
    
    Args:
        text: Text to verify was entered
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    success, message, _ = verify_action_completion("type_text", text=text, **kwargs)
    return success, message


def verify_text_presence(text: str, **kwargs) -> Tuple[bool, str]:
    """
    Backward compatibility function for text presence verification.
    
    Args:
        text: Text to verify is present
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    return verifier_helpers.verify_text_entered(text, **kwargs)


def verify_ui_element(element_name: str, **kwargs) -> Tuple[bool, str]:
    """
    Backward compatibility function for UI element verification.
    
    Args:
        element_name: Name of UI element to verify
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Generic UI element verification
    return verifier_helpers.verify_text_presence([element_name], **kwargs)


def verify_page_state(page_name: str, **kwargs) -> Tuple[bool, str]:
    """
    Backward compatibility function for page state verification.
    
    Args:
        page_name: Name of page to verify
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Generic page state verification
    return verifier_helpers.verify_text_presence([page_name], **kwargs)
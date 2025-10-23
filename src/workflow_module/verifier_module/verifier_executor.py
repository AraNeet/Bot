#!/usr/bin/env python3
"""
Verifier Executor Module - Router for Action Verification

This module routes action types to their corresponding verifier handler functions.
It acts as the central dispatcher that determines which verifier to use based on
what the workflow needs to be checked.

Architecture:
    Action Type (e.g., "enter_advertiser_name")
        ↓
    verifier_executor.py (THIS FILE - routes to appropriate verifier)
        ↓
    verifier_handlers.py (implements the verification, uses verifier.py internally)
        ↓
    verifier.py (performs generic verification operations)

Key Design:
- Routes action types to verifier handler functions
- Extracts parameters from action context
- Calls verifier handler function with parameters
- Returns standardized results
- Handles errors and fallbacks gracefully

Responsibilities:
- Map action type to verifier handler function
- Extract parameters from action context
- Call verifier handler function with parameters
- Return standardized results
- Handle errors and provide fallbacks
"""

from typing import Dict, Any, Tuple, Optional, List
from . import verifier_handlers
from src.notification_module import notify_error
import src.workflow_module.helpers.computer_vision_utils as computer_vision_utils
import time


# ============================================================================
# VERIFIER HANDLER REGISTRY - ACTION TYPE MAPPING
# ============================================================================

# Map action types to their corresponding verifier handler functions
VERIFIER_HANDLERS = {
    # # Navigation actions
    "open_multinetwork_instructions_page": verifier_handlers.verify_multinetwork_page_opened,
    
    # # Search field actions
    "enter_advertiser_name": verifier_handlers.verify_advertiser_name_entered,
    # # "enter_order_number": verifier_handlers.verify_order_number_entered,
    "enter_deal_number": verifier_handlers.verify_deal_number_entered,
    "enter_agency": verifier_handlers.verify_agency_name_entered,
    "enter_begin_date": verifier_handlers.verify_begin_date_entered,
    "enter_end_date": verifier_handlers.verify_end_date_entered,
    
    # Button actions
    "click_search_button": verifier_handlers.verify_search_button_clicked,
    
    # # Form field actions
    # "enter_isci_1": verifier_handlers.verify_isci_1_entered,
    # "enter_isci_2_if_provided": verifier_handlers.verify_isci_2_entered,
    # "enter_isci_3_if_provided": verifier_handlers.verify_isci_3_entered,
    
    # # Save actions
    # "save_instruction": verifier_handlers.verify_instruction_saved,
    
    # # Generic actions (fallback)
    # "type_text": verifier_handlers.verify_text_typed,
    # "click_at_position": verifier_handlers.verify_position_clicked,
    # "press_key": verifier_handlers.verify_key_pressed,
}


# ============================================================================
# VERIFIER EXECUTION FUNCTIONS
# ============================================================================

def verify_action_completion(action_type: str, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that an action completed successfully.
    
    This function routes action types to their corresponding verifier handlers.
    
    Args:
        action_type: Type of action that was executed
        **kwargs: Additional parameters for the verification (e.g., expected values)
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict[str, Any]])
        - success: Whether verification passed
        - message: Success or error message
        - data: Optional additional data (e.g., found regions, coordinates)
        
    Example:
        success, msg, data = verify_action_completion(
            "enter_advertiser_name",
            advertiser_name="Acme Corp"
        )
        
        if success:
            print(f"Verification passed: {msg}")
            if data and 'matched_text' in data:
                print(f"Found text: {data['matched_text']}")
    """
    print(f"[VERIFIER_EXECUTOR] Verifying action completion: '{action_type}'")
    
    try:
        # Check if we have a verifier handler for this action type
        if action_type not in VERIFIER_HANDLERS:
            warning_msg = f"No verifier handler found for action type: '{action_type}'"
            print(f"[VERIFIER_EXECUTOR] ⚠ {warning_msg}")
            return True, warning_msg, None  # Return success to not block workflow
        
        # Get the verifier handler function
        verifier_handler = VERIFIER_HANDLERS[action_type]
        
        print(f"[VERIFIER_EXECUTOR] Calling verifier handler: {verifier_handler.__name__}")
        
        # Call the verifier handler with the provided parameters
        result = verifier_handler(**kwargs)
        
        # Handle different return types from verifier handlers
        if isinstance(result, tuple):
            if len(result) == 2:
                # (success, message)
                success, message = result
                return success, message, None
            elif len(result) == 3:
                # (success, message, data)
                return result
            else:
                # Unexpected tuple length
                error_msg = f"Verifier handler returned unexpected tuple length: {len(result)}"
                print(f"[VERIFIER_EXECUTOR ERROR] {error_msg}")
                return False, error_msg, None
        else:
            # Single return value (assume success)
            return True, str(result), None
            
    except Exception as e:
        error_msg = f"Error verifying action completion for '{action_type}': {e}"
        print(f"[VERIFIER_EXECUTOR ERROR] {error_msg}")
        
        # Send error notification
        try:
            notify_error(f"Verifier Error: {error_msg}")
        except Exception as notify_exception:
            print(f"[VERIFIER_EXECUTOR ERROR] Failed to send error notification: {notify_exception}")
        
        return False, error_msg, None

def has_verifier(action_type: str) -> bool:
    """
    Check if an action type has a corresponding verifier handler.
    
    Args:
        action_type: Type of action to check
        
    Returns:
        True if verifier handler exists, False otherwise
    """
    return action_type in VERIFIER_HANDLERS

def save_failure_context(action_type: str,
                       parameters: Dict[str, Any],
                       verification_error: str,
                       attempt_number: int) -> str:
    """
    Save failure context for debugging purposes.
    
    Args:
        action_type: Type of action that failed
        parameters: Parameters that were used for the action
        verification_error: Error message from verification
        attempt_number: Attempt number for the action
        
    Returns:
        Filepath of saved debug screenshot or error message
    """
    try:
        
        # Generate debug filename
        timestamp = int(time.time())
        filename = f"failure_{action_type}_attempt{attempt_number}_{timestamp}.png"
        
        # Save debug screenshot
        success, filepath = save_debug_screenshot(filename)
        
        if success:
            print(f"[VERIFIER_EXECUTOR] Debug screenshot saved: {filepath}")
            return filepath
        else:
            print(f"[VERIFIER_EXECUTOR] Failed to save debug screenshot: {filepath}")
            return filepath  # Return error message
            
    except Exception as e:
        error_msg = f"Failed to save failure context: {e}"
        print(f"[VERIFIER_EXECUTOR ERROR] {error_msg}")
        return error_msg

def save_debug_screenshot(filename: str = None) -> Tuple[bool, str]:
    """
    Save a debug screenshot for troubleshooting.
    
    Args:
        filename: Optional custom filename
        
    Returns:
        Tuple of (success: bool, filepath or error_message)
    """
    try:
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot"
        
        if filename is None:
            timestamp = int(time.time())
            filename = f"debug_verification_{timestamp}.png"
        
        success, filepath = computer_vision_utils.save_screenshot(screenshot, filename)
        return success, filepath
        
    except Exception as e:
        return False, f"Error saving debug screenshot: {e}"

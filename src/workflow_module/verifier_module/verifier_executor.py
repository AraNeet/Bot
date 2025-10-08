#!/usr/bin/env python3
"""
Verifier Executor Module - Direct Router

This module routes instruction names DIRECTLY to verifier handler functions.
No wrapper functions - just pure routing.

Architecture:
    Instruction Name (e.g., "open_multinetwork_instructions_page")
        ↓
    verifier_executor.py (THIS FILE - routes directly)
        ↓
    verifier_handlers.py (implements the verification, uses verifier_helpers.py internally)

Key Design:
- NO wrapper functions
- NO access to verifier_helpers.py from here
- ONLY routes to verifier_handlers.py
- verifier_handlers.py is responsible for calling verifier_helpers.py

Responsibilities:
- Map instruction name to verifier handler function
- Extract parameters from instruction
- Call verifier handler function with parameters
- Return results
"""

from typing import Dict, Any, Tuple, Optional
from . import verifier_handlers
from src.notification_module import notify_error


# ============================================================================
# VERIFIER HANDLER REGISTRY - DIRECT MAPPING
# ============================================================================

# Map instruction names to their corresponding verifier handler functions
VERIFIER_HANDLERS = {
    # Navigation actions
    "open_multinetwork_instructions_page": verifier_handlers.verify_multinetwork_page_opened,
    
    # Search field actions
    "enter_advertiser_name": verifier_handlers.verify_advertiser_name_entered,
    "enter_order_id": verifier_handlers.verify_order_id_entered,
    "enter_agency": verifier_handlers.verify_agency_name_entered,
    "enter_begin_date": verifier_handlers.verify_begin_date_entered,
    "enter_end_date": verifier_handlers.verify_end_date_entered,
    
    # Button actions
    "click_search_button": verifier_handlers.verify_search_button_clicked,
    
    # Table interaction actions
    "find_row_by_deal_number": verifier_handlers.verify_row_found,
    "right_click_row": verifier_handlers.verify_row_right_clicked,
    "select_edit_multinetwork_instruction": verifier_handlers.verify_edit_menu_selected,
    
    # Form field actions
    "enter_isci_1": verifier_handlers.verify_isci_1_entered,
    "enter_isci_2_if_provided": verifier_handlers.verify_isci_2_entered,
    "enter_isci_3_if_provided": verifier_handlers.verify_isci_3_entered,
    
    # Save actions
    "save_instruction": verifier_handlers.verify_instruction_saved,
    
    # Generic actions (fallback)
    "type_text": verifier_handlers.verify_text_typed,
    "click_at_position": verifier_handlers.verify_position_clicked,
    "press_key": verifier_handlers.verify_key_pressed,
}


# ============================================================================
# VERIFIER EXECUTION FUNCTIONS
# ============================================================================

def execute_verification(instruction_name: str, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute verification for a specific instruction.
    
    This function routes instruction names to their corresponding verifier handlers.
    
    Args:
        instruction_name: Name of the instruction that was executed
        **kwargs: Additional parameters for the verification (e.g., expected values)
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict[str, Any]])
        - success: Whether verification passed
        - message: Success or error message
        - data: Optional additional data (e.g., found regions, coordinates)
        
    Example:
        success, msg, data = execute_verification(
            "open_multinetwork_instructions_page"
        )
        
        if success:
            print(f"Verification passed: {msg}")
            if data and 'region' in data:
                print(f"Found region: {data['region']}")
    """
    print(f"[VERIFIER_EXECUTOR] Executing verification for: '{instruction_name}'")
    
    try:
        # Check if we have a verifier handler for this instruction
        if instruction_name not in VERIFIER_HANDLERS:
            warning_msg = f"No verifier handler found for instruction: '{instruction_name}'"
            print(f"[VERIFIER_EXECUTOR] ⚠ {warning_msg}")
            return True, warning_msg, None  # Return success to not block workflow
        
        # Get the verifier handler function
        verifier_handler = VERIFIER_HANDLERS[instruction_name]
        
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
        error_msg = f"Error executing verification for '{instruction_name}': {e}"
        print(f"[VERIFIER_EXECUTOR ERROR] {error_msg}")
        
        # Send error notification
        try:
            notify_error(f"Verifier Error: {error_msg}")
        except Exception as notify_error:
            print(f"[VERIFIER_EXECUTOR ERROR] Failed to send error notification: {notify_error}")
        
        return False, error_msg, None

def has_verifier(instruction_name: str) -> bool:
    """
    Check if an instruction has a corresponding verifier handler.
    
    Args:
        instruction_name: Name of the instruction to check
        
    Returns:
        True if verifier handler exists, False otherwise
    """
    return instruction_name in VERIFIER_HANDLERS


# ============================================================================
# BATCH VERIFICATION FUNCTIONS
# ============================================================================

def verify_instruction_sequence(instructions: list, **kwargs) -> Tuple[bool, list]:
    """
    Verify a sequence of instructions.
    
    Args:
        instructions: List of instruction names to verify
        **kwargs: Additional parameters for verification
        
    Returns:
        Tuple of (all_passed: bool, results: list)
        - all_passed: Whether all verifications passed
        - results: List of (instruction_name, success, message, data) tuples
    """
    print(f"[VERIFIER_EXECUTOR] Verifying sequence of {len(instructions)} instructions")
    
    results = []
    all_passed = True
    
    for instruction_name in instructions:
        success, message, data = execute_verification(instruction_name, **kwargs)
        results.append((instruction_name, success, message, data))
        
        if not success:
            all_passed = False
            print(f"[VERIFIER_EXECUTOR] ✗ Verification failed for: {instruction_name}")
        else:
            print(f"[VERIFIER_EXECUTOR] ✓ Verification passed for: {instruction_name}")
    
    return all_passed, results

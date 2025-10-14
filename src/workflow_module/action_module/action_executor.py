#!/usr/bin/env python3
"""
Action Executor Module - Direct Router

This module routes action_types DIRECTLY to action_handler functions.
No wrapper functions - just pure routing.

Architecture:
    Instruction JSON (action_type: "enter_advertiser_name")
        ↓
    action_executor.py (THIS FILE - routes directly)
        ↓
    action_handler.py (implements the action, uses actions.py internally)

Key Design:
- NO wrapper functions
- NO access to actions.py from here
- ONLY routes to action_handler.py
- action_handler.py is responsible for calling actions.py

Responsibilities:
- Map action_type to action_handler function
- Extract parameters from instruction
- Call action_handler function with parameters
- Return results
"""

from typing import Dict, Any, Tuple
from . import action_handler
from src.notification_module import notify_error


# ============================================================================
# ACTION HANDLER REGISTRY - DIRECT MAPPING
# ============================================================================

ACTION_HANDLERS: Dict[str, Any] = {
    # ========================================================================
    # APPLICATION-SPECIFIC ACTIONS (action_handler.py)
    # ========================================================================
    
    # Application startup
    # "open_application": action_handler.open_application,
    
    # # Navigation
    # "open_multinetwork_instructions_page": action_handler.open_multinetwork_instructions_page,
    
    # # Search form actions
    # "enter_advertiser_name": action_handler.enter_advertiser_name,
    # # "enter_order_number": action_handler.enter_order_number,
    # "enter_deal_number": action_handler.enter_deal_number,
    # "enter_agency": action_handler.enter_agency,
    # "enter_begin_date": action_handler.enter_begin_date,
    # "enter_end_date": action_handler.enter_end_date,
    # "click_search_button": action_handler.click_search_button,
    # "wait_for_search_results": action_handler.wait_for_search_results,
    
    
    # Table interaction
    "find_row_by_values": action_handler.find_row_by_values,
    # "select_edit_multinetwork_instruction": action_handler.select_edit_multinetwork_instruction,

    # Not implemented
    # # Edit page actions
    # "wait_for_edit_page_load": action_handler.wait_for_edit_page_load,
    # "verify_edit_page_opened": action_handler.verify_edit_page_opened,
    # "enter_isci_1": action_handler.enter_isci_1,
    # "enter_isci_2_if_provided": action_handler.enter_isci_2_if_provided,
    # "enter_isci_3_if_provided": action_handler.enter_isci_3_if_provided,
    
    # # Save actions
    # "save_instruction": action_handler.save_instruction,
    # "verify_save_successful": action_handler.verify_save_successful,
}


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def execute_action(action_type: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Execute an action by routing directly to action_handler.
    
    This function:
    1. Looks up the action_handler function
    2. Extracts parameters needed by that function
    3. Calls the function directly
    4. Returns the result
    
    NO wrapper functions - direct routing only!
    
    Args:
        action_type: Type of action to execute (e.g., "enter_advertiser_name")
        parameters: Parameters dict from instruction
        
    Returns:
        Tuple of (success: bool, message: str)
        
    Example:
        # Instruction has:
        {
            "action_type": "enter_advertiser_name",
            "parameters": {"advertiser_name": "Acme Corp"}
        }
        
        # Executor routes to:
        action_handler.enter_advertiser_name("Acme Corp")
    """
    print(f"\n[EXECUTOR] Executing action: {action_type}")
    print(f"[EXECUTOR] Parameters: {parameters}")
    
    # Check if action type is supported
    if action_type not in ACTION_HANDLERS:
        error_msg = f"Unsupported action type: '{action_type}'"
        print(f"[EXECUTOR ERROR] {error_msg}")
        print(f"[EXECUTOR] Supported actions: {list(ACTION_HANDLERS.keys())}")
        
        notify_error(
            error_msg,
            "action_executor.execute_action",
            {"action_type": action_type, "parameters": parameters}
        )
        
        return False, error_msg
    
    # Get the handler function directly
    handler_func = ACTION_HANDLERS[action_type]
    
    try:
        # Call handler with parameters based on function signature
        # The handler will extract what it needs from parameters dict
        success, message = handler_func(**parameters)
        
        if success:
            print(f"[EXECUTOR SUCCESS] {message}")
        else:
            print(f"[EXECUTOR ERROR] {message}")
        
        return success, message
        
    except TypeError as e:
        # Function signature mismatch (wrong parameters)
        error_msg = f"Parameter mismatch for '{action_type}': {e}"
        print(f"[EXECUTOR ERROR] {error_msg}")
        print(f"[EXECUTOR] Parameters provided: {parameters}")
        
        notify_error(
            error_msg,
            "action_executor.execute_action",
            {
                "action_type": action_type,
                "parameters": parameters,
                "exception": str(e)
            }
        )
        
        return False, error_msg
        
    except Exception as e:
        # Unexpected exception
        error_msg = f"Exception executing action '{action_type}': {e}"
        print(f"[EXECUTOR ERROR] {error_msg}")
        
        notify_error(
            error_msg,
            "action_executor.execute_action",
            {
                "action_type": action_type,
                "parameters": parameters,
                "exception": str(e)
            }
        )
        
        return False, error_msg
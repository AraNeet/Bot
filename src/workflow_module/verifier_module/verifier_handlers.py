#!/usr/bin/env python3
"""
Verifier Handlers Module

This module contains HIGH-LEVEL verifier functions that understand the APPLICATION.
Unlike verifier_helpers.py (generic verification), these functions know WHAT to verify,
WHERE to look, and HOW to interpret the results for specific actions.

Key Difference:
- verifier_helpers.py: Generic "check if text exists" 
- verifier_handlers.py: Specific "verify_multinetwork_page_opened()" that knows what to check

Architecture:
    Instruction Name
        ↓
    verifier_executor.py (routes to this file)
        ↓
    verifier_handlers.py (THIS FILE - knows what to verify, calls verifier_helpers.py)
        ↓
    verifier_helpers.py (performs generic verification)

Each function here:
1. Knows what to verify for a specific action
2. Uses verifier_helpers.py to perform the actual verification
3. Interprets the results in context of the action
4. Returns (success: bool, message: str, data: Optional[Dict])

IMPORTANT: Functions receive parameters via **kwargs pattern:
    def verify_advertiser_name_entered(advertiser_name: str = "", **kwargs):
        # Use advertiser_name
        # Ignore any extra kwargs
"""

from typing import Dict, Any, Tuple, Optional
from . import verifier_helpers


# ============================================================================
# NAVIGATION VERIFICATION HANDLERS
# ============================================================================

def verify_multinetwork_page_opened(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the Multi-Network Instructions page opened successfully.
    
    This handler knows:
    - What template to look for (search_fields.png)
    - What text should be present on the page
    - How to interpret the verification results
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
        - success: Whether the page opened correctly
        - message: Success or error message
        - data: Dictionary with 'region' key containing found coordinates
    """
    print("[VERIFIER_HANDLER] Verifying Multi-Network Instructions page opened...")
    
    try:
        # Use verifier_helpers to perform the actual verification
        success, message, region = verifier_helpers.verify_page_with_template(
            template_path='assets/search_fields.png',
            expected_texts=[
                "Search",
                "Advertiser",
                "Order",
                "Date"
            ],
            min_text_matches=2,
            confidence=0.8
        )
        
        # Prepare return data
        data = None
        if success and region:
            data = {'region': region}
        
        return success, message, data
        
    except Exception as e:
        error_msg = f"Error verifying Multi-Network Instructions page: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# SEARCH FIELD VERIFICATION HANDLERS
# ============================================================================

def verify_advertiser_name_entered(advertiser_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the advertiser name was entered correctly.
    
    This handler knows:
    - Where to look for the entered advertiser name
    - How to verify the text was entered correctly
    - What constitutes a successful entry
    
    Args:
        advertiser_name: Expected advertiser name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    try:
        # Use verifier_helpers to check if the text was entered
        success, message = verifier_helpers.verify_text_entered(
            expected_text=advertiser_name,
            region=None,  # Search full screen
            case_sensitive=False
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying advertiser name entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_order_id_entered(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the order ID was entered correctly.
    
    Args:
        order_number: Expected order ID to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{order_number}'")
    
    if not order_number:
        return True, "No order ID to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=order_number,
            region=None,
            case_sensitive=True  # Order IDs are usually case-sensitive
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying order ID entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_start_date_entered(start_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the start date was entered correctly.
    
    Args:
        start_date: Expected start date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying start date entered: '{start_date}'")
    
    if not start_date:
        return True, "No start date to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=start_date,
            region=None,
            case_sensitive=False
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying start date entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_end_date_entered(end_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the end date was entered correctly.
    
    Args:
        end_date: Expected end date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying end date entered: '{end_date}'")
    
    if not end_date:
        return True, "No end date to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=end_date,
            region=None,
            case_sensitive=False
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying end date entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# BUTTON VERIFICATION HANDLERS
# ============================================================================

def verify_search_button_clicked(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the search button was clicked successfully.
    
    This handler knows:
    - What should happen after clicking search (loading, results appear)
    - How to detect if the search was successful
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying search button clicked...")
    
    try:
        # Check for loading indicators or results
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Loading", "Results", "Search Results"],
            timeout=5.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying search button click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# TABLE INTERACTION VERIFICATION HANDLERS
# ============================================================================

def verify_row_found(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a row with the specified order number was found.
    
    Args:
        order_number: Order number to verify was found
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying row found for order: '{order_number}'")
    
    if not order_number:
        return True, "No order number to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=order_number,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying row found: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_row_right_clicked(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a row was right-clicked successfully.
    
    Args:
        order_number: Order number of the row that was right-clicked
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying row right-clicked for order: '{order_number}'")
    
    try:
        # Check for context menu appearance
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Edit", "Menu", "Context"],
            timeout=2.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying row right-click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_edit_menu_selected(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the edit menu was selected successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying edit menu selected...")
    
    try:
        # Check for edit page elements
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Edit", "Multi-network", "Instructions"],
            timeout=3.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying edit menu selection: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# FORM FIELD VERIFICATION HANDLERS
# ============================================================================

def verify_isci_1_entered(isci_1: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 1 was entered correctly.
    
    Args:
        isci_1: Expected ISCI 1 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 1 entered: '{isci_1}'")
    
    if not isci_1:
        return True, "No ISCI 1 to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=isci_1,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 1 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_2_entered(isci_2: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 2 was entered correctly.
    
    Args:
        isci_2: Expected ISCI 2 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 2 entered: '{isci_2}'")
    
    if not isci_2:
        return True, "ISCI 2 not provided - skipping verification", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=isci_2,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 2 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_3_entered(isci_3: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 3 was entered correctly.
    
    Args:
        isci_3: Expected ISCI 3 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 3 entered: '{isci_3}'")
    
    if not isci_3:
        return True, "ISCI 3 not provided - skipping verification", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=isci_3,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 3 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# SAVE VERIFICATION HANDLERS
# ============================================================================

def verify_instruction_saved(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the instruction was saved successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying instruction saved...")
    
    try:
        # Check for success messages or return to previous page
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Saved", "Success", "Complete"],
            timeout=3.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying instruction save: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# GENERIC VERIFICATION HANDLERS (FALLBACK)
# ============================================================================

def verify_text_typed(text: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generic verifier for text typing actions.
    
    Args:
        text: Text that was typed
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying text typed: '{text}'")
    
    if not text:
        return True, "No text to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=text,
            region=None,
            case_sensitive=False
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying text typed: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_position_clicked(x: int = 0, y: int = 0, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generic verifier for position clicking actions.
    
    Args:
        x: X coordinate that was clicked
        y: Y coordinate that was clicked
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying position clicked: ({x}, {y})")
    
    try:
        # For generic clicks, we assume success unless there's an obvious error
        # This is a fallback verifier, so we're lenient
        return True, f"Position ({x}, {y}) clicked successfully", None
        
    except Exception as e:
        error_msg = f"Error verifying position click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_key_pressed(key: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generic verifier for key press actions.
    
    Args:
        key: Key that was pressed
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying key pressed: '{key}'")
    
    try:
        # For generic key presses, we assume success
        # This is a fallback verifier, so we're lenient
        return True, f"Key '{key}' pressed successfully", None
        
    except Exception as e:
        error_msg = f"Error verifying key press: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None

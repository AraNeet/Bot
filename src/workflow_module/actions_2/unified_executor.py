#!/usr/bin/env python3
"""
Unified Executor Module

This module provides a unified interface for executing actions that:
1. Executes the action
2. Verifies the action completed successfully
3. Handles errors if needed
4. Implements retry logic

This replaces the separate action_executor and verifier_executor pattern.
"""

from typing import Dict, Any, Tuple, Optional
import json
import importlib
from pathlib import Path
from src.notification_module.error_notifier import notify_error

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_action_list(config_path: str = "src/workflow_module/actions_2/action_list.json") -> Dict[str, Any]:
    """
    Load action list from JSON file.
    
    This file stores all the actions that can be completed by the system.
    
    Args:
        config_path: Path to the action list JSON file
        
    Returns:
        Dictionary mapping action types to handler modules
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"[UNIFIED_EXECUTOR] Loaded action list from {config_path}")
        return config
    except FileNotFoundError:
        print(f"[UNIFIED_EXECUTOR ERROR] Action list file not found: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[UNIFIED_EXECUTOR ERROR] Failed to parse action list: {e}")
        return {}

# Load action list at module import
ACTION_LIST = load_action_list()

# ============================================================================
# HANDLER LOADING
# ============================================================================

def get_handler_module(action_type: str):
    """
    Dynamically import and return the handler module for an action type.
    
    Args:
        action_type: The action type (e.g., "enter_advertiser_name")
        
    Returns:
        Handler module object with action, verifier, and error_handler functions
    """
    if action_type not in ACTION_LIST:
        return None
    
    handler_info = ACTION_LIST[action_type]
    module_path = handler_info.get('module')
    
    if not module_path:
        print(f"[UNIFIED_EXECUTOR ERROR] No module path for action type: {action_type}")
        return None
    
    try:
        # Import the handler module dynamically
        module = importlib.import_module(module_path)
        return module
    except ImportError as e:
        print(f"[UNIFIED_EXECUTOR ERROR] Failed to import handler module {module_path}: {e}")
        return None

# ============================================================================
# UNIFIED EXECUTION FUNCTION
# ============================================================================

def execute_action_with_verification(
    action_type: str, 
    parameters: Dict[str, Any],
    max_retries: int = 3,
    verify: bool = True
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute an action with integrated verification and error handling.
    
    This function:
    1. Loads the appropriate handler module
    2. Executes the action
    3. Verifies the action (if verify=True)
    4. Handles errors and implements retry logic
    5. Returns comprehensive results
    
    Args:
        action_type: Type of action to execute (e.g., "enter_advertiser_name")
        parameters: Parameters dict for the action
        max_retries: Maximum number of retry attempts
        verify: Whether to run verification after action
        
    Returns:
        Tuple of (success: bool, message: str, verification_data: Optional[Dict])
        
    Example:
        success, msg, data = execute_action_with_verification(
            "enter_advertiser_name",
            {"advertiser_name": "Acme Corp"},
            max_retries=3,
            verify=True
        )
    """
    print(f"\n[UNIFIED_EXECUTOR] Executing action: {action_type}")
    print(f"[UNIFIED_EXECUTOR] Parameters: {parameters}")
    print(f"[UNIFIED_EXECUTOR] Max retries: {max_retries}, Verify: {verify}")
    
    # Check if action type is supported
    if action_type not in ACTION_LIST:
        error_msg = f"Unsupported action type: '{action_type}'"
        print(f"[UNIFIED_EXECUTOR ERROR] {error_msg}")
        print(f"[UNIFIED_EXECUTOR] Supported actions: {list(ACTION_LIST.keys())}")
        
        notify_error(
            error_msg,
            "unified_executor.execute_action_with_verification",
            {"action_type": action_type, "parameters": parameters}
        )
        
        return False, error_msg, None
    
    # Load handler module
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        error_msg = f"Failed to load handler module for action type: '{action_type}'"
        print(f"[UNIFIED_EXECUTOR ERROR] {error_msg}")
        return False, error_msg, None
    
    # Verify handler module has required functions
    if not hasattr(handler_module, 'action'):
        error_msg = f"Handler module for '{action_type}' missing 'action' function"
        print(f"[UNIFIED_EXECUTOR ERROR] {error_msg}")
        return False, error_msg, None
    
    # Retry loop
    for attempt in range(1, max_retries + 1):
        print(f"\n[UNIFIED_EXECUTOR] Attempt {attempt}/{max_retries}")
        
        # ========================================================================
        # STEP 1: Execute Action
        # ========================================================================
        print(f"[UNIFIED_EXECUTOR] Executing action...")
        try:
            action_success, action_msg = handler_module.action(**parameters)
        except Exception as e:
            action_success = False
            action_msg = f"Exception during action execution: {e}"
            print(f"[UNIFIED_EXECUTOR ERROR] {action_msg}")
        
        if not action_success:
            print(f"[UNIFIED_EXECUTOR ERROR] Action execution failed: {action_msg}")
            
            # Call error handler if available
            if hasattr(handler_module, 'error_handler'):
                print(f"[UNIFIED_EXECUTOR] Calling error handler...")
                try:
                    should_retry, recovery_msg = handler_module.error_handler(
                        error_msg=action_msg,
                        attempt=attempt,
                        max_attempts=max_retries,
                        **parameters
                    )
                    print(f"[UNIFIED_EXECUTOR] Error handler result: {recovery_msg}")
                    
                    if not should_retry or attempt == max_retries:
                        # Don't retry or max attempts reached
                        final_error_msg = f"Action '{action_type}' failed: {action_msg}"
                        notify_error(
                            final_error_msg,
                            "unified_executor.execute_action_with_verification",
                            {
                                "action_type": action_type,
                                "parameters": parameters,
                                "attempts": attempt,
                                "final_error": action_msg
                            }
                        )
                        return False, final_error_msg, None
                    
                    # Retry
                    print(f"[UNIFIED_EXECUTOR] Retrying action...")
                    continue
                    
                except Exception as e:
                    print(f"[UNIFIED_EXECUTOR ERROR] Error handler failed: {e}")
            
            # If this was the last attempt or no error handler, fail
            if attempt == max_retries:
                final_error_msg = f"Action '{action_type}' failed after {max_retries} attempts: {action_msg}"
                notify_error(
                    final_error_msg,
                    "unified_executor.execute_action_with_verification",
                    {
                        "action_type": action_type,
                        "parameters": parameters,
                        "attempts": max_retries,
                        "final_error": action_msg
                    }
                )
                return False, final_error_msg, None
            
            # Otherwise, retry
            print(f"[UNIFIED_EXECUTOR] Retrying action...")
            continue
        
        print(f"[UNIFIED_EXECUTOR SUCCESS] Action executed: {action_msg}")
        
        # ========================================================================
        # STEP 2: Verify Action (if enabled and verifier exists)
        # ========================================================================
        if verify and hasattr(handler_module, 'verifier'):
            print(f"[UNIFIED_EXECUTOR] Verifying action completion...")
            
            try:
                verification_result = handler_module.verifier(**parameters)
                
                # Handle different return types
                if isinstance(verification_result, tuple):
                    if len(verification_result) == 2:
                        verification_success, verification_msg = verification_result
                        verification_data = None
                    elif len(verification_result) == 3:
                        verification_success, verification_msg, verification_data = verification_result
                    else:
                        verification_success = False
                        verification_msg = "Invalid verifier return format"
                        verification_data = None
                else:
                    verification_success = True
                    verification_msg = str(verification_result)
                    verification_data = None
                
            except Exception as e:
                verification_success = False
                verification_msg = f"Exception during verification: {e}"
                verification_data = None
                print(f"[UNIFIED_EXECUTOR ERROR] {verification_msg}")
            
            if verification_success:
                print(f"[UNIFIED_EXECUTOR SUCCESS] Action verified: {verification_msg}")
                return True, f"Action '{action_type}' completed and verified", verification_data
            else:
                print(f"[UNIFIED_EXECUTOR ERROR] Verification failed: {verification_msg}")
                
                # Call error handler for verification failure
                if hasattr(handler_module, 'error_handler'):
                    try:
                        should_retry, recovery_msg = handler_module.error_handler(
                            error_msg=verification_msg,
                            attempt=attempt,
                            max_attempts=max_retries,
                            **parameters
                        )
                        
                        if not should_retry or attempt == max_retries:
                            # Don't retry or max attempts reached
                            final_error_msg = f"Action '{action_type}' failed verification after {attempt} attempts"
                            notify_error(
                                final_error_msg,
                                "unified_executor.execute_action_with_verification",
                                {
                                    "action_type": action_type,
                                    "parameters": parameters,
                                    "verification_error": verification_msg,
                                    "attempts": attempt
                                }
                            )
                            return False, final_error_msg, verification_data
                    except Exception as e:
                        print(f"[UNIFIED_EXECUTOR ERROR] Error handler failed: {e}")
                
                # Check if this was the last attempt
                if attempt == max_retries:
                    final_error_msg = f"Action '{action_type}' failed verification after {max_retries} attempts"
                    notify_error(
                        final_error_msg,
                        "unified_executor.execute_action_with_verification",
                        {
                            "action_type": action_type,
                            "parameters": parameters,
                            "verification_error": verification_msg,
                            "attempts": max_retries
                        }
                    )
                    return False, final_error_msg, verification_data
                
                # Retry on verification failure
                print(f"[UNIFIED_EXECUTOR] Retrying action due to verification failure...")
                continue
        else:
            # No verification requested or no verifier available
            if verify and not hasattr(handler_module, 'verifier'):
                print(f"[UNIFIED_EXECUTOR] No verifier available for action type: '{action_type}'")
            
            return True, f"Action '{action_type}' executed successfully", None
    
    # Should not reach here, but just in case
    return False, f"Unexpected end of retry loop for '{action_type}'", None

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_supported_actions() -> list:
    """
    Get list of supported action types.
    
    Returns:
        List of supported action type strings
    """
    return list(ACTION_LIST.keys())

def has_verifier(action_type: str) -> bool:
    """
    Check if an action type has a verifier.
    
    Args:
        action_type: The action type to check
        
    Returns:
        True if verifier exists, False otherwise
    """
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        return False
    return hasattr(handler_module, 'verifier')

def has_error_handler(action_type: str) -> bool:
    """
    Check if an action type has an error handler.
    
    Args:
        action_type: The action type to check
        
    Returns:
        True if error handler exists, False otherwise
    """
    handler_module = get_handler_module(action_type)
    if handler_module is None:
        return False
    return hasattr(handler_module, 'error_handler')


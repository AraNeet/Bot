#!/usr/bin/env python3
"""
Action Executor Module - Dictionary Dispatch Pattern

This module handles the actual execution of individual actions within the workflow.
Each action follows a three-step pattern:
1. Verify prerequisites (correct state/page/element visibility)
2. Perform any pre-action requirements (finding elements, preparing state)
3. Execute the action itself

This implementation uses the Dictionary Dispatch Pattern for clean, extensible code.
Adding new actions is as simple as creating a handler function and adding it to
the ACTION_HANDLERS dictionary.

The module is designed to work with image template matching and OCR for
element location and verification.
"""

import time
import pyautogui
from typing import Dict, Any, Tuple, Callable
from . import verifier
from src.NotificationModule import email_notifier


# ============================================================================
# EXECUTOR COMMAND FUNCTIONS - Reusable action execution primitives
# ============================================================================

def execute_keyboard_shortcut(keys: list, wait_time: float = 0.5) -> Tuple[bool, str]:
    """
    Execute a keyboard shortcut.
    
    Args:
        keys: List of keys to press (e.g., ["ctrl", "n"])
        wait_time: Time to wait after executing shortcut
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    # Check if keys are provided
    if not keys:
        return False, "No keyboard shortcut keys provided"
    
    try:
        pyautogui.hotkey(*keys)
        time.sleep(wait_time)
        keys_str = '+'.join(keys)
        return True, f"Executed keyboard shortcut: {keys_str}"
    except Exception as e:
        return False, f"Failed to execute keyboard shortcut: {str(e)}"


def execute_type_text(text: str, interval: float = 0.05) -> Tuple[bool, str]:
    """
    Type text using keyboard.
    
    Args:
        text: Text to type
        interval: Delay between keystrokes
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    # Check if text is provided
    if not text:
        return False, "No text content to type"
    
    try:
        pyautogui.typewrite(text, interval=interval)
        return True, f"Typed text ({len(text)} characters)"
    except Exception as e:
        return False, f"Failed to type text: {str(e)}"


def execute_wait(timeout: float) -> Tuple[bool, str]:
    """
    Wait for specified duration.
    
    Args:
        timeout: Time to wait in seconds
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    try:
        time.sleep(timeout)
        return True, f"Waited {timeout} seconds"
    except Exception as e:
        return False, f"Failed to wait: {str(e)}"



# ============================================================================
# PRE-ACTION REQUIREMENT HANDLERS
# ============================================================================

def prepare_keyboard_shortcut(keys: list) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for keyboard shortcut actions."""
    # Check if keys are provided
    if not keys:
        return False, {"error": "No keys provided"}
    
    prepared_data = {
        "method": "keyboard_shortcut",
        "keys": keys
    }
    return True, prepared_data


def prepare_open_file_menu(parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for opening File menu."""
    # For opening File menu, we use Alt+F keyboard shortcut
    return prepare_keyboard_shortcut(["alt", "f"])


def prepare_click_new_file(parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for clicking New file."""
    # For creating new file, we use Ctrl+N keyboard shortcut
    return prepare_keyboard_shortcut(["ctrl", "n"])


def prepare_wait(parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for wait action."""
    timeout = parameters.get("timeout", 5)
    prepared_data = {
        "timeout": timeout,
        "wait_type": "time_based"
    }
    return True, prepared_data


def prepare_enter_text(parameters: Dict[str, Any], param_key: str) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for text entry actions."""
    text = parameters.get(param_key, "")
    # Check if text is provided
    if not text:
        return False, {"error": f"No {param_key} provided"}
    
    prepared_data = {
        "text": text,
        "method": "type_text"
    }
    return True, prepared_data


def prepare_enter_filename(parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for entering filename."""
    return prepare_enter_text(parameters, "filename")


def prepare_enter_text_content(parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for entering text content."""
    return prepare_enter_text(parameters, "text")


def prepare_save_file(parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Prepare data for saving file."""
    # For saving file, we use Ctrl+S keyboard shortcut
    return prepare_keyboard_shortcut(["ctrl", "s"])


# Dictionary mapping action types to preparation functions
PREPARATION_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, Dict[str, Any]]]] = {
    "open_file_menu": prepare_open_file_menu,
    "click_new_file": prepare_click_new_file,
    "wait_for_new_file": prepare_wait,
    "enter_filename": prepare_enter_filename,
    "enter_text": prepare_enter_text_content,
    "save_file": prepare_save_file,
}


def perform_pre_action_requirements(action_type: str, 
                                   parameters: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Perform any requirements needed before executing the action.
    
    This might include:
    - Finding button/image locations using template matching
    - Finding text locations using OCR
    - Preparing the UI state
    - Calculating click coordinates
    
    Args:
        action_type: The type of action about to be performed
        parameters: Parameters for the action
        
    Returns:
        Tuple of (success: bool, prepared_data or error_message)
    """
    print(f"  Performing pre-action requirements for: {action_type}")
    
    # Look up the preparation function for this action type
    preparer = PREPARATION_HANDLERS.get(action_type)
    
    # Check if preparer exists for this action type
    if preparer is None:
        error_msg = f"No preparation handler for action type: {action_type}"
        return False, error_msg
    
    # Execute the preparation function
    success, prepared_data = preparer(parameters)
    
    # Check if preparation was successful
    if not success:
        error_msg = prepared_data.get("error", "Preparation failed")
        return False, error_msg
    
    return True, prepared_data


# ============================================================================
# ACTION EXECUTION HANDLERS
# ============================================================================

def execute_keyboard_action(prepared_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute keyboard shortcut action."""
    method = prepared_data.get("method")
    # Check if method is keyboard shortcut
    if method != "keyboard_shortcut":
        return False, f"Unknown method: {method}"
    
    keys = prepared_data.get("keys", [])
    return execute_keyboard_shortcut(keys, wait_time=0.5)


def execute_wait_action(prepared_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute wait action."""
    wait_type = prepared_data.get("wait_type")
    # Check if wait type is time-based
    if wait_type != "time_based":
        return False, f"Unknown wait type: {wait_type}"
    
    timeout = prepared_data.get("timeout", 5)
    return execute_wait(timeout)


def execute_text_typing_action(prepared_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute text typing action."""
    method = prepared_data.get("method")
    # Check if method is type text
    if method != "type_text":
        return False, f"Unknown method: {method}"
    
    text = prepared_data.get("text")
    return execute_type_text(text, interval=0.05)


# Dictionary mapping action types to execution handler functions
EXECUTION_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, str]]] = {
    "open_file_menu": execute_keyboard_action,
    "click_new_file": execute_keyboard_action,
    "wait_for_new_file": execute_wait_action,
    "enter_filename": execute_text_typing_action,
    "enter_text": execute_text_typing_action,
    "save_file": execute_keyboard_action,
}


def execute_action_step(action_type: str, 
                       prepared_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Execute the actual action using the prepared data.
    
    This is where the actual interaction happens (clicking, typing, etc.)
    
    Args:
        action_type: The type of action to perform
        prepared_data: Data prepared by perform_pre_action_requirements()
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    print(f"  Executing action: {action_type}")
    
    try:
        # Look up the execution handler function for this action type
        handler = EXECUTION_HANDLERS.get(action_type)
        
        # Check if handler exists for this action type
        if handler is None:
            return False, f"Unknown action type for execution: {action_type}"
        
        # Execute the handler function
        return handler(prepared_data)
        
    except Exception as e:
        error_msg = f"Exception during action execution: {str(e)}"
        email_notifier.notify_error(error_msg, "action_executor.execute_action_step",
                                    {"action_type": action_type})
        return False, error_msg


# ============================================================================
# MAIN ACTION CONTROL FUNCTION
# ============================================================================

def execute_action(action_type: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Execute a complete action following the three-step pattern:
    1. Verify prerequisites
    2. Perform pre-action requirements
    3. Execute the action
    
    This function recieve executes the list of actions.
    
    Args:
        action_type: The type of action to execute
        parameters: Parameters for the action
        
    Returns:
        Tuple of (success: bool, result_message)
    """
    # Step 1: Verify prerequisites
    prereq_success, prereq_msg = verifier.verify_prerequisite(action_type, parameters)
    # Check if prerequisites are met
    if not prereq_success:
        error_msg = f"Prerequisite verification failed: {prereq_msg}"
        return False, error_msg
    
    # Step 2: Perform pre-action requirements
    prep_success, prep_data = perform_pre_action_requirements(action_type, parameters)
    # Check if pre-action requirements were performed successfully
    if not prep_success:
        error_msg = f"Pre-action requirements failed: {prep_data}"
        return False, error_msg
    
    prepared_data = prep_data
    
    # Step 3: Execute the action
    exec_success, exec_msg = execute_action_step(action_type, prepared_data)
    # Check if action execution was successful
    if not exec_success:
        error_msg = f"Action execution failed: {exec_msg}"
        return False, error_msg
    
    return True, exec_msg

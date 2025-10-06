#!/usr/bin/env python3
"""
Action Executor Module

This module handles the execution logic for automation actions.
It routes action requests to the appropriate action functions and
manages the execution flow.

Responsibilities:
- Route action types to handler functions
- Execute actions through the actions module
- Handle errors and logging
- Provide action registration for extensibility

The actual action implementations are in the actions module.
"""

from typing import Dict, Any, Tuple, Callable
from src.workflow_module import actions
from src.notification_module import notify_error


# ============================================================================
# ACTION HANDLER WRAPPERS
# ============================================================================

def execute_type_text_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute type_text action from parameters."""
    text = parameters.get("text", "")
    interval = parameters.get("interval", 0.05)
    return actions.type_text(text, interval)


def execute_press_key_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute press_key action from parameters."""
    key = parameters.get("key", "")
    presses = parameters.get("presses", 1)
    
    if not key:
        return False, "No key specified for press_key action"
    
    return actions.press_key(key, presses)


def execute_keyboard_shortcut_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute keyboard_shortcut action from parameters."""
    keys = parameters.get("keys", [])
    
    if not keys:
        return False, "No keys specified for keyboard_shortcut"
    
    return actions.keyboard_shortcut(*keys)


def execute_click_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute click_at_position action from parameters."""
    x = parameters.get("x")
    y = parameters.get("y")
    clicks = parameters.get("clicks", 1)
    button = parameters.get("button", "left")
    
    if x is None or y is None:
        return False, "Missing x or y coordinate for click action"
    
    return actions.click_at_position(x, y, clicks, button)


def execute_right_click_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute right_click_at_position action from parameters."""
    x = parameters.get("x")
    y = parameters.get("y")
    
    if x is None or y is None:
        return False, "Missing x or y coordinate for right_click action"
    
    return actions.right_click_at_position(x, y)


def execute_double_click_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute double_click_at_position action from parameters."""
    x = parameters.get("x")
    y = parameters.get("y")
    
    if x is None or y is None:
        return False, "Missing x or y coordinate for double_click action"
    
    return actions.double_click_at_position(x, y)


def execute_move_mouse_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute move_mouse action from parameters."""
    x = parameters.get("x")
    y = parameters.get("y")
    duration = parameters.get("duration", 0.5)
    
    if x is None or y is None:
        return False, "Missing x or y coordinate for move_mouse action"
    
    return actions.move_mouse(x, y, duration)


def execute_wait_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute wait_duration action from parameters."""
    seconds = parameters.get("seconds", 1.0)
    timeout = parameters.get("timeout", seconds)  # Support both 'seconds' and 'timeout'
    
    return actions.wait_duration(timeout)


def execute_clear_field_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute clear_field action from parameters."""
    num_backspaces = parameters.get("num_backspaces", 50)
    return actions.clear_field(num_backspaces)


def execute_select_dropdown_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute select_dropdown_option action from parameters."""
    option_text = parameters.get("option_text", "")
    search_first = parameters.get("search_first", True)
    wait_after_type = parameters.get("wait_after_type", 0.5)
    
    if not option_text:
        return False, "No option_text specified for select_dropdown"
    
    return actions.select_dropdown_option(option_text, search_first, wait_after_type)


def execute_scroll_down_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute scroll_down action from parameters."""
    clicks = parameters.get("clicks", 3)
    return actions.scroll_down(clicks)


def execute_scroll_up_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute scroll_up action from parameters."""
    clicks = parameters.get("clicks", 3)
    return actions.scroll_up(clicks)


def execute_type_and_enter_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute type_and_enter action from parameters."""
    text = parameters.get("text", "")
    interval = parameters.get("interval", 0.05)
    return actions.type_and_enter(text, interval)


def execute_clear_and_type_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute clear_and_type action from parameters."""
    text = parameters.get("text", "")
    interval = parameters.get("interval", 0.05)
    return actions.clear_and_type(text, interval)


def execute_select_all_action(parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute select_all action from parameters."""
    return actions.select_all()


# ============================================================================
# ACTION HANDLER REGISTRY
# ============================================================================

# Action type to handler function mapping
ACTION_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, str]]] = {
    # Keyboard actions
    "type_text": execute_type_text_action,
    "press_key": execute_press_key_action,
    "keyboard_shortcut": execute_keyboard_shortcut_action,
    
    # Mouse actions
    "click": execute_click_action,
    "click_at_position": execute_click_action,
    "right_click": execute_right_click_action,
    "right_click_at_position": execute_right_click_action,
    "double_click": execute_double_click_action,
    "double_click_at_position": execute_double_click_action,
    "move_mouse": execute_move_mouse_action,
    
    # Wait actions
    "wait": execute_wait_action,
    "wait_duration": execute_wait_action,
    
    # Field actions
    "clear_field": execute_clear_field_action,
    "select_all": execute_select_all_action,
    "select_dropdown": execute_select_dropdown_action,
    
    # Scroll actions
    "scroll_down": execute_scroll_down_action,
    "scroll_up": execute_scroll_up_action,
    
    # Combined actions
    "type_and_enter": execute_type_and_enter_action,
    "clear_and_type": execute_clear_and_type_action,
}


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def execute_action(action_type: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Execute an action based on its type.
    
    This is the main entry point called by the workflow engine.
    It routes to the appropriate handler function based on action_type.
    
    Args:
        action_type: Type of action to execute (e.g., "type_text", "press_key")
        parameters: Parameters for the action
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = execute_action(
            action_type="type_text",
            parameters={"text": "Acme Corp", "interval": 0.05}
        )
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
    
    # Get the handler function
    handler = ACTION_HANDLERS[action_type]
    
    try:
        # Execute the action through handler
        success, message = handler(parameters)
        
        if success:
            print(f"[EXECUTOR SUCCESS] {message}")
        else:
            print(f"[EXECUTOR ERROR] {message}")
        
        return success, message
        
    except Exception as e:
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

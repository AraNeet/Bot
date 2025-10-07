#!/usr/bin/env python3
"""
Actions Module

This module contains all the individual action functions that can be performed
during automation. Each function performs a specific automation task.

Action Categories:
- Keyboard actions: Typing, key presses, shortcuts
- Mouse actions: Clicking, moving
- Wait actions: Delays and timeouts
- Field actions: Clearing fields, selecting options

All action functions follow the same pattern:
- Accept specific parameters
- Return Tuple[bool, str] for success/failure
- Log their operations
"""

import time
import pyautogui
from typing import Tuple

# Configure pyautogui safety settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.5  # Default pause between actions


# ============================================================================
# KEYBOARD ACTIONS
# ============================================================================

def type_text(text: str, interval: float = 0.05) -> Tuple[bool, str]:
    """
    Type text character by character.
    
    Args:
        text: Text to type
        interval: Delay between keystrokes in seconds
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = type_text("Acme Corp", interval=0.05)
    """
    try:
        if not text:
            return True, "No text to type (empty string)"
        
        print(f"[ACTION] Typing text: '{text}' (interval: {interval}s)")
        pyautogui.write(text, interval=interval)
        
        success_msg = f"Successfully typed: '{text}'"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to type text: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

def press_key(key: str, presses: int) -> Tuple[bool, str]:
    """
    Press a specific key one or more times.
    
    Args:
        key: Key to press (e.g., 'enter', 'tab', 'esc', 'down', 'up')
        presses: Number of times to press the key
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = press_key("enter", presses=1)
        success, msg = press_key("down", presses=3)
    """
    try:
        print(f"[ACTION] Pressing key: '{key}' ({presses} time(s))")
        pyautogui.press(key, presses=presses)
        
        success_msg = f"Successfully pressed '{key}' {presses} time(s)"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to press key '{key}': {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

def keyboard_shortcut(*keys) -> Tuple[bool, str]:
    """
    Execute a keyboard shortcut (e.g., Ctrl+C, Alt+F4).
    
    Args:
        *keys: Keys to press simultaneously (e.g., 'ctrl', 'c')
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = keyboard_shortcut('ctrl', 'c')  # Copy
        success, msg = keyboard_shortcut('ctrl', 'v')  # Paste
        success, msg = keyboard_shortcut('alt', 'f4')  # Close window
    """
    try:
        shortcut_str = '+'.join(keys)
        print(f"[ACTION] Executing keyboard shortcut: {shortcut_str}")
        pyautogui.hotkey(*keys)
        
        success_msg = f"Successfully executed shortcut: {shortcut_str}"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to execute shortcut '{'+'.join(keys)}': {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# MOUSE ACTIONS
# ============================================================================

def click_at_position(x: int, y: int, clicks: int = 1, button: str = 'left') -> Tuple[bool, str]:
    """
    Click at specific screen coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        clicks: Number of clicks (1 for single, 2 for double)
        button: Mouse button ('left', 'right', 'middle')
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = click_at_position(100, 200)  # Single left click
        success, msg = click_at_position(100, 200, clicks=2)  # Double click
        success, msg = click_at_position(100, 200, button='right')  # Right click
    """
    try:
        print(f"[ACTION] Clicking at position ({x}, {y}) - {clicks} {button} click(s)")
        pyautogui.click(x, y, clicks=clicks, button=button)
        
        success_msg = f"Successfully clicked at ({x}, {y})"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to click at ({x}, {y}): {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

def move_mouse(x: int, y: int, duration: float = 0.5) -> Tuple[bool, str]:
    """
    Move mouse to specific coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        duration: Time to move in seconds
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = move_mouse(500, 300, duration=0.5)
    """
    try:
        print(f"[ACTION] Moving mouse to ({x}, {y}) over {duration}s")
        pyautogui.moveTo(x, y, duration=duration)
        
        success_msg = f"Successfully moved mouse to ({x}, {y})"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to move mouse: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

def right_click_at_position(x: int, y: int) -> Tuple[bool, str]:
    """
    Right-click at specific screen coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = right_click_at_position(400, 300)
    """
    return click_at_position(x, y, clicks=1, button='right')

def double_click_at_position(x: int, y: int) -> Tuple[bool, str]:
    """
    Double-click at specific screen coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = double_click_at_position(400, 300)
    """
    return click_at_position(x, y, clicks=2, button='left')

# ============================================================================
# WAIT ACTIONS
# ============================================================================

def wait_duration(seconds: float) -> Tuple[bool, str]:
    """
    Wait for a specific duration.
    
    Args:
        seconds: Number of seconds to wait
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = wait_duration(2.5)  # Wait 2.5 seconds
    """
    try:
        print(f"[ACTION] Waiting for {seconds} second(s)")
        time.sleep(seconds)
        
        success_msg = f"Successfully waited {seconds}s"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to wait: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# FIELD ACTIONS
# ============================================================================

def clear_field(num_backspaces: int = 50) -> Tuple[bool, str]:
    """
    Clear an input field by selecting all and deleting.
    
    Args:
        num_backspaces: Number of backspace presses (not used, kept for compatibility)
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = clear_field()
    """
    try:
        print(f"[ACTION] Clearing field (Ctrl+A + Delete)")
        
        # Select all
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        
        # Delete
        pyautogui.press('delete')
        
        success_msg = "Successfully cleared field"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to clear field: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

def select_all() -> Tuple[bool, str]:
    """
    Select all content (Ctrl+A).
    
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = select_all()
    """
    return keyboard_shortcut('ctrl', 'a')

# ============================================================================
# DROPDOWN/SELECTION ACTIONS
# ============================================================================

def select_dropdown_option(option_text: str, 
                          search_first: bool = True,
                          wait_after_type: float = 0.5) -> Tuple[bool, str]:
    """
    Select an option from a dropdown by typing to search.
    
    Args:
        option_text: Text of the option to select
        search_first: Whether to type text to search
        wait_after_type: Wait time after typing
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = select_dropdown_option("Acme Corp")
    """
    try:
        print(f"[ACTION] Selecting dropdown option: '{option_text}'")
        
        if search_first:
            # Type to search in dropdown
            pyautogui.write(option_text, interval=0.05)
            time.sleep(wait_after_type)
        
        # Press enter to select
        pyautogui.press('enter')
        
        success_msg = f"Successfully selected option: '{option_text}'"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to select dropdown option: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# SCROLL ACTIONS
# ============================================================================

def scroll_down(clicks: int = 3) -> Tuple[bool, str]:
    """
    Scroll down by a number of clicks.
    
    Args:
        clicks: Number of scroll clicks (negative for up)
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = scroll_down(5)  # Scroll down 5 clicks
    """
    try:
        print(f"[ACTION] Scrolling down {clicks} click(s)")
        pyautogui.scroll(-clicks)  # Negative for down
        
        success_msg = f"Successfully scrolled down {clicks} click(s)"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to scroll: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

def scroll_up(clicks: int = 3) -> Tuple[bool, str]:
    """
    Scroll up by a number of clicks.
    
    Args:
        clicks: Number of scroll clicks
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = scroll_up(5)  # Scroll up 5 clicks
    """
    try:
        print(f"[ACTION] Scrolling up {clicks} click(s)")
        pyautogui.scroll(clicks)  # Positive for up
        
        success_msg = f"Successfully scrolled up {clicks} click(s)"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        error_msg = f"Failed to scroll: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

# ============================================================================
# COMBINED/COMPLEX ACTIONS
# ============================================================================

def type_and_enter(text: str, interval: float = 0.05) -> Tuple[bool, str]:
    """
    Type text and press Enter.
    
    Args:
        text: Text to type
        interval: Delay between keystrokes
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = type_and_enter("Search query")
    """
    # Type text
    success, msg = type_text(text, interval)
    if not success:
        return False, msg
    
    # Press enter
    time.sleep(0.2)
    return press_key('enter')

def clear_and_type(text: str, interval: float = 0.05) -> Tuple[bool, str]:
    """
    Clear field and type new text.
    
    Args:
        text: Text to type
        interval: Delay between keystrokes
        
    Returns:
        Tuple of (success: bool, message)
        
    Example:
        success, msg = clear_and_type("New text")
    """
    # Clear field
    success, msg = clear_field()
    if not success:
        return False, msg
    
    # Wait a moment
    time.sleep(0.2)
    
    # Type new text
    return type_text(text, interval)
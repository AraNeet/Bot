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
import keyboard
from typing import Tuple

# Configure pyautogui safety settings (for mouse actions only)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5 


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
        # Step 1: Handle empty text case
        if not text:
            return True, "No text to type (empty string)"
        
        print(f"[ACTION] Typing text: '{text}' (interval: {interval}s)")
        
        # Step 2: Type each character using keyboard library
        for char in text:
            keyboard.write(char)
            if interval > 0:
                time.sleep(interval)
        
        # Step 3: Return success
        success_msg = f"Successfully typed: '{text}'"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        # Step 4: Handle errors
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
        
        # Step 1: Press key the specified number of times
        for _ in range(presses):
            keyboard.press_and_release(key)
            # Step 2: Add small delay between multiple presses
            if presses > 1:
                time.sleep(0.1)
        
        # Step 3: Return success
        success_msg = f"Successfully pressed '{key}' {presses} time(s)"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        # Step 4: Handle errors
        error_msg = f"Failed to press key '{key}': {e}"
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
        # Step 1: Log click action
        print(f"[ACTION] Clicking at position ({x}, {y}) - {clicks} {button} click(s)")
        
        # Step 2: Execute click using pyautogui
        pyautogui.click(x, y, clicks=clicks, button=button)
        
        # Step 3: Return success
        success_msg = f"Successfully clicked at ({x}, {y})"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        # Step 4: Handle errors
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
        # Step 1: Log move action
        print(f"[ACTION] Moving mouse to ({x}, {y}) over {duration}s")
        
        # Step 2: Execute move using pyautogui
        pyautogui.moveTo(x, y, duration=duration)
        
        # Step 3: Return success
        success_msg = f"Successfully moved mouse to ({x}, {y})"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        # Step 4: Handle errors
        error_msg = f"Failed to move mouse: {e}"
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
        
        # Step 1: Select all text using Ctrl+A
        keyboard.send('ctrl+a')
        time.sleep(0.1)
        
        # Step 2: Delete selected text using Delete key
        keyboard.press_and_release('delete')
        
        # Step 3: Return success
        success_msg = "Successfully cleared field"
        print(f"[ACTION SUCCESS] {success_msg}")
        return True, success_msg
        
    except Exception as e:
        # Step 4: Handle errors
        error_msg = f"Failed to clear field: {e}"
        print(f"[ACTION ERROR] {error_msg}")
        return False, error_msg

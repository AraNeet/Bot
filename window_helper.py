"""
Window management helper functions for enhanced window operations.
"""

import pygetwindow
import pyautogui
import time
import psutil
from typing import Optional, List, Tuple


def find_window_by_title(title: str, exact_match: bool = False) -> Optional[pygetwindow.Window]:
    """
    Find a window by its title.
    
    Args:
        title: Window title to search for
        exact_match: If True, require exact title match
    
    Returns:
        First matching window object, or None if not found
    """
    try:
        if exact_match:
            windows = [w for w in pygetwindow.getAllWindows() if w.title == title]
        else:
            windows = pygetwindow.getWindowsWithTitle(title)
        
        if windows:
            return windows[0]
        return None
    except Exception as e:
        print(f"Error finding window: {e}")
        return None


def is_window_maximized(window: pygetwindow.Window, threshold: float = 0.9) -> bool:
    """
    Check if a window is maximized.
    
    Args:
        window: Window object to check
        threshold: Percentage of screen that window must cover
    
    Returns:
        True if window is maximized, False otherwise
    """
    try:
        screen_width, screen_height = pyautogui.size()
        
        width_ratio = window.width / screen_width
        height_ratio = window.height / screen_height
        
        return width_ratio >= threshold and height_ratio >= threshold
    except Exception as e:
        print(f"Error checking if window is maximized: {e}")
        return False


def force_window_focus(window: pygetwindow.Window, max_attempts: int = 3) -> bool:
    """
    Force a window to gain focus using multiple methods.
    
    Args:
        window: Window object to focus
        max_attempts: Maximum number of attempts
    
    Returns:
        True if window gained focus, False otherwise
    """
    for attempt in range(max_attempts):
        try:
            window.activate()
            time.sleep(0.3)
            
            if pygetwindow.getActiveWindow() == window:
                return True

        except Exception as e:
            print(f"Error forcing window focus (attempt {attempt + 1}): {e}")
    
    return False


def get_window_handle(app_name: str) -> Optional[pygetwindow.Window]:
    """
    Get a fresh window handle by searching for the application.
    
    Args:
        app_name: The window title or partial title of the application
    
    Returns:
        Window handle if found, None otherwise
    """
    try:
        window = find_window_by_title(app_name)
        if window:
            print("Window handle obtained")
            return window
        else:
            print("Could not find window")
            return None
    except Exception as e:
        print(f"Error getting window handle: {e}")
        return None


def bring_to_foreground(window: pygetwindow.Window) -> bool:
    """
    Ensure the application window is in the foreground and has focus.
    Uses multiple methods to guarantee the window is active.
    
    Args:
        window: Window object to bring to foreground
    
    Returns:
        True if successfully brought to foreground, False otherwise
    """
    if not window:
        print("No window reference provided for foreground operation")
        return False
    
    # Use force_window_focus for more robust focus handling
    return force_window_focus(window)


def is_foreground(window: pygetwindow.Window) -> bool:
    """
    Check if the application window is currently in the foreground.
    
    Args:
        window: Window object to check
    
    Returns:
        True if window is active/foreground, False otherwise
    """
    if not window:
        return False
        
    try:
        active_window = pygetwindow.getActiveWindow()
        if active_window and window:
            is_active = (active_window.title == window.title)
            if is_active:
                print("Window is in foreground")
            else:
                print(f"Window not in foreground. Active: {active_window.title}")
            return is_active
        return False
    except Exception as e:
        print(f"Error checking foreground status: {e}")
        return False


def is_application_open(process_name: str) -> bool:
    """
    Check if the application is already open using psutil.
    
    Args:
        process_name: Name of the process to check (e.g., 'notepad.exe')
    
    Returns:
        True if application is open, False otherwise
    """
    try:
        # Check if process is running
        process_found = False
        for process in psutil.process_iter(['pid', 'name']):
            try:
                # Check if process name matches (case-insensitive)
                if process.info['name'].lower() == process_name.lower():
                    process_found = True
                    print(f"Process '{process_name}' found with PID: {process.info['pid']}")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        if not process_found:
            print(f"Process '{process_name}' is not running")
            return False
    except Exception as e:
        print(f"Error checking if application is open: {e}")
        return False
        
    return process_found


def maximize_application(window: pygetwindow.Window) -> bool:
    """
    Maximize the application window.
    
    Args:
        window: Window object to maximize
    
    Returns:
        True if successfully maximized, False otherwise
    """
    if not window:
        print("No window reference provided")
        return False
    try:
        window.maximize()
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"Error maximizing window: {e}")
        return False

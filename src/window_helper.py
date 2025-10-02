"""
Window management helper functions for enhanced window operations.
"""

import pygetwindow
import pyautogui
import time
import psutil
import subprocess
from typing import Optional, List, Tuple

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

def open_application(app_path: str) -> bool:
    """
    Open the application.
    
    Args:
        app_path: Path to the application executable
    
    Returns:
        True if successfully opened, False otherwise
    """
    if not app_path:
        print("No application path provided")
        return False
    
    try:
        subprocess.Popen(app_path)
        print(f"Launched application: {app_path}")

        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"Error opening application: {e}")
        return False

def get_window_handle(title: str) -> Optional[pygetwindow.Window]:
    """
    Find a window by its title.
    
    Args:
        title: Window title to search for
        exact_match: If True, require exact title match
    
    Returns:
        First matching window object, or None if not found
    """
    try:
        windows = pygetwindow.getWindowsWithTitle(title)
        if windows:
            return windows[0]
        return None
    except Exception as e:
        print(f"Error finding window: {e}")
        return None

def window_focus(window: pygetwindow.Window, max_attempts: int = 3) -> bool:
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

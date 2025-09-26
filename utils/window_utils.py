"""
Window management utilities for enhanced window operations.
"""

import pygetwindow as gw
import pyautogui
import time
import logging
from typing import Optional, List, Tuple


class WindowHelper:
    """Helper class for advanced window management operations."""
    
    def __init__(self):
        """Initialize the WindowHelper."""
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def find_window_by_title(title: str, exact_match: bool = False) -> Optional[gw.Window]:
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
                windows = [w for w in gw.getAllWindows() if w.title == title]
            else:
                windows = gw.getWindowsWithTitle(title)
            
            if windows:
                return windows[0]
            return None
        except Exception as e:
            logging.error(f"Error finding window: {e}")
            return None
    
    @staticmethod
    def get_window_center(window: gw.Window) -> Tuple[int, int]:
        """
        Get the center coordinates of a window.
        
        Args:
            window: Window object
        
        Returns:
            Tuple of (x, y) center coordinates
        """
        center_x = window.left + (window.width // 2)
        center_y = window.top + (window.height // 2)
        return (center_x, center_y)
    
    @staticmethod
    def is_window_maximized(window: gw.Window, threshold: float = 0.9) -> bool:
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
            logging.error(f"Error checking if window is maximized: {e}")
            return False
    
    @staticmethod
    def force_window_focus(window: gw.Window, max_attempts: int = 3) -> bool:
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
                # Method 1: Activate
                window.activate()
                time.sleep(0.3)
                
                if gw.getActiveWindow() == window:
                    return True
                
                # Method 2: Minimize/Restore
                window.minimize()
                time.sleep(0.2)
                window.restore()
                time.sleep(0.3)
                
                if gw.getActiveWindow() == window:
                    return True
                
                # Method 3: Click
                center_x, center_y = WindowHelper.get_window_center(window)
                pyautogui.click(center_x, center_y)
                time.sleep(0.2)
                
                if gw.getActiveWindow() == window:
                    return True
                    
            except Exception as e:
                logging.error(f"Error forcing window focus (attempt {attempt + 1}): {e}")
        
        return False
    
    @staticmethod
    def list_all_windows() -> List[str]:
        """
        Get a list of all window titles.
        
        Returns:
            List of window titles
        """
        try:
            windows = gw.getAllWindows()
            return [w.title for w in windows if w.title]
        except Exception as e:
            logging.error(f"Error listing windows: {e}")
            return []
    
    @staticmethod
    def safe_maximize(window: gw.Window) -> bool:
        """
        Safely maximize a window with error handling.
        
        Args:
            window: Window object to maximize
        
        Returns:
            True if successful, False otherwise
        """
        try:
            window.maximize()
            time.sleep(0.5)
            return True
        except Exception as e:
            logging.error(f"Error maximizing window: {e}")
            
            # Try alternative method
            try:
                window.activate()
                time.sleep(0.2)
                pyautogui.hotkey('win', 'up')
                time.sleep(0.5)
                return True
            except Exception as e2:
                logging.error(f"Alternative maximize also failed: {e2}")
                return False
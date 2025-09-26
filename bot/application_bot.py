"""
Application Manager Bot - Core bot functionality for window management.
"""

import pyautogui
import pygetwindow as gw
import time
import cv2
import numpy as np
from typing import Optional, Tuple
import logging
import psutil
import os
import subprocess


class ApplicationManagerBot:
    """
    A dedicated bot that provides all necessary actions for application management.
    This bot focuses on individual operations without orchestration logic.
    """
    
    def __init__(self, app_name: str, icon_template_path: str = None, 
                 app_path: str = None, max_retries: int = 5, process_name: str = None):
        """
        Initialize the bot with your application details.
        
        Args:
            app_name: The window title or partial title of your application
            icon_template_path: Path to the icon/image template for visual verification
            app_path: Path to the application executable (if needed for opening)
            max_retries: Maximum number of attempts for each operation
            process_name: Name of the process to check (e.g., 'notepad.exe')
        """
        self.app_name = app_name
        self.app_path = app_path
        self.max_retries = max_retries
        self.window = None
        self.logger = logging.getLogger(__name__)
        
        # Extract process name from app_path if not provided
        if process_name:
            self.process_name = process_name
        elif app_path:
            # Get the executable name from the path
            self.process_name = os.path.basename(app_path)
        else:
            # Try to guess from app_name (add .exe if not present)
            self.process_name = app_name if app_name.endswith('.exe') else f"{app_name}.exe"
        
        # Load the icon template if provided
        self.icon_template = None
        if icon_template_path:
            try:
                self.icon_template = cv2.imread(icon_template_path)
                if self.icon_template is not None:
                    self.logger.info(f"Icon template loaded successfully: {icon_template_path}")
                else:
                    self.logger.error(f"Failed to load icon template: {icon_template_path}")
            except Exception as e:
                self.logger.error(f"Error loading icon template: {e}")
        
        self.logger.info(f"Bot initialized for application: {app_name} (process: {self.process_name})")
    
    def find_template_on_screen(self, template: np.ndarray, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Search for a template image on the screen.
        
        Args:
            template: The template image to search for
            confidence: Matching confidence threshold (0-1)
        
        Returns:
            Coordinates of the template if found, None otherwise
        """
        try:
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Template matching
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence:
                # Return center coordinates of the matched template
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y)
            
            return None
        except Exception as e:
            self.logger.error(f"Error in template matching: {e}")
            return None
    
    def is_application_open(self) -> bool:
        """
        Check if the application is already open using psutil.
        
        Returns:
            True if application is open, False otherwise
        """
        try:
            # Check if process is running
            process_found = False
            for process in psutil.process_iter(['pid', 'name']):
                try:
                    # Check if process name matches (case-insensitive)
                    if process.info['name'].lower() == self.process_name.lower():
                        process_found = True
                        self.logger.info(f"Process '{self.process_name}' found with PID: {process.info['pid']}")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if not process_found:
                self.logger.info(f"Process '{self.process_name}' is not running")
                return False
            
            # If process is running, also try to get the window handle
            try:
                windows = gw.getWindowsWithTitle(self.app_name)
                if windows:
                    self.window = windows[0]
                    self.logger.info(f"Application window '{self.app_name}' found and linked")
                else:
                    self.logger.warning(f"Process is running but window '{self.app_name}' not found yet")
                    # Process is running but window might not be ready yet
                    # Still return True since the process exists
            except Exception as e:
                self.logger.warning(f"Could not get window handle: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if application is open: {e}")
            return False
    
    def open_application(self) -> bool:
        """
        Open the application if not already open.
        
        Returns:
            True if successfully opened, False otherwise
        """
        if not self.app_path:
            self.logger.error("No application path provided")
            return False
        
        try:
            subprocess.Popen(self.app_path)
            self.logger.info(f"Launched application: {self.app_path}")
            
            # Wait for application to start
            time.sleep(3)
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening application: {e}")
            return False
    
    def maximize_application(self) -> bool:
        """
        Maximize the application window.
        
        Returns:
            True if successfully maximized, False otherwise
        """
        if not self.window:
            self.logger.error("No window reference available")
            return False
        
        try:
            self.window.maximize()
            self.logger.info("Application window maximized")
            time.sleep(0.5)  # Allow time for window animation
            return True
        except Exception as e:
            self.logger.error(f"Error maximizing window: {e}")
            return False
    
    def bring_to_foreground(self) -> bool:
        """
        Ensure the application window is in the foreground and has focus.
        Uses multiple methods to guarantee the window is active.
        
        Returns:
            True if successfully brought to foreground, False otherwise
        """
        if not self.window:
            self.logger.error("No window reference available for foreground operation")
            return False
        
        try:
            # Method 1: Use activate() to bring to foreground
            self.window.activate()
            time.sleep(0.3)
            
            if self.is_foreground():
                self.logger.info("Successfully brought application to foreground")
                return True
                
            # Method 2: Minimize and restore to force focus
            self.logger.info("Trying minimize/restore method")
            self.window.minimize()
            time.sleep(0.2)
            self.window.restore()
            time.sleep(0.3)
            
            if self.is_foreground():
                return True
            
            # Method 3: Click on the window to ensure focus
            self.logger.info("Trying click method to bring to foreground")
            window_center_x = self.window.left + (self.window.width // 2)
            window_center_y = self.window.top + (self.window.height // 2)
            pyautogui.click(window_center_x, window_center_y)
            time.sleep(0.2)
            
            return self.is_foreground()
            
        except Exception as e:
            self.logger.error(f"Error bringing window to foreground: {e}")
            return False
    
    def is_foreground(self) -> bool:
        """
        Check if the application window is currently in the foreground.
        
        Returns:
            True if window is active/foreground, False otherwise
        """
        try:
            active_window = gw.getActiveWindow()
            if active_window and self.window:
                is_active = (active_window.title == self.window.title)
                if is_active:
                    self.logger.debug("Window is in foreground")
                else:
                    self.logger.debug(f"Window not in foreground. Active: {active_window.title}")
                return is_active
            return False
        except Exception as e:
            self.logger.error(f"Error checking foreground status: {e}")
            return False
    
    def check_visual_open(self) -> bool:
        """
        Use icon/image template to visually check if application is open.
        
        Returns:
            True if visual element is found, False otherwise
        """
        if self.icon_template is None:
            self.logger.warning("No icon template configured for visual verification")
            return True  # Skip visual check if no template
        
        position = self.find_template_on_screen(self.icon_template)
        if position:
            self.logger.info(f"Found application icon at position {position}")
            return True
        else:
            self.logger.error("Application icon not found on screen")
            return False
    
    def check_maximized_visually(self) -> bool:
        """
        Check position of icon/template to verify maximized state.
        
        Returns:
            True if window appears maximized, False otherwise
        """
        if not self.window:
            return False
        
        try:
            # Get screen dimensions
            screen_width, screen_height = pyautogui.size()
            
            # Check window dimensions
            if (self.window.width >= screen_width * 0.95 and 
                self.window.height >= screen_height * 0.90):
                self.logger.info("Window dimensions indicate maximized state")
                
                # Additional visual check if template is available
                if self.icon_template is not None:
                    # Check if icon is visible (should be visible in maximized window)
                    return self.check_visual_open()
                
                return True
            else:
                self.logger.info(f"Window not maximized: {self.window.width}x{self.window.height} "
                           f"(Screen: {screen_width}x{screen_height})")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking maximized state: {e}")
            return False
    
    def refresh_window_handle(self) -> bool:
        """
        Refresh the window handle in case it was lost.
        
        Returns:
            True if window handle was successfully refreshed, False otherwise
        """
        try:
            windows = gw.getWindowsWithTitle(self.app_name)
            if windows:
                self.window = windows[0]
                self.logger.info("Window handle refreshed")
                return True
            self.logger.error("Could not refresh window handle - window not found")
            return False
        except Exception as e:
            self.logger.error(f"Error refreshing window handle: {e}")
            return False
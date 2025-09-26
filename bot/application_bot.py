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
from utils.image_utils import ImageMatcher
from utils.window_utils import WindowHelper


class ApplicationManagerBot:
    """
    A dedicated bot that provides all necessary actions for application management.
    This bot focuses on individual operations without orchestration logic.
    """
    
    def __init__(self, app_name: str, icon_template_path: str = None, 
                 app_path: str = None, max_retries: int = 3, process_name: str = None):
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
        self.logger = logging.getLogger(__name__)
        
        # Extract process name from app_path if not provided
        if process_name:
            self.process_name = process_name
        else:
            # Try to guess from app_name (add .exe if not present)
            self.process_name = app_name if app_name.endswith('.exe') else f"{app_name}.exe"

        # Initialize utility classes
        self.image_matcher = ImageMatcher()
        self.window_helper = WindowHelper()
        
        # Load icon template if provided
        self.icon_template = None
        if icon_template_path:
            self.icon_template = self.image_matcher.load_template(icon_template_path)

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
        except Exception as e:
            self.logger.error(f"Error checking if application is open: {e}")
            return False
            
        return process_found
    
    def open_application(self) -> bool:
        """
        Open the application.
        
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
    
    def get_window_handle(self) -> Optional[object]:
        """
        Get a fresh window handle by searching for the application.
        
        Returns:
            Window handle if found, None otherwise
        """
        try:
            window = self.window_helper.find_window_by_title(self.app_name)
            if window:
                self.logger.debug("Window handle obtained")
                return window
            else:
                self.logger.warning("Could not find window")
                return None
        except Exception as e:
            self.logger.error(f"Error getting window handle: {e}")
            return None
    
    def maximize_application(self, window) -> bool:
        """
        Maximize the application window.
        
        Args:
            window: Window object to maximize
        
        Returns:
            True if successfully maximized, False otherwise
        """
        if not window:
            self.logger.error("No window reference provided")
            return False
        
        # Use WindowHelper for safer maximization
        return self.window_helper.safe_maximize(window)
    
    def bring_to_foreground(self, window) -> bool:
        """
        Ensure the application window is in the foreground and has focus.
        Uses multiple methods to guarantee the window is active.
        
        Args:
            window: Window object to bring to foreground
        
        Returns:
            True if successfully brought to foreground, False otherwise
        """
        if not window:
            self.logger.error("No window reference provided for foreground operation")
            return False
        
        # Use WindowHelper for more robust focus handling
        return self.window_helper.force_window_focus(window)
    
    def is_foreground(self, window) -> bool:
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
            active_window = gw.getActiveWindow()
            if active_window and window:
                is_active = (active_window.title == window.title)
                if is_active:
                    self.logger.debug("Window is in foreground")
                else:
                    self.logger.debug(f"Window not in foreground. Active: {active_window.title}")
                return is_active
            return False
        except Exception as e:
            self.logger.error(f"Error checking foreground status: {e}")
            return False
    
    def find_template_on_screen(self, template) -> Optional[Tuple[int, int]]:
        """
        Find a template on the current screen.
        
        Args:
            template: Template image to search for
            
        Returns:
            Position tuple (x, y) if found, None otherwise
        """
        if template is None:
            return None
            
        try:
            screenshot = self.image_matcher.take_screenshot()
            return self.image_matcher.find_template(screenshot, template)
        except Exception as e:
            self.logger.error(f"Error finding template on screen: {e}")
            return None
    
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
    
    def check_maximized_visually(self, window) -> bool:
        """
        Check if window appears maximized using WindowHelper utility.
        
        Args:
            window: Window object to check
        
        Returns:
            True if window appears maximized, False otherwise
        """
        if not window:
            self.logger.warning("No window provided for maximized check")
            return False
        
        # Use WindowHelper for consistent maximization checking
        is_maximized = self.window_helper.is_window_maximized(window)
        
        if is_maximized:
            self.logger.info("Window dimensions indicate maximized state")
        else:
            self.logger.info(f"Window not maximized: {window.width}x{window.height}")
            
        return is_maximized
    

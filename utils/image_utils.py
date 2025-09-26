"""
Image processing utilities for template matching and visual verification.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
import pyautogui
import logging


class ImageMatcher:
    """Utility class for image matching operations."""
    
    def __init__(self):
        """Initialize the ImageMatcher."""
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def find_template(screenshot: np.ndarray, 
                     template: np.ndarray, 
                     confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Find a template in a screenshot.
        
        Args:
            screenshot: Screenshot image as numpy array
            template: Template image to search for
            confidence: Minimum confidence level (0-1)
        
        Returns:
            Center coordinates of found template, or None if not found
        """
        try:
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence:
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y)
            
            return None
        except Exception as e:
            logging.error(f"Error in template matching: {e}")
            return None
    
    @staticmethod
    def find_all_templates(screenshot: np.ndarray, 
                          template: np.ndarray, 
                          confidence: float = 0.8) -> List[Tuple[int, int]]:
        """
        Find all occurrences of a template in a screenshot.
        
        Args:
            screenshot: Screenshot image as numpy array
            template: Template image to search for
            confidence: Minimum confidence level (0-1)
        
        Returns:
            List of center coordinates for all found templates
        """
        locations = []
        
        try:
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            locations_array = np.where(result >= confidence)
            
            h, w = template.shape[:2]
            for pt in zip(*locations_array[::-1]):
                center_x = pt[0] + w // 2
                center_y = pt[1] + h // 2
                locations.append((center_x, center_y))
            
            return locations
        except Exception as e:
            logging.error(f"Error finding all templates: {e}")
            return []
    
    @staticmethod
    def take_screenshot() -> np.ndarray:
        """
        Take a screenshot and convert it to OpenCV format.
        
        Returns:
            Screenshot as numpy array in BGR format
        """
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return screenshot
    
    @staticmethod
    def load_template(path: str) -> Optional[np.ndarray]:
        """
        Load a template image from file.
        
        Args:
            path: Path to the template image file
        
        Returns:
            Template image as numpy array, or None if loading failed
        """
        try:
            template = cv2.imread(path)
            if template is not None:
                logging.info(f"Template loaded successfully: {path}")
            else:
                logging.error(f"Failed to load template: {path}")
            return template
        except Exception as e:
            logging.error(f"Error loading template {path}: {e}")
            return None
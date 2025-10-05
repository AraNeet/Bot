"""
Image processing helper functions for template matching and visual verification.
Manages all template-related operations including loading and validation.
"""

import cv2
import numpy as np
import os
import json
from typing import Optional, Tuple, List, Dict
import pyautogui
from pathlib import Path

def take_screenshot() -> np.ndarray:
    """
    Take a screenshot and convert it to OpenCV format.
    
    Returns:
        Screenshot as numpy array in BGR format
    """
    screenshot = pyautogui.screenshot()
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return screenshot

def find_template_in_region(screenshot: np.ndarray, 
                           template: np.ndarray,
                           region: Tuple[int, int, int, int],
                           confidence: float = 0.8) -> Optional[Tuple[int, int]]:
    """
    Find a template in a specific region of the screenshot.
    
    Args:
        screenshot: Screenshot image as numpy array
        template: Template image to search for
        region: Region as (x, y, width, height) tuple
        confidence: Minimum confidence level (0-1)
    
    Returns:
        Center coordinates of found template in global coordinates, or None if not found
    """
    try:
        x, y, width, height = region

        # Extract the region from screenshot
        region_img = screenshot[y:y+height, x:x+width]

        # Perform template matching in the region
        result = cv2.matchTemplate(region_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            h, w = template.shape[:2]
            # Convert local coordinates to global coordinates
            center_x = x + max_loc[0] + w // 2
            center_y = y + max_loc[1] + h // 2
            return (center_x, center_y)

        return None

    except Exception as e:
        print(f"Error in region template matching: {e}")
        return None

def get_make_regions(screen_width: int, screen_height: int, 
                      region_size: int = 200) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Get predefined corner regions for template matching.
    
    Args:
        screen_width: Width of the screen
        screen_height: Height of the screen
        region_size: Size of each corner region in pixels
        
    Returns:
        Dictionary with corner region coordinates
    """
    return {
        'top_left': (0, 0, region_size, region_size),
        'top_right': (screen_width - region_size, 0, region_size, region_size),
        'bottom_right': (screen_width - region_size, screen_height - region_size, region_size, region_size)
    }

def check_maximized_by_corners(corner_templates: Dict[str, np.ndarray], 
                              confidence: float = 0.8,
                              region_size: int = 200) -> bool:
    """
    Check if application is maximized by finding all three corner templates.
    
    Args:
        corner_templates: Dictionary with 'top_left', 'top_right', 'bottom_right' templates
        confidence: Minimum confidence level for template matching (0-1)
        region_size: Size of each corner region in pixels
        
    Returns:
        True if all three corner templates are found, False otherwise
    """
    try:
        # Take screenshot
        screenshot = take_screenshot()
        screen_height, screen_width = screenshot.shape[:2]

        # Get corner regions
        corner_regions = get_make_regions(screen_width, screen_height, region_size)

        # Track which corners are found
        corners_found = {}

        # Check each corner template
        for corner_name in ['top_left', 'top_right', 'bottom_right']:
            template = corner_templates.get(corner_name)

            if template is None:
                print(f"No template provided for {corner_name} corner")
                return False

            region = corner_regions[corner_name]
            position = find_template_in_region(screenshot, template, region, confidence)

            if position:
                print(f"Found {corner_name} template at position {position}")
                corners_found[corner_name] = True

            else:
                print(f"{corner_name} template not found in region {region}")
                corners_found[corner_name] = False

        # Application is maximized if all three corners are found
        all_corners_found = all(corners_found.values())

        if all_corners_found:
            print("All corner templates found - application appears maximized")

        else:
            missing_corners = [name for name, found in corners_found.items() if not found]
            print(f"Application not maximized - missing corners: {missing_corners}")

        return all_corners_found

    except Exception as e:
        print(f"Error in corner-based maximization check: {e}")
        return False

def load_template(template_path: str, corner_name: str) -> Optional[np.ndarray]:
    """
    load a template image with error handling and detailed path resolution.

    Args:
        template_path: Path to the template image
        corner_name: Name of the corner for logging

    Returns:
        Template image as numpy array, or None if loading failed
    """
    if not template_path:
        print(f"No {corner_name} template path provided")
        return None

    template_file = Path(template_path)

    print(f"Attempting to load {corner_name} template:")
    print(f"  Raw path: {template_path}")

    if not template_file.exists():
        print(f"Template file does not exist: {template_file.resolve()}")
        return None

    template = cv2.imread(template_path)
    if template is not None:
        print(f"[SUCCESS] Successfully loaded {corner_name} template")
        return template

    else: 
        print(f"Error loading template {template_path}")
        return None

def load_template_config(config_file_path: str = "template.json") -> Optional[Dict[str, str]]:
    """
    Load template paths from configuration file.

    Args:
        config_file_path: Path to JSON config file

    Returns:
        Dictionary of template paths, or None if failed
    """
    if not os.path.exists(config_file_path):
        print(f"Template config file not found: {config_file_path}")
        return None

    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            templates = config.get('templates', {})
            print(f"Template paths loaded from {config_file_path}")
            return templates

    except json.JSONDecodeError as e:
        print(f"Error parsing template config: {e}")
        return None

    except Exception as e:
        print(f"Error loading template config: {e}")
        return None

def validate_template_paths(template_paths: Dict[str, str]) -> bool:
    """
    Validate that all template files exist.
    
    Args:
        template_paths: Dictionary of template name to file path
    
    Returns:
        True if all template files exist, False otherwise
    """
    for template_name, template_path in template_paths.items():
        if not os.path.exists(template_path):
            print(f"Template file not found: {template_path} (for {template_name})")
            return False
    return True

def load_templates(config_file_path: str = "template.json") -> Optional[Dict[str, np.ndarray]]:
    """
    Load all corner templates from configuration.
    
    Args:
        config_file_path: Path to JSON config file
    
    Returns:
        Dictionary of loaded corner templates, or None if failed
    """
    # Load template paths
    template_paths = load_template_config(config_file_path)
    if not template_paths:
        return None

    # Validate paths exist
    if not validate_template_paths(template_paths):
        return None

    # Load templates
    corner_templates = {}
    for corner_name, template_path in template_paths.items():
        template = load_template(template_path, corner_name)
        if template is None:
            print(f"Failed to load template: {corner_name}")
            return None
        corner_templates[corner_name] = template

    print("All corner templates loaded successfully")
    return corner_templates
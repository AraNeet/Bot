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
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

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

def load_template(path: str, name: str):
    if not path:
        print(f"Missing path for {name}")
        return None

    file = Path(path)
    if not file.exists():
        print(f"File not found: {file.resolve()}")
        return None

    img = cv2.imread(path)
    if img is None:
        print(f"Failed to load image: {path}")
        return None

    print(f"[OK] Loaded {name}")
    return img

def load_template_config(config_path: str):
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_template_paths(template_paths: Dict[str, str]):
    for name, path in template_paths.items():
        if not os.path.exists(path):
            print(f"Missing file: {name} -> {path}")
            return False
    return True

def load_template_group(template_paths: Dict[str, str], group_name: str):
    if not validate_template_paths(template_paths):
        return None

    loaded = {}
    for name, path in template_paths.items():
        img = load_template(path, f"{group_name}.{name}")
        if img is None:
            return None
        loaded[name] = img

    print(f"[OK] Group loaded: {group_name}")
    return loaded


def load_templates(config_path: str):
    config = load_template_config(config_path)
    if not config:
        return None

    all_templates = {}

    for group_name, template_paths in config.items():
        print(f"Loading group: {group_name}")

        group = load_template_group(template_paths, group_name)
        if group is None:
            print(f"Failed group: {group_name}")
            return None

        all_templates[group_name] = group

    print("[SUCCESS] All templates loaded")
    return all_templates
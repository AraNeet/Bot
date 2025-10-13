#!/usr/bin/env python3
"""
Computer Vision Helper Module

This module provides basic OpenCV functionality for image processing,
screenshot capture, and visual verification operations.

Core Functions:
- take_screenshot: Capture current screen state
- save_screenshot: Save screenshot to file
- load_image: Load image from file
- convert_color: Convert between color spaces

This module focuses on low-level CV operations that other modules can build upon.
"""

import cv2
import numpy as np
import pyautogui
from typing import Optional, Tuple, Dict
from datetime import datetime
from pathlib import Path


def take_screenshot() -> Optional[np.ndarray]:
    """
    Capture a screenshot of the entire screen.
    
    Returns:
        Screenshot as numpy array in BGR format (OpenCV standard), or None if failed
        
    Example:
        screenshot = take_screenshot()
        if screenshot is not None:
            print(f"Screenshot captured: {screenshot.shape}")
    """
    try:
        # Capture screenshot using pyautogui
        screenshot = pyautogui.screenshot()
        
        # Convert from PIL Image to numpy array
        screenshot_np = np.array(screenshot)
        
        # Convert from RGB (PIL format) to BGR (OpenCV format)
        screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
        
        print(f"[CV] Screenshot captured: {screenshot_bgr.shape[1]}x{screenshot_bgr.shape[0]}")
        return screenshot_bgr
        
    except Exception as e:
        print(f"[CV ERROR] Failed to take screenshot: {e}")
        return None

def save_screenshot(screenshot: np.ndarray, 
                   filename: Optional[str] = None,
                   output_dir: str = "screenshots") -> Tuple[bool, str]:
    """
    Save a screenshot to file.
    
    Args:
        screenshot: Screenshot image as numpy array
        filename: Optional custom filename. If None, generates timestamp-based name
        output_dir: Directory to save screenshots in
        
    Returns:
        Tuple of (success: bool, filepath or error_message)
        
    Example:
        screenshot = take_screenshot()
        success, filepath = save_screenshot(screenshot)
        if success:
            print(f"Saved to: {filepath}")
    """
    try:
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Ensure filename has .png extension
        if not filename.endswith('.png'):
            filename += '.png'
        
        # Full file path
        filepath = output_path / filename
        
        # Save the image
        cv2.imwrite(str(filepath), screenshot)
        
        print(f"[CV] Screenshot saved: {filepath}")
        return True, str(filepath)
        
    except Exception as e:
        error_msg = f"Failed to save screenshot: {e}"
        print(f"[CV ERROR] {error_msg}")
        return False, error_msg

def load_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load an image from file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Image as numpy array in BGR format, or None if failed
        
    Example:
        image = load_image("template.png")
        if image is not None:
            print(f"Image loaded: {image.shape}")
    """
    try:
        # Check if file exists
        if not Path(image_path).exists():
            print(f"[CV ERROR] Image file not found: {image_path}")
            return None
        
        # Load image
        image = cv2.imread(image_path)
        
        if image is None:
            print(f"[CV ERROR] Failed to load image: {image_path}")
            return None
        
        print(f"[CV] Image loaded: {image.shape[1]}x{image.shape[0]} from {image_path}")
        return image
        
    except Exception as e:
        print(f"[CV ERROR] Exception loading image: {e}")
        return None

def get_image_dimensions(image: np.ndarray) -> Tuple[int, int]:
    """
    Get the dimensions of an image.
    
    Args:
        image: Image as numpy array
        
    Returns:
        Tuple of (width, height)
        
    Example:
        width, height = get_image_dimensions(screenshot)
        print(f"Image size: {width}x{height}")
    """
    height, width = image.shape[:2]
    return width, height

def crop_image(image: np.ndarray, 
              x: int, y: int, 
              width: int, height: int,
              preprocess_for_ocr: bool = False) -> Optional[np.ndarray]:
    """
    Crop a region from an image, with optional preprocessing for OCR.
    
    Args:
        image: Input image as numpy array
        x: X-coordinate of top-left corner
        y: Y-coordinate of top-left corner
        width: Width of crop region
        height: Height of crop region
        preprocess_for_ocr: If True, apply OCR preprocessing after cropping
        
    Returns:
        Cropped (and optionally preprocessed) image, or None if failed
        
    Example:
        # Crop with preprocessing
        cropped = crop_image(screenshot, 0, 0, 200, 200, preprocess_for_ocr=True)
    """
    try:
        # Validate coordinates
        img_height, img_width = image.shape[:2]
        
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            print(f"[CV ERROR] Invalid crop coordinates")
            return None
        
        if x + width > img_width or y + height > img_height:
            print(f"[CV ERROR] Crop region exceeds image bounds")
            return None
        
        # Crop using numpy slicing
        cropped = image[y:y+height, x:x+width]
        
        print(f"[CV] Image cropped: region ({x},{y},{width},{height})")
        
        if preprocess_for_ocr:
            cropped = preprocess_image_for_ocr(cropped)
            if cropped is None:
                return None
            print(f"[CV] Applied OCR preprocessing to cropped image")
        
        return cropped
        
    except Exception as e:
        print(f"[CV ERROR] Crop failed: {e}")
        return None

def preprocess_image_for_ocr(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Preprocess an image for OCR to remove artifacts like cursors and underlines.
    
    Args:
        image: Input image to preprocess
        
    Returns:
        Preprocessed image or None if failed
    """
    try:
        if image is None:
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to binarize the image
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Apply morphological operations to remove small artifacts (e.g., cursor)
        kernel = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Dilate to enhance text
        dilated = cv2.dilate(cleaned, kernel, iterations=1)
        
        return dilated
        
    except Exception as e:
        print(f"[CV ERROR] Failed to preprocess image for OCR: {e}")
        return None

def match_template_in_region(screenshot: np.ndarray,
                             template: np.ndarray,
                             region: Tuple[int, int, int, int],
                             confidence: float = 0.8) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
    """
    Find a template within a specific region of a screenshot.
    
    Uses template matching to locate a template image within a defined region.
    Returns whether the template was found and its confidence score.
    
    Args:
        screenshot: Screenshot image as numpy array
        template: Template image to search for
        region: Region as (x, y, width, height) tuple
        confidence: Minimum confidence threshold (0-1)
        
    Returns:
        Tuple of (found: bool, confidence_score: float, position: Optional[Tuple[int, int]])
        Position is (center_x, center_y) in global coordinates if found
        
    Example:
        screenshot = take_screenshot()
        template = load_image('assets/button.png')
        region = (0, 0, 200, 200)  # Top-left corner
        
        found, score, position = match_template_in_region(
            screenshot, template, region, confidence=0.8
        )
        
        if found:
            print(f"Template found at {position} with confidence {score:.2f}")
    """
    try:
        x, y, width, height = region
        
        # Validate region bounds
        screen_height, screen_width = screenshot.shape[:2]
        if x < 0 or y < 0 or x + width > screen_width or y + height > screen_height:
            print(f"[CV ERROR] Region out of bounds: ({x}, {y}, {width}, {height})")
            return False, 0.0, None
        
        # Crop region from screenshot
        region_img = crop_image(screenshot, x, y, width, height)
        if region_img is None:
            print(f"[CV ERROR] Failed to crop region for template matching")
            return False, 0.0, None
        
        # Perform template matching
        result = cv2.matchTemplate(region_img, template, cv2.TM_CCOEFF_NORMED)
        
        # Get best match
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Check if confidence threshold met
        if max_val >= confidence:
            # Calculate center position in region coordinates
            template_height, template_width = template.shape[:2]
            center_x = max_loc[0] + template_width // 2
            center_y = max_loc[1] + template_height // 2
            
            # Convert to global coordinates
            global_x = x + center_x
            global_y = y + center_y
            
            print(f"[CV] Template found in region with confidence {max_val:.2f}")
            print(f"[CV] Position: ({global_x}, {global_y})")
            return True, max_val, (global_x, global_y)
        else:
            print(f"[CV] Template not found in region (confidence {max_val:.2f} < {confidence})")
            return False, max_val, None
            
    except Exception as e:
        print(f"[CV ERROR] Template matching failed: {e}")
        return False, 0.0, None

def find_template_in_region(screenshot: np.ndarray,
                           template_path: str,
                           region: Tuple[int, int, int, int],
                           confidence: float = 0.8) -> Tuple[bool, float, Optional[Tuple[int, int]]]:
    """
    Find a template image within a specific region of a screenshot.
    
    Loads a template from file and searches for it within the specified region.
    Returns whether the template was found, confidence score, and position.
    
    Args:
        screenshot: Screenshot image as numpy array
        template_path: Path to the template image file
        region: Region as (x, y, width, height) tuple
        confidence: Minimum confidence threshold (0-1)
        
    Returns:
        Tuple of (found: bool, confidence_score: float, position: Optional[Tuple[int, int]])
        Position is (center_x, center_y) in global coordinates if found
        
    Example:
        screenshot = take_screenshot()
        region = (94, 46, 74, 72)  # (x, y, width, height)
        
        found, score, position = find_template_in_region(
            screenshot, 'assets/multi_network_Icon.png', region, confidence=0.8
        )
        
        if found:
            print(f"Template found at {position} with confidence {score:.2f}")
    """
    try:
        # Load template image
        template = load_image(template_path)
        if template is None:
            print(f"[CV ERROR] Failed to load template: {template_path}")
            return False, 0.0, None
        
        # Use existing match_template_in_region function
        return match_template_in_region(screenshot, template, region, confidence)
        
    except Exception as e:
        print(f"[CV ERROR] Template finding failed: {e}")
        return False, 0.0, None

def find_template_full_screen(screenshot: np.ndarray,
                             template_path: str,
                             confidence: float = 0.8) -> Tuple[bool, float, Optional[Tuple[int, int]], Optional[Tuple[int, int, int, int]]]:
    """
    Find a template image anywhere on the full screenshot.
    
    Searches the entire screenshot for the template and returns the position and region.
    
    Args:
        screenshot: Screenshot image as numpy array
        template_path: Path to the template image file
        confidence: Minimum confidence threshold (0-1)
        
    Returns:
        Tuple of (found: bool, confidence_score: float, position: Optional[Tuple[int, int]], region: Optional[Tuple[int, int, int, int]])
        - found: Whether template was found
        - confidence_score: Confidence score of the match
        - position: Center coordinates (x, y) if found
        - region: Bounding box (x, y, width, height) if found
        
    Example:
        screenshot = take_screenshot()
        
        found, score, position, region = find_template_full_screen(
            screenshot, 'assets/multi_network_Icon.png', confidence=0.9
        )
        
        if found:
            print(f"Template found at {position} with confidence {score:.2f}")
            print(f"Region: {region}")
    """
    try:
        # Load template image
        template = load_image(template_path)
        if template is None:
            print(f"[CV ERROR] Failed to load template: {template_path}")
            return False, 0.0, None, None
        
        # Get template dimensions
        template_height, template_width = template.shape[:2]
        
        # Perform template matching on full screenshot
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # Check if confidence threshold met
        if max_val >= confidence:
            # Calculate center position
            center_x = max_loc[0] + template_width // 2
            center_y = max_loc[1] + template_height // 2
            
            # Calculate bounding box region
            region = (max_loc[0], max_loc[1], template_width, template_height)
            
            print(f"[CV] Template found on full screen with confidence {max_val:.2f}")
            print(f"[CV] Position: ({center_x}, {center_y}), Region: {region}")
            return True, max_val, (center_x, center_y), region
        else:
            print(f"[CV] Template not found on full screen (confidence {max_val:.2f} < {confidence})")
            return False, max_val, None, None
            
    except Exception as e:
        print(f"[CV ERROR] Full screen template finding failed: {e}")
        return False, 0.0, None, None

def check_corners_maximized(screenshot: np.ndarray,
                           corner_templates: Dict[str, np.ndarray],
                           region_size: int = 200,
                           confidence: float = 0.8) -> Tuple[bool, Dict[str, bool], Dict[str, float]]:
    """
    Check if application is maximized by verifying corner templates.
    
    Checks three corners (top_left, top_right, bottom_right) to determine
    if the application window is maximized.
    
    Args:
        screenshot: Screenshot image as numpy array
        corner_templates: Dictionary with 'top_left', 'top_right', 'bottom_right' templates
        region_size: Size of each corner region in pixels
        confidence: Template matching confidence threshold (0-1)
        
    Returns:
        Tuple of (all_found: bool, corners_found: Dict, confidence_scores: Dict)
        
    Example:
        screenshot = take_screenshot()
        corner_templates = {
            'top_left': load_image('assets/Icon.png'),
            'top_right': load_image('assets/close_x.png'),
            'bottom_right': load_image('assets/bottom_right.png')
        }
        
        all_found, found_dict, scores = check_corners_maximized(
            screenshot, corner_templates
        )
        
        if all_found:
            print("Application is maximized!")
        else:
            missing = [k for k, v in found_dict.items() if not v]
            print(f"Missing corners: {missing}")
    """
    try:
        screen_height, screen_width = screenshot.shape[:2]
        
        # Define corner regions
        corner_regions = {
            'top_left': (0, 0, region_size, region_size),
            'top_right': (screen_width - region_size, 0, region_size, region_size),
            'bottom_right': (screen_width - region_size, screen_height - region_size, region_size, region_size)
        }
        
        corners_found = {}
        confidence_scores = {}
        
        # Check each required corner
        for corner_name in ['top_left', 'top_right', 'bottom_right']:
            template = corner_templates.get(corner_name)
            
            if template is None:
                print(f"[CV ERROR] Missing template for '{corner_name}'")
                corners_found[corner_name] = False
                confidence_scores[corner_name] = 0.0
                continue
            
            region = corner_regions[corner_name]
            
            # Match template in this corner region
            found, score, position = match_template_in_region(
                screenshot, template, region, confidence
            )
            
            corners_found[corner_name] = found
            confidence_scores[corner_name] = score
            
            if found:
                print(f"[CV] ✓ Found {corner_name} corner (confidence: {score:.2f})")
            else:
                print(f"[CV] ✗ {corner_name} corner not found (confidence: {score:.2f})")
        
        # Check if all corners were found
        all_found = all(corners_found.values())
        
        if all_found:
            print(f"[CV SUCCESS] All corner templates found - application appears maximized")
        else:
            missing = [name for name, found in corners_found.items() if not found]
            print(f"[CV] Missing corners: {missing}")
        
        return all_found, corners_found, confidence_scores
        
    except Exception as e:
        print(f"[CV ERROR] Corner checking failed: {e}")
        return False, {}, {}
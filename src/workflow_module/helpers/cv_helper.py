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
from typing import Optional, Tuple
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


def convert_color(image: np.ndarray, 
                 conversion_code: int) -> Optional[np.ndarray]:
    """
    Convert image between color spaces.
    
    Args:
        image: Input image as numpy array
        conversion_code: OpenCV color conversion code (e.g., cv2.COLOR_BGR2GRAY)
        
    Returns:
        Converted image, or None if failed
        
    Common conversion codes:
        - cv2.COLOR_BGR2GRAY: Convert to grayscale
        - cv2.COLOR_BGR2RGB: Convert to RGB
        - cv2.COLOR_BGR2HSV: Convert to HSV
        
    Example:
        gray_image = convert_color(screenshot, cv2.COLOR_BGR2GRAY)
    """
    try:
        converted = cv2.cvtColor(image, conversion_code)
        print(f"[CV] Color conversion applied: {image.shape} -> {converted.shape}")
        return converted
        
    except Exception as e:
        print(f"[CV ERROR] Color conversion failed: {e}")
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
              width: int, height: int) -> Optional[np.ndarray]:
    """
    Crop a region from an image.
    
    Args:
        image: Input image as numpy array
        x: X-coordinate of top-left corner
        y: Y-coordinate of top-left corner
        width: Width of crop region
        height: Height of crop region
        
    Returns:
        Cropped image, or None if failed
        
    Example:
        # Crop top-left 200x200 region
        cropped = crop_image(screenshot, 0, 0, 200, 200)
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
        return cropped
        
    except Exception as e:
        print(f"[CV ERROR] Crop failed: {e}")
        return None


def resize_image(image: np.ndarray, 
                width: int, height: int) -> Optional[np.ndarray]:
    """
    Resize an image to specified dimensions.
    
    Args:
        image: Input image as numpy array
        width: Target width
        height: Target height
        
    Returns:
        Resized image, or None if failed
        
    Example:
        resized = resize_image(screenshot, 800, 600)
    """
    try:
        if width <= 0 or height <= 0:
            print(f"[CV ERROR] Invalid dimensions: {width}x{height}")
            return None
        
        resized = cv2.resize(image, (width, height))
        
        print(f"[CV] Image resized: {image.shape[:2]} -> {resized.shape[:2]}")
        return resized
        
    except Exception as e:
        print(f"[CV ERROR] Resize failed: {e}")
        return None
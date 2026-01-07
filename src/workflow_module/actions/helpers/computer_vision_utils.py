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
from typing import Optional, Tuple, Dict, List
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

def take_screenshot_and_crop(region: Tuple[int, int, int, int], preprocess_for_ocr: bool = False) -> Optional[np.ndarray]:
    """
    Take a screenshot and crop a region from it in one operation.
    
    Args:
        region: Tuple of (x, y, width, height)
        preprocess_for_ocr: If True, apply OCR preprocessing after cropping
        
    Returns:
        Cropped (and optionally preprocessed) image, or None if failed
        
    Example:
        # Take screenshot and crop with preprocessing
        cropped = take_screenshot_and_crop((0, 0, 200, 200), preprocess_for_ocr=True)
    """
    screenshot = take_screenshot()
    if screenshot is None:
        return None
    
    x, y, width, height = region
    return crop_image(screenshot, x, y, width, height, preprocess_for_ocr)

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
            screenshot, 'assets/01_multi_network_Icon.png', region, confidence=0.8
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

def find_blue_highlighted_row(screenshot: np.ndarray,
                             exclude_bottom_pixels: int = 100) -> Tuple[bool, Optional[Dict[str, int]]]:
    """
    Find a blue highlighted row in the screenshot using HSV color detection.
    
    This function detects expanded/selected rows that have a blue background color.
    It filters contours by size and position to find the most likely blue row.
    
    Args:
        screenshot: Screenshot image as numpy array (BGR format)
        exclude_bottom_pixels: Number of pixels from bottom to exclude (default: 100, for taskbar)
        
    Returns:
        Tuple of (found: bool, row_info: Optional[Dict])
        row_info contains {'x': int, 'y': int, 'width': int, 'height': int} if found
        
    Example:
        screenshot = take_screenshot()
        found, row_info = find_blue_highlighted_row(screenshot)
        if found:
            print(f"Blue row at ({row_info['x']}, {row_info['y']})")
    """
    try:
        screen_height, screen_width = screenshot.shape[:2]
        bottom_exclusion_y = max(0, screen_height - exclude_bottom_pixels)
        
        print(f"[CV] Detecting blue highlighted row...")
        print(f"[CV] Screen size: {screen_width}x{screen_height}")
        print(f"[CV] Excluding bottom {exclude_bottom_pixels}px (Y >= {bottom_exclusion_y})")
        
        # Convert to HSV and create blue mask
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Find contours in blue mask
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print(f"[CV] No blue contours found")
            return False, None
        
        print(f"[CV] Found {len(contours)} blue contour(s)")
        
        # Filter candidate contours by size and position
        candidate_contours = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Skip if in bottom exclusion zone
            if y >= bottom_exclusion_y:
                continue
            
            # Filter by height (typical row height range)
            if h < 18 or h > 40:
                continue
            
            # Filter by width (should be reasonably wide for a table row)
            if w < 300:
                continue
            
            candidate_contours.append((cnt, x, y, w, h))
        
        # Choose best candidate
        blue_x, blue_y, blue_w, blue_h = None, None, None, None
        
        if candidate_contours:
            # Sort by width and area (prioritize wider rows)
            candidate_contours.sort(key=lambda item: (item[3], cv2.contourArea(item[0])), reverse=True)
            chosen_cnt, blue_x, blue_y, blue_w, blue_h = candidate_contours[0]
            print(f"[CV] Selected candidate from {len(candidate_contours)} filtered contour(s)")
        else:
            # Fallback: use largest contour regardless of filters
            largest_contour = max(contours, key=cv2.contourArea)
            blue_x, blue_y, blue_w, blue_h = cv2.boundingRect(largest_contour)
            
            # If in exclusion zone, adjust Y position
            if blue_y >= bottom_exclusion_y:
                blue_y = max(0, bottom_exclusion_y - max(blue_h, 40))
            
            print(f"[CV] No candidates passed filters, using largest contour with adjusted position")
        
        row_info = {
            'x': blue_x,
            'y': blue_y,
            'width': blue_w,
            'height': blue_h
        }
        
        print(f"[CV] ✓ Found blue highlighted row at ({blue_x}, {blue_y}) with size {blue_w}x{blue_h}")
        return True, row_info
        
    except Exception as e:
        print(f"[CV ERROR] Error finding blue highlighted row: {e}")
        return False, None

def detect_loading_circle(screenshot: np.ndarray,
                         center_region_ratio: float = 0.4,
                         min_radius: int = 15,
                         max_radius: int = 100,
                         brightness_threshold: int = 180) -> Tuple[bool, Optional[Tuple[int, int, int]]]:
    """
    Detect a loading circle/spinner in the center region of the screen.
    
    Looks for circular shapes with bright/light colors (typical loading spinner appearance).
    The spinner is usually white/light gray on a darker background, or colored.
    
    Args:
        screenshot: Screenshot image as numpy array (BGR format)
        center_region_ratio: Ratio of screen to search (0.4 = 40% from center, default: 0.4)
        min_radius: Minimum circle radius in pixels (default: 15)
        max_radius: Maximum circle radius in pixels (default: 100)
        brightness_threshold: Minimum brightness value (0-255) for spinner color (default: 180)
        
    Returns:
        Tuple of (found: bool, circle_info: Optional[Tuple[x, y, radius]])
        circle_info contains (center_x, center_y, radius) if found
    """
    try:
        screen_height, screen_width = screenshot.shape[:2]
        
        # Define center region to search (middle portion of screen)
        region_width = int(screen_width * center_region_ratio)
        region_height = int(screen_height * center_region_ratio)
        region_x = (screen_width - region_width) // 2
        region_y = (screen_height - region_height) // 2
        
        print(f"[CV] Searching for loading circle in center region: ({region_x}, {region_y}, {region_width}, {region_height})")
        
        # Crop to center region
        center_region = crop_image(screenshot, region_x, region_y, region_width, region_height)
        if center_region is None:
            print(f"[CV ERROR] Failed to crop center region for loading circle detection")
            return False, None
        
        # Convert to grayscale
        gray = cv2.cvtColor(center_region, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Detect bright circular shapes using HoughCircles
        # This detects actual circles in the image
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=max_radius * 2,
            param1=50,  # Upper threshold for edge detection
            param2=30,  # Accumulator threshold for center detection
            minRadius=min_radius,
            maxRadius=max_radius
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            
            # Check each detected circle to see if it matches loading spinner characteristics
            for (x, y, r) in circles:
                # Convert to absolute screen coordinates
                abs_x = region_x + x
                abs_y = region_y + y
                
                # Check if the circle has bright colors (typical of loading spinners)
                # Extract region around circle
                circle_region = center_region[max(0, y-r):min(center_region.shape[0], y+r),
                                              max(0, x-r):min(center_region.shape[1], x+r)]
                
                if circle_region.size > 0:
                    # Calculate average brightness in the circle region
                    gray_region = cv2.cvtColor(circle_region, cv2.COLOR_BGR2GRAY)
                    avg_brightness = np.mean(gray_region)
                    
                    print(f"[CV] Found circle at ({abs_x}, {abs_y}), radius={r}, avg_brightness={avg_brightness:.1f}")
                    
                    # Loading spinners are typically bright (white/light colors)
                    if avg_brightness >= brightness_threshold:
                        print(f"[CV] ✓ Loading circle detected! Position: ({abs_x}, {abs_y}), radius: {r}")
                        return True, (abs_x, abs_y, r)
        
        # Method 2: Color-based detection - look for bright circular regions
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(center_region, cv2.COLOR_BGR2HSV)
        
        # Create mask for bright/white colors (high value in HSV)
        # Bright colors have high V (value) component
        bright_mask = cv2.inRange(hsv, (0, 0, brightness_threshold), (180, 30, 255))
        
        # Find contours of bright regions
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Check if contour is roughly circular
            area = cv2.contourArea(contour)
            
            # Filter by area (should be roughly pi * r^2 for a circle)
            expected_area_min = np.pi * (min_radius ** 2)
            expected_area_max = np.pi * (max_radius ** 2)
            
            if expected_area_min <= area <= expected_area_max:
                # Fit a circle to the contour
                (x, y), r = cv2.minEnclosingCircle(contour)
                x, y, r = int(x), int(y), int(r)
                
                # Check circularity (how close the contour is to a perfect circle)
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    
                    # High circularity (close to 1.0) indicates a circle
                    if circularity > 0.6 and min_radius <= r <= max_radius:
                        abs_x = region_x + x
                        abs_y = region_y + y
                        
                        print(f"[CV] ✓ Loading circle detected via color! Position: ({abs_x}, {abs_y}), radius: {r}, circularity: {circularity:.2f}")
                        return True, (abs_x, abs_y, r)
        
        print(f"[CV] No loading circle detected in center region")
        return False, None
        
    except Exception as e:
        print(f"[CV ERROR] Error detecting loading circle: {e}")
        return False, None

def detect_underline(image: np.ndarray, 
                    min_width_ratio: float = 0.3,
                    bottom_half_only: bool = True) -> bool:
    """
    Detect if there is a horizontal underline in the image.
    
    Args:
        image: Input image (cropped field)
        min_width_ratio: Minimum width of line relative to image width (default 0.3)
        bottom_half_only: If True, only search in the bottom half of the image
        
    Returns:
        True if underline detected, False otherwise
    """
    try:
        if image is None:
            return False
            
        height, width = image.shape[:2]
        
        # Region of interest
        if bottom_half_only:
            roi = image[height//2:, :]
        else:
            roi = image
            
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding to be robust against different text colors
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                      cv2.THRESH_BINARY_INV, 15, 10)
                                      
        # Morphological operations to extract horizontal lines
        # Kernel width should be significant enough to ignore text but keep lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(width * 0.1), 1))
        detected_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(detected_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"[CV] Underline detection: found {len(contours)} horizontal contours")
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Check if width is sufficient
            if w > width * min_width_ratio:
                # Check aspect ratio (width significantly larger than height)
                aspect_ratio = w / h if h > 0 else 999
                if aspect_ratio > 5: 
                    print(f"[CV] ✓ Underline detected! Width: {w}px, Aspect Ratio: {aspect_ratio:.1f}")
                    return True
                    
        return False
        
    except Exception as e:
        print(f"[CV ERROR] Failed to detect underline: {e}")
        return False

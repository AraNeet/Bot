#!/usr/bin/env python3
"""
Text Scanner Helper Module

This module provides basic OCR (Optical Character Recognition) functionality
for extracting text from images and screenshots.

Core Functions:
- extract_text: Extract all text from an image
- find_text: Search for specific text in an image
- extract_text_from_region: Extract text from a specific region

Requirements:
    - pytesseract: Python wrapper for Tesseract OCR
    - Tesseract OCR engine installed on system

This module focuses on text extraction operations that the verifier can use.
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict, Any

# Try to import pytesseract
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[OCR WARNING] pytesseract not installed. OCR functionality disabled.")
    print("[OCR WARNING] Install with: pip install pytesseract")


def check_tesseract_available() -> bool:
    """
    Check if Tesseract OCR is available and properly configured.
    
    Returns:
        True if Tesseract is available, False otherwise
    """
    if not TESSERACT_AVAILABLE:
        print("[OCR ERROR] pytesseract module not installed")
        return False
    
    try:
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"[OCR] Tesseract version: {version}")
        return True
    except Exception as e:
        print(f"[OCR ERROR] Tesseract not properly configured: {e}")
        print("[OCR INFO] Please install Tesseract OCR engine:")
        print("[OCR INFO] - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("[OCR INFO] - Linux: sudo apt-get install tesseract-ocr")
        print("[OCR INFO] - Mac: brew install tesseract")
        return False


def preprocess_for_ocr(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Preprocess an image for better OCR accuracy.
    
    Applies common preprocessing steps:
    - Convert to grayscale
    - Apply thresholding
    - Denoise (optional)
    
    Args:
        image: Input image as numpy array (BGR format)
        
    Returns:
        Preprocessed image, or None if failed
    """
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply thresholding to make text stand out
        # Using adaptive threshold for better results with varying lighting
        processed = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 2
        )
        
        print("[OCR] Image preprocessed for OCR")
        return processed
        
    except Exception as e:
        print(f"[OCR ERROR] Preprocessing failed: {e}")
        return None


def extract_text(image: np.ndarray, 
                preprocess: bool = True,
                lang: str = 'eng') -> Tuple[bool, str]:
    """
    Extract all text from an image using OCR.
    
    Args:
        image: Input image as numpy array
        preprocess: Whether to preprocess image before OCR
        lang: Language for OCR (default: 'eng' for English)
        
    Returns:
        Tuple of (success: bool, extracted_text or error_message)
        
    Example:
        screenshot = cv_helper.take_screenshot()
        success, text = extract_text(screenshot)
        if success:
            print(f"Found text: {text}")
    """
    if not check_tesseract_available():
        return False, "Tesseract OCR not available"
    
    try:
        # Preprocess if requested
        if preprocess:
            processed_image = preprocess_for_ocr(image)
            if processed_image is None:
                return False, "Image preprocessing failed"
        else:
            processed_image = image
        
        # Extract text using pytesseract
        text = pytesseract.image_to_string(processed_image, lang=lang)
        
        # Clean up the text (remove extra whitespace)
        text = text.strip()
        
        print(f"[OCR] Text extracted: {len(text)} characters")
        return True, text
        
    except Exception as e:
        error_msg = f"OCR extraction failed: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, error_msg


def extract_text_from_region(image: np.ndarray, 
                             x: int, y: int, 
                             width: int, height: int,
                             preprocess: bool = True,
                             lang: str = 'eng') -> Tuple[bool, str]:
    """
    Extract text from a specific region of an image.
    
    Args:
        image: Input image as numpy array
        x: X-coordinate of top-left corner
        y: Y-coordinate of top-left corner
        width: Width of region
        height: Height of region
        preprocess: Whether to preprocess image before OCR
        lang: Language for OCR
        
    Returns:
        Tuple of (success: bool, extracted_text or error_message)
        
    Example:
        # Extract text from top-left 300x100 region
        success, text = extract_text_from_region(screenshot, 0, 0, 300, 100)
    """
    try:
        # Validate coordinates
        img_height, img_width = image.shape[:2]
        
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            return False, "Invalid region coordinates"
        
        if x + width > img_width or y + height > img_height:
            return False, "Region exceeds image bounds"
        
        # Crop the region
        region = image[y:y+height, x:x+width]
        
        print(f"[OCR] Extracting text from region ({x},{y},{width},{height})")
        
        # Extract text from the region
        return extract_text(region, preprocess, lang)
        
    except Exception as e:
        error_msg = f"Region text extraction failed: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, error_msg


def find_text(image: np.ndarray, 
             search_text: str,
             case_sensitive: bool = False,
             preprocess: bool = True) -> Tuple[bool, bool]:
    """
    Search for specific text in an image.
    
    Args:
        image: Input image as numpy array
        search_text: Text to search for
        case_sensitive: Whether search should be case-sensitive
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Tuple of (success: bool, found: bool)
        - success: Whether OCR extraction succeeded
        - found: Whether the search text was found
        
    Example:
        success, found = find_text(screenshot, "Submit")
        if success and found:
            print("Submit button text found!")
    """
    # Extract all text from image
    success, extracted_text = extract_text(image, preprocess)
    
    if not success:
        return False, False
    
    # Search for text
    if case_sensitive:
        found = search_text in extracted_text
    else:
        found = search_text.lower() in extracted_text.lower()
    
    if found:
        print(f"[OCR] Text '{search_text}' found in image")
    else:
        print(f"[OCR] Text '{search_text}' not found in image")
    
    return True, found


def get_text_data(image: np.ndarray,
                 preprocess: bool = True) -> Tuple[bool, Any]:
    """
    Get detailed OCR data including text positions.
    
    Returns text along with bounding box coordinates for each detected word.
    Useful for finding exact positions of text elements.
    
    Args:
        image: Input image as numpy array
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Tuple of (success: bool, data or error_message)
        
    Data structure (on success):
    {
        'text': ['word1', 'word2', ...],
        'left': [x1, x2, ...],
        'top': [y1, y2, ...],
        'width': [w1, w2, ...],
        'height': [h1, h2, ...]
    }
    
    Example:
        success, data = get_text_data(screenshot)
        if success:
            for i, word in enumerate(data['text']):
                if word.strip():  # Ignore empty strings
                    x = data['left'][i]
                    y = data['top'][i]
                    print(f"'{word}' at position ({x}, {y})")
    """
    if not check_tesseract_available():
        return False, "Tesseract OCR not available"
    
    try:
        # Preprocess if requested
        if preprocess:
            processed_image = preprocess_for_ocr(image)
            if processed_image is None:
                return False, "Image preprocessing failed"
        else:
            processed_image = image
        
        # Get detailed OCR data
        data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
        
        print(f"[OCR] Detailed text data extracted: {len(data['text'])} elements")
        return True, data
        
    except Exception as e:
        error_msg = f"Failed to get text data: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, error_msg


def find_text_position(image: np.ndarray,
                      search_text: str,
                      case_sensitive: bool = False,
                      preprocess: bool = True) -> Tuple[bool, Optional[Tuple[int, int, int, int]]]:
    """
    Find the position of specific text in an image.
    
    Args:
        image: Input image as numpy array
        search_text: Text to search for
        case_sensitive: Whether search should be case-sensitive
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Tuple of (success: bool, position or None)
        Position is (x, y, width, height) of the text bounding box
        
    Example:
        success, position = find_text_position(screenshot, "Submit")
        if success and position:
            x, y, w, h = position
            center_x = x + w // 2
            center_y = y + h // 2
            print(f"'Submit' button center: ({center_x}, {center_y})")
    """
    # Get detailed text data
    success, data = get_text_data(image, preprocess)
    
    if not success:
        return False, None
    
    # Search through detected text
    for i, word in enumerate(data['text']):
        if not word.strip():  # Skip empty strings
            continue
        
        # Compare text
        match = False
        if case_sensitive:
            match = search_text == word
        else:
            match = search_text.lower() == word.lower()
        
        if match:
            # Found the text, return its position
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            
            print(f"[OCR] Text '{search_text}' found at position ({x}, {y}, {w}, {h})")
            return True, (x, y, w, h)
    
    print(f"[OCR] Text '{search_text}' position not found")
    return True, None
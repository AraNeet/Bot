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
from typing import Optional, Tuple, Any
import pytesseract


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

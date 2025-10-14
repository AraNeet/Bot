#!/usr/bin/env python3
"""
Text Scanner Helper Module

This module provides OCR (Optical Character Recognition) functionality
for extracting text from images and screenshots using EasyOCR.

Core Functions:
- extract_text: Extract all text from an image
- find_text: Search for specific text in an image
- extract_text_from_region: Extract text from a specific region
- find_text_with_position: Find text and return its position
- get_text_data: Get detailed text data with bounding boxes

Requirements:
    - easyocr: EasyOCR library for text recognition
    - opencv-python: For image processing

This module focuses on text extraction operations that the verifier can use.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Any, List, Dict
import os

# Import EasyOCR
try:
    import easyocr
    print("[OCR] EasyOCR imported successfully")
except ImportError as e:
    raise ImportError("EasyOCR is required but not installed. Please install it with: pip install easyocr") from e

# Global EasyOCR instance for performance
_easy_ocr_instance = None

def get_easy_ocr_instance():
    """Get or create a global EasyOCR instance for better performance."""
    global _easy_ocr_instance
    
    if _easy_ocr_instance is None:
        print("[OCR] Initializing EasyOCR...")
        # Initialize EasyOCR with English language
        _easy_ocr_instance = easyocr.Reader(['en'], gpu=True)  # Set gpu=True if you have CUDA
        print("[OCR] EasyOCR initialized successfully")
    
    return _easy_ocr_instance

def preprocess_for_ocr(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Preprocess an image for better OCR accuracy.
    
    For EasyOCR, we can apply some basic preprocessing to improve text recognition.
    
    Args:
        image: Input image as numpy array (BGR format)
        
    Returns:
        Preprocessed image, or None if failed
    """
    try:
        # EasyOCR works well with color images, but we can apply some enhancement
        processed = image.copy()
        
        # Convert to LAB color space for better contrast adjustment
        lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        
        # Merge channels back
        lab = cv2.merge([l, a, b])
        processed = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        print("[OCR] Image preprocessing: applied contrast enhancement")
        return processed
        
    except Exception as e:
        print(f"[OCR ERROR] Preprocessing failed: {e}")
        return None

def extract_text(image: np.ndarray, 
                preprocess: bool = False,
                lang: str = 'en') -> Tuple[bool, str]:
    """
    Extract all text from an image using EasyOCR.
    
    Args:
        image: Input image as numpy array
        preprocess: Whether to preprocess image before OCR (default: False)
        lang: Language for OCR (default: 'en' for English)
        
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
            # Use original image - EasyOCR handles preprocessing internally
            processed_image = image
            print("[OCR] Using original image without preprocessing (EasyOCR handles this internally)")
        
        # Use EasyOCR
        reader = get_easy_ocr_instance()
        
        try:
            # EasyOCR returns a list of tuples: (bbox, text, confidence)
            results = reader.readtext(processed_image, 'beamsearch')
        except Exception as ocr_error:
            print(f"[OCR ERROR] EasyOCR extraction failed: {ocr_error}")
            return False, f"EasyOCR extraction failed: {ocr_error}"
        
        if not results:
            return True, ""  # No text found, but OCR succeeded
        
        # Extract all text from results
        all_text = []
        for bbox, text, confidence in results:
            if confidence > 0.5:  # Only include text with reasonable confidence
                all_text.append(text)
        
        extracted_text = " ".join(all_text).strip()
        
        print(f"[OCR] EasyOCR extracted: {len(extracted_text)} characters")
        return True, extracted_text
        
    except Exception as e:
        error_msg = f"OCR extraction failed: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, error_msg

def find_text(image: np.ndarray, 
             search_text: str,
             case_sensitive: bool = False,
             preprocess: bool = False) -> Tuple[bool, bool]:
    """
    Search for specific text in an image using EasyOCR.
    
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
            print("Submit button found!")
    """
    try:
        # Extract all text first
        success, extracted_text = extract_text(image, preprocess)
        
        if not success:
            return False, False
        
        # Search for the text
        search_lower = search_text.lower() if not case_sensitive else search_text
        text_lower = extracted_text.lower() if not case_sensitive else extracted_text
        
        found = search_lower in text_lower
        
        if found:
            print(f"[OCR] ✓ Found text: '{search_text}'")
        else:
            print(f"[OCR] ✗ Text not found: '{search_text}'")
        
        return True, found
        
    except Exception as e:
        error_msg = f"Text search failed: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, False

def find_text_in_region(image: np.ndarray,
                       search_text: str,
                       region: Tuple[int, int, int, int],
                       case_sensitive: bool = False,
                       preprocess: bool = False) -> Tuple[bool, bool]:
    """
    Search for specific text within a specific region of an image using EasyOCR.
    
    Args:
        image: Input image as numpy array
        search_text: Text to search for
        region: Region to search in (x, y, width, height)
        case_sensitive: Whether search should be case-sensitive
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Tuple of (success: bool, found: bool)
        - success: Whether OCR extraction succeeded
        - found: Whether the search text was found in the region
        
    Example:
        region = (100, 100, 200, 50)  # x, y, width, height
        success, found = find_text_in_region(screenshot, "Submit", region)
    """
    try:
        x, y, width, height = region
        
        # Crop the image to the specified region
        cropped_image = image[y:y+height, x:x+width]
        
        if cropped_image.size == 0:
            return False, False
        
        # Search for text in the cropped region
        return find_text(cropped_image, search_text, case_sensitive, preprocess)
        
    except Exception as e:
        error_msg = f"Region text search failed: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, False

def get_text_data(image: np.ndarray,
                 preprocess: bool = False) -> Tuple[bool, Any]:
    """
    Get detailed OCR data including text positions using EasyOCR.
    
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
        'bbox': [[x1,y1,x2,y2], [x1,y1,x2,y2], ...],
        'confidence': [0.95, 0.87, ...]
    }
    
    Example:
        success, data = get_text_data(screenshot)
        if success:
            for i, word in enumerate(data['text']):
                if word.strip():  # Ignore empty strings
                    bbox = data['bbox'][i]
                    confidence = data['confidence'][i]
                    print(f"'{word}' at bbox {bbox} (confidence: {confidence})")
    """
    try:
        # Preprocess if requested
        if preprocess:
            processed_image = preprocess_for_ocr(image)
            if processed_image is None:
                return False, "Image preprocessing failed"
        else:
            # Use original image - EasyOCR handles preprocessing internally
            processed_image = image
            print("[OCR] Using original image without preprocessing for get_text_data (EasyOCR handles this internally)")
        
        # Use EasyOCR
        reader = get_easy_ocr_instance()
        
        try:
            # EasyOCR returns a list of tuples: (bbox, text, confidence)
            results = reader.readtext(processed_image)
        except Exception as ocr_error:
            print(f"[OCR ERROR] EasyOCR get_text_data failed: {ocr_error}")
            return False, f"EasyOCR get_text_data failed: {ocr_error}"
        
        if not results:
            return True, {'text': [], 'bbox': [], 'confidence': []}
        
        # Extract data from results
        texts = []
        bboxes = []
        confidences = []
        
        for bbox, text, confidence in results:
            if confidence > 0.5:  # Only include text with reasonable confidence
                texts.append(text)
                # Convert bbox format from EasyOCR to our standard format
                # EasyOCR bbox: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                # Our format: [x1, y1, x2, y2]
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                standard_bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                bboxes.append(standard_bbox)
                confidences.append(confidence)
        
        data = {
            'text': texts,
            'bbox': bboxes,
            'confidence': confidences
        }
        
        print(f"[OCR] EasyOCR detailed data: {len(texts)} elements")
        return True, data
        
    except Exception as e:
        error_msg = f"Failed to get text data: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, error_msg

def find_text_with_position(image: np.ndarray,
                           search_text: str,
                           case_sensitive: bool = False,
                           preprocess: bool = False) -> Tuple[bool, bool, Optional[Tuple[int, int, int, int]]]:
    """
    Search for specific text in an image and return its position using EasyOCR.
    
    This function is particularly useful for finding UI elements by their text labels.
    
    Args:
        image: Input image as numpy array
        search_text: Text to search for
        case_sensitive: Whether search should be case-sensitive
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Tuple of (success: bool, found: bool, bbox: Optional[Tuple[int, int, int, int]])
        - success: Whether OCR extraction succeeded
        - found: Whether the search text was found
        - bbox: Bounding box of found text (x, y, width, height) or None if not found
        
    Example:
        success, found, bbox = find_text_with_position(screenshot, "Submit")
        if success and found:
            x, y, w, h = bbox
            print(f"Submit button found at ({x}, {y}) with size {w}x{h}")
    """
    try:
        # Get detailed text data
        success, data = get_text_data(image, preprocess)
        
        if not success:
            return False, False, None
        
        # Search for text in the data
        search_lower = search_text.lower() if not case_sensitive else search_text
        
        for i, text in enumerate(data['text']):
            if not text.strip():  # Skip empty strings
                continue
                
            text_lower = text.lower() if not case_sensitive else text
            
            if search_lower in text_lower:
                # Found the text, return its bounding box
                bbox = data['bbox'][i]
                confidence = data['confidence'][i]
                
                # Convert from [x1, y1, x2, y2] to [x, y, width, height]
                x, y, x2, y2 = bbox
                width = x2 - x
                height = y2 - y
                
                print(f"[OCR] ✓ Found '{search_text}' at ({x}, {y}) with confidence {confidence:.2f}")
                return True, True, (x, y, width, height)
        
        print(f"[OCR] ✗ Text '{search_text}' not found")
        return True, False, None
        
    except Exception as e:
        error_msg = f"Text search with position failed: {e}"
        print(f"[OCR ERROR] {error_msg}")
        return False, False, None

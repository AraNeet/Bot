#!/usr/bin/env python3
"""
Simple OCR Test Script

This script provides a simple function to extract words from an image
using the OCR utilities from the workflow module with EasyOCR.

Usage:
    python ocr_test.py path/to/image.png
    python ocr_test.py path/to/image.jpg
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path

# Add the src directory to the Python path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from workflow_module.helpers import ocr_utils
except ImportError as e:
    print(f"Error importing OCR utils: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def extract_words_from_image(image_path: str) -> tuple[bool, str]:
    """
    Extract all words from an image using EasyOCR.
    
    Args:
        image_path: Path to the image file (PNG, JPG, etc.)
        
    Returns:
        Tuple of (success: bool, extracted_text: str)
        - success: Whether OCR extraction succeeded
        - extracted_text: All text found in the image, or error message if failed
        
    Example:
        success, text = extract_words_from_image("screenshot.png")
        if success:
            print(f"Found text: {text}")
        else:
            print(f"Error: {text}")
    """
    print(f"[OCR_TEST] Processing image: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        return False, f"Image file not found: {image_path}"
    
    try:
        # Load the image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            return False, f"Failed to load image: {image_path}"
        
        print(f"[OCR_TEST] Image loaded successfully: {image.shape}")
        
        # Use OCR utils to extract text
        success, extracted_text = ocr_utils.extract_text(image)
        
        if success:
            if extracted_text.strip():
                print(f"[OCR_TEST] ✓ Successfully extracted {len(extracted_text)} characters")
                return True, extracted_text.strip()
            else:
                print(f"[OCR_TEST] ✓ OCR succeeded but no text found")
                return True, "No text found in image"
        else:
            print(f"[OCR_TEST] ✗ OCR extraction failed")
            return False, extracted_text  # extracted_text contains the error message
            
    except Exception as e:
        error_msg = f"Error processing image: {e}"
        print(f"[OCR_TEST] ✗ {error_msg}")
        return False, error_msg


def extract_words_with_positions(image_path: str) -> tuple[bool, dict]:
    """
    Extract words from an image with their positions using EasyOCR.
    
    Args:
        image_path: Path to the image file (PNG, JPG, etc.)
        
    Returns:
        Tuple of (success: bool, data: dict)
        - success: Whether OCR extraction succeeded
        - data: Dictionary with 'text', 'bbox', 'confidence' lists, or error message if failed
        
    Example:
        success, data = extract_words_with_positions("screenshot.png")
        if success:
            for i, word in enumerate(data['text']):
                bbox = data['bbox'][i]
                confidence = data['confidence'][i]
                print(f"'{word}' at {bbox} (confidence: {confidence})")
    """
    print(f"[OCR_TEST] Processing image with positions: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        return False, f"Image file not found: {image_path}"
    
    try:
        # Load the image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            return False, f"Failed to load image: {image_path}"
        
        print(f"[OCR_TEST] Image loaded successfully: {image.shape}")
        
        # Use OCR utils to get detailed text data
        success, data = ocr_utils.get_text_data(image)
        
        if success:
            if isinstance(data, dict) and data.get('text'):
                print(f"[OCR_TEST] ✓ Successfully extracted {len(data['text'])} text elements")
                return True, data
            else:
                print(f"[OCR_TEST] ✓ OCR succeeded but no text found")
                return True, {"text": [], "bbox": [], "confidence": []}
        else:
            print(f"[OCR_TEST] ✗ OCR extraction failed")
            return False, data  # data contains the error message
            
    except Exception as e:
        error_msg = f"Error processing image: {e}"
        print(f"[OCR_TEST] ✗ {error_msg}")
        return False, error_msg


def main():
    """Main function to run OCR test from command line."""
    if len(sys.argv) != 2:
        print("Usage: python ocr_test.py <image_path>")
        print("Example: python ocr_test.py screenshot.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("="*60)
    print("OCR TEST SCRIPT (EasyOCR)")
    print("="*60)
    
    # Test basic text extraction
    print("\n1. Testing basic text extraction...")
    success, text = extract_words_from_image(image_path)
    
    if success:
        print(f"\n✓ EXTRACTED TEXT:")
        print(f"'{text}'")
    else:
        print(f"\n✗ FAILED: {text}")
        sys.exit(1)
    
    # Test detailed extraction with positions
    print("\n2. Testing detailed extraction with positions...")
    success, data = extract_words_with_positions(image_path)
    
    if success and isinstance(data, dict) and data.get('text'):
        print(f"\n✓ DETAILED RESULTS:")
        for i, word in enumerate(data['text']):
            if word.strip():  # Only show non-empty words
                bbox = data['bbox'][i]
                confidence = data['confidence'][i]
                print(f"  '{word}' at {bbox} (confidence: {confidence:.2f})")
    else:
        print(f"\n✗ DETAILED EXTRACTION FAILED: {data}")
    
    print("\n" + "="*60)
    print("OCR TEST COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()
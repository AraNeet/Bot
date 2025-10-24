#!/usr/bin/env python3
"""
Text Scanner Helper Module

This module provides OCR (Optical Character Recognition) functionality
for extracting text from images and screenshots using PaddleOCR.

Now implemented as a class for better encapsulation and to avoid globals.

Core Methods:
- extract_text: Extract all text from an image
- find_text: Search for specific text in an image
- find_text_in_region: Search for text in a specific region
- find_text_with_position: Find text and return its position
- get_text_data: Get detailed text data with bounding boxes

Requirements:
    - paddleocr: PaddleOCR library for text recognition (install PaddlePaddle first, then pip install paddleocr)
    - opencv-python: For image processing

Usage:
    scanner = TextScanner()
    success, text = scanner.extract_text(image)
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Any, List, Dict
import os

# Import PaddleOCR
try:
    from paddleocr import PaddleOCR
    print("[OCR] PaddleOCR imported successfully")
except ImportError as e:
    raise ImportError("PaddleOCR is required but not installed. Please install PaddlePaddle (see https://www.paddlepaddle.org.cn/en/install/quick), then pip install paddleocr") from e

class TextScanner:
    """Class for handling OCR operations with PaddleOCR."""
    
    def __init__(self, lang: str = 'en'):
        """
        Initialize the TextScanner.
        
        Args:
            lang: Language for OCR (default: 'en')
            use_gpu: Whether to use GPU if available (default: True)
        """
        self._lang = lang
        self._ocr = None  # Lazy initialization
    
    def _get_ocr_instance(self):
        """Get or create the PaddleOCR instance lazily for better performance."""
        if self._ocr is None:
            print("[OCR] Initializing PaddleOCR...")
            self._ocr = PaddleOCR(lang=self._lang, use_doc_unwarping=False, use_doc_orientation_classify=False, use_textline_orientation=False)
            print("[OCR] PaddleOCR initialized successfully")
        return self._ocr

    def extract_text(self, image: np.ndarray) -> Tuple[bool, str]:
        """
        Extract all text from an image using PaddleOCR.
        
        Args:
            image: Input image as numpy array
            preprocess: Whether to preprocess image before OCR (default: False)
            lang: Language for OCR (default: 'en' for English)
            
        Returns:
            Tuple of (success: bool, extracted_text or error_message)
            
        Example:
            success, text = scanner.extract_text(screenshot)
            if success:
                print(f"Found text: {text}")
        """
        try:
            processed_image = image
            
            # Use PaddleOCR (note: lang is set at init, but we can ignore if different for now)
            ocr = self._get_ocr_instance()
            
            try:
                # Use the updated predict method for PaddleOCR 3.0+
                results = ocr.predict(processed_image)
                if not results:  # Handle no results
                    return True, ""  # No text found, but OCR succeeded
            except Exception as ocr_error:
                print(f"[OCR ERROR] PaddleOCR extraction failed: {ocr_error}")
                return False, f"PaddleOCR extraction failed: {ocr_error}"
            
            # Extract from the new Result format (list with one Result for single image)
            res_dict = results[0].json['res']
            
            # Get texts and confidences from the new structure
            texts = res_dict.get('rec_texts', [])
            confidences = res_dict.get('rec_scores', [])
            if isinstance(confidences, np.ndarray):
                confidences = confidences.tolist()
            
            # Extract all text from results with confidence filter
            all_text = []
            for text, confidence in zip(texts, confidences):
                if confidence > 0.7:  # Only include text with reasonable confidence
                    all_text.append(text)
            
            extracted_text = " ".join(all_text).strip()
            
            print(f"[OCR] PaddleOCR extracted: {len(extracted_text)} characters")
            return True, extracted_text
        
        except Exception as e:
            error_msg = f"OCR extraction failed: {e}"
            print(f"[OCR ERROR] {error_msg}")
            return False, error_msg

    def find_text(self, image: np.ndarray, 
                  search_text: str,
                  case_sensitive: bool = False) -> Tuple[bool, bool]:
        """
        Search for specific text in an image using PaddleOCR.
        
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
            success, found = scanner.find_text(screenshot, "Submit")
            if success and found:
                print("Submit button found!")
        """
        try:
            # Extract all text first
            success, extracted_text = self.extract_text(image)
            
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

    def get_text_data(self, image: np.ndarray) -> Tuple[bool, Any]:
        """
        Get detailed OCR data including text positions using PaddleOCR.
        
        Returns text along with bounding box coordinates for each detected word.
        Useful for finding exact positions of text elements.

        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (success: bool, data or error_message)
            
        Data structure (on success):
        {
            'text': ['word1', 'word2', ...],
            'bbox': [[x1,y1,x2,y2], [x1,y1,x2,y2], ...],
            'confidence': [0.95, 0.87, ...]
        }
        
        Example:
            success, data = scanner.get_text_data(screenshot)
            if success:
                for i, word in enumerate(data['text']):
                    if word.strip():  # Ignore empty strings
                        bbox = data['bbox'][i]
                        confidence = data['confidence'][i]
                        print(f"'{word}' at bbox {bbox} (confidence: {confidence})")
        """
        try:
            processed_image = image
            print("[OCR] Using original image for get_text_data (PaddleOCR handles preprocessing internally)")
            
            # Use PaddleOCR
            ocr = self._get_ocr_instance()
            
            try:
                # Use the updated predict method for PaddleOCR 3.0+
                results = ocr.predict(processed_image)
                if not results:  # Handle no results
                    return True, {'text': [], 'bbox': [], 'confidence': []}
            except Exception as ocr_error:
                print(f"[OCR ERROR] PaddleOCR get_text_data failed: {ocr_error}")
                return False, f"PaddleOCR get_text_data failed: {ocr_error}"
            
            # Extract from the new Result format (list with one Result for single image)
            res_dict = results[0].json['res']
            
            # Get texts, confidences, and bboxes from the new structure
            texts = res_dict.get('rec_texts', [])
            confidences = res_dict.get('rec_scores', [])
            if isinstance(confidences, np.ndarray):
                confidences = confidences.tolist()
            bboxes = res_dict.get('rec_boxes', [])
            if isinstance(bboxes, np.ndarray):
                bboxes = bboxes.tolist()
            
            # Filter for reasonable confidence
            filtered_texts = []
            filtered_bboxes = []
            filtered_confidences = []
            for text, confidence, bbox in zip(texts, confidences, bboxes):
                if confidence > 0.5:  # Only include text with reasonable confidence
                    filtered_texts.append(text)
                    # bbox is already [x1, y1, x2, y2]
                    filtered_bboxes.append(bbox)
                    filtered_confidences.append(confidence)
            
            data = {
                'text': filtered_texts,
                'bbox': filtered_bboxes,
                'confidence': filtered_confidences
            }
            
            print(f"[OCR] PaddleOCR detailed data: {len(filtered_texts)} elements")
            return True, data
            
        except Exception as e:
            error_msg = f"Failed to get text data: {e}"
            print(f"[OCR ERROR] {error_msg}")
            return False, error_msg

    def find_text_with_position(self, image: np.ndarray,
                                search_text: str,
                                case_sensitive: bool = False) -> Tuple[bool, bool, Optional[Tuple[int, int, int, int]]]:
        """
        Search for specific text in an image and return its position using PaddleOCR.
        
        This function is particularly useful for finding UI elements by their text labels.
        
        Args:
            image: Input image as numpy array
            search_text: Text to search for
            case_sensitive: Whether search should be case-sensitive
            
        Returns:
            Tuple of (success: bool, found: bool, bbox: Optional[Tuple[int, int, int, int]])
            - success: Whether OCR extraction succeeded
            - found: Whether the search text was found
            - bbox: Bounding box of found text (x, y, width, height) or None if not found
            
        Example:
            success, found, bbox = scanner.find_text_with_position(screenshot, "Submit")
            if success and found:
                x, y, w, h = bbox
                print(f"Submit button found at ({x}, {y}) with size {w}x{h}")
        """
        try:
            # Get detailed text data (no preprocess arg now)
            success, data = self.get_text_data(image)
            
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
        

def match_text_positions(target_texts: List[str], data: Dict[str, List]) -> List[Tuple[int, int, int, int]]:
    """
    Match target texts in OCR data and return first position per matched target.
    
    This function:
    1. Defines lower_targets for case-insensitive matching.
    2. Loops through data["text"] to find first match per target (case-insensitive).
    3. Saves first matched word and position per target in a dict.
    4. Returns list of first positions [(x, y, w, h), ...] for matched targets, sorted by x.
    5. Only fails (returns []) if 3 or more targets are unmatched.
    
    Args:
        target_texts: List of search terms (e.g., [deal_number, advertiser_name, begin_date, end_date])
        data: OCR data from TextScanner.get_text_data (dict with 'text', 'bbox', 'confidence')
    
    Returns:
        List of (x, y, w, h) tuples for first match of each matched target, sorted by x.
        Empty list if 3 or more targets are unmatched.
    """
    # Define lower_targets (lowercase for matching, map to original)
    target_lowers = {t.lower(): t for t in target_texts if t}  # E.g., {'418498': '418498', 'blue apron': 'Blue Apron'}
    if len(target_lowers) != len(target_texts):
        print(f"[ACTION_HANDLER] Not all {len(target_texts)} targets valid—got {len(target_lowers)}!")
        return []
    print(f"[ACTION_HANDLER] Matching targets: {list(target_lowers.values())}")

    # Match across all OCR text (no row tolerance—pure text search!)
    match_info = {}  # Key: lowercase target, Value: (word, (x, y, w, h)) for FIRST match only
    for i, text in enumerate(data['text']):
        if not text.strip():  # Skip empty—clean and respectful!
            continue
        text_lower = text.lower()  # Case-insensitive match
        bbox = data['bbox'][i]  # [x1, y1, x2, y2]
        pos = (bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])  # (x, y, w, h)
        
        # Check if text matches ANY search term (save FIRST match only)
        for target in target_lowers:
            if target not in match_info and target in text_lower:  # Only if not already matched
                match_info[target] = (text, pos)  # Save first (word, pos)
                print(f"[DEBUG] First match for '{target_lowers[target]}': '{text}' at pos {pos}")

    # Check if too many targets are missing (3 or more)
    missing = [target_lowers[t] for t in target_lowers if t not in match_info]
    if len(missing) >= 3:
        print(f"[ACTION_HANDLER] Too many targets missing ({len(missing)}): {missing}. Failing!")
        return []

    # Collect first position per matched target (in order of target_texts)
    positions = []
    for target in target_lowers:
        if target in match_info:
            matched_word, first_pos = match_info[target]  # First (and only) match
            print(f"[ACTION_HANDLER] Target '{target_lowers[target]}' matched with '{matched_word}' at {first_pos}")
            positions.append(first_pos)
        else:
            print(f"[ACTION_HANDLER] Target '{target_lowers[target]}' not matched—skipping!")

    # Sort by x for left-to-right order (wise for later clicking!)
    if positions:
        positions.sort(key=lambda p: p[0])
        print(f"[ACTION_HANDLER] Positions for use later: {positions}")
    
    return positions
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
    import paddle
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
        """
        self._lang = lang
        self._ocr = None  # Lazy initialization
    
    def _get_ocr_instance(self):
        """Get or create the PaddleOCR instance lazily for better performance."""
        if self._ocr is None:
            print("[OCR] Initializing PaddleOCR...")
            use_gpu = paddle.device.cuda.device_count() > 0
            device_name = "GPU" if use_gpu else "CPU"
            
            print(f"[OCR] Initializing PaddleOCR on {device_name}...")
            if use_gpu:
                gpu_count = paddle.device.cuda.device_count()
                print(f"[OCR] GPU device(s) available: {gpu_count}")
                print(f"[OCR] GPU device name: {paddle.device.cuda.get_device_properties(0).name if gpu_count > 0 else 'N/A'}")
            else:
                print("[OCR] No GPU detected, using CPU")
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
    
    Improved matching logic:
    1. Normalizes dates by removing leading zeros (09/16/2025 → 9/16/2025)
    2. Prevents multiple targets from matching the same OCR text box
    3. Prioritizes more specific matches (longer strings, exact matches)
    4. Returns list of unique positions for each matched target
    5. Only fails if 3 or more targets are unmatched
    
    Args:
        target_texts: List of search terms (e.g., [estimate_number, advertiser_name, begin_date, end_date])
        data: OCR data from TextScanner.get_text_data (dict with 'text', 'bbox', 'confidence')
    
    Returns:
        List of (x, y, w, h) tuples for first match of each matched target, sorted by x.
        Empty list if 3 or more targets are unmatched.
    """
    import re
    
    def normalize_for_matching(text: str) -> str:
        """Normalize text for matching - remove leading zeros from dates."""
        # Convert to string and lowercase
        text = str(text).lower()
        # Remove leading zeros from date components (09 → 9, 01 → 1)
        # Match patterns like 09/16/2025 or 01-15-2024
        text = re.sub(r'\b0+(\d)', r'\1', text)
        return text
    
    # Convert all targets to strings and normalize
    target_normalized = {}  # Key: normalized target, Value: original target string
    for t in target_texts:
        if t:
            original = str(t)
            normalized = normalize_for_matching(original)
            target_normalized[normalized] = original
    
    if len(target_normalized) != len(target_texts):
        print(f"[MATCH] Not all {len(target_texts)} targets valid—got {len(target_normalized)}!")
        return []
    
    print(f"[MATCH] Matching targets: {list(target_normalized.values())}")
    
    # Track which OCR text indices have been used to prevent duplicate matches
    used_indices = set()
    
    # First pass: Find matches for each target
    # Store potential matches with scores
    all_matches = {}  # Key: normalized target, Value: list of (score, index, text, pos)
    
    for target_norm, target_orig in target_normalized.items():
        all_matches[target_norm] = []
        
        for i, text in enumerate(data['text']):
            if not text.strip() or i in used_indices:
                continue
            
            text_normalized = normalize_for_matching(text)
            bbox = data['bbox'][i]
            pos = (bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
            
            # Check if target matches this text
            if target_norm in text_normalized:
                # Calculate match score (higher is better)
                # Prioritize: exact match > target is most of text > target is small part of text
                score = 0
                
                if target_norm == text_normalized:
                    # Exact match
                    score = 1000
                elif text_normalized == target_norm.strip():
                    # Exact match after strip
                    score = 900
                else:
                    # Partial match - score based on how much of the text is the target
                    # Longer target strings get higher scores
                    target_ratio = len(target_norm) / len(text_normalized)
                    score = int(target_ratio * 100) + len(target_norm)
                
                all_matches[target_norm].append((score, i, text, pos))
    
    # Second pass: Assign best unique match for each target
    # Sort targets by specificity (longer targets first to get first pick)
    sorted_targets = sorted(target_normalized.keys(), key=lambda t: len(t), reverse=True)
    
    match_info = {}  # Key: normalized target, Value: (text, pos, index)
    
    for target_norm in sorted_targets:
        target_orig = target_normalized[target_norm]
        matches = all_matches.get(target_norm, [])
        
        if not matches:
            print(f"[MATCH] No matches found for '{target_orig}'")
            continue
        
        # Sort by score (highest first) and filter out used indices
        matches = [(score, idx, text, pos) for score, idx, text, pos in matches if idx not in used_indices]
        matches.sort(reverse=True, key=lambda m: m[0])
        
        if matches:
            score, idx, text, pos = matches[0]
            match_info[target_norm] = (text, pos, idx)
            used_indices.add(idx)  # Mark this OCR text as used
            print(f"[MATCH] '{target_orig}' matched to '{text}' at {pos} (score: {score})")
        else:
            print(f"[MATCH] All potential matches for '{target_orig}' already used by other targets")
    
    # Check if too many targets are missing (3 or more)
    missing = [target_normalized[t] for t in target_normalized if t not in match_info]
    if len(missing) >= 3:
        print(f"[MATCH] Too many targets missing ({len(missing)}): {missing}. Failing!")
        return []
    
    # Collect positions in order of original target_texts
    positions = []
    for t in target_texts:
        if t:
            target_norm = normalize_for_matching(str(t))
            if target_norm in match_info:
                text, pos, idx = match_info[target_norm]
                positions.append(pos)
            else:
                print(f"[MATCH] Target '{t}' not matched—skipping!")
    
    # Sort by x for left-to-right order
    if positions:
        positions.sort(key=lambda p: p[0])
        print(f"[MATCH] Final {len(positions)} unique positions (sorted by x): {positions}")
    
    return positions

#!/usr/bin/env python3
"""
Verification Utilities

This module contains shared verification utility functions used by action handlers.
These are low-level utilities that support verification logic including text similarity
and OCR text extraction helpers.
"""

from typing import Optional
import re

# ============================================================================
# TEXT SIMILARITY
# ============================================================================

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        if not text1 or not text2:
            return 0.0
        
        # Remove spaces and special characters for comparison
        clean1 = ''.join(c.lower() for c in text1 if c.isalnum())
        clean2 = ''.join(c.lower() for c in text2 if c.isalnum())
        
        if not clean1 or not clean2:
            return 0.0
        
        # Simple character overlap calculation
        matches = sum(1 for c in clean1 if c in clean2)
        similarity = matches / max(len(clean1), len(clean2))
        return similarity
        
    except Exception as e:
        print(f"[VERIFICATION_UTILS ERROR] Error calculating text similarity: {e}")
        return 0.0

# ============================================================================
# OCR TEXT EXTRACTION HELPERS
# ============================================================================

def extract_string_from_text(ocr_text: str, expected_string: str) -> Optional[str]:
    """
    Extract text string from OCR text using similarity matching.
    
    This function looks for text in OCR output by:
    1. Extracting all text patterns (words/phrases) from the OCR text
    2. Finding the pattern with the highest similarity to the expected string
    
    Args:
        ocr_text: Full OCR text from the field
        expected_string: Expected string to match against
        
    Returns:
        Extracted string or None if not found (with 80% similarity threshold)
    """
    # Clean the OCR text
    ocr_text_clean = ocr_text.strip()
    
    # Extract all text patterns (words/phrases) from the OCR text
    text_patterns = re.findall(r'[A-Za-z][A-Za-z\s]+[A-Za-z]', ocr_text_clean)
    
    if not text_patterns:
        print(f"[VERIFICATION_UTILS] No text patterns found in OCR text")
        return None
    
    # Find the pattern with the highest similarity to the expected string
    best_match = None
    best_similarity = 0.0
    
    for pattern in text_patterns:
        pattern_clean = pattern.strip()
        if len(pattern_clean) < 3:  # Skip very short patterns
            continue
            
        similarity = calculate_text_similarity(expected_string, pattern_clean)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = pattern_clean
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFICATION_UTILS] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFICATION_UTILS] No suitable pattern found (best similarity: {best_similarity:.2%})")
    return None

def extract_number_from_text(ocr_text: str, expected_number: str) -> Optional[str]:
    """
    Extract number from OCR text using similarity matching.
    
    This function looks for numeric patterns in OCR output by:
    1. Extracting all numeric patterns from the OCR text
    2. Finding the pattern with the highest similarity to the expected number
    
    Args:
        ocr_text: Full OCR text from the field
        expected_number: Expected number to match against
        
    Returns:
        Extracted number string or None if not found (with 80% similarity threshold)
    """
    numeric_patterns = re.findall(r'\d+', ocr_text.strip())
    
    if not numeric_patterns:
        print(f"[VERIFICATION_UTILS] No numeric patterns found in OCR text")
        return None
    
    best_match = None
    best_similarity = 0.0
    
    for pattern in numeric_patterns:
        similarity = calculate_text_similarity(expected_number, pattern)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = pattern
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFICATION_UTILS] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFICATION_UTILS] No suitable number pattern found (best similarity: {best_similarity:.2%})")
    return None

def extract_date_from_text(ocr_text: str, expected_date: str) -> Optional[str]:
    """
    Extract date in MM/DD/YYYY format from OCR text, ignoring letters and allowing single-digit months/days.
    
    This function looks for dates in OCR output by:
    1. Removing all letters from the OCR text
    2. Using a regex to find M/D/YYYY or MM/DD/YYYY formats
    3. Normalizing to MM/DD/YYYY format
    4. Finding the pattern with the highest similarity to the expected date
    
    Args:
        ocr_text: Full OCR text from the field
        expected_date: Expected date in MM/DD/YYYY format to match against
        
    Returns:
        Extracted date string in MM/DD/YYYY format or None if not found (with 80% similarity threshold)
    """
    # Clean the OCR text and remove all letters
    ocr_text_clean = re.sub(r'[a-zA-Z]', '', ocr_text.strip())
    
    # Regex for M/D/YYYY or MM/DD/YYYY (months 1-12, days 1-31, year 4 digits)
    date_pattern = r'(\d{1,2})/(\d{1,2})/(\d{4})'
    date_matches = re.findall(date_pattern, ocr_text_clean)
    
    if not date_matches:
        print(f"[VERIFICATION_UTILS] No date patterns found in OCR text: '{ocr_text_clean}'")
        return None
    
    # Normalize matches to MM/DD/YYYY format
    date_strings = []
    for month, day, year in date_matches:
        try:
            # Convert to integers to validate ranges
            month_int = int(month)
            day_int = int(day)
            if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                date_str = f"{month_int:02d}/{day_int:02d}/{year}"
                date_strings.append(date_str)
        except ValueError:
            continue
    
    if not date_strings:
        print(f"[VERIFICATION_UTILS] No valid date patterns found in OCR text: '{ocr_text_clean}'")
        return None
    
    # Find the pattern with the highest similarity to the expected date
    best_match = None
    best_similarity = 0.0
    
    for date_str in date_strings:
        similarity = calculate_text_similarity(expected_date, date_str)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = date_str
    
    if best_match and best_similarity >= 0.8:  # 80% similarity threshold
        print(f"[VERIFICATION_UTILS] Found best match: '{best_match}' (similarity: {best_similarity:.2%})")
        return best_match
    
    print(f"[VERIFICATION_UTILS] No suitable date pattern found (best similarity: {best_similarity:.2%})")
    return None


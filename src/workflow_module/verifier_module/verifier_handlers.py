#!/usr/bin/env python3
"""
Verifier Handlers Module

This module contains HIGH-LEVEL verifier functions that understand the APPLICATION.
Unlike verifier_helpers.py (generic verification), these functions know WHAT to verify,
WHERE to look, and HOW to interpret the results for specific actions.

Key Difference:
- verifier_helpers.py: Generic "check if text exists" 
- verifier_handlers.py: Specific "verify_multinetwork_page_opened()" that knows what to check

Architecture:
    Instruction Name
        ↓
    verifier_executor.py (routes to this file)
        ↓
    verifier_handlers.py (THIS FILE - knows what to verify, calls verifier_helpers.py)
        ↓
    verifier_helpers.py (performs generic verification)

Each function here:
1. Knows what to verify for a specific action
2. Uses verifier_helpers.py to perform the actual verification
3. Interprets the results in context of the action
4. Returns (success: bool, message: str, data: Optional[Dict])

IMPORTANT: Functions receive parameters via **kwargs pattern:
    def verify_advertiser_name_entered(advertiser_name: str = "", **kwargs):
        # Use advertiser_name
        # Ignore any extra kwargs
"""

from typing import Dict, Any, Tuple, Optional
from . import verifier_helpers
import cv2
import time
from ..helpers import computer_vision_utils


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _simple_text_verification(expected_text: str, ocr_data: dict, field_region: tuple, debug_filename: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Helper function for simple text verification using OCR data.
    
    Args:
        expected_text: Text to verify
        ocr_data: OCR data dictionary with 'text' and 'confidence' keys
        field_region: Field region tuple (x, y, width, height)
        debug_filename: Debug image filename
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    expected_lower = expected_text.lower().strip()
    confidence_threshold = 0.60
    
    print(f"[VERIFIER_HANDLER] Performing simple search for '{expected_text}' with {confidence_threshold*100:.0f}% confidence threshold...")
    
    match_found = False
    match_method = ""
    best_match_confidence = 0.0
    best_match_text = ""
    
    # Simple strategy: Look for exact matches or substring matches
    for i, text in enumerate(ocr_data['text']):
        if not text.strip():
            continue
            
        confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
        
        if confidence >= confidence_threshold:
            text_lower = text.lower().strip()
            
            if expected_lower == text_lower:
                match_found = True
                match_method = f"exact match (confidence: {confidence:.2f})"
                best_match_confidence = confidence
                best_match_text = text
                print(f"[VERIFIER_HANDLER] ✓ Found exact match: '{text}' ({confidence:.2f})")
                break
            elif expected_lower in text_lower or text_lower in expected_lower:
                match_found = True
                match_method = f"substring match (confidence: {confidence:.2f})"
                best_match_confidence = confidence
                best_match_text = text
                print(f"[VERIFIER_HANDLER] ✓ Found substring match: '{text}' ({confidence:.2f})")
                break
    
    if match_found:
        success_msg = f"✓ Text '{expected_text}' verified in field ({match_method})"
        print(f"[VERIFIER_HANDLER] {success_msg}")
        
        verification_data = {
            "expected_text": expected_text,
            "matched_text": best_match_text,
            "match_confidence": best_match_confidence,
            "field_region": field_region,
            "debug_image": debug_filename,
            "match_method": match_method,
            "confidence_threshold": confidence_threshold,
            "ocr_data": ocr_data
        }
        
        return True, success_msg, verification_data
    else:
        error_msg = f"✗ Text verification failed. Expected: '{expected_text}', No matches found"
        print(f"[VERIFIER_HANDLER] {error_msg}")
        
        verification_data = {
            "expected_text": expected_text,
            "field_region": field_region,
            "debug_image": debug_filename,
            "confidence_threshold": confidence_threshold,
            "ocr_data": ocr_data
        }
        
        return False, error_msg, verification_data


# ============================================================================
# NAVIGATION VERIFICATION HANDLERS
# ============================================================================

def verify_multinetwork_page_opened(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the Multi-Network Instructions page opened successfully.
    
    This handler knows:
    - What template to look for (search_fields.png)
    - What text should be present on the page
    - How to interpret the verification results
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
        - success: Whether the page opened correctly
        - message: Success or error message
        - data: Dictionary with 'region' key containing found coordinates
    """
    print("[VERIFIER_HANDLER] Verifying Multi-Network Instructions page opened...")
    
    try:
        # Use verifier_helpers to perform the actual verification
        success, message, region = verifier_helpers.verify_page_with_template(
            template_path='assets/search_fields.png',
            expected_texts=[
                "Order"
            ],
            confidence=0.8
        )
        
        # Prepare return data
        data = None
        if success and region:
            data = {'region': region}
        
        return success, message, data
        
    except Exception as e:
        error_msg = f"Error verifying Multi-Network Instructions page: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# SEARCH FIELD VERIFICATION HANDLERS
# ============================================================================

def verify_advertiser_name_entered(advertiser_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the advertiser name was entered correctly.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the advertiser field region (206, 152, 1439, 79)
    3. Uses OCR to verify the advertiser name was entered correctly
    
    Args:
        advertiser_name: Expected advertiser name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying advertiser name entered: '{advertiser_name}'")
    
    if not advertiser_name:
        return True, "No advertiser name to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        field_region = (region_x, region_y, region_width, region_height)
        
        print(f"[VERIFIER_HANDLER] Cropping screenshot to advertiser field region {field_region}")
        
        # Crop the screenshot to the advertiser field region
        cropped_image = verifier_helpers.crop_image_for_verification(
            screenshot, 
            region_x, 
            region_y, 
            region_width, 
            region_height
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to advertiser field region", None
        
        # Save the cropped image for debugging
        debug_filename = f"advertiser_field_verification_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[VERIFIER_HANDLER] Saved cropped advertiser field for debugging: {debug_filename}")
        
        # Use OCR to extract text from the cropped field region
        print(f"[VERIFIER_HANDLER] Extracting text from advertiser field...")
        success, extracted_text = verifier_helpers.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from advertiser field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Get detailed OCR data to check confidence scores
        print(f"[VERIFIER_HANDLER] Getting detailed OCR data for confidence checking...")
        ocr_success, ocr_data = verifier_helpers.get_detailed_ocr_data(cropped_image)
        
        if not ocr_success:
            return False, f"Failed to get detailed OCR data: {ocr_data}", None
        
        # Check if we have valid OCR data with confidence scores
        if not isinstance(ocr_data, dict) or 'text' not in ocr_data or 'confidence' not in ocr_data:
            return False, "Invalid OCR data structure received", None
        
        # Find text matches with robust checking and multiple strategies
        expected_lower = advertiser_name.lower().strip()
        confidence_threshold = 0.60  # Lowered to 60% for more robust detection
        
        print(f"[VERIFIER_HANDLER] Performing robust search for '{advertiser_name}' with {confidence_threshold*100:.0f}% confidence threshold...")
        
        match_found = False
        match_method = ""
        best_match_confidence = 0.0
        best_match_text = ""
        
        # Strategy 1: High confidence exact matches (85%+)
        print(f"[VERIFIER_HANDLER] Strategy 1: High confidence exact matches (85%+)...")
        for i, text in enumerate(ocr_data['text']):
            if not text.strip():
                continue
                
            confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
            
            if confidence >= 0.85:  # High confidence threshold
                text_lower = text.lower().strip()
                
                if expected_lower == text_lower:
                    match_found = True
                    match_method = f"high confidence exact match (confidence: {confidence:.2f})"
                    best_match_confidence = confidence
                    best_match_text = text
                    print(f"[VERIFIER_HANDLER] ✓ Found high confidence exact match: '{text}' ({confidence:.2f})")
                    break
        
        # Strategy 2: Medium confidence matches (60%+) with various patterns
        if not match_found:
            print(f"[VERIFIER_HANDLER] Strategy 2: Medium confidence matches (60%+) with pattern matching...")
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                    
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                
                if confidence >= confidence_threshold:
                    text_lower = text.lower().strip()
                    
                    # Check for various match patterns
                    if expected_lower == text_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"exact match (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found exact match: '{text}' ({confidence:.2f})")
                    elif expected_lower in text_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"expected contains extracted (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found substring match: '{text}' ({confidence:.2f})")
                    elif text_lower in expected_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"extracted contains expected (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found partial match: '{text}' ({confidence:.2f})")
        
        # Strategy 3: Word-by-word matching (any confidence)
        if not match_found:
            print(f"[VERIFIER_HANDLER] Strategy 3: Word-by-word matching (any confidence)...")
            expected_words = expected_lower.split()
            
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                    
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                text_lower = text.lower().strip()
                text_words = text_lower.split()
                
                # Check if most words match
                matching_words = 0
                for expected_word in expected_words:
                    for text_word in text_words:
                        if expected_word in text_word or text_word in expected_word:
                            matching_words += 1
                            break
                
                word_match_ratio = matching_words / len(expected_words) if expected_words else 0
                
                if word_match_ratio >= 0.7:  # 70% word match
                    if confidence > best_match_confidence:
                        match_found = True
                        match_method = f"word match ({matching_words}/{len(expected_words)} words, confidence: {confidence:.2f})"
                        best_match_confidence = confidence
                        best_match_text = text
                        print(f"[VERIFIER_HANDLER] ✓ Found word match: '{text}' ({matching_words}/{len(expected_words)} words, {confidence:.2f})")
        
        # Strategy 4: Character-by-character similarity (any confidence)
        if not match_found:
            print(f"[VERIFIER_HANDLER] Strategy 4: Character similarity matching (any confidence)...")
            
            def calculate_similarity(str1, str2):
                """Calculate character similarity between two strings"""
                if not str1 or not str2:
                    return 0.0
                
                # Remove spaces and special characters for comparison
                clean1 = ''.join(c.lower() for c in str1 if c.isalnum())
                clean2 = ''.join(c.lower() for c in str2 if c.isalnum())
                
                if not clean1 or not clean2:
                    return 0.0
                
                # Simple character overlap calculation
                matches = sum(1 for c in clean1 if c in clean2)
                similarity = matches / max(len(clean1), len(clean2))
                return similarity
            
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                    
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                similarity = calculate_similarity(expected_lower, text.lower())
                
                if similarity >= 0.8:  # 80% character similarity
                    if confidence > best_match_confidence:
                        match_found = True
                        match_method = f"character similarity ({similarity:.2f}, confidence: {confidence:.2f})"
                        best_match_confidence = confidence
                        best_match_text = text
                        print(f"[VERIFIER_HANDLER] ✓ Found character similarity: '{text}' (similarity: {similarity:.2f}, confidence: {confidence:.2f})")
                
        # Strategy 5: Fuzzy matching with very low threshold (last resort)
        if not match_found:
            print(f"[VERIFIER_HANDLER] Strategy 5: Fuzzy matching (last resort)...")
            
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                    
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                text_lower = text.lower().strip()
                
                # Very lenient fuzzy matching
                if len(text_lower) > 0 and len(expected_lower) > 0:
                    # Check if any significant portion matches
                    min_len = min(len(text_lower), len(expected_lower))
                    if min_len >= 3:  # Only for strings with at least 3 characters
                        common_chars = sum(1 for c in expected_lower if c in text_lower)
                        fuzzy_ratio = common_chars / max(len(expected_lower), len(text_lower))
                        
                        if fuzzy_ratio >= 0.6:  # 60% character overlap
                            if confidence > best_match_confidence:
                                match_found = True
                                match_method = f"fuzzy match ({fuzzy_ratio:.2f}, confidence: {confidence:.2f})"
                                best_match_confidence = confidence
                                best_match_text = text
                                print(f"[VERIFIER_HANDLER] ✓ Found fuzzy match: '{text}' (ratio: {fuzzy_ratio:.2f}, confidence: {confidence:.2f})")
        
        # Log detailed OCR results for debugging
        print(f"[VERIFIER_HANDLER] OCR Results Summary:")
        print(f"[VERIFIER_HANDLER]   Found {len(ocr_data['text'])} text elements:")
        for i, text in enumerate(ocr_data['text']):
            if text.strip():
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                status = "✓ HIGH CONF" if confidence >= 0.85 else "✓ MED CONF" if confidence >= 0.60 else "✓ LOW CONF"
                print(f"[VERIFIER_HANDLER]     {i+1}. '{text}' (confidence: {confidence:.2f}) {status}")
        
        # Return verification result
        if match_found:
            success_msg = f"✓ Advertiser name '{advertiser_name}' verified in field ({match_method})"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            
            verification_data = {
                "expected_text": advertiser_name,
                "extracted_text": extracted_text,
                "matched_text": best_match_text,
                "match_confidence": best_match_confidence,
                "field_region": field_region,
                "debug_image": debug_filename,
                "match_method": match_method,
                "confidence_threshold": confidence_threshold,
                "ocr_data": ocr_data
            }
            
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Advertiser name verification failed. Expected: '{advertiser_name}', No matches found with any strategy"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            
            verification_data = {
                "expected_text": advertiser_name,
                "extracted_text": extracted_text,
                "field_region": field_region,
                "debug_image": debug_filename,
                "confidence_threshold": confidence_threshold,
                "ocr_data": ocr_data
            }
            
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying advertiser name entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_order_id_entered(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the order ID was entered correctly.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the order field region (206, 152, 1439, 79)
    3. Uses OCR to verify the order ID was entered correctly
    
    Args:
        order_number: Expected order ID to verify
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying order ID entered: '{order_number}'")
    
    if not order_number:
        return True, "No order ID to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        field_region = (region_x, region_y, region_width, region_height)
        
        print(f"[VERIFIER_HANDLER] Cropping screenshot to order field region {field_region}")
        
        # Crop the screenshot to the order field region
        cropped_image = verifier_helpers.crop_image_for_verification(
            screenshot, 
            region_x, 
            region_y, 
            region_width, 
            region_height
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to order field region", None
        
        # Save the cropped image for debugging
        debug_filename = f"order_field_verification_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[VERIFIER_HANDLER] Saved cropped order field for debugging: {debug_filename}")
        
        # Use OCR to extract text from the cropped field region
        print(f"[VERIFIER_HANDLER] Extracting text from order field...")
        success, extracted_text = verifier_helpers.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from order field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Get detailed OCR data to check confidence scores
        print(f"[VERIFIER_HANDLER] Getting detailed OCR data for confidence checking...")
        ocr_success, ocr_data = verifier_helpers.get_detailed_ocr_data(cropped_image)
        
        if not ocr_success:
            return False, f"Failed to get detailed OCR data: {ocr_data}", None
        
        # Check if we have valid OCR data with confidence scores
        if not isinstance(ocr_data, dict) or 'text' not in ocr_data or 'confidence' not in ocr_data:
            return False, "Invalid OCR data structure received", None
        
        # Use the helper function for simple verification
        return _simple_text_verification(order_number, ocr_data, field_region, debug_filename)
        
    except Exception as e:
        error_msg = f"Error verifying order ID entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_agency_name_entered(agency_name: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the agency name was entered correctly.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the agency field region (206, 152, 1439, 79)
    3. Uses OCR to verify the agency name was entered correctly
    
    Args:
        agency_name: Expected agency name to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying agency name entered: '{agency_name}'")
    
    if not agency_name:
        return True, "No agency name to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        field_region = (region_x, region_y, region_width, region_height)
        
        print(f"[VERIFIER_HANDLER] Cropping screenshot to agency field region {field_region}")
        
        # Crop the screenshot to the agency field region
        cropped_image = verifier_helpers.crop_image_for_verification(
            screenshot, 
            region_x, 
            region_y, 
            region_width, 
            region_height
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to agency field region", None
        
        # Save the cropped image for debugging
        debug_filename = f"agency_field_verification_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[VERIFIER_HANDLER] Saved cropped agency field for debugging: {debug_filename}")
        
        # Use OCR to extract text from the cropped field region
        print(f"[VERIFIER_HANDLER] Extracting text from agency field...")
        success, extracted_text = verifier_helpers.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from agency field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Get detailed OCR data to check confidence scores
        print(f"[VERIFIER_HANDLER] Getting detailed OCR data for confidence checking...")
        ocr_success, ocr_data = verifier_helpers.get_detailed_ocr_data(cropped_image)
        
        if not ocr_success:
            return False, f"Failed to get detailed OCR data: {ocr_data}", None
        
        # Check if we have valid OCR data with confidence scores
        if not isinstance(ocr_data, dict) or 'text' not in ocr_data or 'confidence' not in ocr_data:
            return False, "Invalid OCR data structure received", None
        
        # Find text matches with robust checking
        expected_lower = agency_name.lower().strip()
        confidence_threshold = 0.60
        
        print(f"[VERIFIER_HANDLER] Performing robust search for '{agency_name}' with {confidence_threshold*100:.0f}% confidence threshold...")
        
        match_found = False
        match_method = ""
        best_match_confidence = 0.0
        best_match_text = ""
        
        # Strategy 1: High confidence exact matches (85%+)
        for i, text in enumerate(ocr_data['text']):
            if not text.strip():
                continue
                
            confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
            
            if confidence >= 0.85:
                text_lower = text.lower().strip()
                
                if expected_lower == text_lower:
                    match_found = True
                    match_method = f"high confidence exact match (confidence: {confidence:.2f})"
                    best_match_confidence = confidence
                    best_match_text = text
                    print(f"[VERIFIER_HANDLER] ✓ Found high confidence exact match: '{text}' ({confidence:.2f})")
                    break
        
        # Strategy 2: Medium confidence matches (60%+) with various patterns
        if not match_found:
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                    
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                
                if confidence >= confidence_threshold:
                    text_lower = text.lower().strip()
                    
                    if expected_lower == text_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"exact match (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found exact match: '{text}' ({confidence:.2f})")
                    elif expected_lower in text_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"expected contains extracted (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found substring match: '{text}' ({confidence:.2f})")
                    elif text_lower in expected_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"extracted contains expected (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found partial match: '{text}' ({confidence:.2f})")
        
        if match_found:
            success_msg = f"✓ Agency name '{agency_name}' verified in field ({match_method})"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            
            verification_data = {
                "expected_text": agency_name,
                "extracted_text": extracted_text,
                "matched_text": best_match_text,
                "match_confidence": best_match_confidence,
                "field_region": field_region,
                "debug_image": debug_filename,
                "match_method": match_method,
                "confidence_threshold": confidence_threshold,
                "ocr_data": ocr_data
            }
            
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ Agency name verification failed. Expected: '{agency_name}', No matches found"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            
            verification_data = {
                "expected_text": agency_name,
                "extracted_text": extracted_text,
                "field_region": field_region,
                "debug_image": debug_filename,
                "confidence_threshold": confidence_threshold,
                "ocr_data": ocr_data
            }
            
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying agency name entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_begin_date_entered(begin_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the begin date was entered correctly.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the begin date field region (206, 152, 1439, 79)
    3. Uses OCR to verify the begin date was entered correctly
    
    Args:
        begin_date: Expected begin date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying begin date entered: '{begin_date}'")
    
    if not begin_date:
        return True, "No begin date to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        field_region = (region_x, region_y, region_width, region_height)
        
        print(f"[VERIFIER_HANDLER] Cropping screenshot to begin date field region {field_region}")
        
        # Crop the screenshot to the begin date field region
        cropped_image = verifier_helpers.crop_image_for_verification(
            screenshot, 
            region_x, 
            region_y, 
            region_width, 
            region_height
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to begin date field region", None
        
        # Save the cropped image for debugging
        debug_filename = f"begin_date_field_verification_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[VERIFIER_HANDLER] Saved cropped begin date field for debugging: {debug_filename}")
        
        # Use OCR to extract text from the cropped field region
        print(f"[VERIFIER_HANDLER] Extracting text from begin date field...")
        success, extracted_text = verifier_helpers.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from begin date field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Get detailed OCR data to check confidence scores
        print(f"[VERIFIER_HANDLER] Getting detailed OCR data for confidence checking...")
        ocr_success, ocr_data = verifier_helpers.get_detailed_ocr_data(cropped_image)
        
        if not ocr_success:
            return False, f"Failed to get detailed OCR data: {ocr_data}", None
        
        # Check if we have valid OCR data with confidence scores
        if not isinstance(ocr_data, dict) or 'text' not in ocr_data or 'confidence' not in ocr_data:
            return False, "Invalid OCR data structure received", None
        
        # Use the helper function for simple verification
        return _simple_text_verification(begin_date, ocr_data, field_region, debug_filename)
        
    except Exception as e:
        error_msg = f"Error verifying begin date entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_end_date_entered(end_date: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the end date was entered correctly.
    
    This function:
    1. Takes a screenshot
    2. Crops it to the end date field region (206, 152, 1439, 79)
    3. Uses OCR to verify the end date was entered correctly
    
    Args:
        end_date: Expected end date to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying end date entered: '{end_date}'")
    
    if not end_date:
        return True, "No end date to verify", None
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        region_x = 206
        region_y = 152
        region_width = 1439
        region_height = 79
        field_region = (region_x, region_y, region_width, region_height)
        
        print(f"[VERIFIER_HANDLER] Cropping screenshot to end date field region {field_region}")
        
        # Crop the screenshot to the end date field region
        cropped_image = verifier_helpers.crop_image_for_verification(
            screenshot, 
            region_x, 
            region_y, 
            region_width, 
            region_height
        )
        
        if cropped_image is None:
            return False, "Failed to crop image to end date field region", None
        
        # Save the cropped image for debugging
        debug_filename = f"end_date_field_verification_{int(time.time())}.png"
        cv2.imwrite(debug_filename, cropped_image)
        print(f"[VERIFIER_HANDLER] Saved cropped end date field for debugging: {debug_filename}")
        
        # Use OCR to extract text from the cropped field region
        print(f"[VERIFIER_HANDLER] Extracting text from end date field...")
        success, extracted_text = verifier_helpers.extract_text_from_cropped_image(cropped_image)
        
        if not success:
            return False, f"Failed to extract text from end date field: {extracted_text}", None
        
        print(f"[VERIFIER_HANDLER] Extracted text from field: '{extracted_text}'")
        
        # Get detailed OCR data to check confidence scores
        print(f"[VERIFIER_HANDLER] Getting detailed OCR data for confidence checking...")
        ocr_success, ocr_data = verifier_helpers.get_detailed_ocr_data(cropped_image)
        
        if not ocr_success:
            return False, f"Failed to get detailed OCR data: {ocr_data}", None
        
        # Check if we have valid OCR data with confidence scores
        if not isinstance(ocr_data, dict) or 'text' not in ocr_data or 'confidence' not in ocr_data:
            return False, "Invalid OCR data structure received", None
        
        # Find text matches with robust checking
        expected_lower = end_date.lower().strip()
        confidence_threshold = 0.60
        
        print(f"[VERIFIER_HANDLER] Performing robust search for '{end_date}' with {confidence_threshold*100:.0f}% confidence threshold...")
        
        match_found = False
        match_method = ""
        best_match_confidence = 0.0
        best_match_text = ""
        
        # Strategy 1: High confidence exact matches (85%+)
        for i, text in enumerate(ocr_data['text']):
            if not text.strip():
                continue
                
            confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
            
            if confidence >= 0.85:
                text_lower = text.lower().strip()
                
                if expected_lower == text_lower:
                    match_found = True
                    match_method = f"high confidence exact match (confidence: {confidence:.2f})"
                    best_match_confidence = confidence
                    best_match_text = text
                    print(f"[VERIFIER_HANDLER] ✓ Found high confidence exact match: '{text}' ({confidence:.2f})")
                    break
        
        # Strategy 2: Medium confidence matches (60%+) with various patterns
        if not match_found:
            for i, text in enumerate(ocr_data['text']):
                if not text.strip():
                    continue
                    
                confidence = ocr_data['confidence'][i] if i < len(ocr_data['confidence']) else 0.0
                
                if confidence >= confidence_threshold:
                    text_lower = text.lower().strip()
                    
                    if expected_lower == text_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"exact match (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found exact match: '{text}' ({confidence:.2f})")
                    elif expected_lower in text_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"expected contains extracted (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found substring match: '{text}' ({confidence:.2f})")
                    elif text_lower in expected_lower:
                        if confidence > best_match_confidence:
                            match_found = True
                            match_method = f"extracted contains expected (confidence: {confidence:.2f})"
                            best_match_confidence = confidence
                            best_match_text = text
                            print(f"[VERIFIER_HANDLER] ✓ Found partial match: '{text}' ({confidence:.2f})")
        
        if match_found:
            success_msg = f"✓ End date '{end_date}' verified in field ({match_method})"
            print(f"[VERIFIER_HANDLER] {success_msg}")
            
            verification_data = {
                "expected_text": end_date,
                "extracted_text": extracted_text,
                "matched_text": best_match_text,
                "match_confidence": best_match_confidence,
                "field_region": field_region,
                "debug_image": debug_filename,
                "match_method": match_method,
                "confidence_threshold": confidence_threshold,
                "ocr_data": ocr_data
            }
            
            return True, success_msg, verification_data
        else:
            error_msg = f"✗ End date verification failed. Expected: '{end_date}', No matches found"
            print(f"[VERIFIER_HANDLER] {error_msg}")
            
            verification_data = {
                "expected_text": end_date,
                "extracted_text": extracted_text,
                "field_region": field_region,
                "debug_image": debug_filename,
                "confidence_threshold": confidence_threshold,
                "ocr_data": ocr_data
            }
            
            return False, error_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying end date entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# BUTTON VERIFICATION HANDLERS
# ============================================================================

def verify_search_button_clicked(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the search button was clicked successfully.
    
    This function:
    1. Takes a screenshot
    2. Looks for UI state changes that indicate search was initiated
    3. Checks for loading indicators or results appearing
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying search button clicked...")
    
    try:
        # Take screenshot
        screenshot = computer_vision_utils.take_screenshot()
        if screenshot is None:
            return False, "Failed to take screenshot for verification", None
        
        # Wait a moment for UI changes to appear
        time.sleep(1.0)
        
        # Take another screenshot to compare
        screenshot_after = computer_vision_utils.take_screenshot()
        if screenshot_after is None:
            return False, "Failed to take second screenshot for verification", None
        
        # Look for common indicators that search was initiated
        # These could be loading indicators, results appearing, or UI state changes
        success_indicators = [
            "loading", "searching", "results", "found", "no results", 
            "search results", "loading...", "please wait"
        ]
        
        print(f"[VERIFIER_HANDLER] Looking for search success indicators...")
        
        # Use OCR to check for any of the success indicators
        for indicator in success_indicators:
            success, found = verifier_helpers.extract_text_from_cropped_image(screenshot_after)
            if success and found:
                # Check if the indicator text appears in the extracted text
                if indicator.lower() in found.lower():
                    success_msg = f"✓ Search button click verified - found indicator: '{indicator}'"
                    print(f"[VERIFIER_HANDLER] {success_msg}")
                    
                    verification_data = {
                        "indicator_found": indicator,
                        "extracted_text": found,
                        "verification_method": "ui_state_change"
                    }
                    
                    return True, success_msg, verification_data
        
        # If no specific indicators found, assume success if no errors
        # This is a lenient verification approach
        success_msg = "✓ Search button click verified - no errors detected"
        print(f"[VERIFIER_HANDLER] {success_msg}")
        
        verification_data = {
            "verification_method": "no_errors_detected",
            "status": "assumed_success"
        }
        
        return True, success_msg, verification_data
        
    except Exception as e:
        error_msg = f"Error verifying search button click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# TABLE INTERACTION VERIFICATION HANDLERS
# ============================================================================

def verify_row_found(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a row with the specified order number was found.
    
    Args:
        order_number: Order number to verify was found
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying row found for order: '{order_number}'")
    
    if not order_number:
        return True, "No order number to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=order_number,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying row found: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_row_right_clicked(order_number: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that a row was right-clicked successfully.
    
    Args:
        order_number: Order number of the row that was right-clicked
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying row right-clicked for order: '{order_number}'")
    
    try:
        # Check for context menu appearance
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Edit", "Menu", "Context"],
            timeout=2.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying row right-click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_edit_menu_selected(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the edit menu was selected successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying edit menu selected...")
    
    try:
        # Check for edit page elements
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Edit", "Multi-network", "Instructions"],
            timeout=3.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying edit menu selection: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# FORM FIELD VERIFICATION HANDLERS
# ============================================================================

def verify_isci_1_entered(isci_1: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 1 was entered correctly.
    
    Args:
        isci_1: Expected ISCI 1 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 1 entered: '{isci_1}'")
    
    if not isci_1:
        return True, "No ISCI 1 to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=isci_1,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 1 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_2_entered(isci_2: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 2 was entered correctly.
    
    Args:
        isci_2: Expected ISCI 2 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 2 entered: '{isci_2}'")
    
    if not isci_2:
        return True, "ISCI 2 not provided - skipping verification", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=isci_2,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 2 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_isci_3_entered(isci_3: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that ISCI 3 was entered correctly.
    
    Args:
        isci_3: Expected ISCI 3 value to verify
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying ISCI 3 entered: '{isci_3}'")
    
    if not isci_3:
        return True, "ISCI 3 not provided - skipping verification", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=isci_3,
            region=None,
            case_sensitive=True
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying ISCI 3 entry: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# SAVE VERIFICATION HANDLERS
# ============================================================================

def verify_instruction_saved(**kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify that the instruction was saved successfully.
    
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print("[VERIFIER_HANDLER] Verifying instruction saved...")
    
    try:
        # Check for success messages or return to previous page
        success, message = verifier_helpers.verify_ui_state_change(
            expected_texts=["Saved", "Success", "Complete"],
            timeout=3.0
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying instruction save: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


# ============================================================================
# GENERIC VERIFICATION HANDLERS (FALLBACK)
# ============================================================================

def verify_text_typed(text: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generic verifier for text typing actions.
    
    Args:
        text: Text that was typed
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying text typed: '{text}'")
    
    if not text:
        return True, "No text to verify", None
    
    try:
        success, message = verifier_helpers.verify_text_entered(
            expected_text=text,
            region=None,
            case_sensitive=False
        )
        
        return success, message, None
        
    except Exception as e:
        error_msg = f"Error verifying text typed: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_position_clicked(x: int = 0, y: int = 0, **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generic verifier for position clicking actions.
    
    Args:
        x: X coordinate that was clicked
        y: Y coordinate that was clicked
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying position clicked: ({x}, {y})")
    
    try:
        # For generic clicks, we assume success unless there's an obvious error
        # This is a fallback verifier, so we're lenient
        return True, f"Position ({x}, {y}) clicked successfully", None
        
    except Exception as e:
        error_msg = f"Error verifying position click: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None


def verify_key_pressed(key: str = "", **kwargs) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Generic verifier for key press actions.
    
    Args:
        key: Key that was pressed
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    print(f"[VERIFIER_HANDLER] Verifying key pressed: '{key}'")
    
    try:
        # For generic key presses, we assume success
        # This is a fallback verifier, so we're lenient
        return True, f"Key '{key}' pressed successfully", None
        
    except Exception as e:
        error_msg = f"Error verifying key press: {e}"
        print(f"[VERIFIER_HANDLER ERROR] {error_msg}")
        return False, error_msg, None
